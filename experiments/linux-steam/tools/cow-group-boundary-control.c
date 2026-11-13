/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <pthread.h>
#include "kernel/init.h"
#include "kernel/calls.h"
#include "kernel/mm.h"
#include "fs/real.h"
#include "fs/fd.h"
int ideck_cow_inject_failure;
struct writer {struct mem *mem;page_t page;unsigned char value;};
static pthread_mutex_t start_lock=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t start_condition=PTHREAD_COND_INITIALIZER;
static unsigned arrivals;
static void *write_page(void *arg) {
    struct writer *w=arg;
    assert(!pthread_mutex_lock(&start_lock));arrivals++;
    if(arrivals==4)assert(!pthread_cond_broadcast(&start_condition));
    while(arrivals<4)assert(!pthread_cond_wait(&start_condition,&start_lock));
    assert(!pthread_mutex_unlock(&start_lock));
    read_wrlock(&w->mem->lock);
    unsigned char *p=mem_ptr(w->mem,w->page*PAGE_SIZE,MEM_WRITE);assert(p);*p=w->value;
    read_wrunlock(&w->mem->lock);return NULL;
}
int main(int argc,char **argv) {
    assert(argc==2 && mount_root(&realfs,"/")==0 && become_first_process()==0);
    const page_t first=0x400;unsigned flags=P_READ|P_WRITE;
    assert(!pt_map_nothing(current->mem,first,4,flags));
    const char *mode=argv[1];
    if(!strcmp(mode,"protection"))assert(!pt_set_flags(current->mem,first+2,1,P_READ|P_ANONYMOUS));
    if(!strcmp(mode,"shared"))mem_pt(current->mem,first+2)->flags|=P_SHARED;
    if(!strcmp(mode,"hole"))assert(!pt_unmap(current->mem,first+2,1));
    if(!strcmp(mode,"different"))assert(!pt_map_nothing(current->mem,first+2,1,flags));
    if(!strcmp(mode,"offset"))mem_pt(current->mem,first+2)->offset=0;
    if(!strcmp(mode,"file")){
        struct data *data=mem_pt(current->mem,first)->data;
        data->fd=generic_open("/dev/null",0,0);assert(!IS_ERR(data->fd));
        data->file_offset=8192;
    }
    struct mem child;mem_init(&child);assert(!pt_copy_on_write(current->mem,&child,first,4));
    struct data *old=mem_pt(current->mem,first)->data;
    unsigned refs=atomic_load(&old->refcount);long charged=atomic_load(&anon_page_count);uint64_t changes=current->mem->mmu.changes;
    if(!strcmp(mode,"concurrent")){
        pthread_t threads[4];struct writer writers[4];
        for(unsigned i=0;i<4;i++){writers[i]=(struct writer){.mem=current->mem,.page=first+i,.value=(unsigned char)(31+i)};assert(!pthread_create(&threads[i],NULL,write_page,&writers[i]));}
        for(unsigned i=0;i<4;i++)assert(!pthread_join(threads[i],NULL));
        struct data *group=mem_pt(current->mem,first)->data;assert(group!=old);
        for(unsigned i=0;i<4;i++){
            struct pt_entry *p=mem_pt(current->mem,first+i),*c=mem_pt(&child,first+i);
            assert(p->data==group && *(unsigned char *)((char *)group->data+p->offset)==31+i);
            assert(*(unsigned char *)((char *)c->data->data+c->offset)==0);
        }
        assert(atomic_load(&anon_page_count)==charged);mem_destroy(&child);
        assert(!pt_unmap_always(current->mem,first,4) && !atomic_load(&anon_page_count));
        puts("HOST four concurrent writers retain all bytes in one private group; child unchanged PASS");return 0;
    }
    if(!strcmp(mode,"mmap-fail"))ideck_cow_inject_failure=1;
    if(!strcmp(mode,"data-fail"))ideck_cow_inject_failure=2;
    unsigned char byte=42;int failed=user_write(first*PAGE_SIZE,&byte,1);ideck_cow_inject_failure=0;
    if(strstr(mode,"-fail")){
        assert(failed && mem_pt(current->mem,first)->data==old);
        assert(atomic_load(&old->refcount)==refs && current->mem->mmu.changes==changes);
        for(unsigned i=0;i<4;i++)assert(*(unsigned char *)((char *)old->data+i*PAGE_SIZE)==0);
    }else{
        assert(!failed);struct data *group=mem_pt(current->mem,first)->data;
        assert(group!=old);
        if(!strcmp(mode,"file")){
            assert(group->fd==old->fd && group->file_offset==8192);
            assert(mem_pt(current->mem,first+1)->data==old);
        }else assert(mem_pt(current->mem,first+1)->data==group);
        if(!strcmp(mode,"all"))assert(mem_pt(current->mem,first+3)->data==group);
        else{
            assert(mem_pt(current->mem,first+3)->data==old);
            if(!strcmp(mode,"different"))assert(mem_pt(current->mem,first+2)->data!=old);
            else if(strcmp(mode,"hole"))assert(mem_pt(current->mem,first+2)->data==old);
            else assert(!mem_pt(current->mem,first+2));
        }
        for(unsigned i=0;i<4;i++){
            struct pt_entry *p=mem_pt(&child,first+i);
            if(p)assert(*(unsigned char *)((char *)p->data->data+p->offset)==0);
        }
        if(!strcmp(mode,"all")){
            /* Resolve COW in the child too; parent values must survive. */
            read_wrlock(&child.lock);
            unsigned char *p=mem_ptr(&child,(first+1)*PAGE_SIZE,MEM_WRITE);
            assert(p);*p=91;
            read_wrunlock(&child.lock);
            struct pt_entry *parent=mem_pt(current->mem,first+1);
            assert(*(unsigned char *)((char *)parent->data->data+parent->offset)==0);
            assert(!pt_unmap(current->mem,first+1,1));
            charged--; /* One logical anonymous page, not an entire group. */
            assert(atomic_load(&group->refcount)==3);
        }
    }
    assert(atomic_load(&anon_page_count)==charged);
    mem_destroy(&child);assert(!pt_unmap_always(current->mem,first,4));assert(!atomic_load(&anon_page_count));
    printf("HOST COW group boundary %s PASS\n",mode);return 0;
}
