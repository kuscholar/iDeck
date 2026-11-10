/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#include "JoinableGuests.h"
#include <errno.h>
#include <sys/types.h>
#include <unistd.h>
#ifndef IDECK_JOIN_GUEST_CAPACITY
#define IDECK_JOIN_GUEST_CAPACITY 4096
#endif
#if IDECK_HOST_JOIN_CREATE_EAGAIN && defined(__APPLE__)
#include <TargetConditionals.h>
#if TARGET_OS_IPHONE
#error Native start failure injection is HOST ONLY
#endif
#endif
static pthread_mutex_t join_registry_lock=PTHREAD_MUTEX_INITIALIZER;
static pthread_t join_registry_owner;
static pid_t join_registry_pid;
static unsigned join_registry_slots,join_registry_joined,join_registry_sealed,join_registry_joining;
static uint64_t join_registry_rejected;
static int join_registry_error;
static pthread_t join_registry_threads[IDECK_JOIN_GUEST_CAPACITY];
static int process_owner(void){return !join_registry_pid?-ENODEV:join_registry_pid!=getpid()?-EXDEV:0;}
static int serial_owner(void){int error=process_owner();return error?error:!pthread_equal(join_registry_owner,pthread_self())?-EPERM:0;}
int ideck_joinable_guests_initialize(void){
    pthread_mutex_lock(&join_registry_lock);int error=join_registry_pid?-EBUSY:0;
    if(!error){join_registry_pid=getpid();join_registry_owner=pthread_self();}
    pthread_mutex_unlock(&join_registry_lock);return error;
}
int ideck_joinable_guest_start(pthread_t *thread,const pthread_attr_t *attributes,void *(*entry)(void *),void *argument){
    if(!thread||!entry)return EINVAL;
    int state=PTHREAD_CREATE_JOINABLE;
    if(attributes){int error=pthread_attr_getdetachstate(attributes,&state);if(error)return error;}
    if(state!=PTHREAD_CREATE_JOINABLE)return EINVAL;
    pthread_mutex_lock(&join_registry_lock);int error=-process_owner();
    if(!error&&(join_registry_sealed||join_registry_error))error=EBUSY;
    if(!error&&join_registry_slots>=IDECK_JOIN_GUEST_CAPACITY)error=EAGAIN;
    if(!error){
#if IDECK_HOST_JOIN_CREATE_EAGAIN
        (void)attributes;(void)argument;error=EAGAIN;
#else
        // Publish a successful creation before seal() can close the start gate.
        // The child may already be executing, but cannot escape registration.
        error=pthread_create(thread,attributes,entry,argument);
#endif
        if(!error)join_registry_threads[join_registry_slots++]=*thread;
    }
    if(error)join_registry_rejected++;
    pthread_mutex_unlock(&join_registry_lock);return error;
}
int ideck_joinable_guests_seal(void){
    pthread_mutex_lock(&join_registry_lock);int error=serial_owner();
    if(!error)join_registry_sealed=1;
    pthread_mutex_unlock(&join_registry_lock);return error;
}
int ideck_joinable_guests_join(void){
    pthread_mutex_lock(&join_registry_lock);int error=serial_owner();
    if(!error&&(!join_registry_sealed||join_registry_joining||join_registry_error))error=-EBUSY;
    if(error){pthread_mutex_unlock(&join_registry_lock);return error;}
    join_registry_joining=1;
    while(join_registry_joined<join_registry_slots){
        pthread_t thread=join_registry_threads[join_registry_joined];
        pthread_mutex_unlock(&join_registry_lock);
        // pthread_join waits for pthread cleanup AND TLS destructors. An
        // entry-body counter reaching zero cannot replace this operation.
        int result=pthread_join(thread,NULL);
        pthread_mutex_lock(&join_registry_lock);
        if(result){join_registry_error=result;error=-result;break;}
        join_registry_joined++;
    }
    join_registry_joining=0;
    pthread_mutex_unlock(&join_registry_lock);return error;
}
int ideck_joinable_guests_snapshot(struct ideck_joinable_guests_snapshot *out){
    if(!out)return -EINVAL;
    pthread_mutex_lock(&join_registry_lock);int error=process_owner();
    *out=(struct ideck_joinable_guests_snapshot){.slots=join_registry_slots,.capacity=IDECK_JOIN_GUEST_CAPACITY,
        .joined=join_registry_joined,.sealed=join_registry_sealed,.joining=join_registry_joining,.rejected=join_registry_rejected,.error=join_registry_error,
        .all_registered_children_joined=!error&&join_registry_sealed&&!join_registry_joining&&!join_registry_error&&join_registry_joined==join_registry_slots};
    pthread_mutex_unlock(&join_registry_lock);return error;
}
