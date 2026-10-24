#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 125hz
# Madeira Converter Exception: see LICENSE-EXCEPTION.md
"""Compile the production image-retire code from virtual_ios.c on a POSIX host.

Checks the unloaded-image translation retirement behind MADEIRA_JIT_IMAGE_RETIRE:
off unless the variable is exactly "1", the delete_view call order, equal-base
equal-size image reuse, every owner of a shared image, adjacency, partial
overlap and zero-length ranges. No Wine, game, SDK or device is needed.
Run with python3; it needs a C compiler with AddressSanitizer/UBSan.
"""
from pathlib import Path
import os
import re
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
native = (root / 'build/ntdll-unix/virtual_ios.c').read_text()


def function(source, signature):
    start = source.index(signature)
    return source[start:source.index('\n}', start) + 2] + '\n'


# The retirement must precede unmapping (still under virtual_mutex), and a
# failed unmap or an in-use shared builtin returns before delete_view.
delete = function(native, 'static void delete_view(')
assert delete.index('ios_jit_retire_image') < delete.index('unmap_area(')
guard = re.search(r'    if \(\(view->protect & SEC_IMAGE\) && ios_jit_image_retire_enabled\(\)\)\n'
                  r'        ios_jit_retire_image\( view->base, view->size \);\n', delete)
assert guard, 'delete_view must call ios_jit_retire_image only for SEC_IMAGE views with the switch on'
unmap = function(native, 'static NTSTATUS unmap_view_of_section(')
assert unmap.index('builtin->refcount--') < unmap.index('if (!status)') < unmap.index('delete_view( view )')

code = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <pthread.h>
#define SEC_IMAGE 0x1000000
struct mapping { void *pe_base, *jit_base; size_t size; void *owner; };
struct file_view { void *base; size_t size; unsigned int protect; };
static struct mapping ios_jit_mappings[8];
static int ios_jit_mapping_count;
static pthread_mutex_t ios_pool_lock = PTHREAD_MUTEX_INITIALIZER;
'''
code += function(native, 'static int ios_jit_image_retire_enabled(void)')
code += function(native, 'static void ios_jit_retire_image(')
code += 'static void delete_view_guard( struct file_view *view )\n{\n' + guard.group(0) + '}\n'
code += r'''
static void *lookup(uintptr_t addr) {
    for (int i = 0; i < ios_jit_mapping_count; i++) {
        uintptr_t p = (uintptr_t)ios_jit_mappings[i].pe_base;
        if (p && addr >= p && addr - p < ios_jit_mappings[i].size)
            return (char *)ios_jit_mappings[i].jit_base + (addr - p);
    }
    return NULL;
}
int main(int argc, char **argv) {
    const int on = argc > 1 && !strcmp(argv[1], "on");
    const uintptr_t base = 0x70fb8a0000ULL;
    static char old_code[64], new_code[64], neighbor[64];
    ios_jit_mapping_count = 3;
    /* One image copied for two pseudo-processes, and the next image up. */
    ios_jit_mappings[0] = (struct mapping){(void *)base, old_code, 0x90000, (void *)1};
    ios_jit_mappings[1] = (struct mapping){(void *)base, old_code, 0x90000, (void *)2};
    ios_jit_mappings[2] = (struct mapping){(void *)(base + 0x90000), neighbor, 0x10000, (void *)3};
    assert(lookup(base) == old_code);

    /* A data view never retires anything. */
    struct file_view data = {(void *)base, 0x90000, 0};
    delete_view_guard(&data);
    assert(lookup(base) == old_code);

    struct file_view image = {(void *)base, 0x90000, SEC_IMAGE};
    delete_view_guard(&image);
    if (!on) {
        /* Default: exactly the previous behaviour, the stale copy survives. */
        assert(lookup(base) == old_code);
        assert(ios_jit_mappings[0].size == 0x90000 && ios_jit_mappings[1].size == 0x90000);
        assert(lookup(base + 0x90000) == neighbor);
        puts("PASS (switch off): no translation retired, table unchanged");
        return 0;
    }
    assert(!lookup(base));
    assert(!ios_jit_mappings[0].pe_base && !ios_jit_mappings[1].pe_base);
    assert(!ios_jit_mappings[0].size && !ios_jit_mappings[1].size);
    assert(lookup(base + 0x90000) == neighbor);          /* adjacency is not overlap */

    /* The same base and image size now get a fresh executable copy. */
    ios_jit_mappings[0] = (struct mapping){(void *)base, new_code, 0x90000, (void *)2};
    assert(lookup(base) == new_code);
    ios_jit_retire_image((void *)(base + 0x80000), 0x10000);
    assert(!lookup(base));                               /* partial overlap retires it */
    assert(lookup(base + 0x90000) == neighbor);
    ios_jit_retire_image((void *)(base + 0x90000), 0);   /* zero length: nothing */
    assert(lookup(base + 0x90000) == neighbor);
    ios_jit_retire_image((void *)(base + 0x9ffff), 1);   /* last byte of the neighbour */
    assert(!lookup(base + 0x90000));
    /* A range that ends at the top of the address space must not wrap. */
    ios_jit_mappings[2] = (struct mapping){(void *)0x1000, neighbor, 0x1000, (void *)3};
    ios_jit_retire_image((void *)(UINTPTR_MAX - 0xfff), 0x1000);
    assert(lookup(0x1000) == neighbor);
    puts("PASS (switch on): image unload/reuse, shared owners, adjacency, partial overlap, zero length");
    return 0;
}
'''

with tempfile.TemporaryDirectory(prefix='madeira-image-retire-') as directory:
    folder = Path(directory)
    source = folder / 'check.c'
    source.write_text(code)
    executable = folder / 'check'
    subprocess.run([os.environ.get('CC', 'cc'), '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-g',
                    '-fsanitize=address,undefined', '-fno-sanitize-recover=all', '-pthread',
                    str(source), '-o', str(executable)], check=True)
    runs = [(None, 'off'), ('0', 'off'), ('yes', 'off'), ('11', 'off'), ('', 'off'), ('1', 'on')]
    for value, mode in runs:
        env = dict(os.environ)
        env.pop('MADEIRA_JIT_IMAGE_RETIRE', None)
        if value is not None:
            env['MADEIRA_JIT_IMAGE_RETIRE'] = value
        result = subprocess.run([str(executable), mode], env=env, check=True, capture_output=True, text=True)
        print(f'MADEIRA_JIT_IMAGE_RETIRE={value!r}: {result.stdout.strip()}')
        assert ('[jit-image-retire] enabled' in result.stderr) == (mode == 'on'), result.stderr
        if mode == 'on':
            assert '[jit-image-retire] unmapped=' in result.stderr, result.stderr
        else:
            assert '[jit-image-retire]' not in result.stderr, result.stderr
print('PASS: image retire is off by default and retires overlapping translations when enabled')
