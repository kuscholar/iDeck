/* SPDX-License-Identifier: LGPL-2.1-or-later */
#ifndef IDECK_CEF64_FIXED_GUARD_H
#define IDECK_CEF64_FIXED_GUARD_H
#include <stdint.h>

/* The owned-layout experiment must not satisfy a guest jumbo retry by
 * replacing the native FEX reservation. Small legacy fixed FEX allocations
 * are outside this narrow guard; this is not a general address-space broker.
 * End is exclusive; the request bounds, when present, use an inclusive high.
 */
static int cef64_fixed_fex_conflict(uint64_t base, uint64_t size,
                                   uint64_t arena, uint64_t end,
                                   uint64_t low, uint64_t high)
{
    if (!base || size < UINT64_C(0x40000000) || !arena || end <= arena) return 0;
    if (size > UINT64_MAX - base) return 1;
    if (base >= end || base + size <= arena) return 0;
    /* A genuine FEX allocation explicitly constrains the whole request to
     * its published arena. A bare fixed address is not that contract. */
    if (low >= arena && high >= low && high < end && base >= low &&
        base <= high && size - 1 <= high - base) return 0;
    return 1;
}
#endif
