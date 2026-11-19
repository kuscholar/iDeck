/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#ifndef IDECK_SHARED_FILE_RESERVE_H
#define IDECK_SHARED_FILE_RESERVE_H
#include <stddef.h>
#include <stdint.h>
#include <sys/types.h>
#define IDECK_FILE_RESERVE_BYTES (16u * 1024u * 1024u)
struct ideck_file_reserve_stats {
    unsigned state, slots, live, quarantined;
    size_t page_bytes, live_bytes, peak_bytes;
    uint64_t attempts, mapped, released, capacity_refusals, map_failures;
    uint64_t release_failures, invalid_releases;
};
/* One native lifetime. Ordinary mappings, code/JIT and guest addresses are not
 * accepted here. A failed map/cleanup quarantines the reserve, never retries. */
int ideck_file_reserve_prepare(void);
void *ideck_file_reserve_after_enomem(int fd, size_t bytes, off_t offset,
                                     int prot, int flags, int original_errno);
/* 0: outside this reserve; 1: owned mapping released; negative: owned/refused.
 * A negative result must NEVER fall through to another native munmap. */
int ideck_file_reserve_release(void *pointer, size_t bytes);
int ideck_file_reserve_snapshot(struct ideck_file_reserve_stats *out);
/* Only after all Linux users have stopped and every owned mapping is released.
 * No reinitialization or Linux restart is allowed after this terminal drain. */
int ideck_file_reserve_drain(void);
const char *ideck_file_reserve_marker(void);
#endif
