/* SPDX-License-Identifier: LGPL-2.1-or-later */
#ifndef MADEIRA_X18_SIGNED_LOAD_H
#define MADEIRA_X18_SIGNED_LOAD_H
#include <stdint.h>
#include <string.h>
/* ARM64 LDRSW Xt,[Xn,#imm12*4], including XZR target. Called only
 * after the existing Mach handler has validated the fault as a TEB access. */
static inline int ios_x18_ldrsw(uint32_t insn, uintptr_t address, uint64_t *value)
{
    int32_t word;
    if ((insn & 0xffc00000u) != 0xb9800000u) return 0;
    memcpy(&word, (const void *)address, sizeof word);
    *value = (uint64_t)(int64_t)word;
    return 1;
}
#endif
