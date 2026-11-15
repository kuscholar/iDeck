/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#include "BlockedWaitCallers.h"
#include "kernel/init.h"
#include "kernel/calls.h"
#include "kernel/mm.h"
#include "fs/real.h"
#include "fs/fd.h"
#include <assert.h>
#include <pthread.h>
#include <stdio.h>
#include <string.h>

static pthread_mutex_t gate=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t condition=PTHREAD_COND_INITIALIZER;
static int locked,done;
static void *hold(void *arg){struct mem *mem=arg;write_wrlock(&mem->lock);
    pthread_mutex_lock(&gate);locked=1;pthread_cond_broadcast(&condition);
    while(!done)pthread_cond_wait(&condition,&gate);pthread_mutex_unlock(&gate);
    write_wrunlock(&mem->lock);return NULL;
}
int main(int argc,char **argv){
    assert(argc==2&&!mount_root(&realfs,"/")&&!become_first_process());
    const char *mode=argv[1];page_t stack=0x400,code=0x600;
    assert(!pt_map_nothing(current->mem,stack,4,P_READ|P_WRITE|P_GROWSDOWN));
    assert(!pt_map_nothing(current->mem,code,1,P_READ|P_WRITE));
    struct pt_entry *cp=mem_pt(current->mem,code);
    cp->data->fd=generic_open("/dev/null",0,0);assert(!IS_ERR(cp->data->fd));
    for(unsigned i=0;i<4;i++){
        uint64_t fp=stack*PAGE_SIZE+0x100+i*32,lr=code*PAGE_SIZE+0x100+i*0x80;
        uint64_t abi[2]={i==3?0:fp+32,lr};assert(!user_write(fp,abi,sizeof abi));
        uint32_t instructions[9];for(unsigned j=0;j<9;j++)instructions[j]=0xd503201f;
        instructions[3]=0x94000008+i;assert(!user_write(lr-16,instructions,sizeof instructions));
    }
    cp->flags=P_READ|P_EXEC;
    uint64_t fp=stack*PAGE_SIZE+0x100,original[2];assert(!user_read(fp,original,sizeof original));
    unsigned expected_count=4,expected_status=0;struct pt_entry *sp=mem_pt(current->mem,stack);
    size_t saved_offset=sp->offset;
    if(!strcmp(mode,"unaligned")){fp++;expected_count=0;expected_status=4;}
    else if(!strcmp(mode,"unmapped")){fp=0x700100;expected_count=0;expected_status=2;}
    else if(!strcmp(mode,"nonstack")){sp->flags&=~P_GROWSDOWN;expected_count=0;expected_status=2;}
    else if(!strcmp(mode,"stack-no-read")){sp->flags&=~P_READ;expected_count=0;expected_status=2;}
    else if(!strcmp(mode,"code-no-exec")){cp->flags&=~P_EXEC;expected_count=0;expected_status=3;}
    else if(!strcmp(mode,"code-no-file")){
        fd_close(cp->data->fd);cp->data->fd=NULL;expected_count=0;expected_status=3;
    }else if(!strcmp(mode,"bad-data-bound")){sp->offset=sp->data->size;expected_count=0;expected_status=2;}
    else if(!strcmp(mode,"noncall")){
        uint32_t word=0xd503201f;cp->flags|=P_WRITE;assert(!user_write(original[1]-4,&word,4));cp->flags&=~P_WRITE;expected_count=0;expected_status=3;
    }else if(!strcmp(mode,"cycle")||!strcmp(mode,"distant")){
        uint64_t next=!strcmp(mode,"cycle")?fp:fp+2*1024*1024;
        assert(!user_write(fp,&next,8));expected_count=1;expected_status=4;
    }else if(!strcmp(mode,"terminal")){uint64_t zero=0;assert(!user_write(fp,&zero,8));expected_count=1;}
    else if(!strcmp(mode,"code-page-cross")){
        uint64_t lr=code*PAGE_SIZE+4;assert(!user_write(fp+8,&lr,8));expected_count=0;expected_status=3;
    }else assert(!strcmp(mode,"valid")||!strcmp(mode,"busy"));
    uint64_t generation=current->mem->mmu.changes;long charged=atomic_load(&anon_page_count);
    struct ideck_wait_callers observed;
    if(!strcmp(mode,"busy")){
        pthread_t thread;assert(!pthread_create(&thread,NULL,hold,current->mem));
        pthread_mutex_lock(&gate);while(!locked)pthread_cond_wait(&condition,&gate);pthread_mutex_unlock(&gate);
        ideck_blocked_wait_callers(current->mem,fp,&observed);
        assert(!observed.count&&observed.status==1);
        pthread_mutex_lock(&gate);done=1;pthread_cond_broadcast(&condition);pthread_mutex_unlock(&gate);assert(!pthread_join(thread,NULL));
    }else{
        ideck_blocked_wait_callers(current->mem,fp,&observed);
        assert(observed.count==expected_count&&observed.status==expected_status);
        for(unsigned i=0;i<observed.count;i++)assert(observed.frames[i].lr==code*PAGE_SIZE+0x100+i*0x80&&observed.frames[i].code[3]==0x94000008+i);
    }
    assert(current->mem->mmu.changes==generation&&atomic_load(&anon_page_count)==charged);
    sp->offset=saved_offset;
    assert(!pt_unmap_always(current->mem,stack,4)&&!pt_unmap_always(current->mem,code,1));
    puts("HOST bounded existing ABI/code caller snapshot PASS; no page materialization/accounting/generation changes");return 0;
}
