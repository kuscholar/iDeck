/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#ifndef IDECK_CHECKED_FRAME_SNAPSHOT_H
#define IDECK_CHECKED_FRAME_SNAPSHOT_H
#include <stdint.h>
struct ideck_frame_snapshot_stats {
    uint64_t calls,failures,live_frames,live_bytes,peak_live_bytes,releases;
};
void ideck_frame_snapshot_stats_read(struct ideck_frame_snapshot_stats * _Nullable);
const char * _Nonnull ideck_frame_snapshot_marker(void);
#ifdef __OBJC__
#import <Foundation/Foundation.h>
/* Validated immutable independent copy; nil means stop display via existing
 * failure path. No alias of the mutable decoder pixels, no retry/fake frame.
 * Only the pixel allocation is checked; tiny Foundation object allocation is
 * not made infallible and no Objective-C exceptions are intercepted. */
NSData * _Nullable ideck_checked_frame_snapshot(NSData * _Nullable,uint16_t,uint16_t);
#endif
#endif
