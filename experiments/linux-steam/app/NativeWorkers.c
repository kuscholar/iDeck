/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#include "NativeWorkers.h"
#include <stdatomic.h>
#include <stdbool.h>
#include <limits.h>
#include <errno.h>
#if IDECK_LAB_JOIN_NATIVE_WORKERS
#include "NativeWorkerJoins.h"
#endif
#if IDECK_HOST_WORKER_CREATE_EAGAIN && defined(__APPLE__)
#include <TargetConditionals.h>
#if TARGET_OS_IPHONE
#error Worker-start failure injection is a host-only control
#endif
#endif
static atomic_uint counts[IDECK_WORKER_KINDS];
static atomic_bool invalid;
static int valid(enum ideck_worker_kind kind){return (unsigned)kind<IDECK_WORKER_KINDS;}
static void retire(enum ideck_worker_kind kind){
    unsigned value=atomic_load_explicit(&counts[kind],memory_order_acquire);
    do{
        if(!value){atomic_store(&invalid,true);return;}
    }while(!atomic_compare_exchange_weak_explicit(&counts[kind],&value,value-1,memory_order_acq_rel,memory_order_acquire));
}
int ideck_native_worker_start(enum ideck_worker_kind kind,pthread_t *thread,
    const pthread_attr_t *attributes,void *(*entry)(void *),void *argument){
    if(!valid(kind)||!thread||!entry)return EINVAL;
    unsigned n=atomic_fetch_add_explicit(&counts[kind],1,memory_order_acq_rel);
    if(n>=INT_MAX)atomic_store(&invalid,true);
#if IDECK_HOST_WORKER_CREATE_EAGAIN
    (void)attributes;(void)argument;
    int error=EAGAIN; /* explicitly generated HOST-ONLY negative archive */
#elif IDECK_LAB_JOIN_NATIVE_WORKERS
    int error=ideck_worker_joins_start(kind,thread,attributes,entry,argument);
#else
    int error=pthread_create(thread,attributes,entry,argument);
#endif
    if(error)retire(kind);
    return error;
}
void ideck_native_worker_retire_timer(void *unused){(void)unused;retire(IDECK_WORKER_TIMER);}
void ideck_native_worker_retire_profile(void *unused){(void)unused;retire(IDECK_WORKER_PROFILE);}
void ideck_native_worker_retire_tty(void *unused){(void)unused;retire(IDECK_WORKER_TTY);}
void ideck_native_worker_retire_forward(void *unused){(void)unused;retire(IDECK_WORKER_FORWARD);}
int ideck_native_workers_live(enum ideck_worker_kind kind){
    if(!valid(kind)||atomic_load_explicit(&invalid,memory_order_acquire))return -1;
    unsigned value=atomic_load_explicit(&counts[kind],memory_order_acquire);
    return value>INT_MAX?-1:(int)value;
}
int ideck_native_workers_total(void){
    unsigned total=0;
    for(unsigned i=0;i<IDECK_WORKER_KINDS;i++){
        int n=ideck_native_workers_live((enum ideck_worker_kind)i);
        if(n<0||(unsigned)n>INT_MAX-total)return -1;
        total+=(unsigned)n;
    }
    return (int)total;
}
const char *ideck_native_workers_marker(void){return "IDECK_NATIVE_WORKERS_V1";}
