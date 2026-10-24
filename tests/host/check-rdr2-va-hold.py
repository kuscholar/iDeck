#!/usr/bin/env python3
"""Social Club layout 2 with room for RDR2.exe's 8960 MB reserve (virtual_ios.c
env MADEIRA_RDR2_VA_HOLD); no Wine runs.

RDR2.exe reserves 8960 MB in one block as it starts; with layout 2 as GTA V
uses it the band had no gap that large (build 457, log 2026-10-08 21:20:59).
Compiles the layout 2 slot table, ios_sc2_hold / ios_sc2_unhold /
ios_sc2_boot_holds and the jumbo holdback (ios_jumbo_holdback_init / take)
against a fake Mach map that starts with the app's PROT_NONE hold over
[0x7000000000, +4 GB), and checks:
  - without the env layout 2 holds exactly what it held before, prints the
    same line, and no holdback exists;
  - with it: libcef.dll's pools [0x7000000000, +256 MB) taken over from the
    app's hold and the rest of that hold released to the furniture (floor
    0x7010000000); chrome_elf.dll's metadata [0x7400000000, +6400 MB),
    libcef.dll's metadata [0x7590000000, +1 GB); Oilpan's slot 1 GB (the FEX
    arena then starts at 0x7c40000000); chrome_elf.dll's pools where they
    were; [0x75d0000000, 0x7800000000) held and registered
    as the jumbo holdback, which an 8960 MB request gets once and a smaller
    one (Social Club's hinted 1 GB) never;
  - a mapping that is not the app's hold stays where it is (no release);
  - a jumbo-mb in madeira.cfg does not replace that hold;
  - a mapping in the way leaves no holdback and says so, the slots stay held;
  - a slot released and held again goes back to the same place;
  - another layout ignores the env;
and textually that the grant path takes the slot geometry from the table.
Needs python3 and a C compiler (CC, default cc).
"""
from pathlib import Path
import os
import re
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
src = (root / 'build/ntdll-unix/virtual_ios.c').read_text()


def between(start, end_marker_after):
    a = src.index(start)
    b = src.index(end_marker_after, a)
    return src[a:src.index('\n}\n', b) + 3]


defines = '\n'.join(re.findall(r'^#define IOS_SC(?:2_[A-Z0-9_]+|_ARENA_BASE)\s.*$', src, re.M))
jumbo = between('static uintptr_t ios_jumbo_hold_base;', 'static uintptr_t ios_jumbo_holdback_take( size_t size )\n{')
slots = between('enum { IOS_SC2_NONE,', 'static void ios_sc2_rdr2_geometry(void)\n{')
holds = between('/* Hold slot k natively', 'static void ios_sc2_boot_holds(void)\n{')

harness = r'''
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <stdarg.h>
#include <errno.h>
#include <sys/mman.h>
typedef int kern_return_t;
typedef unsigned int mach_msg_type_number_t, natural_t;
typedef int mach_port_t, vm_prot_t, vm_inherit_t;
typedef uint64_t mach_vm_address_t, mach_vm_size_t;
typedef int *vm_region_info_t, *vm_region_recurse_info_t, *task_info_t;
typedef struct { int protection; } vm_region_basic_info_data_64_t;
typedef struct { int protection; } vm_region_submap_info_data_64_t;
typedef struct { unsigned long long max_address; } task_vm_info_data_t;
#define KERN_SUCCESS 0
#define KERN_NO_SPACE 3
#define MACH_PORT_NULL 0
#define MEMORY_OBJECT_NULL 0
#define VM_FLAGS_FIXED 0
#define VM_PROT_NONE 0
#define VM_PROT_ALL 7
#define VM_INHERIT_COPY 1
#define VM_REGION_BASIC_INFO_64 9
#define VM_REGION_BASIC_INFO_COUNT_64 1
#define VM_REGION_SUBMAP_INFO_COUNT_64 1
#define TASK_VM_INFO 22
#define TASK_VM_INFO_COUNT 1
static int mach_task_self(void) { return 1; }

/* the fake map: sorted, non-overlapping regions */
struct reg { uint64_t lo, hi; int prot; };
static struct reg map[64];
static int map_n;
static void map_add(uint64_t lo, uint64_t hi, int prot)
{
    int i = map_n++;
    while (i > 0 && map[i - 1].lo > lo) { map[i] = map[i - 1]; i--; }
    map[i].lo = lo; map[i].hi = hi; map[i].prot = prot;
}
static int map_overlaps(uint64_t lo, uint64_t hi)
{
    int i;
    for (i = 0; i < map_n; i++) if (map[i].lo < hi && lo < map[i].hi) return 1;
    return 0;
}
static void map_remove(uint64_t lo, uint64_t hi)
{
    struct reg keep[64];
    int i, n = 0;
    for (i = 0; i < map_n; i++)
    {
        if (map[i].hi <= lo || map[i].lo >= hi) { keep[n++] = map[i]; continue; }
        if (map[i].lo < lo) { keep[n] = map[i]; keep[n].hi = lo; n++; }
        if (map[i].hi > hi) { keep[n] = map[i]; keep[n].lo = hi; n++; }
    }
    memcpy(map, keep, sizeof(keep[0]) * n);
    map_n = n;
}
static kern_return_t mach_vm_map(int t, mach_vm_address_t *a, mach_vm_size_t s, mach_vm_size_t mask, int flags,
                                 int obj, uint64_t off, int copy, vm_prot_t cur, vm_prot_t max, vm_inherit_t inh)
{
    (void)t; (void)mask; (void)flags; (void)obj; (void)off; (void)copy; (void)max; (void)inh;
    if (map_overlaps(*a, *a + s)) return KERN_NO_SPACE;
    map_add(*a, *a + s, cur);
    return KERN_SUCCESS;
}
static kern_return_t mach_vm_deallocate(int t, mach_vm_address_t a, mach_vm_size_t s)
{ (void)t; map_remove(a, a + s); return KERN_SUCCESS; }
static int fake_munmap(void *a, size_t s) { map_remove((uint64_t)(uintptr_t)a, (uint64_t)(uintptr_t)a + s); return 0; }
#define munmap fake_munmap
static kern_return_t mach_vm_region(int t, mach_vm_address_t *a, mach_vm_size_t *s, int f, vm_region_info_t i,
                                    mach_msg_type_number_t *c, mach_port_t *o)
{
    int k;
    (void)t; (void)f; (void)c; (void)o;
    for (k = 0; k < map_n; k++)
        if (map[k].hi > *a)
        {
            *a = map[k].lo; *s = map[k].hi - map[k].lo;
            ((vm_region_basic_info_data_64_t *)i)->protection = map[k].prot;
            return KERN_SUCCESS;
        }
    return 1;
}
static kern_return_t mach_vm_region_recurse(int t, mach_vm_address_t *a, mach_vm_size_t *s, natural_t *d,
                                            vm_region_recurse_info_t i, mach_msg_type_number_t *c)
{ (void)t; (void)a; (void)s; (void)d; (void)i; (void)c; return 1; }
static kern_return_t task_info(int t, int f, task_info_t out, mach_msg_type_number_t *c)
{ (void)t; (void)f; (void)c; ((task_vm_info_data_t *)out)->max_address = 0x8000000000ull; return KERN_SUCCESS; }
static void *anon_mmap_tryfixed(void *start, size_t size, int prot, int flags)
{ (void)size; (void)prot; (void)flags; return start; }
static int cfg_jumbo_mb;
static int madeira_cfg_int(const char *key, int def) { return !strcmp(key, "jumbo-mb") ? cfg_jumbo_mb : def; }
static int ios_sc_layout_mode = 2;
static int ios_sc2_rdr2;
static int ios_sc_layout(void) { return ios_sc_layout_mode; }
static char out[1 << 16]; static size_t outn;
static int fake_dprintf(int fd, const char *fmt, ...)
{
    va_list ap;
    int w;
    (void)fd;
    va_start(ap, fmt);
    w = vsnprintf(out + outn, sizeof out - outn, fmt, ap);
    va_end(ap);
    if (w > 0) outn += w;
    return w;
}
#define dprintf fake_dprintf
''' + defines + '\n' + jumbo + slots + holds + r'''
#undef dprintf
#undef munmap
static int fail(const char *what)
{
    int i;
    printf("%s", out);
    for (i = 0; i < map_n; i++) printf("  region [0x%llx,0x%llx) prot=%d\n", (unsigned long long)map[i].lo,
                                       (unsigned long long)map[i].hi, map[i].prot);
    printf("FAIL: %s\n", what);
    return 1;
}
static int has(const char *needle) { return strstr(out, needle) != NULL; }
static int region(uint64_t lo, uint64_t hi)
{
    int i;
    for (i = 0; i < map_n; i++) if (map[i].lo == lo && map[i].hi == hi) return 1;
    return 0;
}
static int covered(uint64_t lo, uint64_t hi)   /* [lo, hi) mapped without gaps */
{
    int i;
    for (i = 0; i < map_n && lo < hi; i++)
        if (map[i].lo <= lo && map[i].hi > lo) lo = map[i].hi;
    return lo >= hi;
}
#define GB(x) ((uint64_t)(x) << 30)
#define ALL_HELD ((1u << IOS_SC2_E) | (1u << IOS_SC2_L) | (1u << IOS_SC2_J2) | (1u << IOS_SC2_J2L) | (1u << IOS_SC2_OILPAN))

int main(int argc, char **argv)
{
    const char *s = argc > 1 ? argv[1] : "";

    map_add(0x7000000000ull, 0x7100000000ull, 0);          /* the app's hold (StikJITHelper.swift) */
    map_add(0x7900000000ull, 0x7952848000ull, 3);          /* the JIT pool's RW alias */
    if (!strcmp(s, "off"))
    {
        ios_sc2_boot_holds();
        if (ios_sc2_held != ALL_HELD || ios_sc_layout_mode != 2 || ios_sc2_rdr2) return fail("layout 2 is not held as before");
        if (!has("[sc-cef] layout 2: held libcef.dll's pools [0x7000000000,+4 GB), PartitionAlloc metadata of chrome_elf.dll "
                 "[0x7400000000,+8 GB) and libcef.dll [0x7600000000,+8 GB), chrome_elf.dll's pools [0x7800000000,+4 GB), Oilpan "
                 "[0x7c00000000,+4 GB); RW alias 0x7900000000, V8 cage 0x7a00000000, furniture floor 0x7100000000\n"))
            return fail("the layout 2 line changed");
        if (!region(0x7400000000ull, 0x7600000000ull) || !region(0x7600000000ull, 0x7800000000ull) ||
            !region(0x7800000000ull, 0x7900000000ull) || !region(0x7c00000000ull, 0x7d00000000ull) ||
            !region(0x7000000000ull, 0x7100000000ull))
            return fail("a slot is not where layout 2 puts it");
        if (ios_jumbo_hold_size || has("MADEIRA_RDR2_VA_HOLD")) return fail("a holdback without the env");
        if (ios_sc2_slots[IOS_SC2_L].size != GB(4) || ios_sc2_slots[IOS_SC2_J2L].base != 0x7600000000ull ||
            ios_sc2_slots[IOS_SC2_J2L].size != GB(8) || ios_sc2_slots[IOS_SC2_J2].size != GB(8) ||
            ios_sc2_slots[IOS_SC2_OILPAN].size != GB(4) || ios_sc2_floor != 0x7100000000ull ||
            ios_sc2_arena_lo != 0x7d00000000ull)
            return fail("the slot table changed without the env");
        printf("PASS: without MADEIRA_RDR2_VA_HOLD layout 2 holds and prints exactly what it did\n");
        return 0;
    }
    if (!strcmp(s, "on"))
    {
        ios_sc2_boot_holds();
        if (ios_sc2_held != ALL_HELD || !ios_sc2_rdr2) return fail("the variant did not hold every slot");
        if (ios_sc2_slots[IOS_SC2_L].base != 0x7000000000ull || ios_sc2_slots[IOS_SC2_L].size != (256ull << 20) ||
            ios_sc2_slots[IOS_SC2_J2L].base != 0x7590000000ull || ios_sc2_slots[IOS_SC2_J2L].size != GB(1) ||
            ios_sc2_slots[IOS_SC2_J2].base != 0x7400000000ull || ios_sc2_slots[IOS_SC2_J2].size != 0x190000000ull ||
            ios_sc2_slots[IOS_SC2_E].base != 0x7800000000ull || ios_sc2_slots[IOS_SC2_E].size != GB(4) ||
            ios_sc2_slots[IOS_SC2_OILPAN].base != 0x7c00000000ull || ios_sc2_slots[IOS_SC2_OILPAN].size != GB(1) ||
            ios_sc2_arena_lo != 0x7c40000000ull)
            return fail("the variant geometry is wrong");
        if (!region(0x7c00000000ull, 0x7c40000000ull)) return fail("Oilpan's 1 GB slot is not held");
        if (!region(0x7400000000ull, 0x7590000000ull) || !region(0x7590000000ull, 0x75d0000000ull) ||
            !region(0x75d0000000ull, 0x7800000000ull))
            return fail("a metadata slot or the RDR2 hold is not where it belongs");
        if (!region(0x7000000000ull, 0x7010000000ull) || covered(0x7010000000ull, 0x7010001000ull) ||
            covered(0x70fffff000ull, 0x7100000000ull) || ios_sc2_floor != 0x7010000000ull)
            return fail("the app's hold was not cut down to libcef.dll's 256 MB, or the floor did not move");
        if (!has("[sc-cef] MADEIRA_RDR2_VA_HOLD: [0x7010000000,0x7100000000) released from the app's hold; "
                 "the furniture starts at 0x7010000000 (3840 MB more)"))
            return fail("no release line");
        if (ios_jumbo_hold_base != 0x75d0000000ull || ios_jumbo_hold_size != 0x230000000ull || ios_jumbo_hold_keep)
            return fail("the RDR2 hold is not the jumbo holdback");
        if (!has("[sc-cef] layout 2 with MADEIRA_RDR2_VA_HOLD: held libcef.dll's pools [0x7000000000,+256 MB) and its "
                 "PartitionAlloc metadata [0x7590000000,+1024 MB), chrome_elf.dll's metadata [0x7400000000,+6400 MB) and "
                 "pools [0x7800000000,+4 GB), Oilpan [0x7c00000000,+1024 MB)"))
            return fail("no variant line");
        if (!has("[sc-cef] MADEIRA_RDR2_VA_HOLD: [0x75d0000000,0x7800000000) held for one 8960 MB reserve"))
            return fail("no hold line");
        if (has("[sc-cef] layout 2: held libcef.dll's pools [0x7000000000,+4 GB)")) return fail("the layout 2 line is misleading here");
        /* the slots are released for their grants and held again when a dead helper's grant goes */
        ios_sc2_unhold(IOS_SC2_L);
        ios_sc2_unhold(IOS_SC2_J2L);
        if (covered(0x7000000000ull, 0x7000001000ull) || covered(0x7590000000ull, 0x7590001000ull))
            return fail("released slots are still mapped");
        if (!ios_sc2_hold(IOS_SC2_J2L) || !region(0x7590000000ull, 0x75d0000000ull)) return fail("a re-hold went elsewhere");
        if (!ios_sc2_hold(IOS_SC2_L) || !region(0x7000000000ull, 0x7010000000ull)) return fail("libcef's re-hold went elsewhere");
        if (ios_jumbo_holdback_take(0x40000000) || ios_jumbo_hold_size != 0x230000000ull)
            return fail("a 1 GB request (Social Club's hinted one) got the hold");
        printf("PASS: with MADEIRA_RDR2_VA_HOLD: libcef's pools 256 MB, furniture from 0x7010000000, chrome_elf metadata "
               "6400 MB, libcef metadata 1 GB, [0x75d0000000,0x7800000000) held as the jumbo holdback\n");
        return 0;
    }
    if (!strcmp(s, "take"))
    {
        ios_sc2_boot_holds();
        if (ios_jumbo_holdback_take(0x230000001ull)) return fail("a request larger than the hold took it");
        if (ios_jumbo_holdback_take(0x200000000ull) || ios_jumbo_holdback_take(0x22fff0000ull))
            return fail("a request smaller than 8960 MB took the hold");
        if (ios_jumbo_holdback_take(0x230000000ull) != 0x75d0000000ull) return fail("RDR2's 8960 MB does not get the hold");
        if (covered(0x75d0000000ull, 0x75d0001000ull) || covered(0x77ffff0000ull, 0x7800000000ull))
            return fail("the hold is still mapped after the take");
        if (!has("[jumbo-hold] ml996 releasing the holdback 0x75d0000000 +8960 MB for a 8960 MB request")) return fail("no release line");
        if (ios_jumbo_holdback_take(0x230000000ull)) return fail("the hold was given twice");
        printf("PASS: the hold goes once, only to an 8960 MB request, and is unmapped first\n");
        return 0;
    }
    if (!strcmp(s, "jumbo-mb"))
    {
        ios_sc2_boot_holds();
        cfg_jumbo_mb = 9856;
        ios_jumbo_holdback_init();
        if (ios_jumbo_hold_base != 0x75d0000000ull || ios_jumbo_hold_size != 0x230000000ull) return fail("jumbo-mb replaced the hold");
        if (!has("[jumbo-hold] jumbo-mb = 9856 ignored: 0x75d0000000 +8960 MB is already held (MADEIRA_RDR2_VA_HOLD)"))
            return fail("no ignored line");
        printf("PASS: a jumbo-mb in madeira.cfg leaves the RDR2 hold alone\n");
        return 0;
    }
    if (!strcmp(s, "blocked"))
    {
        map_add(0x7700000000ull, 0x7700004000ull, 3);
        ios_sc2_boot_holds();
        if (ios_jumbo_hold_size || ios_jumbo_hold_base) return fail("a hold over a mapping");
        if (!has("[sc-cef] MADEIRA_RDR2_VA_HOLD: could not hold [0x75d0000000,0x7800000000) (kr=3, holdback 0 MB)"))
            return fail("no could-not-hold line");
        if (ios_sc2_held != ALL_HELD || ios_sc_layout_mode != 2) return fail("the slots were dropped with the hold");
        if (!region(0x7700000000ull, 0x7700004000ull) || covered(0x7600000000ull, 0x7700000000ull))
            return fail("the blocked hold left something mapped or removed the mapping in its way");
        printf("PASS: a mapping in the way: no holdback, a line, the slots stay held\n");
        return 0;
    }
    if (!strcmp(s, "noapp"))
    {
        map_remove(0x7000000000ull, 0x7100000000ull);
        ios_sc2_boot_holds();
        if (ios_sc2_held != ALL_HELD || !region(0x7000000000ull, 0x7010000000ull) || covered(0x7010000000ull, 0x7010001000ull))
            return fail("without the app's hold libcef.dll's pools are not mapped fresh");
        if (!has("[0x7010000000,0x7100000000) was free; the furniture starts at 0x7010000000")) return fail("no was-free line");
        printf("PASS: without the app's hold libcef.dll's pools are mapped fresh and the furniture range was free\n");
        return 0;
    }
    if (!strcmp(s, "foreign"))
    {
        /* something other than the app's PROT_NONE hold sits in the range the furniture would get */
        map_remove(0x7000000000ull, 0x7100000000ull);
        map_add(0x7000000000ull, 0x7010000000ull, 0);
        map_add(0x7050000000ull, 0x7050004000ull, 3);
        ios_sc2_boot_holds();
        if (!region(0x7050000000ull, 0x7050004000ull)) return fail("a foreign mapping was removed");
        if (!has("[0x7010000000,0x7100000000) is partly mapped by something else")) return fail("no partly-mapped line");
        printf("PASS: a mapping that is not the app's hold stays where it is\n");
        return 0;
    }
    if (!strcmp(s, "layout1"))
    {
        ios_sc_layout_mode = 1;
        ios_sc2_boot_holds();
        if (ios_sc2_rdr2 || ios_sc2_held || ios_jumbo_hold_size || outn) return fail("another layout used the env");
        if (ios_sc2_slots[IOS_SC2_L].size != GB(4)) return fail("the table changed in another layout");
        printf("PASS: another layout ignores MADEIRA_RDR2_VA_HOLD\n");
        return 0;
    }
    printf("unknown scenario %s\n", s);
    return 2;
}
'''

cc = os.environ.get('CC', 'cc')
with tempfile.TemporaryDirectory(prefix='madeira-rdr2-va-hold-') as directory:
    c = Path(directory) / 'h.c'
    exe = Path(directory) / 'h'
    c.write_text(harness)
    build = subprocess.run([cc, '-std=gnu11', '-Wall', '-Werror', '-Wno-unused-function', '-Wno-unused-variable',
                            '-Wno-unused-but-set-variable', '-fsanitize=address,undefined', '-o', str(exe), str(c)],
                           capture_output=True, text=True)
    assert build.returncode == 0, build.stdout + build.stderr
    for scenario in ('off', 'on', 'take', 'jumbo-mb', 'blocked', 'noapp', 'foreign', 'layout1'):
        env = {k: v for k, v in os.environ.items() if not k.startswith('MADEIRA_')}
        if scenario != 'off':
            env['MADEIRA_RDR2_VA_HOLD'] = '1'
        run = subprocess.run([str(exe), scenario], capture_output=True, text=True, env=env)
        print(run.stdout, end='')
        assert run.returncode == 0, (scenario, run.stdout + run.stderr)

route = src[src.index('static int ios_sc2_route('):]
route = route[:route.index('\n}\n')]
assert 'base = ios_sc2_slots[k].base;' in route and 's = ios_sc2_slots[k].size;' in route, \
    'the grant path takes the slot geometry from the table'
boot = src[src.index('static void ios_sc2_boot_holds(void)\n{'):]
boot = boot[:boot.index('\n}\n')]
assert boot.index('if (ios_sc_layout() != 2) return;') < boot.index('if (ios_sc2_rdr2_hold_enabled()) ios_sc2_rdr2_geometry();') \
    < boot.index('for (k = IOS_SC2_E; k <= IOS_SC2_OILPAN; k++)'), 'the geometry is set for layout 2 only, before any hold'
print('PASS: the grant path takes the slot geometry from the table, set for layout 2 only before any hold')
