/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * HOST ONLY actual genuine Steam frontend graceful-exit experiment. No
 * credentials, game execution, runtime reset or device operation. If a real
 * join remains pending, the external owner observes it; no forced success.
 */
#include "LinuxLabRuntime.h"
#include "ToolInstall.h"
#include "NativeKernelLog.h"
#include "NativeWorkerJoins.h"
#include "JoinableGuests.h"
#include "JoinedProfile.h"
#include "NativeSignalLease.h"
#include "kernel/guest_profile.h"
#include "kernel/task.h"
#include "kernel/calls.h"
#include "kernel/init.h"
#include "fs/devices.h"
#include "fs/path.h"
#include "LinuxSteamSession.h"
#include "GuestLifetime.h"
#include <signal.h>
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
extern const char *sock_tmp_prefix;
extern void sigusr1_handler(int);
#ifndef IDECK_HOST_SHUTDOWN_PROFILE
#define IDECK_HOST_SHUTDOWN_PROFILE 1
#endif
static void *payload(const char *bundle,const char *name,size_t *size){
    char path[4096];int n=snprintf(path,sizeof path,"%s/LabCompatibility/%s",bundle,name);if(n<0||n>=(int)sizeof path)return NULL;
    int fd=open(path,O_RDONLY|O_NOFOLLOW|O_CLOEXEC);if(fd<0)return NULL;
    struct stat st;if(fstat(fd,&st)||!S_ISREG(st.st_mode)||st.st_size<=0||st.st_size>262144){close(fd);return NULL;}
    void *data=malloc((size_t)st.st_size);if(!data){close(fd);return NULL;}
    size_t copied=0;while(copied<(size_t)st.st_size){ssize_t count=read(fd,(char *)data+copied,(size_t)st.st_size-copied);if(count<0&&errno==EINTR)continue;if(count<=0){free(data);close(fd);return NULL;}copied+=(size_t)count;}
    close(fd);*size=copied;return data;
}
static void stage(const char *value,int status){printf("HOST_SHUTDOWN_STAGE phase=%s status=%d guest_entries=%d native_entries=%d\n",value,status,ideck_linux_lab_live_guest_threads(),ideck_linux_lab_native_worker_entries());fflush(stdout);}
static unsigned guest_structs(void){
    unsigned count=0;lock(&pids_lock);
    /* Full fixed identity range, not last allocation (which can wrap). */
    for(unsigned pid=2;pid<MAX_PID;pid++)if(pid_get_task_zombie(pid))count++;
    unlock(&pids_lock);return count;
}
static int reap_owned_zombies(unsigned *reaped){
    /* All actual guest/native workers are joined and creation sealed first.
     * Borrow ONLY the existing native init context, never execute/exit PID1.
     * Native wait4 with NULL guest output pointers and WNOHANG is bounded.
     */
    lock(&pids_lock);struct task *init=pid_get_task(1);unlock(&pids_lock);
    if(!init||current)return -EINVAL;
    current=init;int status=0;*reaped=0;
    for(unsigned i=0;i<=MAX_PID;i++){
        int_t value=(int_t)sys_wait4(-1,0,1,0);
        if(value>0){(*reaped)++;continue;}
        status=value==-10?0:value==0?-EBUSY:(int)value;break;
    }
    current=NULL;return status;
}
static int second_pid,second_status;
static void observe_second(struct task *task,int status){if(task->pid==second_pid)second_status=status;}
static void *run_second(void *task){current=task;task_run_current();return NULL;}
static int next_frontend(void){
    assert(!current);
    const char *stale[]={"/tmp/.X99-lock","/tmp/.X11-unix/X99","/tmp/ideck-display-ready","/tmp/ideck-vnc-password"};
    assert(!become_new_init_child());second_pid=current->pid;second_status=-1;
    for(unsigned i=0;i<4;i++){int error=generic_unlinkat(AT_PWD,stale[i]);assert(!error||error==-2);}
    assert(!create_stdio("/dev/null",MEM_MAJOR,DEV_NULL_MINOR));
    const char args[]=IDECK_LINUX_STEAM_ARGS;
    const char env[]="HOME=/root\0PATH=/usr/bin:/bin\0LANG=C\0STEAM_RUNTIME=1\0"
        "LD_LIBRARY_PATH=/Steam/steamrtarm64:/Steam/steamrtarm64/libs:/lib/aarch64-linux-gnu\0";
    assert(!do_execve("/bin/sh",3,args,env));
    exit_hook=observe_second;struct task *child=current;current=NULL;pthread_t thread;
    ideck_guest_lifetime_reserve();assert(!pthread_create(&thread,NULL,run_second,child));
    assert(!pthread_join(thread,NULL));return second_status;
}
static void reacquire_handlers(void){
    struct sigaction action={0};action.sa_handler=sigusr1_handler;
    sigemptyset(&action.sa_mask);sigaddset(&action.sa_mask,SIGUSR1);
    assert(!sigaction(SIGUSR1,&action,NULL));assert(signal(SIGPIPE,SIG_IGN)!=SIG_ERR);
}
int main(int argc,char **argv){
    int elf_control=0;
    if(argc!=4)return 2;
    struct ideck_tool_payload tool={0};
    tool.executable=payload(argv[3],"ideck-madeira",&tool.executable_size);
    tool.compatibility=payload(argv[3],"compatibilitytool.vdf",&tool.compatibility_size);
    tool.manifest=payload(argv[3],"toolmanifest.vdf",&tool.manifest_size);
    if(!tool.executable||!tool.compatibility||!tool.manifest)return 2;
    char socket_directory[]="/tmp/ideck-exit-XXXXXX",prefix[128],profile[4096];
    if(!mkdtemp(socket_directory))return 2;
    int n=snprintf(prefix,sizeof prefix,"%s/sock",socket_directory);if(n<0||n>=(int)sizeof prefix)return 2;sock_tmp_prefix=prefix;
    n=snprintf(profile,sizeof profile,"%s/own-private-profile.txt",argv[2]);if(n<0||n>=(int)sizeof profile)return 2;
    assert(!ideck_native_log_start(argv[2]));
    assert(!ideck_worker_joins_initialize()&&!ideck_joinable_guests_initialize());
#if IDECK_HOST_SHUTDOWN_PROFILE
    assert(!setenv("ISH_GUEST_PROFILE",profile,1));
#else
    assert(!unsetenv("ISH_GUEST_PROFILE"));
#endif
    guest_profile_init();
    struct ideck_signal_lease *signals=ideck_signal_lease_capture(sigusr1_handler);assert(signals);
    for(unsigned wave=1;wave<=2;wave++){
    printf("HOST_RESTART_WAVE begin=%u\n",wave);fflush(stdout);
    stage("before_frontend",0);ideck_native_log_resources();
    int status=wave==2?next_frontend():elf_control?ideck_linux_lab_run(argv[1]):ideck_linux_lab_steam_frontend_with_tool(argv[1],&tool);
    stage("frontend_call_returned",status);
    if(strcmp(ideck_linux_lab_stage(),"guest-exited"))return 3;
    assert(!ideck_signal_lease_claim(signals));
    assert(!ideck_joinable_guests_seal());stage("joining_guest_threads",0);
    assert(!ideck_joinable_guests_join());stage("guests_joined",0);
    assert(!ideck_worker_joins_seal()&&!ideck_joined_profile_request_stop());stage("joining_native_workers",0);
    assert(!ideck_worker_joins_finish()&&!ideck_joined_profile_release_buffers());stage("native_workers_joined",0);
    struct ideck_worker_joins_snapshot workers;struct ideck_joinable_guests_snapshot guests;struct ideck_joined_profile_snapshot profiler;
    assert(!ideck_worker_joins_snapshot(&workers)&&workers.all_tracked_worker_threads_joined);
    assert(!ideck_joinable_guests_snapshot(&guests)&&guests.all_registered_children_joined);
    assert(!ideck_joined_profile_snapshot(&profiler)&&profiler.buffers_released&&!profiler.logical_retained_bytes);
    unsigned before=guest_structs(),reaped=0;int waited=reap_owned_zombies(&reaped);unsigned after=guest_structs();
    printf("HOST_GUEST_REAP before=%u reaped=%u after=%u status=%d\n",before,reaped,after,waited);fflush(stdout);
    if(waited||after)return 4;
    struct ideck_signal_quiescence proof={1,1,(int)after,ideck_linux_lab_live_guest_threads(),ideck_linux_lab_native_worker_entries()};
    assert(proof.native_guest_entries==0&&proof.other_native_workers==0);
    assert(!ideck_signal_lease_release(signals,&proof)&&!ideck_signal_lease_destroy(signals));
    ideck_native_log_resources();
    printf("HOST_STEAM_SHUTDOWN elf_control=%d tracked_threads_joined=1 native_signals_restored=1 guest_reaped=%u initial_wait_status=%d\n",elf_control,reaped,status);
    puts("scope=HOST_STEAM_EXIT_RESOURCE_COMPONENTS_ONLY_NOT_FULL_ROOT_RESET_WINE_GAME_OR_IPAD_SUCCESS");fflush(stdout);
    printf("HOST_RESTART_WAVE complete=%u status=%d\n",wave,status);fflush(stdout);
    if(status)return 5;
    if(wave==1){
        assert(!ideck_joinable_guests_begin_next_wave());
        assert(!ideck_worker_joins_begin_next_wave());
        signals=ideck_signal_lease_capture(sigusr1_handler);assert(signals);
        reacquire_handlers();
    }
    }
    puts("scope=HOST_TWO_REAL_STEAM_WAVES_ONLY_NOT_WINE_APP_IPAD_SUCCESS");return 0;
}
