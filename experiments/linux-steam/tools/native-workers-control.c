/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * HOST ONLY worker accounting, never game execution or full native teardown. */
#include "NativeWorkers.h"
#include "LinuxLabRuntime.h"
#include "kernel/guest_profile.h"
#include "kernel/native_offload.h"
#include "fs/tty.h"
#include "util/timer.h"
#include <assert.h>
#include <stdatomic.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
static atomic_bool release_workers;
static atomic_uint callbacks,forwarders;
static void (*retire_role[IDECK_WORKER_KINDS])(void *)={ideck_native_worker_retire_timer,
    ideck_native_worker_retire_profile,ideck_native_worker_retire_tty,ideck_native_worker_retire_forward};
static void tick(void){struct timespec t={0,1000000};nanosleep(&t,NULL);}
static void *role_entry(void *opaque){
    enum ideck_worker_kind role=(enum ideck_worker_kind)(uintptr_t)opaque;
    pthread_cleanup_push(retire_role[role],NULL);
    assert(ideck_native_workers_live(role)>=1);
    while(!atomic_load(&release_workers))tick();
    if(role==IDECK_WORKER_TTY)pthread_exit(NULL); // Exercise outer cleanup on exit.
    pthread_cleanup_pop(1);return NULL;
}
static void *never_started(void *unused){(void)unused;atomic_fetch_add(&callbacks,1);return NULL;}
static void timer_fired(void *unused){(void)unused;atomic_fetch_add(&callbacks,1);}
static int native_handler(int argc,char **argv,int input,int output,int error){
    (void)argv;(void)input;
    assert(argc==1);int count=ideck_native_workers_live(IDECK_WORKER_FORWARD);
    assert(count==2);atomic_store(&forwarders,(unsigned)count);
    assert(write(output,"own fixture\n",12)==12);assert(write(error,"own fixture\n",12)==12);return 37;
}
static void wait_zero(void){for(unsigned i=0;i<2000&&ideck_native_workers_total()!=0;i++)tick();assert(ideck_native_workers_total()==0);}
int main(int argc,char **argv){
    if(argc<2||argc>4)return 2;dup2(2,666);
    assert(!strcmp(ideck_native_workers_marker(),"IDECK_NATIVE_WORKERS_V1"));assert(ideck_native_workers_total()==0);
    assert(ideck_linux_lab_native_worker_entries()==0);
    if(!strcmp(argv[1],"roles")){
        pthread_t threads[IDECK_WORKER_KINDS];
        for(unsigned i=0;i<IDECK_WORKER_KINDS;i++)assert(!ideck_native_worker_start((enum ideck_worker_kind)i,&threads[i],NULL,role_entry,(void *)(uintptr_t)i));
        for(unsigned i=0;i<IDECK_WORKER_KINDS;i++)assert(ideck_native_workers_live((enum ideck_worker_kind)i)==1);
        assert(ideck_native_workers_total()==IDECK_WORKER_KINDS);
        assert(ideck_linux_lab_native_worker_entries()==IDECK_WORKER_KINDS);atomic_store(&release_workers,true);
        for(unsigned i=0;i<IDECK_WORKER_KINDS;i++)assert(!pthread_join(threads[i],NULL));wait_zero();
        pthread_t unused;assert(ideck_native_worker_start((enum ideck_worker_kind)-1,&unused,NULL,role_entry,NULL)==EINVAL);
        assert(ideck_native_worker_start(IDECK_WORKER_TIMER,NULL,NULL,role_entry,NULL)==EINVAL);
        assert(ideck_native_worker_start(IDECK_WORKER_TIMER,&unused,NULL,NULL,NULL)==EINVAL);assert(ideck_native_workers_total()==0);
        puts("pending-role-counts-return-and-pthread-exit=PASS");return 0;
    }
    if(!strcmp(argv[1],"failure")){
        pthread_t thread;
        for(unsigned i=0;i<IDECK_WORKER_KINDS;i++)assert(ideck_native_worker_start((enum ideck_worker_kind)i,&thread,NULL,never_started,NULL)==EAGAIN);
        assert(!atomic_load(&callbacks));assert(ideck_native_workers_total()==0);puts("failed-start-reservations-retired=PASS");return 0;
    }
    if(!strcmp(argv[1],"underflow")){
        ideck_native_worker_retire_timer(NULL);assert(ideck_native_workers_total()==-1);
        assert(ideck_linux_lab_native_worker_entries()==-1);
        for(unsigned i=0;i<IDECK_WORKER_KINDS;i++)assert(ideck_native_workers_live((enum ideck_worker_kind)i)==-1);
        puts("underflow-invalidates-all-accounting=PASS");return 0;
    }
    if(!strcmp(argv[1],"timer")){
        struct timer *timer=timer_new(CLOCK_MONOTONIC,timer_fired,NULL);assert(timer);
        struct timer_spec spec={{0,10000000},{0,10000000}};
        assert(!timer_set(timer,spec,NULL));assert(ideck_native_workers_live(IDECK_WORKER_TIMER)==1);
        for(unsigned i=0;i<2000&&atomic_load(&callbacks)<3;i++)tick();assert(atomic_load(&callbacks)>=3);
        timer_free(timer);wait_zero();unsigned stopped=atomic_load(&callbacks);
        for(unsigned i=0;i<30;i++)tick();assert(atomic_load(&callbacks)==stopped);
        puts("actual-timer-callbacks-free-and-retirement=PASS");return 0;
    }
    if(!strcmp(argv[1],"tty")){
        // A private pipe replaces ONLY this test process's stdin. No terminal
        // mode/security/user input change; ioctl returns ENOTTY by design.
        int saved=dup(STDIN_FILENO),pipes[2];assert(saved>=0&&!pipe(pipes));assert(dup2(pipes[0],STDIN_FILENO)>=0);close(pipes[0]);
        struct tty tty={0};tty.num=1;extern struct tty_driver_ops real_tty_ops;
        assert(!real_tty_ops.init(&tty));assert(ideck_native_workers_live(IDECK_WORKER_TTY)==1);
        real_tty_ops.cleanup(&tty);wait_zero();assert(dup2(saved,STDIN_FILENO)>=0);close(saved);close(pipes[1]);
        puts("actual-private-pipe-tty-cleanup-counted=PASS");return 0;
    }
    if(argc<3)return 2;
    if(!strcmp(argv[1],"forward")){
        assert(!native_offload_add_handler("worker-control",native_handler));
        assert(ideck_linux_lab_run(argv[2])==(37<<8));assert(atomic_load(&forwarders)==2);wait_zero();
        assert(ideck_linux_lab_live_guest_threads()==0);puts("actual-guest-native-forwarders-joined=PASS");return 0;
    }
    if(!strcmp(argv[1],"profile")){
        if(argc!=4)return 2;assert(!setenv("ISH_GUEST_PROFILE",argv[3],1));guest_profile_init();
        assert(ideck_native_workers_live(IDECK_WORKER_PROFILE)==1);
        assert(ideck_linux_lab_run(argv[2])==0);assert(ideck_linux_lab_live_guest_threads()==0);
        assert(ideck_native_workers_total()==1);assert(ideck_native_workers_live(IDECK_WORKER_PROFILE)==1);
        assert(ideck_linux_lab_native_worker_entries()==1);
        puts("actual-profiler-outlives-all-guest-entries=PASS");
        puts("scope=profiler remains live until this host test process exits; no stop or Wine handoff claim");return 0;
    }
    return 2;
}
