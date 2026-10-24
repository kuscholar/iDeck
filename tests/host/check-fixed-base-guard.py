#!/usr/bin/env python3
"""A version query cannot use up the fixed-base window; no Wine runs.

In every GTA V Enhanced session (builds 449-456) the Rockstar Games
Launcher's resource-only view of Social-Club-Setup.exe (0x7a7d000 at its
ImageBase 0x140000000) took the reserved executable window; SocialClubHelper.exe
then landed at 0x141c00000 and later maps at 0x140000000 were REFUSED c0000018.
RDR2.exe has no relocations and can only run there.
Compiles build/ntdll-unix/virtual_ios.c's window code (ios_exe_win_init through
ios_exe_win_commit_claim) against a fake vm_deallocate and checks:
  - without env MADEIRA_FIXED_BASE_GUARD a resource-only view still takes the
    window, as before;
  - with it set to 1, a resource-only view of 64 MB or more takes neither the
    window nor an interval held for the next generation; the main image after
    it does, and its claim commits;
  - a small resource-only view keeps the 64 MB floor's own line, and a small
    one with stripped relocations is declined by the guard;
  - the guard line stops after 8;
and textually that virtual_map_section sets and clears the flag around
virtual_map_image and that the check sits between the floor and the release.
Needs python3 and a C compiler (CC, default cc).
"""
from pathlib import Path
import os
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
src = (root / 'build/ntdll-unix/virtual_ios.c').read_text()

start = src.index('static uint64_t ios_exe_win_base, ios_exe_win_size;')
commit = src.index('void ios_exe_win_commit_claim( void *base, size_t size, int mapped )\n{')
chunk = src[start:src.index('\n}\n', commit) + 3]

harness = r'''
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <stdarg.h>
#include <fcntl.h>
#include <unistd.h>
#include <pthread.h>
#include <sys/mman.h>
typedef int kern_return_t;
typedef uintptr_t vm_address_t;
typedef size_t vm_size_t;
#define KERN_SUCCESS 0
static unsigned mach_task_self(void) { return 1; }
static int dealloc_n; static vm_address_t dealloc_addr; static vm_size_t dealloc_size;
static kern_return_t vm_deallocate(unsigned task, vm_address_t a, vm_size_t s)
{ (void)task; dealloc_n++; dealloc_addr = a; dealloc_size = s; return KERN_SUCCESS; }
static int release_notes;
static void ios_va_release_note(void) { release_notes++; }
static char out[1 << 16]; static size_t outn;
static int fake_dprintf(int fd, const char *f, ...)
{ va_list ap; int w; (void)fd; va_start(ap, f); w = vsnprintf(out + outn, sizeof out - outn, f, ap); va_end(ap); if (w > 0) outn += w; return w; }
#define dprintf fake_dprintf
''' + chunk + r'''
#undef dprintf
static void *anon_mmap_tryfixed(void *start, size_t size, int prot, int flags)
{ (void)size; (void)prot; (void)flags; return start; }

#define WIN ((const void *)0x140000000ull)
static int fail(const char *what) { printf("%s\nFAIL: %s\n", out, what); return 1; }
static int count(const char *needle) { int n = 0; const char *p = out; while ((p = strstr(p, needle))) { n++; p++; } return n; }

int main(int argc, char **argv)
{
    const char *s = argc > 1 ? argv[1] : "";
    int i;
    setenv("WINE_IOS_EXE_WINDOW", "140000000:8000000", 1);
    if (!strcmp(s, "off")) {
        ios_exe_win_resource_request = 1;
        if (ios_exe_win_claim(WIN, 0x7a7d000) != 1) return fail("without the guard a resource-only view no longer takes the window");
        ios_exe_win_resource_request = 0;
        if (dealloc_n != 1 || dealloc_addr != 0x140000000ull || dealloc_size != 0x8000000) return fail("the window was not released whole");
        if (!strstr(out, "ml977: RELEASED the executable window to 0x140000000+0x7a7d000")) return fail("no RELEASED line");
        if (count("[exe-window] guard:")) return fail("guard line without the guard");
        printf("PASS: without MADEIRA_FIXED_BASE_GUARD a resource-only view takes the window, as before\n");
        return 0;
    }
    setenv("MADEIRA_FIXED_BASE_GUARD", "1", 1);
    if (!strcmp(s, "main")) {
        ios_exe_win_resource_request = 1;
        if (ios_exe_win_claim(WIN, 0x7a7d000) != 0) return fail("the guard let a resource-only view take the window");
        ios_exe_win_resource_request = 0;
        if (dealloc_n || release_notes || ios_exe_win_state != 1) return fail("the window was touched by a declined view");
        if (!strstr(out, "[exe-window] guard: 0x140000000+0x7a7d000 is a resource-only image view")) return fail("no guard line");
        if (ios_exe_win_claim(WIN, 0x7528000) != 1) return fail("the main image did not get the window");
        if (dealloc_n != 1 || dealloc_size != 0x8000000 || release_notes != 1 || ios_exe_win_state != 0) return fail("the window was not released to the main image");
        ios_exe_win_commit_claim((void *)WIN, 0x7528000, 1);
        if (ios_exewin_st != IOS_EXEWIN_OWNED || ios_exe_win_img_size != 0x7528000) return fail("the main image's claim did not commit");
        if (!strstr(out, "ml988: fixed base 0x140000000+0x7528000 is OWNED by gen 1")) return fail("no OWNED line");
        printf("PASS: with the guard a resource-only view is declined and the main image after it takes the window\n");
        return 0;
    }
    if (!strcmp(s, "held")) {
        ios_exe_win_init();
        ios_exe_win_state = 0;
        ios_exe_win_held_base = (void *)WIN; ios_exe_win_held_size = 0x7528000;
        ios_exewin_st = IOS_EXEWIN_HELD_READY;
        ios_exe_win_resource_request = 1;
        if (ios_exe_win_claim(WIN, 0x7528000) != 0) return fail("the guard let a resource-only view take the held interval");
        ios_exe_win_resource_request = 0;
        if (dealloc_n || ios_exe_win_held_base != WIN || ios_exewin_st != IOS_EXEWIN_HELD_READY) return fail("the held interval was touched");
        if (ios_exe_win_claim(WIN, 0x7528000) != 1) return fail("the next generation did not get the held interval");
        if (dealloc_n != 1 || dealloc_size != 0x7528000 || ios_exewin_st != IOS_EXEWIN_CLAIMING) return fail("the held interval was not released to the next generation");
        printf("PASS: with the guard a resource-only view leaves the interval held for the next generation\n");
        return 0;
    }
    if (!strcmp(s, "small")) {
        ios_exe_win_resource_request = 1;
        if (ios_exe_win_claim(WIN, 0x2014000) != 0) return fail("a small relocatable view took the window");
        if (!strstr(out, "ml977: NOT releasing the window for 0x140000000+0x2014000")) return fail("the floor's own line is missing");
        if (count("[exe-window] guard:")) return fail("the guard spoke for a view the floor already refuses");
        ios_exe_win_stripped_request = 1;
        if (ios_exe_win_claim(WIN, 0x60000) != 0) return fail("a small stripped resource-only view took the window");
        if (!strstr(out, "[exe-window] guard: 0x140000000+0x60000")) return fail("no guard line for the small stripped view");
        ios_exe_win_resource_request = 0;
        if (ios_exe_win_claim(WIN, 0x60000) != 1) return fail("a small stripped main image lost the window");
        ios_exe_win_stripped_request = 0;
        printf("PASS: small views keep the floor's line; a small stripped view is declined, its main image is not\n");
        return 0;
    }
    if (!strcmp(s, "cap")) {
        ios_exe_win_resource_request = 1;
        for (i = 0; i < 20; i++)
            if (ios_exe_win_claim(WIN, 0x7a7d000) != 0) return fail("a repeated resource-only view took the window");
        if (count("[exe-window] guard:") != 8) return fail("the guard line is not capped at 8");
        printf("PASS: the guard line stops after 8\n");
        return 0;
    }
    printf("unknown scenario %s\n", s);
    return 2;
}
'''

cc = os.environ.get('CC', 'cc')
with tempfile.TemporaryDirectory(prefix='madeira-fixed-base-guard-') as directory:
    c = Path(directory) / 'g.c'
    exe = Path(directory) / 'g'
    c.write_text(harness)
    # ios_retire_mark, compiled along, keeps two statements on one line
    build = subprocess.run([cc, '-std=gnu11', '-Wall', '-Werror', '-Wno-unused-function', '-Wno-unused-variable',
                            '-Wno-misleading-indentation',
                            '-fsanitize=address,undefined', '-o', str(exe), str(c), '-lpthread'],
                           capture_output=True, text=True)
    assert build.returncode == 0, build.stdout + build.stderr
    for scenario in ('off', 'main', 'held', 'small', 'cap'):
        env = {k: v for k, v in os.environ.items() if k != 'MADEIRA_FIXED_BASE_GUARD'}
        run = subprocess.run([str(exe), scenario], capture_output=True, text=True, env=env)
        print(run.stdout, end='')
        assert run.returncode == 0, (scenario, run.stdout + run.stderr)

claim = src[src.index('static int ios_exe_win_claim( const void *addr, size_t size )\n{'):]
claim = claim[:claim.index('\n}\n')]
assert claim.index('"ml977: NOT releasing the window for %p+%#lx (under the 64MB floor) -- "') \
    < claim.index('if (ios_exe_win_resource_request && ios_fixed_base_guard())') \
    < claim.index('if (ios_exe_win_state != 1)'), 'the guard sits between the floor and the release'
section = src[src.index('static unsigned int virtual_map_section( HANDLE handle,'):]
section = section[:section.index('\n}\n')]
set_at = section.index('ios_exe_win_resource_request = !(access & SECTION_MAP_EXECUTE) &&')
map_at = section.index('res = virtual_map_image( handle, addr_ptr, size_ptr, shared_file,')
clear_at = section.index('ios_exe_win_resource_request = 0;')
assert set_at < map_at < clear_at, 'virtual_map_section sets the flag before virtual_map_image and clears it after'
assert '!NtCurrentTeb()->Tib.ArbitraryUserPointer;' in section[set_at:map_at], 'loader maps (ArbitraryUserPointer) are not resource-only'
print('PASS: virtual_map_section marks resource-only image views around virtual_map_image; the check sits between the floor and the release')
