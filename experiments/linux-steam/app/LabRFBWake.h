/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#pragma once
#import "RFBClient.h"

/* Use the existing RFB queue for one move before the click. The press and
 * release are separate button transitions so neither coalesces with motion. */
static inline void ideck_rfb_wake(LRRFBClient *client, uint16_t x, uint16_t y) {
    uint16_t approachX = x >= 8 ? x - 8 : x + 1;
    [client pointerX:approachX y:y buttons:0];
    [client pointerX:x y:y buttons:1];
    [client pointerX:x y:y buttons:0];
}
