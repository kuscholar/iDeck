// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
#ifndef IDECK_MAC_COMPACT_ALLOCATOR_H
#define IDECK_MAC_COMPACT_ALLOCATOR_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
struct IDeckMacAllocatorResult {
    uint64_t abi, compiled_mac, allocations, frees, failures;
    uint64_t pool_bytes, disjoint, cleaned, glued;
};
#ifdef __cplusplus
static_assert(sizeof(IDeckMacAllocatorResult)==72, "Fixed cross-platform result ABI");
#else
_Static_assert(sizeof(struct IDeckMacAllocatorResult)==72, "Fixed cross-platform result ABI");
#endif
int IDeckRunMacAllocator(struct IDeckMacAllocatorResult*, uint64_t);
#ifdef __cplusplus
}
#endif
#endif
