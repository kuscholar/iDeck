# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Opt-in copied Linux realfs/last-reference hooks; never vendor edits."""

REAL_PREFIX = '''#include "SharedFileReserve.h"
#include <sys/mman.h>
#include <errno.h>
#if IDECK_FILE_RESERVE_REALFS_HOST_INJECTION
#if defined(__ENVIRONMENT_IPHONE_OS_VERSION_MIN_REQUIRED__)
#error Host mapping injection must never be compiled into iOS
#endif
extern void *ideck_file_reserve_test_original_map(void *,size_t,int,int,int,off_t);
#define ideck_reserve_original_map ideck_file_reserve_test_original_map
#else
#define ideck_reserve_original_map mmap
#endif
static void ideck_reserve_failed_transfer_release(void *pointer,size_t bytes) {
    int saved=errno;
    int handled=ideck_file_reserve_release(pointer,bytes);
    if(!handled)munmap(pointer,bytes);
    /* A refused owned span is never passed to an unrelated native unmap. */
    errno=saved;
}
'''


def patch_real(body):
    assert 'IDECK_FILE_MMAP_PROBE_V1' not in body and 'FileMmapProbe.inc' not in body, 'Do not combine reserve allocator with observational mapping/headroom probes'
    old = '''    char *memory = mmap(NULL, map_size,
            mmap_prot, mmap_flags, fd->real_fd, real_offset);'''
    assert body.count(old) == 1, 'Expected exact ordinary in-file native mapping only'
    body = body.replace(old, old.replace('= mmap(', '= ideck_reserve_original_map('))
    old = '''        if (runtime_memory_failure) runtime_memory_failure("mmap file", 0, map_size, mmap_prot, mmap_flags, native_error);
        return result;'''
    new = '''        if (runtime_memory_failure) runtime_memory_failure("mmap file", 0, map_size, mmap_prot, mmap_flags, native_error);
        /* Try a distinct bounded allocator using only pre-owned native VA.
         * Retain the original failure diagnostics. No syscall retry loop,
         * guessed guest address, file copy or fabricated successful bytes. */
        memory = ideck_file_reserve_after_enomem(fd->real_fd, map_size,
                real_offset, mmap_prot, mmap_flags, native_error);
        if (memory == MAP_FAILED) return result;'''
    assert body.count(old) == 1, 'Expected the qualified native file failure path'
    body = body.replace(old, new)
    old = 'munmap(memory, map_size);'
    assert body.count(old) == 3, 'Require existing three failed-transfer cleanup sites'
    body = body.replace(old, 'ideck_reserve_failed_transfer_release(memory, map_size);')
    return REAL_PREFIX + body + '\nconst char *ideck_file_reserve_real_marker(void){return "IDECK_SHARED_FILE_RESERVE_REAL_V1";}\n'


def patch_memory(body):
    assert '#include "CowBackingBroker.h"' in body, 'Require the qualified original-span broker layout'
    old = '            if (!owned) munmap(data->data, data->size);'
    new = '''            if (!owned) {
                int reserved = ideck_file_reserve_release(data->data, data->size);
                if (!reserved) munmap(data->data, data->size);
                /* Errors retain/quarantine owned VA. Never unmap it twice. */
            }'''
    assert body.count(old) == 1, 'Expected exactly the last-reference release hook'
    return '#include "SharedFileReserve.h"\n' + body.replace(old, new) + '\nconst char *ideck_file_reserve_memory_marker(void){return "IDECK_SHARED_FILE_RESERVE_MEMORY_V1";}\n'
