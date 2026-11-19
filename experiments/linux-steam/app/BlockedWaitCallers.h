/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#ifndef IDECK_BLOCKED_WAIT_CALLERS_H
#define IDECK_BLOCKED_WAIT_CALLERS_H
#include <stdint.h>
struct mem;
#ifndef IDECK_WAIT_CALLER_LIMIT
#define IDECK_WAIT_CALLER_LIMIT 4
#endif
#if IDECK_WAIT_CALLER_LIMIT != 4 && IDECK_WAIT_CALLER_LIMIT != 8 && IDECK_WAIT_CALLER_LIMIT != 16
#error Select the original4 or explicit bounded8/16 caller frames only
#endif
struct ideck_wait_caller { uint64_t lr; uint32_t code[9]; };
struct ideck_wait_callers {
    unsigned count, status;
    struct ideck_wait_caller frames[IDECK_WAIT_CALLER_LIMIT];
};
/* Caller retains the mm lifetime. Nonblocking, existing PTEs ONLY. Read exactly
 * main-stack ABI next-FP/LR fields and file-backed executable instruction words.
 * No arbitrary stack/object/string buffers, guest-page faults or mutations.
 * Status:0 limit/end,1 lock busy,2 unavailable stack,3 unavailable code/call,
 * 4 invalid chain. Best effort only; caller must revalidate blocked CPU state.
 */
void ideck_blocked_wait_callers(struct mem *, uint64_t fp, struct ideck_wait_callers *);
const char *ideck_blocked_wait_callers_marker(void);
#endif
