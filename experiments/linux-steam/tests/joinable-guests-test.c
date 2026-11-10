/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#include "JoinableGuests.h"
#include <assert.h>
#include <stdatomic.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <sys/wait.h>
#include <unistd.h>
#include <time.h>
static pthread_key_t key;
static pthread_mutex_t gate=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t wake=PTHREAD_COND_INITIALIZER;
static int released;
static atomic_int body_done,tls_started,tls_done,pending_observed;
static void tick(void){struct timespec delay={0,1000000};nanosleep(&delay,NULL);}
static void destructor(void *value){
    assert(value==(void *)1);pthread_mutex_lock(&gate);atomic_store(&tls_started,1);
    while(!released)assert(!pthread_cond_wait(&wake,&gate));
    pthread_mutex_unlock(&gate);atomic_store(&tls_done,1);
}
static void *entry(void *argument){assert(!pthread_setspecific(key,(void *)1));atomic_store(&body_done,1);return argument;}
static void *empty(void *argument){return argument;}
static void *foreign_owner(void *argument){(void)argument;assert(ideck_joinable_guests_seal()==-EPERM&&ideck_joinable_guests_join()==-EPERM);return NULL;}
static void *release_tls(void *argument){
    (void)argument;struct ideck_joinable_guests_snapshot observed;
    for(unsigned i=0;i<10000;i++){
        assert(!ideck_joinable_guests_snapshot(&observed));
        if(observed.joining){
            assert(observed.sealed&&observed.joined==0&&!observed.all_registered_children_joined);
            assert(atomic_load(&body_done)&&atomic_load(&tls_started)&&!atomic_load(&tls_done));
            atomic_store(&pending_observed,1);pthread_mutex_lock(&gate);released=1;pthread_cond_signal(&wake);pthread_mutex_unlock(&gate);return NULL;
        }
        tick();
    }
    assert(!"native join never became pending");return NULL;
}
int main(int argc,char **argv){
    if(argc!=2)return 2;
    struct ideck_joinable_guests_snapshot observed;assert(ideck_joinable_guests_snapshot(&observed)==-ENODEV);
    assert(!ideck_joinable_guests_initialize()&&ideck_joinable_guests_initialize()==-EBUSY);
    assert(ideck_joinable_guests_join()==-EBUSY);
    pid_t child=fork();assert(child>=0);if(!child)_exit(ideck_joinable_guests_seal()==-EXDEV?0:1);int status;assert(waitpid(child,&status,0)==child&&WIFEXITED(status)&&!WEXITSTATUS(status));
    pthread_t worker;
    if(!strcmp(argv[1],"failure")){
        for(unsigned i=0;i<1000;i++)assert(ideck_joinable_guest_start(&worker,NULL,empty,NULL)==EAGAIN);
        assert(!ideck_joinable_guests_snapshot(&observed)&&observed.slots==0&&observed.joined==0&&observed.rejected==1000);
        assert(!ideck_joinable_guests_seal()&&!ideck_joinable_guests_join());
        puts("native-creation-failure-no-reservation-leak=PASS");return 0;
    }
    assert(!strcmp(argv[1],"tls"));assert(!pthread_key_create(&key,destructor));
    pthread_attr_t attributes;assert(!pthread_attr_init(&attributes)&&!pthread_attr_setdetachstate(&attributes,PTHREAD_CREATE_DETACHED));
    assert(ideck_joinable_guest_start(&worker,&attributes,empty,NULL)==EINVAL);assert(!pthread_attr_destroy(&attributes));
    assert(!ideck_joinable_guest_start(&worker,NULL,entry,NULL));
    for(unsigned i=0;i<10000&&!atomic_load(&tls_started);i++)tick();assert(atomic_load(&body_done)&&atomic_load(&tls_started)&&!atomic_load(&tls_done));
    assert(!ideck_joinable_guests_snapshot(&observed)&&observed.slots==1&&observed.joined==0&&!observed.all_registered_children_joined);
    puts("entry-returned-while-native-tls-is-still-live=PASS");
    for(unsigned i=1;i<observed.capacity;i++)assert(!ideck_joinable_guest_start(&worker,NULL,empty,NULL));
    assert(ideck_joinable_guest_start(&worker,NULL,empty,NULL)==EAGAIN);
    assert(!pthread_create(&worker,NULL,foreign_owner,NULL)&&!pthread_join(worker,NULL));
    assert(!ideck_joinable_guests_seal());assert(ideck_joinable_guest_start(&worker,NULL,empty,NULL)==EBUSY);
    assert(!pthread_create(&worker,NULL,release_tls,NULL));assert(!ideck_joinable_guests_join());assert(!pthread_join(worker,NULL));
    assert(atomic_load(&pending_observed)&&atomic_load(&tls_done));assert(!ideck_joinable_guests_snapshot(&observed));
    assert(observed.slots==observed.capacity&&observed.joined==observed.capacity&&observed.all_registered_children_joined&&!observed.joining&&!observed.error);
    assert(!ideck_joinable_guests_join()&&!pthread_key_delete(key));
    puts("join-waits-for-tls-and-all-owned-child-pthreads=PASS");puts("seal-capacity-native-owner-and-detached-refusal=PASS");
    puts("scope=HOST_CHILD_PTHREADS_ONLY_NOT_LINUX_QUIESCENCE_WINE_OR_DEVICE");return 0;
}
