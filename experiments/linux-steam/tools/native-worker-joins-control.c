/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * Actual pinned worker providers and ARM64 controls. No app/device/Wine launch.
 */
#include "NativeWorkerJoins.h"
#include "JoinableGuests.h"
#include "LinuxLabRuntime.h"
#include "kernel/native_offload.h"
#include "fs/tty.h"
#include "util/timer.h"
#include <assert.h>
#include <stdatomic.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
static atomic_uint callbacks,forwarders;
static atomic_int tls_started,tls_done,release_tls,pending;
static pthread_key_t tls_key;
static void tick(void){struct timespec t={0,1000000};nanosleep(&t,NULL);}
static void destructor(void *value){assert(value==(void *)1);atomic_store(&tls_started,1);while(!atomic_load(&release_tls))tick();atomic_store(&tls_done,1);}
static void fired(void *with_tls){if(with_tls)assert(!pthread_setspecific(tls_key,(void *)1));atomic_fetch_add(&callbacks,1);}
static void *release(void *unused){
    (void)unused;struct ideck_worker_joins_snapshot s;
    for(unsigned i=0;i<10000;i++){
        assert(!ideck_worker_joins_snapshot(&s));
        if(s.sealed&&s.joining){
            assert(!ideck_native_workers_total()&&atomic_load(&tls_started)&&!atomic_load(&tls_done));
            assert(!s.all_tracked_worker_threads_joined&&!s.reaped);atomic_store(&pending,1);atomic_store(&release_tls,1);return NULL;
        }
        tick();
    }
    assert(!"real timer TLS join never became pending");return NULL;
}
static int handler(int argc,char **argv,int input,int output,int error){
    (void)argv;(void)input;assert(argc==1&&ideck_native_workers_live(IDECK_WORKER_FORWARD)==2);
    atomic_store(&forwarders,2);assert(write(output,"own fixture\n",12)==12&&write(error,"own fixture\n",12)==12);return 37;
}
int main(int argc,char **argv){
    if(argc<2||argc>3)return 2;dup2(2,666);assert(!ideck_worker_joins_initialize());
    pthread_t helper;int have_helper=0,saved=-1,pipes[2]={-1,-1};struct tty tty_fixture={0};
    if(!strcmp(argv[1],"timer")||!strcmp(argv[1],"timer-tls")){
        int tls=!strcmp(argv[1],"timer-tls");if(tls)assert(!pthread_key_create(&tls_key,destructor));
        struct timer *timer=timer_new(CLOCK_MONOTONIC,fired,tls?(void *)1:NULL);assert(timer);
        struct timer_spec spec={{0,1000000},{0,tls?0:1000000}};assert(!timer_set(timer,spec,NULL));
        for(unsigned i=0;i<10000&&(tls?!atomic_load(&tls_started):atomic_load(&callbacks)<3);i++)tick();
        assert(atomic_load(&callbacks)>0);if(tls)assert(atomic_load(&tls_started)&&!tls_done);
        timer_free(timer);
        if(tls){assert(!pthread_create(&helper,NULL,release,NULL));have_helper=1;}
    }else if(!strcmp(argv[1],"tty")){
        saved=dup(STDIN_FILENO);assert(saved>=0&&!pipe(pipes));assert(dup2(pipes[0],STDIN_FILENO)>=0);close(pipes[0]);
        tty_fixture.num=1;extern struct tty_driver_ops real_tty_ops;
        assert(!real_tty_ops.init(&tty_fixture));
        /* Original provider cleanup already cancels its private blocking read;
         * no new cancellation policy. New registry must actually join it. */
        real_tty_ops.cleanup(&tty_fixture);
    }else{
        assert(argc==3&&(!strcmp(argv[1],"ordinary")||!strcmp(argv[1],"forward")));
        int forward=!strcmp(argv[1],"forward");assert(!ideck_joinable_guests_initialize());
        if(forward)assert(!native_offload_add_handler("worker-control",handler));
        assert(ideck_linux_lab_run(argv[2])==(forward?37<<8:0));
        assert(!ideck_joinable_guests_seal()&&!ideck_joinable_guests_join());
        if(forward)assert(atomic_load(&forwarders)==2);
    }
    assert(!ideck_worker_joins_seal()&&!ideck_worker_joins_finish());
    if(have_helper){assert(!pthread_join(helper,NULL));assert(pending&&tls_done&&!pthread_key_delete(tls_key));}
    if(saved>=0){assert(dup2(saved,STDIN_FILENO)>=0);close(saved);close(pipes[1]);}
    struct ideck_worker_joins_snapshot s;assert(!ideck_worker_joins_snapshot(&s)&&s.all_tracked_worker_threads_joined&&!s.error&&!ideck_native_workers_total());
    if(!strcmp(argv[1],"forward"))assert(s.externally_joined==2&&s.started==2&&!s.reaped);
    else if(strcmp(argv[1],"ordinary"))assert(s.started==1&&s.reaped==1&&!s.externally_joined);
    printf("actual-pinned-provider-joins=PASS\nmode=%s started=%llu reaped=%llu externally_joined=%llu reaper_joined=%u\n",argv[1],(unsigned long long)s.started,(unsigned long long)s.reaped,(unsigned long long)s.externally_joined,s.reaper_joined);
    puts("scope=HOST_TRACKED_WORKERS_ONLY_NO_FULL_LINUX_RESET_WINE_GAME_OR_IPAD_SUCCESS");return 0;
}
