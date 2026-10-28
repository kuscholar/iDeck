// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
#include "pool-layout.h"
#include <stdint.h>
int ideck_plan_pool(uintptr_t mapping,size_t span,size_t pool,size_t guard,IDeckPoolPlan *out) {
    if(!out || !mapping || !pool || (pool&(pool-1)) || !guard || guard>pool) return 0;
    if(mapping>UINTPTR_MAX-span || mapping>UINTPTR_MAX-guard) return 0;
    uintptr_t start=mapping+guard;
    if(start>UINTPTR_MAX-(pool-1)) return 0;
    uintptr_t base=(start+pool-1)&~(uintptr_t)(pool-1);
    if(base>UINTPTR_MAX-pool || base+pool>mapping+span) return 0;
    out->base=base;out->size=pool;return 1;
}
