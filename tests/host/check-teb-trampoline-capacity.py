#!/usr/bin/env python3
"""Exercise the production slot allocator and TEB accessors. The old 256-slot
limit must reproduce shared-slot collisions; the full preallocated page must
retain every thread's identity without touching the following image."""
from pathlib import Path
import os
import re
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
source = (root / 'build/ntdll-unix/virtual_ios.c').read_text()
assert 'jit_pool_offset = 0x4000;  /* one 16KB iOS page */' in source
defines = '\n'.join(re.findall(r'^#define IOS_JIT_(?:TRAMPOLINE_SIZE|MAX_SLOTS) .*$', source, re.M))
assert '#define IOS_JIT_MAX_SLOTS (0x4000 / IOS_JIT_TRAMPOLINE_SIZE)' in defines


def body(signature):
    start = source.index(signature)
    return source[start:source.index('\n}', start) + 2]


functions = '\n'.join(body(s) for s in (
    'int ios_jit_alloc_trampoline_slot(void)',
    'void ios_jit_set_teb_slot(int slot, uintptr_t teb)',
    'void *ios_jit_get_trampoline(int slot)',
))
assert 'code[0] = 0x58FFFFD2;' in functions and 'code[1] = 0xD61F0220;' in functions
for change in ('mprotect(', 'mmap(', 'malloc(', '__sync_fetch_and_sub', 'ios_pool_ledger'):
    assert change not in functions

harness = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <pthread.h>
static void *ios_jit_rw_base_global, *ios_jit_rx_base_global;
static volatile int32_t ios_jit_next_slot;
static unsigned cache_calls;
static _Alignas(16) unsigned char backing[0x4000 + 64];
static void sys_icache_invalidate(void *p, size_t size)
{
    assert(size == 8 && (uintptr_t)p >= (uintptr_t)backing + 32 + 8);
    assert((uintptr_t)p + size <= (uintptr_t)backing + 32 + 0x4000);
    __sync_fetch_and_add(&cache_calls, 1);
}
''' + defines + '\n' + functions + r'''
enum { WORKERS = 16, EACH = 64, TOTAL = WORKERS * EACH };
static int slots[TOTAL];
static uint64_t tebs[TOTAL];
static void *allocate(void *p)
{
    unsigned first = (unsigned)(uintptr_t)p * EACH;
    for (unsigned n = first; n < first + EACH; ++n) {
        slots[n] = ios_jit_alloc_trampoline_slot();
        tebs[n] = 0x7100000000ULL + n * 0x10000ULL;
        ios_jit_set_teb_slot(slots[n], tebs[n]);
        assert(ios_jit_get_trampoline(slots[n]) == (char *)ios_jit_rx_base_global + slots[n] * 16 + 8);
    }
    return NULL;
}
int main(int argc, char **argv)
{
    assert(argc == 2);
    unsigned legacy = (unsigned)atoi(argv[1]);
    memset(backing, 0xa5, sizeof(backing));
    ios_jit_rw_base_global = ios_jit_rx_base_global = backing + 32;
    pthread_t workers[WORKERS];
    if (legacy) {
        /* Reproduce identity corruption without introducing a C data race
         * in the negative control's intentionally shared slot. */
        for (unsigned i = 0; i < WORKERS; ++i) allocate((void *)(uintptr_t)i);
    } else {
        for (unsigned i = 0; i < WORKERS; ++i)
            assert(pthread_create(&workers[i], NULL, allocate, (void *)(uintptr_t)i) == 0);
        for (unsigned i = 0; i < WORKERS; ++i) assert(pthread_join(workers[i], NULL) == 0);
    }
    unsigned seen[TOTAL] = {0}, collisions = 0, incorrect_tebs = 0;
    for (unsigned i = 0; i < TOTAL; ++i) {
        assert(slots[i] >= 0 && slots[i] < IOS_JIT_MAX_SLOTS);
        if (seen[slots[i]]++) collisions++;
        uint64_t value;
        memcpy(&value, backing + 32 + slots[i] * 16, 8);
        incorrect_tebs += value != tebs[i];
        const uint32_t *code = ios_jit_get_trampoline(slots[i]);
        assert(code[0] == 0x58FFFFD2 && code[1] == 0xD61F0220);
    }
    assert(cache_calls == IOS_JIT_MAX_SLOTS);
    if (legacy) assert(collisions && incorrect_tebs && IOS_JIT_MAX_SLOTS == 256);
    else {
        assert(!collisions && !incorrect_tebs && IOS_JIT_MAX_SLOTS == TOTAL);
        assert(ios_jit_get_trampoline(TOTAL-1) == backing + 32 + 0x4000 - 8);
        assert(!ios_jit_get_trampoline(-1) && !ios_jit_get_trampoline(TOTAL));
        unsigned char before[sizeof(backing)];
        memcpy(before, backing, sizeof(before));
        ios_jit_set_teb_slot(-1, 1);
        ios_jit_set_teb_slot(TOTAL, 1);
        assert(!memcmp(before, backing, sizeof(before)));
        /* Unmapped/uninitialised views remain no-ops; never dereference null. */
        ios_jit_rw_base_global = ios_jit_rx_base_global = NULL;
        ios_jit_next_slot = 0;
        assert(ios_jit_alloc_trampoline_slot() == 0);
        ios_jit_set_teb_slot(0, 1);
        assert(!ios_jit_get_trampoline(0) && !memcmp(before, backing, sizeof(before)));
    }
    for (unsigned i = 0; i < 32; ++i) assert(backing[i] == 0xa5 && backing[32 + 0x4000 + i] == 0xa5);
    printf("PASS: %s %u allocations, collisions=%u incorrect_TEB=%u; guards intact\n",
           legacy ? "old limit" : "full page", TOTAL, collisions, incorrect_tebs);
}
'''
with tempfile.TemporaryDirectory(prefix='teb-trampoline-capacity-') as directory:
    temp = Path(directory)
    for old in (True, False):
        text = harness.replace('#define IOS_JIT_MAX_SLOTS (0x4000 / IOS_JIT_TRAMPOLINE_SIZE)',
                               '#define IOS_JIT_MAX_SLOTS 256') if old else harness
        unit = temp / 'test.c'
        unit.write_text(text)
        exe = temp / ('old' if old else 'full')
        subprocess.run([os.environ.get('CC', 'cc'), '-std=c11', '-Wall', '-Wextra', '-Werror',
                        '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
                        str(unit), '-pthread', '-o', str(exe)], check=True)
        subprocess.run([str(exe), str(int(old))], check=True)
