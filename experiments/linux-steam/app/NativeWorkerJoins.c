/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#include "NativeWorkerJoins.h"
#include <errno.h>
#include <stdatomic.h>
#include <string.h>
#include <sys/types.h>
#include <unistd.h>
#ifndef IDECK_WORKER_JOIN_CAPACITY
#define IDECK_WORKER_JOIN_CAPACITY 4096
#endif
#if (IDECK_HOST_WORKER_JOIN_CREATE_EAGAIN || IDECK_HOST_WORKER_JOIN_FAILURE) && defined(__APPLE__)
#include <TargetConditionals.h>
#if TARGET_OS_IPHONE
#error Join failure injection is HOST ONLY
#endif
#endif
static pthread_mutex_t registry_lock=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t changed=PTHREAD_COND_INITIALIZER;
static _Atomic pid_t owner_pid;
static pthread_t owner_thread,reaper_thread;
struct entry {
    pthread_t thread;
    void *(*body)(void *);
    void *argument;
    uint64_t generation;
    enum ideck_worker_kind kind;
    unsigned active,body_done,joining;
};
static struct entry entries[IDECK_WORKER_JOIN_CAPACITY];
static uint64_t generation,started,reaped,externally_joined,rejected;
static unsigned active,sealed,reaper_started,reaper_joined,finishing;
static int fault;
static int process_owner(void){
    pid_t pid=atomic_load_explicit(&owner_pid,memory_order_acquire);
    /* Check before locking: a foreign fork must never touch an inherited lock. */
    return !pid?-ENODEV:pid!=getpid()?-EXDEV:0;
}
static int serial_owner(void){int err=process_owner();return err?err:!pthread_equal(owner_thread,pthread_self())?-EPERM:0;}
int ideck_worker_joins_owner_check(void){return serial_owner();}
#if !IDECK_HOST_WORKER_JOIN_CREATE_EAGAIN
static void body_done(void *argument){
    struct entry *e=argument;
    pthread_mutex_lock(&registry_lock);
    if(!e->active||e->body_done)fault=EPROTO;
    else e->body_done=1;
    pthread_cond_broadcast(&changed);pthread_mutex_unlock(&registry_lock);
}
static void *trampoline(void *argument){
    struct entry *e=argument;void *result;
    pthread_cleanup_push(body_done,e);
    result=e->body(e->argument);
    pthread_cleanup_pop(1);
    return result;
}
#endif
static int join_managed(pthread_t thread){
#if IDECK_HOST_WORKER_JOIN_FAILURE
    (void)thread;return EINVAL;
#else
    return pthread_join(thread,NULL);
#endif
}
static void *reaper(void *unused){
    (void)unused;pthread_mutex_lock(&registry_lock);
    for(;;){
        struct entry *e=NULL;
        if(fault)break;
        for(unsigned i=0;i<IDECK_WORKER_JOIN_CAPACITY;i++)
            if(entries[i].active&&entries[i].kind!=IDECK_WORKER_FORWARD&&entries[i].body_done&&!entries[i].joining){e=&entries[i];break;}
        if(!e){
            if(sealed&&!active)break;
            pthread_cond_wait(&changed,&registry_lock);continue;
        }
        e->joining=1;uint64_t id=e->generation;pthread_t thread=e->thread;
        pthread_mutex_unlock(&registry_lock);
        /* No Linux/creator lock held. Body completion does not cover TLS. */
        int error=join_managed(thread);
        pthread_mutex_lock(&registry_lock);
        if(error){fault=error;break;}
        if(!e->active||e->generation!=id||!e->body_done){fault=EPROTO;break;}
        memset(e,0,sizeof *e);active--;reaped++;
        pthread_cond_broadcast(&changed);
    }
    pthread_cond_broadcast(&changed);pthread_mutex_unlock(&registry_lock);return NULL;
}
int ideck_worker_joins_initialize(void){
    pid_t previous=atomic_load_explicit(&owner_pid,memory_order_acquire);
    if(previous)return previous==getpid()?-EBUSY:-EXDEV;
    pthread_mutex_lock(&registry_lock);int error=atomic_load(&owner_pid)?EBUSY:0;
    if(!error){
        owner_thread=pthread_self();atomic_store_explicit(&owner_pid,getpid(),memory_order_release);
        error=pthread_create(&reaper_thread,NULL,reaper,NULL);
        if(error)fault=error;else reaper_started=1;
    }
    pthread_mutex_unlock(&registry_lock);return -error;
}
int ideck_worker_joins_start(enum ideck_worker_kind kind,pthread_t *thread,const pthread_attr_t *attributes,void *(*body)(void *),void *argument){
    int error=-process_owner();if(error)return error;
    if((unsigned)kind>=IDECK_WORKER_KINDS||!thread||!body)return EINVAL;
    if(attributes){int state;error=pthread_attr_getdetachstate(attributes,&state);if(error)return error;if(state!=PTHREAD_CREATE_JOINABLE)return EINVAL;}
    pthread_mutex_lock(&registry_lock);
    if(sealed||fault)error=EBUSY;
    struct entry *e=NULL;
    if(!error){
        for(unsigned i=0;i<IDECK_WORKER_JOIN_CAPACITY;i++)if(!entries[i].active){e=&entries[i];break;}
        if(!e)error=EAGAIN;
    }
    if(!error){
        *e=(struct entry){.body=body,.argument=argument,.generation=++generation,.kind=kind,.active=1};
#if IDECK_HOST_WORKER_JOIN_CREATE_EAGAIN
        error=EAGAIN;
#else
        /* The new thread cannot publish completion/reuse while this lock is
         * held. Registration is complete before the caller sees its handle. */
        error=pthread_create(&e->thread,attributes,trampoline,e);
#endif
        if(error)memset(e,0,sizeof *e);
        else {*thread=e->thread;active++;started++;}
    }
    if(error)rejected++;
    pthread_mutex_unlock(&registry_lock);return error;
}
int ideck_worker_joins_external(pthread_t thread,void **result){
    int error=-process_owner();if(error)return error;
    if(pthread_equal(thread,pthread_self()))return EDEADLK;
    pthread_mutex_lock(&registry_lock);struct entry *e=NULL;
    for(unsigned i=0;i<IDECK_WORKER_JOIN_CAPACITY;i++)
        if(entries[i].active&&entries[i].kind==IDECK_WORKER_FORWARD&&!entries[i].joining&&pthread_equal(entries[i].thread,thread)){e=&entries[i];break;}
    if(!e){pthread_mutex_unlock(&registry_lock);return ESRCH;}
    e->joining=1;uint64_t id=e->generation;
    pthread_mutex_unlock(&registry_lock);
    error=pthread_join(thread,result);
    pthread_mutex_lock(&registry_lock);
    if(error){fault=error;}
    else if(!e->active||e->generation!=id||!e->body_done){fault=EPROTO;error=EPROTO;}
    else {memset(e,0,sizeof *e);active--;externally_joined++;}
    pthread_cond_broadcast(&changed);pthread_mutex_unlock(&registry_lock);return error;
}
int ideck_worker_joins_seal(void){
    int error=serial_owner();if(error)return error;
    pthread_mutex_lock(&registry_lock);sealed=1;pthread_cond_broadcast(&changed);pthread_mutex_unlock(&registry_lock);return 0;
}
int ideck_worker_joins_finish(void){
    int error=serial_owner();if(error)return error;
    pthread_mutex_lock(&registry_lock);
    if(!sealed||finishing){pthread_mutex_unlock(&registry_lock);return -EBUSY;}
    if(reaper_joined){error=-fault;pthread_mutex_unlock(&registry_lock);return error;}
    if(!reaper_started){error=fault?-fault:-ENODEV;pthread_mutex_unlock(&registry_lock);return error;}
    finishing=1;pthread_mutex_unlock(&registry_lock);
    /* Can stay pending for real live/TLS-held workers; no cancel/timeout lie. */
    int joined=pthread_join(reaper_thread,NULL);
    pthread_mutex_lock(&registry_lock);finishing=0;
    if(joined)fault=joined;else reaper_joined=1;
    error=fault?-fault:active?-EBUSY:0;
    pthread_mutex_unlock(&registry_lock);return error;
}
int ideck_worker_joins_snapshot(struct ideck_worker_joins_snapshot *out){
    if(!out)return -EINVAL;
    int error=process_owner();if(error)return error;
    pthread_mutex_lock(&registry_lock);
    *out=(struct ideck_worker_joins_snapshot){.started=started,.reaped=reaped,.externally_joined=externally_joined,.rejected=rejected,.capacity=IDECK_WORKER_JOIN_CAPACITY,.active=active,.sealed=sealed,.reaper_started=reaper_started,.reaper_joined=reaper_joined,.error=fault,
        .all_tracked_worker_threads_joined=sealed&&reaper_joined&&!fault&&!active&&started==reaped+externally_joined};
    for(unsigned i=0;i<IDECK_WORKER_JOIN_CAPACITY;i++)if(entries[i].active){
        if(entries[i].kind==IDECK_WORKER_FORWARD)out->external++;else out->managed++;
        out->joining+=entries[i].joining;
    }
    pthread_mutex_unlock(&registry_lock);return 0;
}
int ideck_worker_joins_begin_next_wave(void){
#if IDECK_LAB_WORKER_WAVES
    int error=serial_owner();if(error)return error;
    pthread_mutex_lock(&registry_lock);
    if(!sealed||finishing||!reaper_joined||active||fault)error=-EBUSY;
    if(!error){
        /* All old handles including the reaper have actually joined. No
         * provider globals are reset; especially no profiler revival. */
        int created=pthread_create(&reaper_thread,NULL,reaper,NULL);
        if(created){fault=created;error=-created;}
        else {sealed=0;reaper_started=1;reaper_joined=0;}
    }
    pthread_mutex_unlock(&registry_lock);return error;
#else
    return -ENOTSUP;
#endif
}
