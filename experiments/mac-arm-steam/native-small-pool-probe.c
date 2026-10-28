// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
// Geometry/capacity discriminator ONLY. Not PartitionAlloc or CEF integration.
// Reserves real disjoint PROT_NONE chunks with aligned subranges and guard space.
// No fake grants, MAP_FIXED, mprotect, runtime code patch, JIT or memory writes.
#include "pool-layout.h"
#include <dlfcn.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>
__attribute__((constructor)) static void SmallPoolProbe(void) {
    const char *enabled=getenv("IDeckSmallPoolProbe");
    if(!enabled || strcmp(enabled,"1")) return;
    void *system=dlopen("/usr/lib/libSystem.B.dylib",RTLD_LAZY);
    void *(*reserve)(void *,size_t,int,int,int,off_t)=dlsym(system,"mmap");
    int (*release)(void *,size_t)=dlsym(system,"munmap");
    if(!reserve || !release) {fprintf(stderr,"[ideck-small-pool] setup=failed\n");_exit(2);}
    long page=sysconf(_SC_PAGESIZE);
    if(page<=0 || (size_t)page>(256ULL<<20)) _exit(2);
    const size_t pool=256ULL<<20,span=pool*2+(size_t)page;
    void *chunks[2]={MAP_FAILED,MAP_FAILED};IDeckPoolPlan plans[2]={{0},{0}};int valid=1,clean=1;
    for(unsigned i=0;i<2;++i) {
        errno=0;chunks[i]=reserve(NULL,span,PROT_NONE,MAP_PRIVATE|MAP_ANON,(int)0xfd000000,0);
        int error=chunks[i]==MAP_FAILED?errno:0;
        int planned=chunks[i]!=MAP_FAILED && ideck_plan_pool((uintptr_t)chunks[i],span,pool,(size_t)page,&plans[i]);
        valid &= planned;
        fprintf(stderr,"[ideck-small-pool] index=%u reserved=%d errno=%d aligned-plan=%d pool-bytes=%zu guard-bytes=%ld\n",i,chunks[i]!=MAP_FAILED,error,planned,pool,page);
    }
    int disjoint=valid && ((uintptr_t)chunks[0]+span<=(uintptr_t)chunks[1] || (uintptr_t)chunks[1]+span<=(uintptr_t)chunks[0]);
    int masks=valid;
    for(unsigned i=0;i<2 && valid;++i) {
        uintptr_t base=plans[i].base,mask=~(uintptr_t)(pool-1);
        masks &= (base&mask)==base && ((base+pool-1)&mask)==base && ((base-1)&mask)!=base && ((base+pool)&mask)!=base;
    }
    for(unsigned i=0;i<2;++i) if(chunks[i]!=MAP_FAILED) clean &= release(chunks[i],span)==0;
    fprintf(stderr,"[ideck-small-pool] geometry=%d disjoint=%d masks=%d cleanup=%d memory-written=0 cef-integrated=0\n",valid,disjoint,masks,clean);
    _exit(valid && disjoint && masks && clean?0:3);
}
