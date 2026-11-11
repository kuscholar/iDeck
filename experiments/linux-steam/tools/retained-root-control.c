/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * HOST prototype only: retain one mounted kernel/root/native init and execute
 * a NEW ELF child after fully joining/reaping the prior guest wave. No original
 * runtime consumed flag, global resets, auth, Wine, Steam or App target changes.
 */
#include "LinuxLabRuntime.h"
#include "JoinableGuests.h"
#include "GuestLifetime.h"
#include "kernel/task.h"
#include "kernel/init.h"
#include "kernel/calls.h"
#include "kernel/mm.h"
#include "fs/devices.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static void preserve_report(const char *root,unsigned wave){
    char source[4096],target[4096],line[256];unsigned count=0;
    assert(snprintf(source,sizeof source,"%s/probe-results.txt",root)<(int)sizeof source);
    assert(snprintf(target,sizeof target,"%s/wave-%u-results.txt",root,wave)<(int)sizeof target);
    FILE *input=fopen(source,"r"),*output=fopen(target,"wx");assert(input&&output);
    while(fgets(line,sizeof line,input)){
        size_t length=strlen(line);assert(length>=6&&!strcmp(line+length-6,"=PASS\n"));
        assert(fputs(line,output)>=0);count++;
    }
    assert(!ferror(input)&&count==16);assert(!fclose(input)&&!fclose(output));
}
static int wave_pid, wave_status;
static void observed_exit(struct task *task, int status) {
    if(task->pid==wave_pid)wave_status=status;
}
static void *enter(void *task) {current=task;task_run_current();return NULL;}
static struct task *reap(void) {
    assert(!current);
    lock(&pids_lock);struct task *init=pid_get_task(1);unlock(&pids_lock);
    assert(init);current=init;
    for(unsigned i=0;i<MAX_PID;i++){
        int_t result=(int_t)sys_wait4(-1,0,1,0);
        if(result>0)continue;
        assert(result==-10);break;
    }
    lock(&pids_lock);
    for(unsigned pid=2;pid<MAX_PID;pid++)assert(!pid_get_task_zombie(pid));
    unlock(&pids_lock);current=NULL;return init;
}
int main(int argc,char **argv) {
    if(argc!=2)return 2;
    assert(!ideck_joinable_guests_initialize());
    assert(!ideck_linux_lab_run(argv[1]));
    assert(!ideck_joinable_guests_seal()&&!ideck_joinable_guests_join());
    assert(!ideck_linux_lab_live_guest_threads());
    struct task *init=reap();struct mm *init_mm=init->mm;
    preserve_report(argv[1],1);
    void *init_root=init->fs;
    for(unsigned wave=2;wave<=4;wave++) {
        assert(!ideck_joinable_guests_begin_next_wave());
        assert(!become_new_init_child());wave_pid=current->pid;wave_status=-1;
        assert(!create_stdio("/dev/null",MEM_MAJOR,DEV_NULL_MINOR));
        assert(!do_execve("/probe",1,"/probe\0","HOME=/root\0PATH=/bin:/usr/bin\0"));
        exit_hook=observed_exit;
        struct task *child=current;current=NULL;pthread_t thread;
        ideck_guest_lifetime_reserve();
        assert(!pthread_create(&thread,NULL,enter,child));
        assert(!pthread_join(thread,NULL)); /* Initial child is separately owned. */
        assert(wave_status==0);
        assert(!ideck_joinable_guests_seal()&&!ideck_joinable_guests_join());
        assert(!ideck_linux_lab_live_guest_threads());
        assert(reap()==init&&init->mm==init_mm&&init->fs==init_root);
        preserve_report(argv[1],wave);
        struct ideck_joinable_guests_snapshot s;
        assert(!ideck_joinable_guests_snapshot(&s)&&s.all_registered_children_joined);
        printf("RETAINED_ROOT wave=%u wait_status=%d joined=%u cumulative_slots=%u same_init_root_mm=1\n",wave,wave_status,s.joined,s.slots);fflush(stdout);
    }
    assert(ideck_linux_lab_run(argv[1])==-16); /* Original one-shot policy intact. */
    puts("scope=HOST_FOUR_ELF_WAVES_ONLY_NO_STEAM_WINE_APP_IPAD_OR_SAFE_HANDOFF_PERMISSION");
    return 0;
}
