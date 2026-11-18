/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#ifndef IDECK_FRAME_SNAPSHOT_POOL_H
#define IDECK_FRAME_SNAPSHOT_POOL_H
#include <stdint.h>
enum { IDECK_FRAME_POOL_SLOTS=4 };
struct ideck_frame_pool_stats {
    uint64_t preparations,allocation_failures,native_buffers,native_bytes;
    uint64_t calls,invalid,exhausted,live_slots,peak_slots,releases;
};
void ideck_frame_pool_stats_read(struct ideck_frame_pool_stats * _Nullable);
#ifdef __OBJC__
#import <Foundation/Foundation.h>
/* Prepare before Linux. A snapshot's last consumer returns its slot. Pool
 * ownership survives controller teardown while ANY snapshot is retained.
 * No late pixel allocations, blocking waits, retries, mutable alias or resize.
 * Tiny Foundation object allocations are not made infallible. */
@interface IDECKFrameSnapshotPool : NSObject
- (nullable instancetype)initWithWidth:(uint16_t)width height:(uint16_t)height;
- (nullable NSData *)snapshotPixels:(nullable NSData *)pixels width:(uint16_t)width height:(uint16_t)height;
@end
#endif
#endif
