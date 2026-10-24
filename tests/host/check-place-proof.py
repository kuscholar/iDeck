#!/usr/bin/env python3
"""A placement walk that found no gap is remembered (build/ntdll-unix/virtual_ios.c); no Wine runs.

Compiles the production ios_ml1027_place, its proof (ios_place_proven_full) and
the release epoch (ios_va_release_note) against a fake task map: a stub
mach_vm_region_recurse that counts its calls, task_info for the ceiling,
anon_mmap_tryfixed that inserts into the map, and a fake monotonic clock.
  - the first ask that fits nowhere walks the map and fails;
  - the same or any larger ask then fails WITHOUT a walk;
  - an ask no larger than the largest gap still walks and is placed;
  - releasing something older than the proof makes the next ask walk again;
  - releasing (all or part of) a reservation made after the proof does not --
    V8's 4 GB step reserves, releases and asks for the padded size ten times;
  - a new proof forgets those reservations, as it saw them mapped;
  - the proof growing older than IOS_PLACE_PROOF_NS walks again;
  - MADEIRA_PLACE_PROOF=0 walks every time;
and textually that every release path in the file bumps the epoch (unmap_area
unless the range is such a reservation), allocate_virtual_memory notes its
reservations, the NO GAP FITS line reports the largest gap and the walk time,
and NtRaiseException names a Chromium out-of-memory exit's request size.
Needs python3 and a C compiler (CC, default cc).
"""
from pathlib import Path
import os
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
src = (root / 'build/ntdll-unix/virtual_ios.c').read_text()
thread = (root / 'build/ntdll-unix/thread_ios.c').read_text()

epoch = src[src.index('static unsigned long ios_va_release_epoch;'):]
epoch = epoch[:epoch.index('\n}\n') + 3]
place = src[src.index('#define IOS_PLACE_PROOF_NS'):]
place = place[:place.index('\n}\n', place.index('static void *ios_ml1027_place( size_t size, int prot )')) + 3]

harness = r'''
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <time.h>
#include <sys/mman.h>
typedef uint64_t mach_vm_address_t, mach_vm_size_t;
typedef unsigned int natural_t, mach_msg_type_number_t;
typedef int kern_return_t;
typedef struct { int is_submap; } vm_region_submap_info_data_64_t;
typedef void *vm_region_recurse_info_t;
typedef struct { uint64_t max_address; } task_vm_info_data_t;
typedef void *task_info_t;
#define KERN_SUCCESS 0
#define VM_REGION_SUBMAP_INFO_COUNT_64 1
#define TASK_VM_INFO_COUNT 1
#define TASK_VM_INFO 22
#define CEIL 0x8000000000ull
#define GB (1ull << 30)
static int mach_task_self( void ) { return 1; }
static kern_return_t task_info( int t, int flavor, task_info_t info, mach_msg_type_number_t *cnt )
{ (void)t; (void)flavor; (void)cnt; ((task_vm_info_data_t *)info)->max_address = CEIL; return KERN_SUCCESS; }

static struct { uint64_t base, size; } map[64];
static int nmap;
static unsigned long walk_calls;
static kern_return_t mach_vm_region_recurse( int task, mach_vm_address_t *addr, mach_vm_size_t *size,
                                             natural_t *depth, vm_region_recurse_info_t info,
                                             mach_msg_type_number_t *cnt )
{
    int i;
    (void)task; (void)depth; (void)cnt;
    walk_calls++;
    for (i = 0; i < nmap; i++)
        if (map[i].base + map[i].size > *addr)
        {
            *addr = map[i].base; *size = map[i].size;
            ((vm_region_submap_info_data_64_t *)info)->is_submap = 0;
            return KERN_SUCCESS;
        }
    return 1;
}
static void map_add( uint64_t base, uint64_t size )
{
    int i = nmap++, j;
    while (i && map[i - 1].base > base) { map[i] = map[i - 1]; i--; }
    map[i].base = base; map[i].size = size;
    for (j = 0; j + 1 < nmap; j++)
        if (map[j].base + map[j].size > map[j + 1].base) { fprintf( stderr, "overlap\n" ); exit( 1 ); }
}
static void map_del( uint64_t base )
{
    int i;
    for (i = 0; i < nmap; i++) if (map[i].base == base) break;
    for (; i + 1 < nmap; i++) map[i] = map[i + 1];
    nmap--;
}
static void *anon_mmap_tryfixed( void *start, size_t size, int prot, int flags )
{
    uint64_t a = (uint64_t)(uintptr_t)start;
    int i;
    (void)prot; (void)flags;
    for (i = 0; i < nmap; i++)
        if (a < map[i].base + map[i].size && map[i].base < a + size) return MAP_FAILED;
    map_add( a, size );
    return start;
}
static int ios_jit_pool_intersects( void *p, size_t s ) { (void)p; (void)s; return 0; }
static uint64_t fake_ns = 1000000000ull;
static int fake_clock_gettime( int clk, struct timespec *ts )
{ (void)clk; ts->tv_sec = fake_ns / 1000000000ull; ts->tv_nsec = fake_ns % 1000000000ull; return 0; }
#define clock_gettime fake_clock_gettime
''' + epoch + place + r'''
static int fails;
#define CHECK(c) do { if (!(c)) { fprintf( stderr, "FAIL line %d: %s\n", __LINE__, #c ); fails++; } } while (0)
static int walked( size_t size, void **got )
{
    unsigned long before = walk_calls;
    *got = ios_ml1027_place( size, 3 );
    return walk_calls != before;
}
/* allocate_virtual_memory's success path and unmap_area's first lines */
static void reserve( uint64_t base, uint64_t size ) { map_add( base, size ); ios_place_note_new( (void *)base, size ); }
static void release( uint64_t base, uint64_t size )
{
    int i;
    for (i = 0; i < nmap; i++)
        if (map[i].base <= base && base + size <= map[i].base + map[i].size)
        {
            uint64_t b = map[i].base, s = map[i].size;
            map_del( b );
            if (base > b) map_add( b, base - b );
            if (base + size < b + s) map_add( base + size, b + s - base - size );
            break;
        }
    if (!ios_place_release_is_fresh( (void *)base, size )) ios_va_release_note();
}
int main( int argc, char **argv )
{
    void *got;
    (void)argv;
    /* occupied [4 GB, 8 GB), a 3 GB gap, occupied up to 16 MB below the ceiling */
    map_add( 0x100000000ull, 4 * GB );
    map_add( 0x2c0000000ull, 0x7fff000000ull - 0x2c0000000ull );
    if (argc > 1)   /* MADEIRA_PLACE_PROOF=0 */
    {
        CHECK( walked( 16 * GB, &got ) && got == MAP_FAILED );
        CHECK( walked( 16 * GB, &got ) && got == MAP_FAILED );
        CHECK( !ios_place_proof_skips );
        if (!fails) puts( "PASS: MADEIRA_PLACE_PROOF=0 walks every time" );
        return fails != 0;
    }
    CHECK( walked( 16 * GB, &got ) && got == MAP_FAILED );          /* the first ask walks */
    CHECK( ios_place_proof_gap == 3 * GB );
    fake_ns += 1000000;
    CHECK( !walked( 16 * GB, &got ) && got == MAP_FAILED );         /* the same ask: no walk */
    CHECK( !walked( 8 * GB, &got ) && got == MAP_FAILED );          /* smaller, still above 3 GB */
    CHECK( !walked( 0x1ffff0000ull, &got ) && got == MAP_FAILED );  /* V8's padded retry */
    CHECK( ios_place_proof_skips == 3 );
    CHECK( walked( 3 * GB, &got ) && got == (void *)0x200000000ull ); /* fits: walked and placed */
    CHECK( walked( 2 * GB, &got ) && got == MAP_FAILED );           /* the gap is gone: 16 MB tail */
    CHECK( ios_place_proof_gap == 16ull << 20 );
    CHECK( !walked( 1 * GB, &got ) && got == MAP_FAILED );
    release( 0x200000000ull, 3 * GB );                               /* made before the proof */
    CHECK( walked( 1 * GB, &got ) && got == (void *)0x200000000ull );
    CHECK( ios_place_proof_gap == 3 * GB );                          /* that walk proved 3 GB at most */
    CHECK( !walked( 16 * GB, &got ) && got == MAP_FAILED );
    fake_ns += IOS_PLACE_PROOF_NS + 1;                               /* the proof ages out */
    CHECK( walked( 16 * GB, &got ) && got == MAP_FAILED );
    CHECK( ios_place_proof_gap == 2 * GB );                          /* what is left of the gap */
    CHECK( !walked( 16 * GB, &got ) );
    /* V8's 4 GB step: reserve, find it misaligned, release, ask for the padded size */
    reserve( 0x240000000ull, 2 * GB );
    CHECK( !walked( 4 * GB, &got ) && got == MAP_FAILED );
    release( 0x240000000ull, 2 * GB );                               /* reserved after the proof */
    CHECK( !walked( 4 * GB, &got ) && got == MAP_FAILED );           /* still proven: no walk */
    reserve( 0x240000000ull, 2 * GB );
    release( 0x240000000ull, 1 * GB );                               /* part of it, too */
    CHECK( !walked( 4 * GB, &got ) );
    release( 0x280000000ull, 1 * GB );
    /* something older than the proof is released: walk again */
    release( 0x200000000ull, 1 * GB );
    CHECK( walked( 16 * GB, &got ) && got == MAP_FAILED && ios_place_proof_gap == 3 * GB );
    /* a new proof forgets what was reserved under the old one */
    reserve( 0x200000000ull, 1 * GB );
    fake_ns += IOS_PLACE_PROOF_NS + 1;
    CHECK( walked( 16 * GB, &got ) && ios_place_proof_gap == 2 * GB );
    release( 0x200000000ull, 1 * GB );                               /* mapped when that walk ran */
    CHECK( walked( 16 * GB, &got ) && ios_place_proof_gap == 3 * GB );
    if (!fails) puts( "PASS: an ask above the last walk's largest gap fails without a walk until a release or 2 s" );
    return fails != 0;
}
'''

with tempfile.TemporaryDirectory() as tmp:
    c = Path(tmp) / 'place.c'
    c.write_text(harness)
    exe = Path(tmp) / 'place'
    subprocess.run([os.environ.get('CC', 'cc'), '-std=gnu11', '-Wall', '-Werror', '-Wno-unused-function',
                    str(c), '-o', str(exe)], check=True)
    env = dict(os.environ)
    env.pop('MADEIRA_PLACE_PROOF', None)
    out = subprocess.run([str(exe)], capture_output=True, text=True, env=env)
    print(out.stdout.strip() or out.stderr.strip())
    assert out.returncode == 0, out.stderr
    assert 'refused without a walk' in out.stderr and 'NO GAP FITS' in out.stderr
    out = subprocess.run([str(exe), 'off'], capture_output=True, text=True,
                         env=dict(env, MADEIRA_PLACE_PROOF='0'))
    print(out.stdout.strip() or out.stderr.strip())
    assert out.returncode == 0, out.stderr

# --- textual wiring -----------------------------------------------------------
def body(name):
    b = src[src.index(name):]
    return b[:b.index('\n}\n')]

unmap = body('static void unmap_area( void *start, size_t size )')
assert unmap.index('if (!ios_place_release_is_fresh( start, size )) ios_va_release_note();') < unmap.index('munmap(')
alloc = body('static NTSTATUS allocate_virtual_memory(')
assert alloc.index('base = view->base;') < alloc.index('ios_place_note_new( base, ROUND_SIZE( 0, view->size, host_page_mask ) );') \
    < alloc.index('server_leave_uninterrupted_section( &virtual_mutex, &sigset );'), 'noted under virtual_mutex'
assert 'ios_va_release_note();' in body('static void remove_reserved_area( void *addr, size_t size )')
take = body('static uintptr_t ios_jumbo_holdback_take( size_t size )')
assert take.index('munmap( (void *)base, ios_jumbo_hold_size );') < take.index('ios_va_release_note();')
carve = body('static uintptr_t ios_jumbo_holdback_carve( size_t size )')
assert carve.index('if (munmap( (void *)at, size ) != 0)') < carve.index('ios_va_release_note();')
cage = body('static NTSTATUS ios_cage_grant(')
assert cage.index('munmap( (void *)(uintptr_t)IOS_CAGE_BASE, IOS_CAGE_REAL_SIZE );') < cage.index('ios_va_release_note();')
unhold = body('static void ios_sc2_unhold( int k )')
assert unhold.index('mach_vm_deallocate(') < unhold.index('ios_va_release_note();')
drop = body('static void ios_sc_pa_drop_hold(void)')
assert drop.index('mach_vm_deallocate(') < drop.index('ios_va_release_note();')
exe = body('static int ios_exe_win_claim( const void *addr, size_t size )')
assert exe.count('ios_va_release_note();') == 2 and exe.count('vm_deallocate(') == 2
walk = body('static void *ios_ml1027_place( size_t size, int prot )')
assert walk.index('if (ios_place_proven_full( size, t0 ))') < walk.index('mach_vm_region_recurse(')
assert 'largest gap "' in walk and 'walk %llu ms)' in walk
raise_ = thread[thread.index('NTSTATUS WINAPI NtRaiseException( EXCEPTION_RECORD *rec, CONTEXT *context, BOOL first_chance )'):]
raise_ = raise_[:raise_.index('status = send_debug_event(')]
assert 'rec->ExceptionCode == 0xE0000008' in raise_ and '[chromium-oom]' in raise_
print('PASS: every release bumps the epoch; the walk reports its largest gap and time; Chromium OOM sizes are logged')
