/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#include "JoinedProfile.h"
#include "NativeWorkerJoins.h"
#include "JoinableGuests.h"
#include "LinuxLabRuntime.h"
#include "kernel/guest_profile.h"
#include "emu/tlb.h"
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>
static void *foreign(void *unused){
    (void)unused;struct ideck_joined_profile_snapshot s;
    assert(ideck_joined_profile_request_stop()==-EPERM&&ideck_joined_profile_release_buffers()==-EPERM&&ideck_joined_profile_snapshot(&s)==-EPERM);return NULL;
}
int main(int argc,char **argv){
    if(argc!=4)return 2;
    int enabled=strcmp(argv[3],"disabled")!=0,leak=!strcmp(argv[3],"producer-leak");
    assert(!strcmp(argv[3],"enabled")||!strcmp(argv[3],"disabled")||leak);
    dup2(2,666);assert(!ideck_worker_joins_initialize()&&!ideck_joinable_guests_initialize());
    assert(!unsetenv("ISH_GUEST_PROFILE"));if(enabled)assert(!setenv("ISH_GUEST_PROFILE",argv[2],1));
    guest_profile_init();
    assert(ideck_native_workers_live(IDECK_WORKER_PROFILE)==enabled);
    assert(ideck_joined_profile_request_stop()==-EAGAIN&&ideck_joined_profile_release_buffers()==-EAGAIN);
    pthread_t helper;assert(!pthread_create(&helper,NULL,foreign,NULL)&&!pthread_join(helper,NULL));
    assert(!ideck_linux_lab_run(argv[1]));
    assert(!ideck_joinable_guests_seal()&&!ideck_joinable_guests_join());
    assert(ideck_joined_profile_request_stop()==-EAGAIN); // Worker admission is still open.
    assert(!ideck_worker_joins_seal());
    struct ideck_joined_profile_snapshot before,joined,after;
    assert(!ideck_joined_profile_snapshot(&before)&&before.sampler_started==(unsigned)enabled&&!before.sampler_completed&&!before.stop_requested&&!before.retained_bytes_known);
    assert(ideck_native_workers_total()==enabled&&ideck_joined_profile_release_buffers()==-EAGAIN);
    assert(!ideck_joined_profile_request_stop()&&!ideck_worker_joins_finish());
    assert(!ideck_joined_profile_snapshot(&joined)&&joined.stop_requested&&joined.sampler_completed==(unsigned)enabled&&joined.retained_bytes_known);
    assert(!ideck_native_workers_total());
    if(enabled)assert(joined.logical_retained_bytes>=6u*1024u*1024u);else assert(!joined.logical_retained_bytes);
    struct tlb fixture={0};
    if(leak){
        guest_profile_register(&fixture,777);
        assert(ideck_joined_profile_release_buffers()==-EBUSY&&guest_profile_enabled);
        guest_profile_unregister(&fixture);
    }
    assert(!ideck_joined_profile_release_buffers()&&!ideck_joined_profile_release_buffers());
    assert(!ideck_joined_profile_snapshot(&after)&&after.buffers_released&&after.retained_bytes_known&&!after.logical_retained_bytes&&!guest_profile_enabled);
    guest_profile_init();assert(!ideck_native_workers_total()&&!guest_profile_enabled); // No revival after close.
    if(enabled){
        struct stat first,last;assert(!stat(argv[2],&first)&&first.st_size>0);
        for(unsigned i=0;i<20;i++){struct timespec t={0,10000000};nanosleep(&t,NULL);}
        assert(!stat(argv[2],&last)&&first.st_size==last.st_size&&first.st_mtimespec.tv_sec==last.st_mtimespec.tv_sec&&first.st_mtimespec.tv_nsec==last.st_mtimespec.tv_nsec);
    }else assert(access(argv[2],F_OK)&&errno==ENOENT);
    printf("actual-profiler-stop-join-and-release=PASS\nmode=%s started=%u completed=%u retained_logical_before=%llu after=%llu\n",argv[3],joined.sampler_started,joined.sampler_completed,(unsigned long long)joined.logical_retained_bytes,(unsigned long long)after.logical_retained_bytes);
    puts("scope=HOST_PROFILER_ONLY_NOT_FULL_LINUX_TEARDOWN_WINE_GAME_OR_IPAD_SUCCESS");return 0;
}
