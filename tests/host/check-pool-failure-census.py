#!/usr/bin/env python3
"""Exercise the actual read-only pool failure census under both capacities
and parallel failures. The diagnostic cannot grant allocations or change
the existing free list, owner records, cursor or reuse grace."""
from pathlib import Path
import os
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
source = (root / 'build/ntdll-unix/virtual_ios.c').read_text()


def body(signature):
    start = source.index(signature)
    return source[start:source.index('\n}', start) + 2]


census = body('static void ios_pool_failure_census( size_t want )')
assert 'jit_pool_size,' not in census and 'jit_pool_size -' not in census
hole = body('static size_t ios_pool_hole_between(') + '\n' + body('static size_t ios_pool_holes_between(')
assert 'ios_pool_holes_between( ios_jit_pool_size_global, jit_pool_offset, ios_jit_tail_reserved,' in census, \
    'the census leaves pool-mid\'s second hole out of the virgin room too'
assert source.count('ios_pool_failure_census( alloc_size );') == 1
site = source[source.index('ios_pool_failure_census( alloc_size );') - 80:][:160]
assert 'if (offset == (size_t)-1)' in site
for mutation in ('mprotect(', 'munmap(', 'madvise(', 'ios_pool_alloc_range(', 'ios_pool_recycle_code_range(',
                 'malloc(', 'ios_pool_ledger[', 'ios_tail_carves['):
    assert mutation not in census

harness = r'''
#include <assert.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <pthread.h>
#include <time.h>
#define MB ((size_t)1 << 20)
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define IOS_POOL_REUSE_GRACE_SEC 3
struct ios_pool_free { size_t off, size; time_t freed_at; int advised; };
static struct ios_pool_free ios_pool_freelist[8];
static unsigned ios_pool_free_count;
static size_t ios_jit_pool_size_global, jit_pool_offset, ios_jit_tail_reserved;
static size_t ios_jit_hole_off_eff, ios_jit_hole_end_eff;
static size_t ios_jit_hole2_off, ios_jit_hole2_end;   /* pool-mid: no second hole here */
static size_t ios_jit_low_reserved, ios_jit_low_size_global;
static pthread_mutex_t ios_pool_lock = PTHREAD_MUTEX_INITIALIZER;
static char output[16384];
static size_t length;
static unsigned lines;
static time_t fake_time(time_t *p) { if (p) *p = 100; return 100; }
static int capture(int fd, const char *format, ...)
{
    assert(fd == 2);
    va_list args;
    va_start(args, format);
    int n = vsnprintf(output + length, sizeof(output) - length, format, args);
    va_end(args);
    assert(n > 0 && length + (size_t)n < sizeof(output));
    length += (size_t)n;
    lines++;
    return n;
}
#define time fake_time
#define dprintf capture
''' + hole + '\n' + census + r'''
#undef time
#undef dprintf
static void *fail(void *p) { ios_pool_failure_census((size_t)p); return NULL; }
int main(int argc, char **argv)
{
    assert(argc == 2);
    unsigned which = (unsigned)strtoul(argv[1], NULL, 10);
    ios_jit_pool_size_global = 896 * MB;
    jit_pool_offset = 600 * MB;
    ios_jit_tail_reserved = 64 * MB;
    ios_jit_hole_off_eff = 700 * MB;
    ios_jit_hole_end_eff = 708 * MB;
    ios_jit_low_size_global = 316 * MB;
    ios_jit_low_reserved = 311 * MB;
    ios_pool_free_count = 4;
    ios_pool_freelist[0] = (struct ios_pool_free){MB, MB/2, 50, 1};
    ios_pool_freelist[1] = (struct ios_pool_free){2*MB, MB, 98, 0};
    ios_pool_freelist[2] = (struct ios_pool_free){4*MB, 8*MB, 90, 3};
    ios_pool_freelist[3] = (struct ios_pool_free){16*MB, 2*MB, 97, 1};
    if (which == 1) {
        jit_pool_offset = ios_jit_pool_size_global + 1;
        ios_jit_low_reserved = ios_jit_low_size_global + 1;
    } else if (which == 2) {
        jit_pool_offset = 720 * MB; /* already beyond the hole */
        ios_jit_low_size_global = 0;
        ios_jit_low_reserved = 0;
    }
    size_t before[] = {ios_jit_pool_size_global, jit_pool_offset, ios_jit_tail_reserved,
        ios_jit_hole_off_eff, ios_jit_hole_end_eff, ios_jit_low_reserved, ios_jit_low_size_global};
    struct ios_pool_free saved[8];
    memcpy(saved, ios_pool_freelist, sizeof(saved));
    ios_pool_failure_census(6 * MB);
    assert(lines == 1);
    assert(strstr(output, "free_bytes=0xb80000 largest=0x800000"));
    assert(strstr(output, "aged_bytes=0xa80000 aged_largest=0x800000"));
    assert(strstr(output, "raw_size_fit=1 aged_size_fit=1 poison_marked_bytes=0x800000"));
    if (which == 0) assert(strstr(output, "main_virgin=0xe000000 c_virgin=0x500000 c_image_virgin=0x100000"));
    if (which == 1) assert(strstr(output, "main_virgin=0x0 c_virgin=0x0 c_image_virgin=0x0"));
    if (which == 2) assert(strstr(output, "main_virgin=0x7000000 c_virgin=0x0 c_image_virgin=0x0"));
    size_t saved_length = length;
    ios_pool_failure_census(6 * MB);
    assert(length == saved_length); /* retries do not duplicate evidence */
    pthread_t workers[12];
    for (size_t i = 0; i < 12; ++i)
        assert(pthread_create(&workers[i], NULL, fail, (void *)((i + 1) * 0x4000)) == 0);
    for (unsigned i = 0; i < 12; ++i) assert(pthread_join(workers[i], NULL) == 0);
    assert(lines == 8 && !memcmp(saved, ios_pool_freelist, sizeof(saved)) && ios_pool_free_count == 4);
    size_t after[] = {ios_jit_pool_size_global, jit_pool_offset, ios_jit_tail_reserved,
        ios_jit_hole_off_eff, ios_jit_hole_end_eff, ios_jit_low_reserved, ios_jit_low_size_global};
    assert(!memcmp(before, after, sizeof(before)));
    puts("PASS: capacity, hole, code reserve, grace, poisoned ranges, underflow and bounded parallel census");
}
'''
with tempfile.TemporaryDirectory(prefix='pool-failure-census-') as directory:
    temp = Path(directory)
    unit = temp / 'test.c'
    unit.write_text(harness)
    exe = temp / 'test'
    subprocess.run([os.environ.get('CC', 'cc'), '-std=c11', '-Wall', '-Wextra', '-Werror',
                    '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
                    str(unit), '-pthread', '-o', str(exe)], check=True)
    for case in range(3):
        subprocess.run([str(exe), str(case)], check=True)
