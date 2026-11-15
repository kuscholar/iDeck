/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#ifndef IDECK_COW_BACKING_BROKER_H
#define IDECK_COW_BACKING_BROKER_H
#include <stddef.h>
#include <stdint.h>
/* One native-page slot per private CoW object, independently aligned. Whole
 * chunks are actual kernel-owned anonymous RW mappings at kernel-chosen
 * addresses. No guest/file/shared mapping, fixed address or soft reservation.
 * Allocation failure is returned, never substituted with an overlapping grant.
 */
void *ideck_cow_broker_allocate(size_t bytes);
/* 1: exact owned allocation released; 0: foreign pointer, original path owns it;
 * negative errno: pointer inside an active chunk violates the ownership record.
 * A failed last-chunk munmap preserves that allocation and its ownership record.
 */
int ideck_cow_broker_release_owned(void *address,size_t bytes);
struct ideck_cow_broker_stats {
    uint64_t allocation_calls,release_calls,map_attempts,map_failures,unmap_calls;
    uint64_t live_slots,live_guest_bytes,live_chunks,reserved_native_bytes;
    uint64_t ownership_errors,native_unmap_failures,overlap_rejections,capacity_refusals;
    uint64_t advice_calls,advice_failures;
};
void ideck_cow_broker_read_stats(struct ideck_cow_broker_stats *out);
const char *ideck_cow_broker_marker(void);
#endif
