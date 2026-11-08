/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#include "GuestLifetime.h"
#include <stdatomic.h>
#include <limits.h>
#include <stdbool.h>
static atomic_uint pending_or_running;
static atomic_bool invalid;
void ideck_guest_lifetime_reserve(void) {
    unsigned n=atomic_fetch_add_explicit(&pending_or_running,1,memory_order_acq_rel);
    if(n==UINT_MAX)atomic_store(&invalid,true);
}
void ideck_guest_lifetime_retire(void *unused) {
    (void)unused;
    unsigned value=atomic_load_explicit(&pending_or_running,memory_order_acquire);
    do {
        if(!value){atomic_store(&invalid,true);return;}
    } while(!atomic_compare_exchange_weak_explicit(&pending_or_running,&value,value-1,memory_order_acq_rel,memory_order_acquire));
}
unsigned ideck_guest_lifetime_live(void) {
    return atomic_load(&invalid)?UINT_MAX:atomic_load_explicit(&pending_or_running,memory_order_acquire);
}
const char *ideck_guest_lifetime_marker(void){return "IDECK_GUEST_LIFETIME_V1";}
