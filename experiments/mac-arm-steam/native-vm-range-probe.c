// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
// Diagnostic only: public APIs, PROT_NONE, no overwrite, no private ranges,
// no entitlement, no fake grant, no access/protection change or CEF integration.
#include <dlfcn.h>
#include <errno.h>
#include <mach/mach.h>
#include <mach/vm_map.h>
_Static_assert(sizeof(vm_address_t)==8 && sizeof(vm_size_t)==8,"Probe requires SDK LP64 VM ABI");
#include <mach/task_info.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>
__attribute__((constructor)) static void VMRangeProbe(void) {
    const char *setting=getenv("IDeckNativeVMRangeProbe");
    if(!setting || strcmp(setting,"1"))return;
    task_vm_info_data_t task={0};mach_msg_type_number_t count=TASK_VM_INFO_COUNT;
    kern_return_t kr=task_info(mach_task_self(),TASK_VM_INFO,(task_info_t)&task,&count);
    if(kr!=KERN_SUCCESS || count*sizeof(natural_t)<offsetof(task_vm_info_data_t,max_address)+sizeof task.max_address || task.min_address>=task.max_address){fprintf(stderr,"[ideck-vm-range] setup=failed task=%d\n",kr);_exit(2);}
    vm_address_t cursor=task.min_address;uint64_t largest=0,mapped=0,inaccessible=0;unsigned regions=0;int inventory=0;
    while(cursor<task.max_address && regions<8192) {
        vm_address_t address=cursor;vm_size_t size=0;
        vm_region_basic_info_data_64_t info={0};mach_msg_type_number_t n=VM_REGION_BASIC_INFO_COUNT_64;mach_port_t object=MACH_PORT_NULL;
        kr=vm_region_64(mach_task_self(),&address,&size,VM_REGION_BASIC_INFO_64,(vm_region_info_t)&info,&n,&object);
        if(object!=MACH_PORT_NULL)mach_port_deallocate(mach_task_self(),object);
        if(kr==KERN_INVALID_ADDRESS){uint64_t gap=task.max_address-cursor;if(gap>largest)largest=gap;inventory=1;break;}
        if(kr!=KERN_SUCCESS || n<VM_REGION_BASIC_INFO_COUNT_64 || !size || address<cursor || size>UINT64_MAX-address){fprintf(stderr,"[ideck-vm-range] inventory-error=%d\n",kr);break;}
        if(address>task.max_address){uint64_t gap=task.max_address-cursor;if(gap>largest)largest=gap;inventory=1;break;}
        if(address-cursor>largest)largest=address-cursor;
        uint64_t end=address+size;if(end>task.max_address)end=task.max_address;
        mapped+=end-address;if(info.protection==VM_PROT_NONE)inaccessible+=end-address;
        cursor=end;++regions;
    }
    if(cursor==task.max_address)inventory=1;
    fprintf(stderr,"[ideck-vm-range] inventory=%d regions=%u mapped-bytes=%llu no-access-mapped-bytes=%llu largest-unmapped-gap=%llu task-span=%llu\n",inventory,regions,(unsigned long long)mapped,(unsigned long long)inaccessible,(unsigned long long)largest,(unsigned long long)(task.max_address-task.min_address));
    const vm_size_t sizes[]={1ULL<<30,8ULL<<30,16ULL<<30};int clean=1;
    for(unsigned i=0;i<3 && clean;++i) {
        vm_address_t address=0;
        // ANYWHERE is kernel placement under its normal range policy; no FIXED,
        // OVERWRITE, custom ranges or aliases. Maximum protection stays NONE.
        kr=vm_map(mach_task_self(),&address,sizes[i],0,VM_FLAGS_ANYWHERE,MACH_PORT_NULL,0,FALSE,VM_PROT_NONE,VM_PROT_NONE,VM_INHERIT_NONE);
        kern_return_t released=kr==KERN_SUCCESS?vm_deallocate(mach_task_self(),address,sizes[i]):KERN_SUCCESS;
        clean &= released==KERN_SUCCESS;
        fprintf(stderr,"[ideck-vm-range] api=vm_map bytes=%llu result=%d success=%d cleanup=%d\n",(unsigned long long)sizes[i],kr,kr==KERN_SUCCESS,released==KERN_SUCCESS);
    }
    void *system=dlopen("/usr/lib/libSystem.B.dylib",RTLD_LAZY);
    void *(*mapfn)(void *,size_t,int,int,int,off_t)=system?dlsym(system,"mmap"):NULL;
    int (*unmapfn)(void *,size_t)=system?dlsym(system,"munmap"):NULL;
    if(clean && mapfn && unmapfn) {
        size_t size=8ULL<<30;errno=0;void *p=mapfn(NULL,size,PROT_NONE,MAP_PRIVATE|MAP_ANON,-1,0);int error=p==MAP_FAILED?errno:0;
        int released=p==MAP_FAILED || unmapfn(p,size)==0;clean &= released;
        fprintf(stderr,"[ideck-vm-range] api=mmap bytes=%zu errno=%d success=%d cleanup=%d\n",size,error,p!=MAP_FAILED,released);
    }else{fprintf(stderr,"[ideck-vm-range] mmap-setup-or-cleanup-failed=1\n");clean=0;}
    fprintf(stderr,"[ideck-vm-range] complete=1 cleanup=%d memory-written=0 cef-integrated=0\n",clean);
    _exit(inventory && clean?0:3);
}
