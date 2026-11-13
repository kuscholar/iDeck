/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * HOST ONLY. Exact real kernel mm_copy/clone with scoped allocation failure. */
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "kernel/init.h"
#include "kernel/calls.h"
#include "kernel/mm.h"
#include "kernel/errno.h"
#include "fs/real.h"
#include "fs/fd.h"
static unsigned fail_calloc, fail_malloc, nc, nm;
static int armed;
void *ideck_test_calloc(size_t n,size_t size) {
    if(armed && ++nc==fail_calloc){errno=ENOMEM;return NULL;}
    return calloc(n,size);
}
void *ideck_test_malloc(size_t size) {
    if(armed && ++nm==fail_malloc){errno=ENOMEM;return NULL;}
    return malloc(size);
}
static page_t pages[]={0x200,0x400,0x40000,0x8000000,0x8000001};
static struct data *backings[5];
static unsigned flags[5];
static long original_count;
static void check_parent(void) {
    assert(atomic_load(&anon_page_count)==original_count);
    for(unsigned i=0;i<5;i++){
        struct pt_entry *p=mem_pt(current->mem,pages[i]);
        assert(p && p->data==backings[i] && atomic_load(&p->data->refcount)==1);
        assert((p->flags & ~P_COW)==flags[i]);
        if(i!=4)assert(*(unsigned char *)p->data->data==(unsigned char)(90+i));
        if(flags[i]&P_SHARED)assert(!(p->flags&P_COW));
    }
}
static void setup(void) {
    assert(mount_root(&realfs,"/")==0 && become_first_process()==0);
    current->mm->exefile=generic_open("/dev/null",0,0);
    assert(!IS_ERR(current->mm->exefile));
    for(unsigned i=0;i<5;i++){
        flags[i]=P_READ|P_WRITE|P_ANONYMOUS;
        if(i==3)flags[i]|=P_SHARED;
        if(i==4)flags[i]=P_ANONYMOUS; /* PROT_NONE is not charged. */
        assert(!pt_map_nothing(current->mem,pages[i],1,flags[i]));
        struct pt_entry *p=mem_pt(current->mem,pages[i]);backings[i]=p->data;
        if(i!=4)*(unsigned char *)p->data->data=(unsigned char)(90+i);
    }
    assert(!pt_map_lazy(current->mem,0x9000000,3,P_READ|P_WRITE));
    assert(!pt_map_lazy(current->mem,0xa000000,7,P_READ));
    original_count=atomic_load(&anon_page_count);check_parent();
}
int main(int argc,char **argv) {
    assert(argc==4);setup();
    fail_calloc=(unsigned)atoi(argv[2]);fail_malloc=(unsigned)atoi(argv[3]);
    armed=1;
    if(!strcmp(argv[1],"clone")){
        dword_t value=sys_clone(17,0,0,0,0);armed=0;
        assert((int)value==_ENOMEM);check_parent();
    }else{
        struct mm *child=mm_copy(current->mm);armed=0;
        if(fail_calloc || fail_malloc){assert(child==NULL);check_parent();}
        else{
            assert(child);unsigned reservations=0;
            for(struct mem_reservation *r=child->mem.reservations;r;r=r->next)reservations++;
            assert(reservations==2);
            for(unsigned i=0;i<5;i++){
                struct pt_entry *p=mem_pt(&child->mem,pages[i]);
                assert(p && p->data==backings[i] && atomic_load(&p->data->refcount)==2);
                assert((p->flags & ~P_COW)==flags[i]);
            }
            mm_release(child);check_parent();
        }
    }
    printf("HOST fork failure control mode=%s calloc=%u malloc=%u PASS\n",argv[1],nc,nm);
    return 0;
}
