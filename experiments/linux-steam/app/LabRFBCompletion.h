/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#import "RFBClient.h"
#if IDECK_LAB_RFB_LIFETIME
@interface LRRFBClient (LabCompletion)
/* Completion runs on main AFTER the decoder and all admitted input blocks
 * return, including callbacks/autorelease pools. No future starts/input admitted.
 * No timer-based success, group wait on main or Linux/game quiescence claim.
 */
- (void)ideckStopWithCompletion:(dispatch_block_t)completion;
@end
#endif
