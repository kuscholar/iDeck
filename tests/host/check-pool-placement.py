#!/usr/bin/env python3
"""Compile the production pool allocator and exercise both image-slot placements.

The build-409-shaped case has a 560MB lower run, a 320MB upper run, a
240MB image slot, and a 91.3MB later image. Region C misses a 64MB request
by 80KB. The default placement and budget must reproduce the refusal;
changing only placement or only headroom must still refuse; combining the
opt-ins must provide a contiguous allocation without a larger pool.

This is a host allocator check, not an iOS/Wine/game execution test. Mach
queries report clean synthetic pool pages; the unchanged poison/grace paths
are checked separately by check-pool-split.py.
"""
from pathlib import Path
import os
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
source = (root / 'build/ntdll-unix/virtual_ios.c').read_text()


def function(signature):
    start = source.index(signature)
    return source[start:source.index('\n}', start) + 2] + '\n'


helpers = ''.join(function(sig) for sig in (
    'static int ios_pool_big_layout(',
    'static size_t ios_pool_parse_head_reserve(',
    'static size_t ios_pool_hole_head_place(',
    'static size_t ios_pool_hole_tail_start(',
    'static size_t ios_pool_hole_between(',
    'static size_t ios_pool_holes_head_place(',
    'static int ios_pool_skip_pieces(',
    'static size_t ios_pool_code_cap(',
    'static int ios_pool_low_take(',
    'static int ios_pool_best_fit(',
    'static int ios_pool_keep_big(',
))
allocator = function('static size_t ios_pool_alloc_range_ex(')
reclaim = function('void ios_jit_reclaim_process( void *peb )')
assert 'off < ios_pool_big_off + ios_pool_big_size && off + size > ios_pool_big_off' in reclaim
assert 'ios_pool_big_taken = 0;' in reclaim and 'ios_pool_big_freed_at = time( NULL );' in reclaim
assert reclaim.index('ios_pool_big_taken = 0;') < reclaim.index('ios_pool_free_put(')
assert 'ios_pool_parse_head_reserve( getenv( "MADEIRA_POOL_HEAD_RESERVE_MB" ) )' in source
assert 'const char *lower = getenv( "MADEIRA_POOL_BIG_SLOT_BELOW" );' in source
assert 'int below = lower && !strcmp( lower, "1" );' in source
assert 'if (!fits && below)' in source, 'an unavailable lower slot must try the existing upper placement'
assert ('#define IOS_POOL_IN_HOLE(o) ((size_t)(o) - ios_jit_hole_off < ios_jit_hole_end - ios_jit_hole_off || \\\n'
        '                             (size_t)(o) - ios_jit_hole2_off < ios_jit_hole2_end - ios_jit_hole2_off)') in source, \
    'the warmer skips the native holes (pool-mid adds a second), never the slot'
assert source.count('if (IOS_POOL_IN_HOLE(o)) continue;') == 4, 'the warmer skips only the native hole'

harness = r'''
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <pthread.h>
#include <unistd.h>
#define MB ((size_t)1 << 20)
#define CHECK(c) do { if (!(c)) { fprintf(stderr, "failed line %d: %s\n", __LINE__, #c); exit(1); } } while (0)
#define IOS_POOL_BIG_MIN (64u * 1024 * 1024)
#define IOS_POOL_LEDGER_MAX 1024
#define IOS_POOL_FREE_MAX 256
#define IOS_POOL_REUSE_GRACE_SEC 3
struct ios_pool_free { size_t off, size; time_t freed_at; int advised; };
struct ios_pool_alloc { size_t off, size; void *peb; };
static struct ios_pool_free ios_pool_freelist[IOS_POOL_FREE_MAX];
static struct ios_pool_alloc ios_pool_ledger[IOS_POOL_LEDGER_MAX];
static int ios_pool_free_count, ios_pool_ledger_count, ios_pool_last_alloc_reused;
static size_t jit_pool_offset, ios_jit_hole_off_eff, ios_jit_hole_end_eff;
static size_t ios_jit_hole2_off, ios_jit_hole2_end;   /* pool-mid: no second hole here */
static size_t ios_pool_big_off, ios_pool_big_size;
static int ios_pool_big_taken;
static time_t ios_pool_big_freed_at;
static pthread_mutex_t ios_pool_lock = PTHREAD_MUTEX_INITIALIZER;
static void *ios_jit_rx_base_global = (void *)(uintptr_t)0x148000000ULL;
static void *ios_jit_rw_base_global = (void *)(uintptr_t)0x7929000000ULL;
static size_t ios_jit_pool_size_global, ios_jit_low_size_global;
static uintptr_t ios_wow_base(void) { return 0; }
static struct { uintptr_t user_va, user_va_end, jit_rw_alias; } ios_jit_anon_aliases[16];
static int ios_jit_anon_alias_count;
static void *ios_jit_current_peb(void) { return (void *)(uintptr_t)1; }
static void ios_mono_alias_retire(uintptr_t va) { (void)va; }
static int ios_pool_range_execable(size_t off, size_t size, unsigned *cur, unsigned *max)
{ (void)off; (void)size; if (cur) *cur = 5; if (max) *max = 7; return 1; }
static int ios_pool_live_overlap(uintptr_t start, size_t size, size_t *off_out, void **peb_out)
{
    size_t off = start - (uintptr_t)ios_jit_rw_base_global;
    for (int i = 0; i < ios_pool_ledger_count; i++)
        if (ios_pool_ledger[i].off < off + size && ios_pool_ledger[i].off + ios_pool_ledger[i].size > off)
        { *off_out = ios_pool_ledger[i].off; *peb_out = ios_pool_ledger[i].peb; return 1; }
    return 0;
}
typedef int (*ios_pool_region_fn)(uint64_t *, uint64_t *, unsigned *);
static int ios_pool_mach_region(uint64_t *addr, uint64_t *size, unsigned *prot)
{ (void)addr; (void)size; (void)prot; return -1; }
static int ios_pool_execable_runs(uint64_t rx, size_t off, size_t size, ios_pool_region_fn fn,
                                 size_t *ro, size_t *rs, int max)
{ (void)rx; (void)off; (void)size; (void)fn; (void)ro; (void)rs; (void)max; return 0; }
''' + helpers + allocator + r'''
static size_t total = 0x37690000, native_lo = 560 * MB, native_hi = 0x23690000;

static void setup(int below)
{
    jit_pool_offset = 0;
    ios_pool_free_count = ios_pool_ledger_count = ios_jit_anon_alias_count = 0;
    ios_pool_big_taken = 0; ios_pool_big_freed_at = 0;
    ios_pool_big_size = 240 * MB;
    CHECK(ios_pool_big_layout(total, native_lo, native_hi, ios_pool_big_size, below,
                             &ios_pool_big_off, &ios_jit_hole_off_eff, &ios_jit_hole_end_eff));
}

/* Use many small real allocator requests to replay the observed head bytes.
 * Equal chunk boundaries on both sides make the native-hole jump exact. */
static void advance(size_t from, size_t to, size_t tail)
{
    while (from < to)
    {
        size_t size = to - from < 4 * MB ? to - from : 4 * MB;
        size_t off = ios_pool_alloc_range_ex(size, total - tail, (size_t)-1, 0);
        CHECK(off != (size_t)-1);
        CHECK(off >= native_hi || off + size <= native_lo);
        CHECK(off >= ios_pool_big_off + ios_pool_big_size || off + size <= ios_pool_big_off);
        from += size;
    }
}

static int launch_case(int below, size_t reserve)
{
    setup(below);
    size_t cef = ios_pool_alloc_range_ex(0xefc0000, total, (size_t)-1, 0);
    CHECK(cef == ios_pool_big_off && ios_pool_big_taken);
    CHECK(ios_pool_ledger[0].off == cef && ios_pool_ledger[0].peb == (void *)(uintptr_t)1);
    advance(0, 0x1dd14000, 0); /* head when the first 64MB tail carve happened */
    size_t cap = ios_pool_code_cap(total, jit_pool_offset, 0,
                                   ios_jit_hole_off_eff, ios_jit_hole_end_eff, reserve);
    volatile size_t low_used = 0xd014000;
    size_t tail = 0, granted = 0;
    for (size_t request = 128 * MB; request >= MB; request >>= 1)
    {
        size_t low_off;
        int low_fits = request <= 272 * MB - low_used;
        if (request > cap && !low_fits) continue;
        if (low_fits)
            CHECK(ios_pool_low_take(&low_used, 272 * MB, request, &low_off));
        else
        {
            size_t start = ios_pool_hole_tail_start(total, 0, request,
                                                    ios_jit_hole_off_eff, ios_jit_hole_end_eff);
            CHECK(start + request <= total && total - start - request >= jit_pool_offset);
            tail = start + request;
        }
        granted = request;
        break;
    }
    CHECK(granted == (reserve == 48 * MB ? 64 * MB : 32 * MB));
    CHECK(tail == (reserve == 48 * MB ? 64 * MB : 0));
    advance(0x1dd14000, 0x1f074000, tail);
    size_t off = ios_pool_alloc_range_ex(0x5b4c000, total - tail, (size_t)-1, 0);
    if (off != (size_t)-1)
    {
        CHECK(off >= native_hi && off + 0x5b4c000 <= total - tail);
        CHECK(off >= ios_pool_big_off + ios_pool_big_size || off + 0x5b4c000 <= ios_pool_big_off);
        CHECK(ios_pool_ledger[ios_pool_ledger_count - 1].size == 0x5b4c000);
    }
    return off != (size_t)-1;
}

static uint32_t rng = 41;
static uint32_t next(void) { rng = rng * 1664525u + 1013904223u; return rng; }

/* Start at the observed build-410 bump cursor before SHELL32. The page-fit
 * geometry uses the census's whole-MB lower bounds, not invented exact holes.
 * Replay the first missing image and a minimum remaining import budget; this
 * is a capacity check, not a claim that the game's full dependency set ran. */
static int imports_case(int page_fit, int preserve_code)
{
    const size_t before_shell = 0x35f40000, old_skip = 0x243d0000 - 320 * MB;
    native_lo = (page_fit ? 571 : 560) * MB;
    native_hi = 0x243d0000;
    total = native_hi + (page_fit ? 316 : 304) * MB;
    CHECK(total - (native_hi - native_lo) <= 896 * MB);
    setup(1);
    CHECK(ios_pool_alloc_range_ex(0xefc0000, total, (size_t)-1, 0) == ios_pool_big_off);
    jit_pool_offset = before_shell - old_skip + ios_jit_hole_end_eff - ios_jit_hole_off_eff;
    size_t limit = total - (preserve_code ? 0 : 16 * MB);
    if (ios_pool_alloc_range_ex(0x984000, limit, (size_t)-1, 0) == (size_t)-1) return 0;
    /* 31.078MB of unique missing-image requests plus 4.531MB of other later
     * imports, less the 9.516MB SHELL32 allocation already made. */
    size_t rest = 0x1f14000 + (0x363c8000 - before_shell) - 0x984000;
    return ios_pool_alloc_range_ex(rest, limit, (size_t)-1, 0) != (size_t)-1;
}

/* Keep the exact A/B geometry from the 411 log. Recovering C's unused 8MB
 * holds the helper's 32MB code buffer outside this pool. Replay RPCRT4 and
 * the observed minimum remaining image demand; unknown future imports are
 * intentionally not inferred from a successful capacity check. */
static int imports_411_case(int fit_c)
{
    total = 0x38000000;
    native_lo = 0x24ff4000;
    native_hi = 0x2566c000;
    setup(1);
    CHECK(ios_pool_big_off == 0x15ff4000);
    CHECK(ios_pool_alloc_range_ex(0xefc0000, total, (size_t)-1, 0) == ios_pool_big_off);
    jit_pool_offset = 0x35f78000;
    size_t limit = total - (fit_c ? 0 : 32 * MB);
    if (ios_pool_alloc_range_ex(0xf4000, limit, (size_t)-1, 0) == (size_t)-1) return 0;
    /* Unique failed-image requests (22.703125MB), plus later successful
     * head bytes (0.515625MB), less the RPCRT4 request already made. */
    size_t rest = 0x16b4000 + (0x35ffc000 - 0x35f78000) - 0xf4000;
    return ios_pool_alloc_range_ex(rest, limit, (size_t)-1, 0) != (size_t)-1;
}

int main(void)
{
    size_t slot = 11, lo = 12, hi = 13;
    CHECK(ios_pool_big_layout(total, native_lo, native_hi, 240 * MB, 0, &slot, &lo, &hi));
    CHECK(slot == native_hi && lo == native_lo && hi == native_hi + 240 * MB);
    CHECK(ios_pool_big_layout(total, native_lo, native_hi, 240 * MB, 1, &slot, &lo, &hi));
    CHECK(slot == 320 * MB && lo == slot && hi == native_hi);
    CHECK(!ios_pool_big_layout(total, 495 * MB, native_hi, 240 * MB, 1, &slot, &lo, &hi));
    CHECK(!ios_pool_big_layout(total, native_lo, native_hi, (size_t)-1, 0, &slot, &lo, &hi));
    CHECK(!ios_pool_big_layout(total, native_lo, native_hi, 240 * MB + 1, 1, &slot, &lo, &hi));
    CHECK(!ios_pool_big_layout(total, 0, 0, 240 * MB, 0, &slot, &lo, &hi));
    CHECK(!ios_pool_big_layout(total, native_hi, native_lo, 240 * MB, 1, &slot, &lo, &hi));
    CHECK(!ios_pool_big_layout(total, native_lo, total + 1, 240 * MB, 1, &slot, &lo, &hi));
    CHECK(!ios_pool_big_layout(total, native_lo, native_hi, 32 * MB, 1, &slot, &lo, &hi));
    puts("PASS: upper placement unchanged; lower slot stays in its run and retains 256MB startup room");

    const char *bad[] = {NULL, "", "0", "47", "257", "-128", "128x", " 128", "99999999999999999999999"};
    for (size_t i = 0; i < sizeof(bad) / sizeof(bad[0]); i++)
        CHECK(ios_pool_parse_head_reserve(bad[i]) == 48 * MB);
    CHECK(ios_pool_parse_head_reserve("48") == 48 * MB);
    CHECK(ios_pool_parse_head_reserve("128") == 128 * MB);
    CHECK(ios_pool_parse_head_reserve("256") == 256 * MB);
    CHECK(ios_pool_code_cap(total, (size_t)-1, 0, 0, 0, 48 * MB) == 16 * MB);
    CHECK(ios_pool_code_cap(total, 0, (size_t)-1, 0, 0, 48 * MB) == 16 * MB);
    for (int i = 0; i < 10000; i++)
    {
        size_t head = (next() % 561) * MB, tail = (next() % 321) * MB;
        size_t hole = ios_pool_hole_between(total, head, tail, native_lo, native_hi + 240 * MB);
        size_t room = total > head + tail + hole + 48 * MB ? total - head - tail - hole - 48 * MB : 0;
        size_t old = 16 * MB;
        while (old < 128 * MB && old * 2 <= room) old *= 2;
        CHECK(ios_pool_code_cap(total, head, tail, native_lo, native_hi + 240 * MB, 48 * MB) == old);
    }
    puts("PASS: bounded headroom parser and 10,000 default-budget comparisons, including exhausted cursors");

    CHECK(!launch_case(0, 48 * MB));
    CHECK(!launch_case(1, 48 * MB));
    CHECK(!launch_case(0, 128 * MB));
    CHECK(launch_case(1, 128 * MB));
    puts("PASS: observed allocator refusal reproduced; both opt-ins provide the later image without a larger pool");

    setup(1);
    jit_pool_offset = 319 * MB;
    size_t after = ios_pool_alloc_range_ex(4 * MB, total, (size_t)-1, 0);
    CHECK(after == native_hi && ios_pool_free_count == 1);
    CHECK(ios_pool_freelist[0].off == 319 * MB && ios_pool_freelist[0].size == MB);
    CHECK(ios_pool_alloc_range_ex(MB, total, (size_t)-1, 0) == 319 * MB);
    CHECK(!ios_pool_free_count && !ios_pool_big_taken);
    CHECK(ios_pool_alloc_range_ex(MB, total, (size_t)-1, 0) == native_hi + 4 * MB);
    puts("PASS: jumping a lower slot returns only the preceding unused bytes to the freelist");

    /* A pool-tail freelist-only request may not steal either image slot. */
    for (int below = 0; below < 2; below++)
    {
        setup(below);
        CHECK(ios_pool_alloc_range_ex(64 * MB, 0, (size_t)-1, 0) == (size_t)-1);
        CHECK(!ios_pool_big_taken && !ios_pool_ledger_count);
        /* An anchored image out of reach also cannot consume the reserved slot. */
        CHECK(ios_pool_alloc_range_ex(64 * MB, 0x4000, 0, 0x4000) == (size_t)-1);
        CHECK(!ios_pool_big_taken);
        size_t reserve = ios_pool_hole_tail_start(total, 0, 128 * MB,
                                                 ios_jit_hole_off_eff, ios_jit_hole_end_eff);
        size_t tail_off = total - reserve - 128 * MB;
        CHECK(tail_off >= ios_jit_hole_end_eff || tail_off + 128 * MB <= ios_jit_hole_off_eff);
    }
    puts("PASS: neither tail nor anchored requests can steal a slot; tail placement excludes both sides");
    CHECK(!imports_case(0, 0));
    CHECK(!imports_case(1, 0));
    CHECK(!imports_case(0, 1));
    CHECK(imports_case(1, 1));
    puts("PASS: the 410-shaped import budget needs both saved code-buffer space and page-fit capacity, within 896MB");
    CHECK(!imports_411_case(0));
    CHECK(imports_411_case(1));
    puts("PASS: the 411-shaped RPCRT4 refusal and minimum remaining import budget fit when C preserves 32MB of main-pool capacity");
    return 0;
}
'''

with tempfile.TemporaryDirectory(prefix='madeira-pool-placement-') as directory:
    cfile = Path(directory) / 'pool-placement.c'
    binary = Path(directory) / 'pool-placement'
    cfile.write_text(harness)
    subprocess.run([os.environ.get('CC', 'cc'), '-std=c11', '-D_POSIX_C_SOURCE=200809L',
                    '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined',
                    '-fno-omit-frame-pointer', '-pthread', str(cfile), '-o', str(binary)], check=True)
    # Allocator diagnostics use synthetic addresses; show only the contract results.
    completed = subprocess.run([str(binary)], capture_output=True, text=True)
    print(completed.stdout, end='')
    if completed.returncode:
        print(completed.stderr, end='')
        completed.check_returncode()
