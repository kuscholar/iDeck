/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#import "RFBClient.h"
#if IDECK_LAB_RFB_LIFETIME
typedef struct {
    uint64_t started;
    uint64_t decoded;
} IDECKRFBDecodeProgress;

@interface LRRFBClient (LabCompletion)
/* Completion runs on main AFTER the decoder and all admitted input blocks
 * return, including callbacks/autorelease pools. No future starts/input admitted.
 * No timer-based success, group wait on main or Linux/game quiescence claim.
 */
- (void)ideckStopWithCompletion:(dispatch_block_t)completion;
/* One non-incremental request per connected viewer. Completion runs on the
 * input queue and means only that the request bytes were written locally. */
- (BOOL)ideckRequestFullRefreshWithCompletion:(void (^)(BOOL written))completion;
/* Connection counters. A decoded message can contain zero rectangles.
 * RFB replies do not identify their originating request. */
- (IDECKRFBDecodeProgress)ideckDecodeProgress;
@end
#endif
