// SPDX-License-Identifier: GPL-3.0-or-later
#include "pool-layout.h"
#include <assert.h>
#include <stdio.h>
int main(void) {
    IDeckPoolPlan plan={0};const size_t pool=256ULL<<20,guard=16384,span=pool*2+guard;
    for(uintptr_t base=0x100000000; base<0x200000000; base+=123457) {
        assert(ideck_plan_pool(base,span,pool,guard,&plan));
        assert(plan.base%pool==0 && plan.base-base>=guard && plan.base+pool<=base+span);
        uintptr_t mask=~(uintptr_t)(pool-1);
        assert((plan.base&mask)==plan.base && ((plan.base+pool-1)&mask)==plan.base);
        assert(((plan.base-1)&mask)!=plan.base && ((plan.base+pool)&mask)!=plan.base);
    }
    assert(!ideck_plan_pool(UINTPTR_MAX-guard,span,pool,guard,&plan));
    assert(!ideck_plan_pool(0x100000000,pool-1,pool,guard,&plan));
    assert(!ideck_plan_pool(0x100000000,span,pool+1,guard,&plan));
    assert(!ideck_plan_pool(0x100000000,span,pool,0,&plan));
    assert(!ideck_plan_pool(0x100000000,span,pool,guard,NULL));
    puts("small-pool plan PASS: alignment, mask boundaries, guard, containment, overflow and invalid inputs");
}
