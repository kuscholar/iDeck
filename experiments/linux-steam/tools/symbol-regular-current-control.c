/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * HOST synthetic ordinary global; compile WITHOUT Linux namespace include.
 * This models the name/type collision, not Wine behavior or authentication.
 */
#include <stdint.h>
uintptr_t current = UINT64_C(0x55aa11223344);
uintptr_t *ideck_test_regular_current(void) { return &current; }
