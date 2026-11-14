/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#ifndef IDECK_LAB_DOCK_REQUEST_BRIDGE_H
#define IDECK_LAB_DOCK_REQUEST_BRIDGE_H
#include <stddef.h>
#include <stdint.h>
/* Synchronous copy into one bounded native Swift slot, metadata ONLY.
 * Native caller owns the sequence/frame and must retain the original policy
 * request. This is NOT Wine admission, a license result or a game exit ACK. */
int32_t ideck_lab_receive_dock_request(const void *frame,size_t size,uint64_t sequence);
uint64_t ideck_lab_pending_dock_sequence(void);
#if IDECK_LAB_NATIVE_SETUP_TRANSITION
/* Same retained controller factory as the isolated cold native setup route.
 * Main-thread-only presentation; never starts a guest or enters credentials. */
void *ideck_lab_madeira_setup_controller(void);
#endif
#endif
