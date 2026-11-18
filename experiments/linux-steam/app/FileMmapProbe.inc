/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * Own Lab-only failure discriminator. No guest data/paths are read, no original
 * request is retried or repaired, and none of these mappings reaches a PTE.
 * Each successful diagnostic mapping is immediately released without touching
 * its contents. A failed release stops the probe; the original error survives.
 */
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#if IDECK_LAB_VA_HEADROOM_PROBE
#include "VAHeadroomProbe.h"
#endif
#ifndef IDECK_LAB_FILE_MMAP_PROBE
#define IDECK_LAB_FILE_MMAP_PROBE 0
#endif
#ifndef IDECK_MMAP_PROBE_LOG
#define IDECK_MMAP_PROBE_LOG(line) printk("%s\n", (line))
#endif

static void ideck_file_mmap_failure_probe(int tid, int tgid, int fd,
        size_t bytes, off_t offset, int prot, int flags, int original_error,
        size_t host_page) {
#if IDECK_LAB_FILE_MMAP_PROBE
    static atomic_bool used;
    if (original_error != ENOMEM || fd < 0 || offset != 0 ||
            flags != MAP_SHARED || prot != (PROT_READ | PROT_WRITE) ||
            host_page < 4096 || host_page > 65536 ||
            (host_page & (host_page - 1)) || bytes < host_page ||
            bytes > 16u * 1024u * 1024u) return;
    if (atomic_exchange_explicit(&used, 1, memory_order_relaxed)) return;
    int saved = errno;
    char line[384];
    struct stat metadata;
    int status = fstat(fd, &metadata);
    if (status || !S_ISREG(metadata.st_mode) || metadata.st_size < 0 ||
            (uint64_t)metadata.st_size < bytes) {
        snprintf(line, sizeof line,
                "IDECK_FILE_MMAP_PROBE_V1 phase=skipped tid=%d tgid=%d stat_ok=%d original_error=%d original_result_preserved=1",
                tid, tgid, status == 0, original_error);
        IDECK_MMAP_PROBE_LOG(line);
        errno = saved;
        return;
    }
    snprintf(line, sizeof line,
            "IDECK_FILE_MMAP_PROBE_V1 phase=begin tid=%d tgid=%d bytes=%zu host_page=%zu original_error=%d once_per_native_lifetime=1 payload_read=0 original_result_preserved=1",
            tid, tgid, bytes, host_page, original_error);
    IDECK_MMAP_PROBE_LOG(line);
    struct trial { size_t bytes; int prot, flags, fd; } trials[] = {
        {host_page, PROT_READ | PROT_WRITE, MAP_SHARED, fd},
        {bytes, PROT_READ, MAP_SHARED, fd},
        {bytes, PROT_READ | PROT_WRITE, MAP_PRIVATE, fd},
        {bytes, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1},
    };
    unsigned attempted = 0;
    int all_released = 1;
    for (unsigned i = 0; i < sizeof trials / sizeof trials[0]; i++) {
        const struct trial *trial = &trials[i];
        errno = 0;
        void *mapping = mmap(NULL, trial->bytes, trial->prot, trial->flags,
                trial->fd, 0);
        int mapped = mapping != MAP_FAILED;
        int map_error = mapped ? 0 : errno;
        int released = !mapped;
        int release_error = 0;
        if (mapped) {
            errno = 0;
            released = munmap(mapping, trial->bytes) == 0;
            if (!released) release_error = errno;
        }
        attempted++;
        snprintf(line, sizeof line,
                "IDECK_FILE_MMAP_PROBE_V1 phase=trial tid=%d tgid=%d trial=%u bytes=%zu prot=%d flags=%d mapped=%d map_errno=%d released=%d release_errno=%d original_result_preserved=1",
                tid, tgid, i, trial->bytes, trial->prot, trial->flags,
                mapped, map_error, released, release_error);
        IDECK_MMAP_PROBE_LOG(line);
        if (!released) { all_released = 0; break; }
    }
#if IDECK_LAB_VA_HEADROOM_PROBE
    if (all_released) ideck_va_headroom_probe(fd,bytes,offset,prot,flags,original_error);
#endif
    snprintf(line, sizeof line,
            "IDECK_FILE_MMAP_PROBE_V1 phase=end tid=%d tgid=%d attempted=%u all_released=%d original_result_preserved=1",
            tid, tgid, attempted, all_released);
    IDECK_MMAP_PROBE_LOG(line);
    errno = saved;
#else
    (void)tid; (void)tgid; (void)fd; (void)bytes; (void)offset;
    (void)prot; (void)flags; (void)original_error; (void)host_page;
#endif
}
