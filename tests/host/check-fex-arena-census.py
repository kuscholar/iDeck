#!/usr/bin/env python3
"""Compile the actual failure census; verify clipping, protection accounting,
alignment, bounded output and its failure-only integration."""
from pathlib import Path
import os
import re
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
source = (root / 'build/ntdll-unix/virtual_ios.c').read_text()
signature = 'static void ios_fex_arena_census( void *start, void *end, size_t request, size_t align_mask )'
start = source.index(signature)
body = source[start:source.index('\n}', start) + 2]
call = 'if (!ptr) ios_fex_arena_census( start, end, size, align_mask );'
assert source.count(call) == 1
assert source.index('static BYTE get_page_vprot(') < start < source.index(call)
site = source[source.index(call) - 120:source.index(call) + 230]
assert '#ifdef WINE_IOS' in site and 'got mem with map_free_area' in site
assert 'get_page_vprot( (void *)p )' in body
for mutation in ('mprotect(', 'munmap(', 'VirtualFree(', 'malloc(', 'calloc(', 'mach_vm_read', '->base['):
    assert mutation not in body

harness = r'''
#include <assert.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef uintptr_t ULONG_PTR;
typedef unsigned char BYTE;
#define VPROT_COMMITTED 0x20
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
struct file_view { void *base; size_t size; unsigned protect; };
static struct { struct file_view entries[48]; unsigned count; } views_tree;
#define WINE_RB_FOR_EACH_ENTRY(v,t,type,field) \
 for (unsigned iter = 0; iter < (t)->count && ((v) = &(t)->entries[iter], 1); ++iter)
static ULONG_PTR ios_fex_arena_base_unix, ios_fex_arena_end_unix;
static size_t page_size = 4096;
static struct { uintptr_t lo, hi; } committed_ranges[4];
static unsigned nranges, reads;
static char output[32768];
static size_t length;
static BYTE get_page_vprot(const void *p)
{
    uintptr_t a = (uintptr_t)p;
    assert(a >= ios_fex_arena_base_unix && a < ios_fex_arena_end_unix);
    reads++;
    for (unsigned i = 0; i < nranges; ++i)
        if (a >= committed_ranges[i].lo && a < committed_ranges[i].hi) return VPROT_COMMITTED;
    return 0;
}
static int capture(int fd, const char *format, ...)
{
    assert(fd == 2);
    va_list args;
    va_start(args, format);
    int n = vsnprintf(output + length, sizeof(output) - length, format, args);
    va_end(args);
    assert(n > 0 && length + (size_t)n < sizeof(output));
    length += (size_t)n;
    return n;
}
#define dprintf capture
''' + body + r'''
#undef dprintf
static void view(uintptr_t base, size_t size, unsigned flags)
{
    assert(views_tree.count < ARRAY_SIZE(views_tree.entries));
    views_tree.entries[views_tree.count++] = (struct file_view){(void *)base, size, flags};
}
static void commit(uintptr_t lo, uintptr_t hi)
{
    assert(nranges < ARRAY_SIZE(committed_ranges));
    committed_ranges[nranges].lo = lo;
    committed_ranges[nranges++].hi = hi;
}
int main(int argc, char **argv)
{
    assert(argc == 2);
    unsigned which = (unsigned)strtoul(argv[1], NULL, 10);
    uintptr_t lo = 0x7d00000000ULL, hi = lo + 0x10000;
    size_t mask = 0x3fff;
    if (which == 3) hi = lo + 0x400000;
    ios_fex_arena_base_unix = lo;
    ios_fex_arena_end_unix = hi;
    /* Rejected calls must neither read protections nor consume the cap. */
    ios_fex_arena_census((void *)(lo - 1), (void *)hi, 4096, mask);
    ios_fex_arena_census((void *)lo, (void *)(hi + 1), 4096, mask);
    ios_fex_arena_census((void *)lo, (void *)lo, 4096, mask);
    ios_fex_arena_base_unix = 0;
    ios_fex_arena_census((void *)lo, (void *)hi, 4096, mask);
    ios_fex_arena_base_unix = lo;
    ios_fex_arena_end_unix = lo;
    ios_fex_arena_census((void *)lo, (void *)hi, 4096, mask);
    ios_fex_arena_end_unix = hi;
    page_size = 0;
    ios_fex_arena_census((void *)lo, (void *)hi, 4096, mask);
    page_size = 4096;
    assert(length == 0 && reads == 0);
    if (which == 1) { view(lo, hi - lo, 3); commit(lo, hi); }
    else if (which == 2) {
        view(lo - 0x5000, 0x1000, 3); /* outside, skipped */
        view(lo - 0x1000, 0x3000, 3);
        view(lo + 0x5000, 0x2000, 0x23);
        view(lo + 0xf000, 0x4000, 3);
        view(hi + 0x1000, 0x1000, 3); /* outside, skipped */
        commit(lo, lo + 0x1000);
        commit(lo + 0x5000, lo + 0x6000);
        commit(lo + 0xf000, hi);
    } else if (which == 3) {
        uintptr_t p = lo;
        for (unsigned i = 1; i <= 40; ++i) { view(p, i * 4096, 3); p += i * 4096; }
    } else if (which == 4) {
        /* Detect overlapping bookkeeping without negative free bytes or
         * double-counting the committed total. Real views are disjoint. */
        view(lo, 0x8000, 3); view(lo + 0x4000, 0x8000, 3); commit(lo, hi);
    } else if (which == 5) { view(lo - 0x1000, SIZE_MAX, 3); }
    else if (which == 6) { mask = SIZE_MAX; }
    else if (which == 7) { lo += 0x8000; } /* caller subrange, arena stays whole */
    ios_fex_arena_census((void *)lo, (void *)hi, 4096, mask);
    assert(length && strstr(output, "(virtual bytes, not residency)"));
    unsigned read_count = reads;
    size_t saved = length;
    ios_fex_arena_census((void *)lo, (void *)hi, 8192, mask);
    assert(length == saved && reads == read_count);
    unsigned lines = 0;
    for (size_t i = 0; i < length; ++i) lines += output[i] == '\n';
    assert(lines <= 34);
    puts(output);
    return 0;
}
'''
expected = [
    dict(views=0, covered=0, free=0x10000, committed=0, overlap=0, holes=1, maxgap=0x10000, max_aligned_gap=0x10000),
    dict(views=1, covered=0x10000, free=0, committed=0x10000, overlap=0, holes=0, maxgap=0, max_aligned_gap=0),
    dict(views=3, covered=0x5000, free=0xb000, committed=0x3000, overlap=0, holes=2, maxgap=0x8000, max_aligned_gap=0x7000),
    dict(views=40, covered=820*4096, free=204*4096, committed=0, overlap=0, holes=1, maxgap=204*4096, max_aligned_gap=204*4096),
    dict(views=2, covered=0xc000, free=0x4000, committed=0xc000, overlap=0x4000, holes=1, maxgap=0x4000, max_aligned_gap=0x4000),
    dict(views=1, covered=0x10000, free=0, committed=0, overlap=0, holes=0, maxgap=0, max_aligned_gap=0),
    dict(views=0, covered=0, free=0x10000, committed=0, overlap=0, holes=1, maxgap=0x10000, max_aligned_gap=0),
    dict(views=0, covered=0, free=0x10000, committed=0, overlap=0, holes=1, maxgap=0x10000, max_aligned_gap=0x10000),
]
with tempfile.TemporaryDirectory(prefix='fex-arena-census-') as temp:
    temp = Path(temp)
    path = temp / 'test.c'
    path.write_text(harness)
    exe = temp / 'test'
    subprocess.run([os.environ.get('CC', 'cc'), '-std=c11', '-Wall', '-Wextra', '-Werror',
                    '-fsanitize=address,undefined', '-fno-sanitize-recover=all', str(path), '-o', str(exe)], check=True)
    for case, wanted in enumerate(expected):
        result = subprocess.check_output([str(exe), str(case)], text=True)
        summary = result.splitlines()[0]
        for name, value in wanted.items():
            found = re.search(r'\b' + name + r'=(0x[0-9a-f]+|\d+)\b', summary)
            assert found and int(found[1], 0) == value, (case, name, value, summary)
        if case == 2:
            assert 'size=0x3000 view_flags=0x3 views=1 reserved=0x2000 committed=0x1000' in result
        if case == 3:
            assert 'other_sizes views=8 reserved=0x124000 committed=0x0' in result
            assert len(result.strip().splitlines()) == 34
        if case == 7:
            assert 'failed_range=0x7d00008000..0x7d00010000' in summary
print('PASS: live census clipping, committed accounting, alignment, overlaps, overflow, bucket/output cap and failure-only integration')
