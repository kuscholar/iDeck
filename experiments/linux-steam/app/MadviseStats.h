/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#ifndef IDECK_MADVISE_STATS_H
#define IDECK_MADVISE_STATS_H
#include <stdint.h>
struct ideck_madvise_stats {
    uint64_t calls,dontneed_calls,dontneed_requested_bytes,free_calls,free_requested_bytes;
};
/* Independent relaxed atomic totals; requested bytes are NOT reclaimed bytes.
 * No addresses, guest contents, process names or argv are collected. */
void ideck_madvise_stats_read(struct ideck_madvise_stats *out);
const char *ideck_madvise_stats_marker(void);
#endif
