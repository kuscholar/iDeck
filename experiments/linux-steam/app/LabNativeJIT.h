/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#ifndef IDECK_LAB_NATIVE_JIT_H
#define IDECK_LAB_NATIVE_JIT_H
#include <stdint.h>
/* Classic activation disabled after actual Air protection failure. No BRK. */
int ideck_lab_native_jit_prepare_classic(void);
#define IDECK_LAB_DEBUGGER_JIT_MAGIC UINT64_C(0x49444a4954525831)
#define IDECK_LAB_DEBUGGER_JIT_BYTES (UINT64_C(120)<<20)
#if IDECK_LAB_DEBUGGER_PREPARED_JIT
extern volatile uint64_t ideck_lab_debugger_jit_offer[5];
int ideck_lab_native_jit_prepare_debugger(void);
#endif
struct ideck_lab_native_jit_stats {
    int activation_status; /* 0 not attempted, 1 region verified, -1 refused */
    uint64_t blocks,segments,code_bytes;
};
/* Read-only: does not initialise, activate, allocate or change an engine. */
void ideck_lab_native_jit_read(struct ideck_lab_native_jit_stats *stats);
#endif
