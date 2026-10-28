// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
// Read-only task-map inspection + genuine PROT_NONE reservations, then unmap.
// No fixed mapping, smaller substitute, protection change, fake success or JIT.
#include <dlfcn.h>
#include <errno.h>
#include <mach/mach.h>
#include <mach/task_info.h>
#include <stddef.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <stdarg.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>
static FILE *ReportFile;
static void Report(const char *format, ...) {
    va_list args;va_start(args,format);vfprintf(stderr,format,args);va_end(args);
    if (ReportFile) {va_start(args,format);vfprintf(ReportFile,format,args);va_end(args);fflush(ReportFile);}
}
__attribute__((constructor)) static void NativeVMProbe(void) {
    const char *enabled=getenv("IDeckNativeVMProbe");
    if (!enabled || strcmp(enabled,"1")!=0) return;
    const char *home=getenv("HOME");char reportPath[PATH_MAX];
    if (home && snprintf(reportPath,sizeof reportPath,"%s/Documents/ideck-native-vm-%ld.txt",home,(long)getpid())<(int)sizeof reportPath)
        ReportFile=fopen(reportPath,"w");
    void *system=dlopen("/usr/lib/libSystem.B.dylib",RTLD_LAZY);
    void *(*realmap)(void *,size_t,int,int,int,off_t)=dlsym(system,"mmap");
    int (*realunmap)(void *,size_t)=dlsym(system,"munmap");
    int (*statusfn)(pid_t,unsigned,void *,size_t)=dlsym(system,"csops");
    if (!realmap || !realunmap) {Report("[ideck-mac-vm] setup=failed\n");_exit(2);}
    uint32_t status=0;int statusRead=statusfn && statusfn(getpid(),0,&status,sizeof status)==0;
    Report("[ideck-mac-vm] cs-status-read=%d debugged=%d flags=0x%x\n",statusRead,statusRead && (status&0x10000000)!=0,status);
    task_vm_info_data_t info={0};mach_msg_type_number_t count=TASK_VM_INFO_COUNT;
    kern_return_t kr=task_info(mach_task_self(),TASK_VM_INFO,(task_info_t)&info,&count);
    int valid=kr==KERN_SUCCESS && count*sizeof(natural_t)>=offsetof(task_vm_info_data_t,max_address)+sizeof info.max_address;
    Report("[ideck-mac-vm] task-info=%d count=%u range-valid=%d min=0x%llx max=0x%llx\n",kr,count,valid,valid?(unsigned long long)info.min_address:0,valid?(unsigned long long)info.max_address:0);
    const size_t sizes[]={4096,1ULL<<30,16ULL<<30,32ULL<<30};
    int clean=1;
    for(unsigned i=0;i<sizeof sizes/sizeof sizes[0];++i) {
        errno=0;
        // CEF's actual tag253 request in launch20 used fd=(int)0xfd000000.
        void *base=realmap(NULL,sizes[i],PROT_NONE,MAP_PRIVATE|MAP_ANON,(int)0xfd000000,0);
        int error=base==MAP_FAILED?errno:0;
        int aligned=base!=MAP_FAILED && ((uintptr_t)base&((16ULL<<30)-1))==0;
        int unmapped=base==MAP_FAILED?1:realunmap(base,sizes[i])==0;
        clean &= unmapped;
        Report("[ideck-mac-vm] reserve-bytes=%zu success=%d errno=%d aligned16GiB=%d unmapped=%d\n",sizes[i],base!=MAP_FAILED,error,aligned,unmapped);
    }
    Report("[ideck-mac-vm] complete=1 cleanup=%d memory-written=0 cef-initialized=0\n",clean);
    if (ReportFile) fclose(ReportFile);
    _exit(clean?0:3);
}
