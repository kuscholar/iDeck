/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#include "NativeWorkerJoins.h"
#include <assert.h>
#include <errno.h>
#include <stdatomic.h>
#include <stdio.h>
#include <string.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>
static pthread_mutex_t gate=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t wake=PTHREAD_COND_INITIALIZER;
static pthread_key_t tls_key;
static int released;
static atomic_int tls_started,tls_done,pending_observed;
struct job {enum ideck_worker_kind kind;int tls,wait;};
static struct job simple={IDECK_WORKER_TIMER,0,0};
static void tick(void){struct timespec t={0,1000000};nanosleep(&t,NULL);}
static void release(void){pthread_mutex_lock(&gate);released=1;pthread_cond_broadcast(&wake);pthread_mutex_unlock(&gate);}
static void wait_gate(void){pthread_mutex_lock(&gate);while(!released)assert(!pthread_cond_wait(&wake,&gate));pthread_mutex_unlock(&gate);}
static void destructor(void *value){assert(value==(void *)1);atomic_store(&tls_started,1);wait_gate();atomic_store(&tls_done,1);}
static void retire(void *argument){
    struct job *job=argument;
    if(job->kind==IDECK_WORKER_FORWARD)ideck_native_worker_retire_forward(NULL);
    else ideck_native_worker_retire_timer(NULL);
}
static void *entry(void *argument){
    struct job *job=argument;
    pthread_cleanup_push(retire,job);
    if(job->tls)assert(!pthread_setspecific(tls_key,(void *)1));
    if(job->wait)wait_gate();
    pthread_cleanup_pop(1);
    return (void *)13;
}
static void *foreign(void *unused){
    (void)unused;assert(ideck_worker_joins_seal()==-EPERM&&ideck_worker_joins_finish()==-EPERM);return NULL;
}
static void *release_tls(void *argument){
    int external=argument!=NULL;struct ideck_worker_joins_snapshot s;
    for(unsigned i=0;i<10000;i++){
        assert(!ideck_worker_joins_snapshot(&s));
        if(s.joining&&(external||s.sealed)){
            assert(s.active==1&&!s.reaped&&!s.externally_joined&&!s.all_tracked_worker_threads_joined);
            assert(!ideck_native_workers_total()&&atomic_load(&tls_started)&&!atomic_load(&tls_done));
            atomic_store(&pending_observed,1);release();return NULL;
        }
        tick();
    }
    assert(!"actual join did not remain pending for TLS");return NULL;
}
static void wait_empty(void){
    struct ideck_worker_joins_snapshot s;
    for(unsigned i=0;i<10000;i++){assert(!ideck_worker_joins_snapshot(&s));assert(!s.error);if(!s.active)return;tick();}
    assert(!"worker reaper never drained");
}
static void *producer(void *unused){
    (void)unused;
    for(unsigned i=0;i<2500;i++){
        pthread_t thread;unsigned attempts=0;
        for(;;){
            int error=ideck_native_worker_start(IDECK_WORKER_TIMER,&thread,NULL,entry,&simple);
            if(!error)break;
            assert(error==EAGAIN&&++attempts<10000);tick();
        }
    }
    return NULL;
}
int main(int argc,char **argv){
    if(argc!=2)return 2;
    struct ideck_worker_joins_snapshot s;pthread_t worker;
    assert(ideck_worker_joins_snapshot(&s)==-ENODEV);
    assert(!ideck_worker_joins_initialize()&&ideck_worker_joins_initialize()==-EBUSY);
    assert(ideck_worker_joins_finish()==-EBUSY);
    pid_t child=fork();assert(child>=0);
    if(!child)_exit(ideck_worker_joins_snapshot(&s)==-EXDEV&&ideck_worker_joins_seal()==-EXDEV?0:1);
    int status;assert(waitpid(child,&status,0)==child&&WIFEXITED(status)&&!WEXITSTATUS(status));
    pthread_t helper;assert(!pthread_create(&helper,NULL,foreign,NULL)&&!pthread_join(helper,NULL));
    pthread_attr_t attr;assert(!pthread_attr_init(&attr)&&!pthread_attr_setdetachstate(&attr,PTHREAD_CREATE_DETACHED));
    assert(ideck_native_worker_start(IDECK_WORKER_TIMER,&worker,&attr,entry,&simple)==EINVAL);
    assert(!pthread_attr_destroy(&attr)&&!ideck_native_workers_total());
    if(!strcmp(argv[1],"failure")){
        for(unsigned i=0;i<1000;i++)assert(ideck_native_worker_start(IDECK_WORKER_TIMER,&worker,NULL,entry,&simple)==EAGAIN);
        assert(!ideck_native_workers_total()&&!ideck_worker_joins_snapshot(&s)&&!s.active&&!s.started);
        assert(!ideck_worker_joins_seal()&&!ideck_worker_joins_finish());
        puts("1000-create-failures-no-worker-counter-or-handle-leak=PASS");
    }else if(!strcmp(argv[1],"join-failure")){
        assert(!ideck_native_worker_start(IDECK_WORKER_TIMER,&worker,NULL,entry,&simple));
        for(unsigned i=0;i<10000;i++){assert(!ideck_worker_joins_snapshot(&s));if(s.error)break;tick();}
        assert(s.error==EINVAL&&s.active==1&&!s.all_tracked_worker_threads_joined);
        assert(!ideck_worker_joins_seal()&&ideck_worker_joins_finish()==-EINVAL);
        assert(!ideck_native_workers_total());assert(!pthread_join(worker,NULL)); // Test-only real cleanup after injected join failure.
        assert(ideck_native_worker_start(IDECK_WORKER_TIMER,&worker,NULL,entry,&simple)==EBUSY);
        assert(!ideck_worker_joins_snapshot(&s)&&s.error&&!s.all_tracked_worker_threads_joined);
        puts("failed-join-never-certifies-quiescence-even-with-zero-body-count=PASS");return 0;
    }else if(!strcmp(argv[1],"reuse")){
        struct job held={IDECK_WORKER_TIMER,0,1};
        assert(!ideck_worker_joins_snapshot(&s)&&s.capacity==8);
        for(unsigned i=0;i<s.capacity;i++)assert(!ideck_native_worker_start(IDECK_WORKER_TIMER,&worker,NULL,entry,&held));
        assert(ideck_native_worker_start(IDECK_WORKER_TIMER,&worker,NULL,entry,&held)==EAGAIN);
        assert(ideck_native_workers_total()==8);release();wait_empty();
        pthread_t producers[4];for(unsigned i=0;i<4;i++)assert(!pthread_create(&producers[i],NULL,producer,NULL));
        for(unsigned i=0;i<4;i++)assert(!pthread_join(producers[i],NULL));
        assert(!ideck_worker_joins_seal()&&!ideck_worker_joins_finish());
        assert(!ideck_worker_joins_snapshot(&s)&&s.started==10008&&s.reaped==10008&&!s.active);
        puts("eight-active-slots-reused-only-after-10008-actual-joins=PASS");
    }else{
        int external=!strcmp(argv[1],"external");assert(external||!strcmp(argv[1],"managed"));
        assert(!pthread_key_create(&tls_key,destructor));
        struct job job={external?IDECK_WORKER_FORWARD:IDECK_WORKER_TIMER,1,0};
        assert(!ideck_native_worker_start(job.kind,&worker,NULL,entry,&job));
        for(unsigned i=0;i<10000&&!atomic_load(&tls_started);i++)tick();
        assert(atomic_load(&tls_started)&&!ideck_native_workers_total());
        if(!external)assert(ideck_worker_joins_external(worker,NULL)==ESRCH);
        assert(!pthread_create(&helper,NULL,release_tls,external?(void *)1:NULL));
        if(external){void *result=NULL;assert(!ideck_worker_joins_external(worker,&result)&&result==(void *)13);}
        assert(!ideck_worker_joins_seal()&&!ideck_worker_joins_finish());assert(!pthread_join(helper,NULL));
        assert(atomic_load(&pending_observed)&&atomic_load(&tls_done));assert(!pthread_key_delete(tls_key));
        assert(!ideck_worker_joins_snapshot(&s)&&s.started==1&&(external?s.externally_joined:s.reaped)==1);
        puts(external?"forwarder-original-owner-join-includes-held-TLS=PASS":"managed-reaper-join-includes-held-TLS-after-body-counter-zero=PASS");
    }
    assert(!ideck_worker_joins_snapshot(&s)&&s.all_tracked_worker_threads_joined&&s.reaper_joined&&!s.error);
    assert(!ideck_native_workers_total()&&ideck_worker_joins_finish()==0);
    assert(ideck_native_worker_start(IDECK_WORKER_TIMER,&worker,NULL,entry,&simple)==EBUSY);
    puts("scope=TRACKED_NATIVE_WORKERS_ONLY_NOT_FULL_LINUX_TEARDOWN_OR_WINE_PERMISSION");return 0;
}
