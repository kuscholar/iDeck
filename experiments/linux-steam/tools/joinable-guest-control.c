/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#include "JoinableGuests.h"
#include "LinuxLabRuntime.h"
#include <stdio.h>
#include <string.h>
#include <assert.h>
#include <unistd.h>
#include <time.h>
int main(int argc,char **argv){
    if(argc!=3||(strcmp(argv[2],"ordinary")&&strcmp(argv[2],"orphan")))return 2;
    dup2(2,666);assert(!ideck_joinable_guests_initialize());assert(!ideck_linux_lab_run(argv[1]));
    struct ideck_joinable_guests_snapshot observed;assert(!ideck_joinable_guests_snapshot(&observed));
    assert(observed.slots>0&&!observed.sealed&&!observed.all_registered_children_joined);
    int orphan=!strcmp(argv[2],"orphan");
    if(orphan){
        assert(ideck_linux_lab_live_guest_threads()==1);char p[4096];assert(snprintf(p,sizeof p,"%s/child-after-parent-exit",argv[1])<(int)sizeof p);assert(access(p,F_OK));
    }
    struct timespec before,after;assert(!clock_gettime(CLOCK_MONOTONIC,&before));
    assert(!ideck_joinable_guests_seal()&&!ideck_joinable_guests_join());assert(!clock_gettime(CLOCK_MONOTONIC,&after));
    assert(!ideck_joinable_guests_snapshot(&observed)&&observed.all_registered_children_joined&&observed.slots==observed.joined&&!observed.error);
    assert(ideck_linux_lab_live_guest_threads()==0&&ideck_linux_lab_run(argv[1])==-16);
    if(orphan){char p[4096];assert(snprintf(p,sizeof p,"%s/child-after-parent-exit",argv[1])<(int)sizeof p);assert(!access(p,F_OK));}
    long long ms=(after.tv_sec-before.tv_sec)*1000+(after.tv_nsec-before.tv_nsec)/1000000;
    printf("actual-arm64-child-pthreads-joined=PASS\nregistered=%u joined=%u join_wait_ms=%lld\n",observed.slots,observed.joined,ms);
    puts("scope=HOST_CHILD_GUESTS_ONLY_NO_FULL_TEARDOWN_WINE_GAME_OR_IPAD_SUCCESS");return 0;
}
