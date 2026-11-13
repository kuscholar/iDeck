/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * HOST deterministic pt_map metadata failure after actual native mmap.
 * Does not inject allocation failures into any app/device/Steam runtime.
 */
#include <mach/mach.h>
#include <mach/mach_vm.h>
#include "kernel/memory.h"
#include "kernel/calls.h"
#include "kernel/errno.h"
#include "fs/fd.h"
#include <assert.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdlib.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>

size_t real_page_size;
void (*runtime_memory_failure)(const char *,uint64_t,uint64_t,int,int,int);
static void *captured;
static size_t captured_size;
static int injected_error;
int errno_map(void){return errno==ENOMEM?_ENOMEM:_EINVAL;}
void fd_report_mapping_failure(struct fd *fd,int guest_fd,const char *stage,
    uint64_t address,uint64_t length,uint64_t offset,unsigned prot,unsigned flags,int host,int result){
    (void)fd;(void)guest_fd;(void)stage;(void)address;(void)length;(void)offset;(void)prot;(void)flags;(void)host;(void)result;
}
int ideck_test_pt_map(struct mem *mem,page_t start,pages_t pages,void *memory,size_t offset,unsigned flags){
    (void)mem;(void)start;(void)flags;captured=memory;captured_size=pages*PAGE_SIZE+offset;
    errno=EAGAIN;return injected_error;
}
extern int realfs_mmap(struct fd *,struct mem *,page_t,pages_t,off_t,int,int);
int main(int argc,char **argv){
    if(argc!=3)return 2;
    int fixed=!strcmp(argv[1],"fixed");assert(fixed||!strcmp(argv[1],"baseline"));
    real_page_size=(size_t)sysconf(_SC_PAGESIZE);
    char name[4096];assert(snprintf(name,sizeof name,"%s/own-map-fixture",argv[2])<(int)sizeof name);
    int native=open(name,O_CREAT|O_EXCL|O_RDWR,0600);assert(native>=0);
    // Full native-page + partial tail exercises all three backing branches.
    assert(!ftruncate(native,(off_t)(real_page_size+real_page_size/2)));
    unsigned checked=0;
    for(unsigned branch=0;branch<3;branch++)for(unsigned failure=0;failure<2;failure++){
        struct fd fd={.real_fd=native};
        pages_t pages=(branch==0?real_page_size:real_page_size*3)/PAGE_SIZE;
        int flags=branch==2?MMAP_SHARED:MMAP_PRIVATE;
        injected_error=failure?_ENOMEM:0;captured=NULL;
        assert(realfs_mmap(&fd,NULL,32,pages,0,P_READ,flags)==injected_error);
        assert(captured&&errno==EAGAIN);
        // Darwin mincore can report a hole without a failing return value.
        // Query self VM region coverage, not Linux mincore error semantics.
        mach_vm_address_t query=(uintptr_t)captured;mach_vm_size_t size=0;
        vm_region_basic_info_data_64_t info={0};mach_msg_type_number_t count=VM_REGION_BASIC_INFO_COUNT_64;
        mach_port_t object=MACH_PORT_NULL;
        kern_return_t result=mach_vm_region(mach_task_self(),&query,&size,VM_REGION_BASIC_INFO_64,(vm_region_info_t)&info,&count,&object);
        if(object!=MACH_PORT_NULL)mach_port_deallocate(mach_task_self(),object);
        int mapped=result==KERN_SUCCESS&&query<=(uintptr_t)captured&&(uintptr_t)captured-query<size;
        assert(mapped==(!failure||!fixed));
        if(mapped)assert(!munmap(captured,captured_size));
        checked++;
    }
    assert(!close(native)&&!unlink(name));
    printf("HOST file-map ownership cases=%u mode=%s baseline_leak=%d fix_scope=failed_transfer_only_not_original_ENOMEM\n",checked,argv[1],!fixed);
    return 0;
}
