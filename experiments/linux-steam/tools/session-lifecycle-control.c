/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * HOST ONLY. Virtual guest PIDs, never Darwin processes. Does not start Wine
 * or claim that an empty task table establishes full native quiescence. */
#include "LinuxLabRuntime.h"
#include "kernel/task.h"
#include "kernel/signal.h"
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <time.h>
#include <limits.h>
static int failures;
static void check(const char *name,int ok){printf("%s=%s\n",name,ok?"PASS":"FAIL");if(!ok)failures++;}
static int live_guests(void){int count=0;lock(&pids_lock);for(unsigned i=2;i<MAX_PID;i++)if(pid_get_task(i))count++;unlock(&pids_lock);return count;}
static int exists(const char *root,const char *name){char path[PATH_MAX];int n=snprintf(path,sizeof path,"%s/%s",root,name);return n>0&&(size_t)n<sizeof path&&!access(path,F_OK);}
int main(int argc,char **argv){
    if(argc!=3|| (strcmp(argv[2],"observe")&&strcmp(argv[2],"signal")&&strcmp(argv[2],"standard")&&strcmp(argv[2],"failure")))return 2;
    int stop=!strcmp(argv[2],"signal"),standard=!strcmp(argv[2],"standard"),failure=!strcmp(argv[2],"failure");dup2(2,666);
    check(failure?"child-start-failure-propagates":"initial-guest-exits-zero",ideck_linux_lab_run(argv[1])==(failure?512:0));
    if(standard||failure){
        struct timespec tick={0,10000000};
        for(int i=0;i<300;i++){
            int count=ideck_linux_lab_live_guest_threads();
            if(!live_guests()&&(count==0||count==-95))break;
            nanosleep(&tick,NULL);
        }
        check("no-live-guest-table-entries",live_guests()==0);
#if IDECK_LAB_GUEST_LIFETIME
        check("all-native-start-reservations-retired",ideck_linux_lab_live_guest_threads()==0);
#else
        check("tracking-disabled-reports-unsupported",ideck_linux_lab_live_guest_threads()==-95);
#endif
        check("runtime-reentry-still-refused",ideck_linux_lab_run(argv[1])==-16);
        return failures?1:0;
    }
    check("reported-guest-exited",!strcmp(ideck_linux_lab_stage(),"guest-exited"));
    check("child-handshake-observed",exists(argv[1],"child-started")&&exists(argv[1],"initial-exiting"));
    int live=live_guests();printf("guest-tasks-after-initial-return=%d\n",live);check("orphan-still-live-after-return",live==1);
#if IDECK_LAB_GUEST_LIFETIME
    check("native-reserved-or-running-counts-orphan",ideck_linux_lab_live_guest_threads()==1);
#endif
    if(stop){
        struct task *saved=current;lock(&pids_lock);struct task *init=pid_get_task(1);unlock(&pids_lock);
        if(!init)return 3;current=init;int r=(int)sys_kill(-1,SIGTERM_);current=saved;check("virtual-namespace-signal-accepted",r==0);
    }
    struct timespec tick={0,10000000};for(int i=0;i<300;i++)nanosleep(&tick,NULL);
    check(stop?"signalled-child-cannot-write-late-marker":"orphan-executes-after-initial-return",exists(argv[1],"child-after-parent-exit")==!stop);
    check("no-live-guest-table-entries",live_guests()==0);
#if IDECK_LAB_GUEST_LIFETIME
    check("native-guest-cleanup-count-drains",ideck_linux_lab_live_guest_threads()==0);
#endif
    check("runtime-reentry-still-refused",ideck_linux_lab_run(argv[1])==-16);
    printf("scope=host interpreter; no native-thread quiescence, Wine or iPad handoff proof\n");return failures?1:0;
}
