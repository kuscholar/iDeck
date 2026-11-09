/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * HOST ONLY unsanitized real-interpreter resource discriminator. */
#include "LinuxLabRuntime.h"
#include <mach/mach.h>
#include <mach/task_info.h>
#include <pthread.h>
#include <assert.h>
#include <fcntl.h>
#include <stdio.h>
#include <time.h>
#include <unistd.h>
static int result=-999;
static void *run(void *root) {result=ideck_linux_lab_run(root);return NULL;}
static void path(char *out,size_t size,const char *root,const char *name) {
    int n=snprintf(out,size,"%s/%s",root,name);assert(n>0&&(size_t)n<size);
}
static void await(const char *root,const char *name) {
    char p[4096];path(p,sizeof p,root,name);
    for(unsigned i=0;i<15000;i++) {if(!access(p,F_OK))return;usleep(2000);}
    fprintf(stderr,"own control timed out waiting for %s\n",name);assert(0);
}
static void marker(const char *root,const char *name) {
    char p[4096];path(p,sizeof p,root,name);int fd=open(p,O_CREAT|O_EXCL|O_WRONLY,0600);assert(fd>=0);assert(write(fd,"1",1)==1);assert(!close(fd));
}
static uint64_t footprint(void) {
    task_vm_info_data_t info={0};mach_msg_type_number_t count=TASK_VM_INFO_COUNT;
    assert(task_info(mach_task_self(),TASK_VM_INFO,(task_info_t)&info,&count)==KERN_SUCCESS);
    assert(count>=TASK_VM_INFO_REV1_COUNT);return info.phys_footprint;
}
int main(int argc,char **argv) {
    if(argc!=2)return 2;
    pthread_t thread;assert(!pthread_create(&thread,NULL,run,argv[1]));
    await(argv[1],"memory-reserved");uint64_t reserved=footprint();marker(argv[1],"start-touch");
    await(argv[1],"memory-ready");uint64_t touched=footprint();marker(argv[1],"release");
    assert(!pthread_join(thread,NULL));assert(result==0);await(argv[1],"memory-unmapped");uint64_t unmapped=footprint();
    printf("{\"host_page_bytes\":%d,\"guest_touched_bytes\":67108864,\"reserved_footprint_bytes\":%llu,\"touched_footprint_bytes\":%llu,\"unmapped_footprint_bytes\":%llu,\"touch_delta_bytes\":%lld,\"guest_status\":%d}\n",
        getpagesize(),(unsigned long long)reserved,(unsigned long long)touched,(unsigned long long)unmapped,(long long)touched-(long long)reserved,result);
    return 0;
}
