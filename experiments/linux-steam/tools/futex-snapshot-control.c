/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#include "NativeKernelLog.h"
#include "LinuxLabRuntime.h"
#include <assert.h>
#include <fcntl.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
static int result=-1;
static void *run(void *root){result=ideck_linux_lab_run(root);return NULL;}
int main(int argc,char **argv){
    if(argc!=3)return 2;
    assert(!ideck_native_log_start(argv[2]));pthread_t guest;assert(!pthread_create(&guest,NULL,run,argv[1]));
    char path[4096];assert(snprintf(path,sizeof path,"%s/wait-ready",argv[1])<(int)sizeof path);
    for(unsigned i=0;i<10000&&access(path,F_OK);i++)usleep(1000);
    assert(!access(path,F_OK));
    char logpath[4096];assert(snprintf(logpath,sizeof logpath,"%s/%s",argv[2],ideck_native_log_name())<(int)sizeof logpath);
    int observed=0;
    for(unsigned i=0;i<1000&&!observed;i++){
        ideck_linux_lab_log_tasks();FILE *f=fopen(logpath,"rb");assert(f);char body[131072];size_t n=fread(body,1,sizeof body-1,f);assert(!ferror(f)&&n<sizeof body-1);body[n]=0;fclose(f);
        char *line=strstr(body,"LINUX_FUTEX_SAMPLE tid=2 tgid=2 op=128 expected=0 bitset=0 timed=0 ");
        if(line){assert(strstr(line,"caller_pc=0x")&&strstr(line,"caller_lr=0x")&&strstr(line,"no_memory_read=1"));observed=1;}
        else usleep(1000);
    }
    assert(observed);assert(snprintf(path,sizeof path,"%s/release",argv[1])<(int)sizeof path);
    int fd=open(path,O_WRONLY|O_CREAT|O_EXCL,0600);assert(fd>=0&&!close(fd));
    assert(!pthread_join(guest,NULL)&&result==0);
    puts("HOST actual blocked ARM64 private futex metadata observed; ordinary wake/guest exit0 unchanged; NOT CEF/device diagnosis");return 0;
}
