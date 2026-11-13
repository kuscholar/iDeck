/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#include "RetainedFrontend.h"
#include <errno.h>
#if IDECK_LAB_RETAINED_FRONTEND
#if !IDECK_LAB_STEAM_FRONTEND || !IDECK_LAB_COMPAT_TOOL || !IDECK_LAB_GUEST_LIFETIME || !IDECK_LAB_NATIVE_WORKERS
#error Retained frontend requires explicit frontend/tool and actual lifetime providers
#endif
#include "LinuxLabRuntime.h"
#include "NativeWorkerJoins.h"
#include "JoinableGuests.h"
#include "JoinedProfile.h"
#include "NativeSignalLease.h"
#include "GuestLifetime.h"
#include "LinuxSteamSession.h"
#include "kernel/guest_profile.h"
#include "kernel/task.h"
#include "kernel/calls.h"
#include "kernel/init.h"
#include "fs/devices.h"
#include "fs/path.h"
#include <pthread.h>
#include <signal.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
static pthread_mutex_t state_lock=PTHREAD_MUTEX_INITIALIZER;
static pthread_t owner;
static pid_t owner_pid;
static char *owned_root;
static struct ideck_frontend_transport_boundary owned_transport;
static struct ideck_frontend_result state;
static int initial_pid,initial_status;
extern void sigusr1_handler(int);
static void observe(struct task *task,int status){if(task->pid==initial_pid)initial_status=status;}
static void *enter(void *task){current=task;task_run_current();return NULL;}
static void phase(int value){pthread_mutex_lock(&state_lock);state.phase=value;pthread_mutex_unlock(&state_lock);}
static int restart_guest(void){
    if(current)return -EBUSY;
    int error=become_new_init_child();if(error)return error;
    initial_pid=current->pid;initial_status=-1;
    const char *stale[]={"/tmp/.X99-lock","/tmp/.X11-unix/X99","/tmp/ideck-display-ready","/tmp/ideck-vnc-password"};
    for(unsigned i=0;i<4;i++){error=generic_unlinkat(AT_PWD,stale[i]);if(error&&error!=-2)return error;}
    error=create_stdio("/dev/null",MEM_MAJOR,DEV_NULL_MINOR);if(error)return error;
    const char args[]=IDECK_LINUX_STEAM_ARGS;
    const char env[]="HOME=/root\0PATH=/usr/bin:/bin\0LANG=C\0STEAM_RUNTIME=1\0"
        "LD_LIBRARY_PATH=/Steam/steamrtarm64:/Steam/steamrtarm64/libs:/lib/aarch64-linux-gnu\0";
    error=do_execve("/bin/sh",3,args,env);if(error)return error;
    exit_hook=observe;struct task *child=current;current=NULL;pthread_t thread;
    ideck_guest_lifetime_reserve();error=pthread_create(&thread,NULL,enter,child);
    if(error){ideck_guest_lifetime_retire(NULL);return -error;}
    phase(IDECK_FRONTEND_RUNNING);
    error=pthread_join(thread,NULL);return error?-error:initial_status;
}
static int reap(unsigned *count){
    if(current)return -EBUSY;
    lock(&pids_lock);struct task *init=pid_get_task(1);unlock(&pids_lock);
    if(!init)return -ENOENT;
    current=init;int error=-EOVERFLOW;*count=0;
    for(unsigned i=0;i<=MAX_PID;i++){
        int_t value=(int_t)sys_wait4(-1,0,1,0);
        if(value>0){(*count)++;continue;}
        error=value==-10?0:value==0?-EBUSY:value;break;
    }
    current=NULL;
    lock(&pids_lock);
    for(unsigned pid=2;pid<MAX_PID;pid++)if(pid_get_task_zombie(pid)){error=-EBUSY;break;}
    unlock(&pids_lock);return error;
}
static int handlers(void){
    struct sigaction action={0};action.sa_handler=sigusr1_handler;
    sigemptyset(&action.sa_mask);sigaddset(&action.sa_mask,SIGUSR1);
    if(sigaction(SIGUSR1,&action,NULL)||signal(SIGPIPE,SIG_IGN)==SIG_ERR)return -errno;
    return 0;
}
int ideck_retained_frontend_snapshot(struct ideck_frontend_result *out){
    if(!out)return -EINVAL;
    pthread_mutex_lock(&state_lock);*out=state;pthread_mutex_unlock(&state_lock);return 0;
}
int ideck_retained_frontend_run(const char *root,const struct ideck_tool_payload *tool,const struct ideck_frontend_transport_boundary *transport,struct ideck_frontend_result *out){
    if(!out)return -EINVAL;
    *out=(struct ideck_frontend_result){.guest_status=-1,.error=-EINVAL};
    if(!root||root[0]!='/'||strnlen(root,4096)==4096||!tool||!transport)return -EINVAL;
    if((transport->embedded!=0&&transport->embedded!=1)||
       (transport->embedded&&!transport->drain)||(!transport->embedded&&(transport->drain||transport->context)))return -EINVAL;
    if(getenv("ISH_GUEST_PROFILE")&&*getenv("ISH_GUEST_PROFILE")){out->error=-ENOTSUP;return -ENOTSUP;} /* No profiler revival. */
    pthread_mutex_lock(&state_lock);int error=0;unsigned wave=state.wave+1;
    if(owner_pid&&owner_pid!=getpid())error=-EXDEV;
    else if(owner_pid&&!pthread_equal(owner,pthread_self()))error=-EPERM;
    else if(owner_pid&&!ideck_frontend_restart_ready(&state))error=-EBUSY;
    else if(owned_root&&strcmp(owned_root,root))error=-EXDEV;
    else if(owner_pid&&(owned_transport.embedded!=transport->embedded||owned_transport.drain!=transport->drain||owned_transport.context!=transport->context))error=-EXDEV;
    if(!error&&!owner_pid){
        owned_root=strdup(root);if(!owned_root)error=-ENOMEM;
        else {owner_pid=getpid();owner=pthread_self();owned_transport=*transport;}
    }
    if(!error)state=(struct ideck_frontend_result){.wave=wave,.phase=IDECK_FRONTEND_PREPARING};
    *out=state;pthread_mutex_unlock(&state_lock);if(error)return error;
    struct ideck_signal_lease *signals=NULL;unsigned reaped=0;int status=-1;
    if(wave==1){
        error=ideck_worker_joins_initialize();if(error)goto finish;
        error=ideck_joinable_guests_initialize();if(error)goto finish;
        guest_profile_init();
    }else{
        error=ideck_joinable_guests_begin_next_wave();if(error)goto finish;
        error=ideck_worker_joins_begin_next_wave();if(error)goto finish;
    }
    signals=ideck_signal_lease_capture(sigusr1_handler);if(!signals){error=-errno;goto finish;}
    if(wave>1){error=handlers();if(error)goto finish;}
    status=wave==1?ideck_linux_lab_steam_frontend_with_tool(root,tool):restart_guest();
    if(status<0||strcmp(ideck_linux_lab_stage(),"guest-exited")){error=status<0?status:-EPROTO;goto finish;}
    phase(IDECK_FRONTEND_DRAINING);
    if((error=ideck_signal_lease_claim(signals)))goto finish;
    if((error=ideck_joinable_guests_seal())||(error=ideck_joinable_guests_join()))goto finish;
    if((error=ideck_worker_joins_seal())||(error=ideck_joined_profile_request_stop()))goto finish;
    if((error=ideck_worker_joins_finish())||(error=ideck_joined_profile_release_buffers()))goto finish;
    struct ideck_joinable_guests_snapshot guests;struct ideck_worker_joins_snapshot workers;
    if((error=ideck_joinable_guests_snapshot(&guests))||(error=ideck_worker_joins_snapshot(&workers)))goto finish;
    if(!guests.all_registered_children_joined||!workers.all_tracked_worker_threads_joined){error=-EBUSY;goto finish;}
    if((error=reap(&reaped)))goto finish;
    if(transport->embedded&&(error=transport->drain(transport->context,status)))goto finish;
    struct ideck_signal_quiescence proof={1,1,0,ideck_linux_lab_live_guest_threads(),ideck_linux_lab_native_worker_entries()};
    if((error=ideck_signal_lease_release(signals,&proof)))goto finish;
    if((error=ideck_signal_lease_destroy(signals)))goto finish;
    signals=NULL;
finish:
    /* On ambiguous failure, preserve state/lease/resources for diagnosis. No
     * forced cleanup or recreation over a live task. Do not continue to Wine. */
    pthread_mutex_lock(&state_lock);state.guest_status=status;state.error=error;state.reaped=reaped;
    state.phase=error?IDECK_FRONTEND_POISONED:IDECK_FRONTEND_DORMANT;*out=state;
    pthread_mutex_unlock(&state_lock);return error;
}
#else
int ideck_retained_frontend_run(const char *root,const struct ideck_tool_payload *tool,const struct ideck_frontend_transport_boundary *transport,struct ideck_frontend_result *out){(void)root;(void)tool;(void)transport;(void)out;return -ENOTSUP;}
int ideck_retained_frontend_snapshot(struct ideck_frontend_result *out){(void)out;return -ENOTSUP;}
#endif
