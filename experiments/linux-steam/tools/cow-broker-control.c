/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * HOST real mmap ownership and deliberately broken backend controls. */
#include "CowBackingBroker.h"
#include <sys/mman.h>
#include <unistd.h>
#include <pthread.h>
#include <errno.h>
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <stdint.h>
static unsigned backend_maps,backend_unmaps,real_maps,real_unmaps,fail_map,fail_unmap;
static unsigned advice_calls,fail_advice;
static int duplicate_next;
static void *first_mapping;
void *ideck_broker_test_mmap(void *hint,size_t n,int prot,int flags,int fd,off_t off){
    backend_maps++;assert(!hint && prot==(PROT_READ|PROT_WRITE) && flags==(MAP_PRIVATE|MAP_ANONYMOUS) && fd==-1 && !off);
    if(fail_map==backend_maps){errno=ENOMEM;return MAP_FAILED;}
    if(duplicate_next){duplicate_next=0;assert(first_mapping);return first_mapping;}
    void *p=mmap(hint,n,prot,flags,fd,off);assert(p!=MAP_FAILED);real_maps++;
    if(!first_mapping)first_mapping=p;return p;
}
int ideck_broker_test_munmap(void *p,size_t n){
    backend_unmaps++;
    if(fail_unmap==backend_unmaps){errno=EIO;return -1;}
    int r=munmap(p,n);assert(!r);real_unmaps++;return r;
}
int ideck_broker_test_madvise(void *p,size_t n,int advice){
    advice_calls++;size_t page=(size_t)sysconf(_SC_PAGESIZE);
    assert(p&&(uintptr_t)p%page==0&&n==page&&advice==MADV_FREE);
    if(fail_advice==advice_calls){errno=EIO;return -1;}
    return madvise(p,n,advice);
}
static struct ideck_cow_broker_stats snapshot(void){struct ideck_cow_broker_stats s;ideck_cow_broker_read_stats(&s);return s;}
static void empty(void){struct ideck_cow_broker_stats s=snapshot();assert(!s.live_slots&&!s.live_chunks&&!s.live_guest_bytes&&!s.reserved_native_bytes);assert(real_maps==real_unmaps);}
static void *take(size_t bytes,unsigned char value){
    unsigned char *p=ideck_cow_broker_allocate(bytes);assert(p!=MAP_FAILED);
    for(size_t i=0;i<bytes;i++)assert(!p[i]);memset(p,value,bytes);return p;
}
static void check(const void *p,size_t bytes,unsigned char value){for(size_t i=0;i<bytes;i++)assert(((const unsigned char *)p)[i]==value);}
static void release(void *p,size_t n){assert(ideck_cow_broker_release_owned(p,n)==1);}
static pthread_mutex_t barrier_lock=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t barrier_cond=PTHREAD_COND_INITIALIZER;
static unsigned arrivals,generation;
static void barrier(void){pthread_mutex_lock(&barrier_lock);unsigned old=generation;
    if(++arrivals==8){arrivals=0;generation++;pthread_cond_broadcast(&barrier_cond);}
    else while(old==generation)pthread_cond_wait(&barrier_cond,&barrier_lock);
    pthread_mutex_unlock(&barrier_lock);
}
static void *concurrent_slots[8][32];
static void *worker(void *arg){unsigned id=(unsigned)(uintptr_t)arg;size_t page=(size_t)sysconf(_SC_PAGESIZE);
    for(unsigned wave=0;wave<8;wave++){
        unsigned char value=(unsigned char)(id+wave*8+1);
        for(unsigned j=0;j<32;j++)concurrent_slots[id][j]=take(page,value);
        barrier();
        if(!id)for(unsigned a=0;a<256;a++)for(unsigned b=a+1;b<256;b++){
            uintptr_t x=(uintptr_t)concurrent_slots[a/32][a%32],y=(uintptr_t)concurrent_slots[b/32][b%32];
            assert(x+page<=y||y+page<=x);
        }
        for(unsigned j=0;j<32;j++)check(concurrent_slots[id][j],page,value);
        barrier();for(unsigned j=0;j<32;j++)release(concurrent_slots[id][j],page);barrier();
    }return NULL;
}
int main(int argc,char **argv){
    assert(argc==2);setvbuf(stdout,NULL,_IONBF,0);size_t page=(size_t)sysconf(_SC_PAGESIZE);assert(page>=4096&&page<=65536);
    const char *mode=argv[1];void *p[256]={0};
    if(!strcmp(mode,"baseline")||!strcmp(mode,"baseline-sparse")||!strcmp(mode,"dense")||!strcmp(mode,"sparse")){
        int sparse=strstr(mode,"sparse")!=NULL;
        unsigned count=sparse?16:128;size_t bytes=sparse?page/2:page;
        if(bytes<4096)bytes=4096;int direct=!strncmp(mode,"baseline",8);
        for(unsigned i=0;i<count;i++){
            p[i]=direct?mmap(NULL,bytes,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0):take(bytes,41);
            assert(p[i]!=MAP_FAILED);if(direct)memset(p[i],41,bytes);
            for(unsigned j=0;j<i;j++)assert((uintptr_t)p[i]+page<=(uintptr_t)p[j]||(uintptr_t)p[j]+page<=(uintptr_t)p[i]);
        }
        struct ideck_cow_broker_stats s=snapshot();
        printf("HOST mode=%s objects=%u guest_bytes=%zu selected_native_mmap_calls=%u native_reserved_bytes=%llu NOT_RSS_or_VM_region_count=1\n",mode,count,count*bytes,direct?count:backend_maps,(unsigned long long)(direct?count*page:s.reserved_native_bytes));
        if(!direct)assert(s.live_slots==count&&s.live_chunks==1&&s.live_guest_bytes==count*bytes&&backend_maps==1);
        for(unsigned i=0;i<count;i++){check(p[i],bytes,41);if(direct)assert(!munmap(p[i],bytes));else release(p[i],bytes);}
    }else if(!strcmp(mode,"stranded-sparse")){
        for(unsigned i=0;i<256;i++)p[i]=take(page,43);
        for(unsigned i=0;i<256;i++)if(i!=0&&i!=128)release(p[i],page);
        struct ideck_cow_broker_stats s=snapshot();
        assert(s.live_slots==2&&s.live_chunks==2&&s.advice_calls==254&&advice_calls==254&&!s.advice_failures);
        assert(s.reserved_native_bytes==256*page&&s.live_guest_bytes==2*page);
        check(p[0],page,43);check(p[128],page,43);
        printf("HOST sparse_retention live_objects=2 logical_bytes=%zu reserved_native_bytes=%llu advice_calls=254 physical_reclaim_NOT_measured=1\n",2*page,(unsigned long long)s.reserved_native_bytes);
        release(p[0],page);release(p[128],page);
    }else if(!strcmp(mode,"advice-fail")){
        p[0]=take(page,31);p[1]=take(page,53);fail_advice=1;
        release(p[0],page);assert(snapshot().advice_failures==1&&snapshot().live_slots==1);
        check(p[1],page,53);p[0]=take(page,71);check(p[1],page,53);
        release(p[0],page);release(p[1],page);
    }else if(!strcmp(mode,"invalid-reuse")){
        assert(ideck_cow_broker_allocate(0)==MAP_FAILED&&errno==EINVAL);
        assert(ideck_cow_broker_allocate(1)==MAP_FAILED&&errno==EINVAL);
        assert(ideck_cow_broker_allocate(page+4096)==MAP_FAILED&&errno==EINVAL);assert(!backend_maps);
        char foreign=0;assert(!ideck_cow_broker_release_owned(&foreign,1));
        p[0]=take(page,31);p[1]=take(page,53);
        assert(ideck_cow_broker_release_owned((char *)p[0]+1,page)<0);
        assert(ideck_cow_broker_release_owned(p[0],page-1)<0);
        assert(ideck_cow_broker_release_owned((char *)p[0]+page*3,page)<0);
        check(p[0],page,31);check(p[1],page,53);release(p[0],page);
        assert(ideck_cow_broker_release_owned(p[0],page)<0);p[0]=take(page,71);
        check(p[1],page,53);release(p[0],page);release(p[1],page);assert(snapshot().ownership_errors==4);
    }else if(!strcmp(mode,"fail-first")){
        fail_map=1;assert(ideck_cow_broker_allocate(page)==MAP_FAILED&&errno==ENOMEM);
        assert(backend_maps==1&&!real_maps&&snapshot().map_failures==1);
    }else if(!strcmp(mode,"fail-second")||!strcmp(mode,"overlap")||!strcmp(mode,"capacity")){
        unsigned count=!strcmp(mode,"capacity")?256:128;
        for(unsigned i=0;i<count;i++)p[i]=take(page,(unsigned char)(i+1));
        if(!strcmp(mode,"fail-second"))fail_map=2;
        if(!strcmp(mode,"overlap"))duplicate_next=1;
        unsigned attempts=backend_maps;
        assert(ideck_cow_broker_allocate(page)==MAP_FAILED);
        if(!strcmp(mode,"overlap")){assert(errno==EFAULT&&snapshot().overlap_rejections==1&&backend_maps==attempts+1&&!backend_unmaps);}
        else if(!strcmp(mode,"capacity")){assert(errno==ENOMEM&&snapshot().capacity_refusals==1&&backend_maps==attempts);}
        else assert(errno==ENOMEM&&snapshot().map_failures==1&&backend_maps==2);
        for(unsigned i=0;i<count;i++)check(p[i],page,(unsigned char)(i+1));
        release(p[0],page);attempts=backend_maps;p[0]=take(page,79);assert(backend_maps==attempts);
        for(unsigned i=0;i<count;i++)release(p[i],page);
    }else if(!strcmp(mode,"unmap-fail")){
        p[0]=take(page,89);fail_unmap=1;
        assert(ideck_cow_broker_release_owned(p[0],page)==-EIO);check(p[0],page,89);
        assert(snapshot().live_slots==1&&snapshot().live_chunks==1&&snapshot().native_unmap_failures==1);
        release(p[0],page);assert(backend_unmaps==2&&real_unmaps==1);
    }else if(!strcmp(mode,"concurrency")){
        pthread_t t[8];for(unsigned i=0;i<8;i++)assert(!pthread_create(&t[i],NULL,worker,(void *)(uintptr_t)i));
        for(unsigned i=0;i<8;i++)assert(!pthread_join(t[i],NULL));
        assert(snapshot().allocation_calls==2048&&real_maps==16&&real_unmaps==16);
    }else assert(!"Unknown test mode");
    empty();printf("HOST broker %s PASS; real_maps=%u real_unmaps=%u foreign grants untouched\n",mode,real_maps,real_unmaps);return 0;
}
