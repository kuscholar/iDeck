/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * HOST ONLY: actual Linux realfs/sys_mmap/PTE/fd lifetime, owned fixtures. */
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>
#include "kernel/init.h"
#include "kernel/calls.h"
#include "kernel/task.h"
#include "kernel/mm.h"
#include "kernel/errno.h"
#include "fs/real.h"
#include "fs/fd.h"
#include "SharedFileReserve.h"
static int refuse_map,fail_data,fail_metadata;
static unsigned native_failures;
void *ideck_file_reserve_test_original_map(void *p,size_t n,int prot,int flags,int fd,off_t off){
    if(refuse_map){native_failures++;errno=ENOMEM;return MAP_FAILED;}
    return mmap(p,n,prot,flags,fd,off);
}
void *ideck_reserve_test_malloc(size_t n){
    if(fail_data){fail_data=0;errno=ENOMEM;return NULL;}return malloc(n);
}
void *ideck_reserve_test_calloc(size_t n,size_t s){
    if(fail_metadata){fail_metadata=0;errno=ENOMEM;return NULL;}return calloc(n,s);
}
static struct ideck_file_reserve_stats snapshot(void){
    struct ideck_file_reserve_stats s;assert(!ideck_file_reserve_snapshot(&s));return s;
}
int main(int argc,char **argv){
    assert(argc==3);const char *mode=argv[1];const size_t bytes=262144;
    int native=open(argv[2],O_CREAT|O_EXCL|O_RDWR,0600);assert(native>=0&&!ftruncate(native,bytes*2));
    unsigned char *alias=mmap(NULL,bytes*2,PROT_READ|PROT_WRITE,MAP_SHARED,native,0);assert(alias!=MAP_FAILED);
    for(size_t i=0;i<bytes*2;i++)alias[i]=(unsigned char)(i*17+3);
    assert(!mount_root(&realfs,"/")&&!become_first_process());
    struct fd *file=generic_open(argv[2],O_RDWR_,0);assert(!IS_ERR(file));
    int ismemfd=!strcmp(mode,"memfd")||!strcmp(mode,"memfd-close");
    if(ismemfd){int error=0;assert(!fd_close(file));file=memfd_new("owned-reserve-control",2,&error);assert(file&&!error);}
    fd_t number=f_install(file,0);assert(number>=0);unsigned fdrefs=atomic_load(&file->refcount);
    if(ismemfd){
        assert(!sys_ftruncate64(number,bytes*2)&&!munmap(alias,bytes*2));
        alias=mmap(NULL,bytes*2,PROT_READ|PROT_WRITE,MAP_SHARED,file->real_fd,0);assert(alias!=MAP_FAILED);
        for(size_t i=0;i<bytes*2;i++)alias[i]=(unsigned char)(i*17+3);
    }
    int ordinary=!strcmp(mode,"ordinary"),off=!strcmp(mode,"unprepared");
    if(!off)assert(!ideck_file_reserve_prepare());
    refuse_map=!ordinary;fail_data=!strcmp(mode,"data-failure");fail_metadata=!strcmp(mode,"pte-failure");
    addr_t first=0x1800000000ULL,second=first+0x400000;dword_t flags=MMAP_SHARED|MMAP_FIXED,prot=P_READ|P_WRITE;size_t length=bytes;qword_t offset=0;
    int excluded=0;
    if(!strcmp(mode,"readonly")){prot=P_READ;excluded=1;}
    else if(!strcmp(mode,"private")){flags=MMAP_PRIVATE|MMAP_FIXED;excluded=1;}
    else if(!strcmp(mode,"offset")){offset=bytes;excluded=1;}
    else if(!strcmp(mode,"unaligned")){length=4096;excluded=sysconf(_SC_PAGESIZE)>4096;}
    sdword_t expected=(off||excluded||fail_data||fail_metadata)?_ENOMEM:0;
    unsigned long changes=current->mem->mmu.changes;int used=current->mem->pgdir_used;
    addr_t result=sys_mmap64(first,length,prot,flags,number,offset);
    if(expected){
        assert((int64_t)result==expected&&!mem_pt(current->mem,PAGE(first)));
        assert(atomic_load(&file->refcount)==fdrefs&&current->mem->mmu.changes==changes&&current->mem->pgdir_used==used);
        struct ideck_file_reserve_stats s=snapshot();assert(!s.live&&!s.quarantined);
        if(!strcmp(mode,"data-failure")||!strcmp(mode,"pte-failure"))assert(s.mapped==1&&s.released==1);
        else assert(!s.mapped);
    }else{
        assert(result==first);struct pt_entry *entry=mem_pt(current->mem,PAGE(first));assert(entry&&entry->data);
        struct data *data=entry->data;assert(data->fd&&atomic_load(&data->refcount)==length/PAGE_SIZE);
        /* This pinned kernel retains mapping identity, not the open host fd.
         * The actual Darwin file mapping owns its backing after fd close. */
        assert(atomic_load(&file->refcount)==fdrefs+(unsigned)ismemfd);
        if(ismemfd)assert(file->memfd->maywrite_maps==1&&(sdword_t)sys_fcntl(number,1033,F_SEAL_WRITE_)==_EBUSY);
        unsigned char value=0;assert(!user_read(first+101,&value,1)&&value==alias[101]);
        value=0xa1;assert(!user_write(first+101,&value,1)&&alias[101]==value);
        if(!strcmp(mode,"suspend")){
            uint64_t token=0;
            struct mem child;mem_init(&child);
            assert(!pt_copy_on_write(current->mem,&child,PAGE(first),bytes/PAGE_SIZE));
            assert(!sys_munmap(first,bytes)&&snapshot().live==1);
            assert(ideck_file_reserve_suspend(&token)==-EBUSY&&!token);
            mem_destroy(&child);
            assert(!snapshot().live&&!ideck_file_reserve_suspend(&token)&&token);

            /* The original native mmap fails on this fixture. While suspended,
             * verify the fallback cannot install a PTE or take a reference. */
            unsigned long parked_changes=current->mem->mmu.changes;
            int parked_used=current->mem->pgdir_used;
            assert((int64_t)sys_mmap64(first,bytes,P_READ|P_WRITE,flags,number,0)==_ENOMEM);
            assert(!mem_pt(current->mem,PAGE(first))&&snapshot().mapped==1);
            assert(current->mem->mmu.changes==parked_changes&&current->mem->pgdir_used==parked_used);
            assert(atomic_load(&file->refcount)==fdrefs);

            /* The native alias remains usable while Linux has no mapping. */
            alias[101]=0x7b;
            assert(!ideck_file_reserve_resume(token));
            assert(sys_mmap64(first,bytes,P_READ|P_WRITE,flags,number,0)==first);
            assert(!user_read(first+101,&value,1)&&value==0x7b);
            value=0x63;assert(!user_write(first+101,&value,1)&&alias[101]==value);
            assert(!sys_munmap(first,bytes));
            struct ideck_file_reserve_stats s=snapshot();
            assert(!s.live&&s.mapped==2&&s.released==2);
        }else if(!strcmp(mode,"fork")){
            struct mem child;mem_init(&child);
            assert(!pt_copy_on_write(current->mem,&child,PAGE(first),bytes/PAGE_SIZE));
            assert(atomic_load(&data->refcount)==2*bytes/PAGE_SIZE&&snapshot().live==1);
            assert(!sys_close(number));number=-1;
            value=0x37;assert(!user_write(first+101,&value,1));
            struct pt_entry *inherited=mem_pt(&child,PAGE(first));
            assert(inherited&&inherited->data==data&&!(inherited->flags&P_COW));
            assert(*((unsigned char *)data->data+inherited->offset+101)==0x37);
            assert(!sys_munmap(first,bytes)&&snapshot().live==1);
            assert(*(unsigned char *)((char *)inherited->data->data+inherited->offset+101)==0x37);
            mem_destroy(&child);assert(!snapshot().live&&snapshot().released==1);
        }else if(!strcmp(mode,"aliases")||!strcmp(mode,"memfd-close")){
            assert(sys_mmap64(second,bytes,P_READ|P_WRITE,MMAP_SHARED|MMAP_FIXED,number,0)==second);
            assert(!sys_close(number));number=-1; /* mappings own the actual fd */
            value=0x62;assert(!user_write(second+101,&value,1)&&alias[101]==value);
            assert(!user_read(first+101,&value,1)&&value==0x62);
            assert(snapshot().live==2);
            assert(!sys_munmap(first,PAGE_SIZE));assert(snapshot().live==2);
            assert(!user_read(first+PAGE_SIZE+101,&value,1)&&value==alias[PAGE_SIZE+101]);
            assert(!sys_munmap(first+PAGE_SIZE,bytes-PAGE_SIZE));assert(snapshot().live==1);
            assert(!user_read(second+101,&value,1)&&value==0x62);
            assert(!sys_munmap(second,bytes));assert(!snapshot().live&&snapshot().released==2);
        }else{
            assert(!sys_munmap(first,length));assert(!snapshot().live);
            assert(snapshot().mapped==(unsigned)!ordinary&&snapshot().released==(unsigned)!ordinary);
            if(ismemfd){
                assert(!file->memfd->maywrite_maps&&atomic_load(&file->refcount)==fdrefs);
                assert(!(sdword_t)sys_fcntl(number,1033,F_SEAL_WRITE_));
                unsigned calls=native_failures;
                assert((int64_t)sys_mmap64(first,bytes,P_READ|P_WRITE,MMAP_SHARED|MMAP_FIXED,number,0)==_EPERM);
                assert(native_failures==calls&&!snapshot().live);
            }
        }
    }
    if(number>=0)assert(!sys_close(number));
    assert(!munmap(alias,bytes*2)&&!close(native));
    if(!off)assert(!ideck_file_reserve_drain());
    printf("real Linux sys_mmap64/realfs/PTE/fd mode=%s original_failures=%u result=%lld PASS\n",mode,native_failures,(long long)result);
    return 0;
}
