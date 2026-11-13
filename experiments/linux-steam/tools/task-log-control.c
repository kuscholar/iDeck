/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * HOST ONLY: real guest wait, bounded nonblocking numeric task snapshots. */
#include "NativeKernelLog.h"
#include "LinuxLabRuntime.h"
#include "kernel/task.h"
#include <assert.h>
#include <fcntl.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
static int result=-1;
static void *run(void *root) {result=ideck_linux_lab_run(root);return NULL;}
static void path(char *out,const char *root,const char *name) {
    int n=snprintf(out,4096,"%s/%s",root,name);assert(n>0&&n<4096);
}
static void await(const char *root,const char *name) {
    char p[4096];path(p,root,name);
    for(unsigned i=0;i<15000;i++){if(!access(p,F_OK))return;usleep(2000);}
    assert(!"Guest marker timeout");
}
static void marker(const char *root,const char *name) {
    char p[4096];path(p,root,name);int fd=open(p,O_CREAT|O_EXCL|O_WRONLY,0600);assert(fd>=0);assert(write(fd,"1",1)==1);assert(!close(fd));
}
int main(int argc,char **argv) {
    if(argc!=3)return 2;
    assert(!ideck_native_log_start(argv[2]));
    ideck_linux_lab_log_tasks(); // Phase0 refuses access to uninitialized table.
    pthread_t thread;assert(!pthread_create(&thread,NULL,run,argv[1]));
    await(argv[1],"memory-reserved");
    lock(&pids_lock);ideck_linux_lab_log_tasks();unlock(&pids_lock); // Must not wait recursively.
    lock(&pids_lock);struct task *task=pid_get_task(2);assert(task);lock(&task->general_lock);unlock(&pids_lock);
    ideck_linux_lab_log_tasks();unlock(&task->general_lock); // Same-thread busy row is skipped.
    ideck_linux_lab_log_tasks();marker(argv[1],"start-touch");
    await(argv[1],"memory-ready");ideck_linux_lab_log_tasks();marker(argv[1],"release");
    assert(!pthread_join(thread,NULL)&&result==0);ideck_linux_lab_log_tasks();
    char p[4096];path(p,argv[2],ideck_native_log_name());FILE *f=fopen(p,"rb");assert(f);assert(!fseek(f,0,SEEK_END));long n=ftell(f);assert(n>0&&n<1000000);rewind(f);
    char *body=calloc((size_t)n+1,1);assert(body&&fread(body,1,(size_t)n,f)==(size_t)n);fclose(f);
    assert(strstr(body,"unavailable=runtime_not_started")&&strstr(body,"unavailable=pid_lock_busy"));
    assert(strstr(body,"skipped_busy=1")&&strstr(body,"LINUX_TASK tid=2 tgid=2"));
    /* Existing kernel PROCESS_EVENT lines have their own private diagnostics.
     * Check this new numeric sampler's rows, not unrelated log producers. */
    for(char *line=strtok(body,"\n");line;line=strtok(NULL,"\n")) {
        if(strncmp(line,"LINUX_TASK",10))continue;
        assert(!strstr(line," pc=")&&!strstr(line," sp=")&&!strstr(line,"comm=")&&!strstr(line,"argv="));
    }
    free(body);puts("real-guest-live-and-post-exit-numeric-snapshots=PASS");
    puts("not-started-and-contended-locks-do-not-block=PASS");
    puts("non-futex-rows-have-no-register-address-argument-or-name-payload=PASS");return 0;
}
