/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#include "WineInitialJoin.h"
#include <errno.h>
#include <mach/mach.h>
#include <stdlib.h>
#include <unistd.h>
static pthread_mutex_t lock=PTHREAD_MUTEX_INITIALIZER;
static pid_t owner;
static pthread_t initial_thread;
static struct ideck_wine_initial_snapshot state;
enum { THREAD_LIMIT = 1024 };
struct thread_sample {
    uint64_t ids[THREAD_LIMIT];
    unsigned count;
};
static struct thread_sample baseline;
static int baseline_error;
static uint64_t observer_id;

static int sample_threads(struct thread_sample *out, uint64_t exclude) {
    thread_act_array_t threads = NULL;
    mach_msg_type_number_t count = 0;
    const task_t self = mach_task_self();
    if (task_threads(self, &threads, &count) != KERN_SUCCESS) return EIO;

    int error = count > THREAD_LIMIT ? EOVERFLOW : 0;
    out->count = 0;
    for (mach_msg_type_number_t i = 0; i < count; i++) {
        if (!error) {
            thread_identifier_info_data_t identity;
            mach_msg_type_number_t size = THREAD_IDENTIFIER_INFO_COUNT;
            if (thread_info(threads[i], THREAD_IDENTIFIER_INFO, (thread_info_t)&identity, &size) != KERN_SUCCESS ||
                size != THREAD_IDENTIFIER_INFO_COUNT || !identity.thread_id) {
                error = EIO;
            } else if (identity.thread_id != exclude) {
                out->ids[out->count++] = identity.thread_id;
            }
        }
        if (mach_port_deallocate(self, threads[i]) != KERN_SUCCESS) error = EIO;
    }
    if (threads && vm_deallocate(self, (vm_address_t)threads, count * sizeof(*threads)) != KERN_SUCCESS)
        error = EIO;
    return error;
}

struct watch { pthread_t thread; uint64_t generation; };
static void *observe(void *opaque) {
    struct watch *watch=opaque;
    int error=pthread_join(watch->thread,NULL);
    uint64_t thread_id = 0;
    int identity_error = pthread_threadid_np(NULL, &thread_id);
    pthread_mutex_lock(&lock);
    if(owner==getpid()&&state.generation==watch->generation){
        if(!error)state.initial_joined=1;
        if (!identity_error) observer_id = thread_id;
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
    observer_id = 0;
    baseline_error = sample_threads(&baseline, 0);
    int error=pthread_create(thread,attributes,entry,argument);
    if(error){state.phase=IDECK_WINE_INITIAL_START_FAILED;state.create_error=error;pthread_mutex_unlock(&lock);free(watch);return error;}
    state.phase=IDECK_WINE_INITIAL_ACTIVE;state.initial_created=1;
    initial_thread=*thread;
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
int ideck_lab_wine_initial_report_result(unsigned source,uint32_t code) {
    if((source!=IDECK_WINE_BODY_NORMAL_RETURN&&source!=IDECK_WINE_BODY_LONGJMP)||
       (source==IDECK_WINE_BODY_NORMAL_RETURN&&code))return EINVAL;
    pthread_mutex_lock(&lock);
    int error=!owner||!state.initial_created?ENODEV:owner!=getpid()?EXDEV:
        !pthread_equal(initial_thread,pthread_self())?EPERM:
        state.body_result_source?EALREADY:state.initial_joined?ESTALE:0;
    if(!error){state.body_result_source=source;state.body_exit_code=code;}
    pthread_mutex_unlock(&lock);return error;
}
int ideck_lab_wine_initial_report_server_join(int attempted,int join_error,unsigned main_outcome) {
    if((attempted!=0&&attempted!=1)||join_error<0||(!attempted&&join_error)||
       main_outcome>IDECK_WINE_SERVER_MAIN_RETURNED_NONZERO||
       ((!attempted||join_error)&&main_outcome!=IDECK_WINE_SERVER_MAIN_UNKNOWN))return EINVAL;
    pthread_mutex_lock(&lock);
    int error=!owner||!state.initial_created?ENODEV:owner!=getpid()?EXDEV:
        !pthread_equal(initial_thread,pthread_self())?EPERM:
        state.server_join_state?EALREADY:state.initial_joined?ESTALE:0;
    if(!error){
        state.server_join_error=join_error;
        state.server_main_outcome=main_outcome;
        if(!attempted)state.server_join_state=IDECK_WINE_SERVER_NO_HANDLE;
        else state.server_join_state=join_error?IDECK_WINE_SERVER_JOIN_FAILED:IDECK_WINE_SERVER_JOINED;
    }
    pthread_mutex_unlock(&lock);
    return error;
}
int ideck_lab_wine_thread_census(uint64_t generation, struct ideck_wine_thread_census *out) {
    if (!out || !generation) return EINVAL;
    *out = (struct ideck_wine_thread_census){0};
    pthread_mutex_lock(&lock);
    int error = !owner ? ENODEV : owner != getpid() ? EXDEV :
        generation != state.generation ? ESTALE :
        !state.initial_joined || state.observer_error ? EBUSY :
        !observer_id ? EIO : baseline_error;
    if (!error) {
        struct thread_sample current;
        error = sample_threads(&current, observer_id);
        if (!error) {
            out->baseline_count = baseline.count;
            out->current_count = current.count;
            for (unsigned i = 0; i < current.count; i++) {
                unsigned j = 0;
                while (j < baseline.count && baseline.ids[j] != current.ids[i]) j++;
                if (j == baseline.count) out->started_since_baseline++;
            }
        }
    }
    pthread_mutex_unlock(&lock);
    return error;
}

int ideck_lab_wine_initial_ready(void) {
    struct ideck_wine_initial_snapshot value;
    int error=ideck_lab_wine_initial_snapshot(&value);if(error)return error;
    return value.phase==IDECK_WINE_INITIAL_ACTIVE||value.phase==IDECK_WINE_INITIAL_OBSERVER_FAILED?EBUSY:0;
}
