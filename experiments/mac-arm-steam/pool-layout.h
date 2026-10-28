// SPDX-License-Identifier: GPL-3.0-or-later
#ifndef IDECK_POOL_LAYOUT_H
#define IDECK_POOL_LAYOUT_H
#include <stddef.h>
#include <stdint.h>
typedef struct {uintptr_t base; size_t size;} IDeckPoolPlan;
int ideck_plan_pool(uintptr_t mapping,size_t span,size_t pool,size_t guard,IDeckPoolPlan *out);
#endif
