/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#include "WineInitialJoin.h"
#include <errno.h>
#include <stdlib.h>
#include <unistd.h>
static pthread_mutex_t lock=PTHREAD_MUTEX_INITIALIZER;
static pid_t owner;
static struct ideck_wine_initial_snapshot state;
struct watch { pthread_t thread; uint64_t generation; };
static void *observe(void *opaque) {
    struct watch *watch=opaque;
    int error=pthread_join(watch->thread,NULL);
    pthread_mutex_lock(&lock);
    if(owner==getpid()&&state.generation==watch->generation){
        if(!error)state.initial_joined=1;
        if(error&&!state.observer_error)state.observer_error=error;
        state.phase=state.observer_error?IDECK_WINE_INITIAL_OBSERVER_FAILED:IDECK_WINE_INITIAL_JOINED;
    }
    pthread_mutex_unlock(&lock);
    free(watch);return NULL;
}
int ideck_lab_wine_initial_create(pthread_t *thread,const pthread_attr_t *attributes,void *(*entry)(void *),void *argument) {
    if(!thread||!entry)return EINVAL;
    int detach=PTHREAD_CREATE_JOINABLE;
    if(attributes){int error=pthread_attr_getdetachstate(attributes,&detach);if(error)return error;}
    if(detach!=PTHREAD_CREATE_JOINABLE)return EINVAL;
    struct watch *watch=malloc(sizeof *watch);if(!watch)return ENOMEM;
    pthread_mutex_lock(&lock);
    if((owner&&owner!=getpid())||state.phase==IDECK_WINE_INITIAL_ACTIVE||state.phase==IDECK_WINE_INITIAL_OBSERVER_FAILED){
        int error=owner&&owner!=getpid()?EXDEV:EBUSY;pthread_mutex_unlock(&lock);free(watch);return error;
    }
    if(state.generation==UINT64_MAX){pthread_mutex_unlock(&lock);free(watch);return EOVERFLOW;}
    owner=getpid();state=(struct ideck_wine_initial_snapshot){.generation=state.generation+1};
    int error=pthread_create(thread,attributes,entry,argument);
    if(error){state.phase=IDECK_WINE_INITIAL_START_FAILED;state.create_error=error;pthread_mutex_unlock(&lock);free(watch);return error;}
    state.phase=IDECK_WINE_INITIAL_ACTIVE;state.initial_created=1;
    watch->thread=*thread;watch->generation=state.generation;
    pthread_t observer;error=pthread_create(&observer,NULL,observe,watch);
    if(error){
        /* Preserve the joinable game thread. No detach/cancel or false exit. */
        state.phase=IDECK_WINE_INITIAL_OBSERVER_FAILED;state.observer_error=error;free(watch);
    }else{
        /* Only the observer is detached; it runs no Wine body or guest TLS. */
        error=pthread_detach(observer);
        if(error){state.phase=IDECK_WINE_INITIAL_OBSERVER_FAILED;state.observer_error=error;}
    }
    pthread_mutex_unlock(&lock);
    return 0; /* The actual initial thread was created, even on observer failure. */
}
int ideck_lab_wine_initial_snapshot(struct ideck_wine_initial_snapshot *out) {
    if(!out)return EINVAL;
    pthread_mutex_lock(&lock);int error=owner&&owner!=getpid()?EXDEV:0;
    if(!error)*out=state;
    pthread_mutex_unlock(&lock);return error;
}
int ideck_lab_wine_initial_ready(void) {
    struct ideck_wine_initial_snapshot value;
    int error=ideck_lab_wine_initial_snapshot(&value);if(error)return error;
    return value.phase==IDECK_WINE_INITIAL_ACTIVE||value.phase==IDECK_WINE_INITIAL_OBSERVER_FAILED?EBUSY:0;
}
