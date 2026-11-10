/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * HOST ONLY real pinned kernel mappings, not iPad/Steam validation.
 */
#include "kernel/task.h"
#include "kernel/calls.h"
#include "kernel/errno.h"
#include "fs/fd.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <stdatomic.h>
#include <pthread.h>
#include <sched.h>
extern uint64_t ideck_private_discard_count(void);
extern uint64_t ideck_private_discard_replaced_bytes(void);
static struct task owner;
static unsigned checks;
static const page_t base = 0x4100000;
static void check(const char *name, int ok) { printf("%s=%s\n", name, ok?"PASS":"FAIL"); assert(ok); checks++; }
static struct mem *fresh(void) {
    static const struct fd_ops noop={0};
    owner.mm=mm_new();assert(owner.mm);owner.mem=&owner.mm->mem;current=&owner;
    /* mm_copy requires the loader's retained executable description. Supply a
     * real kernel-owned no-I/O description, not a NULL/fabricated descriptor. */
    owner.mm->exefile=fd_create(&noop);assert(owner.mm->exefile);return owner.mem;
}
static void finish(void) { mm_release(owner.mm);owner.mm=NULL;owner.mem=NULL; }
static void map(struct mem *mem,page_t page,pages_t pages,unsigned flags) {
    write_wrlock(&mem->lock);assert(pt_map_nothing(mem,page,pages,flags)==0);write_wrunlock(&mem->lock);
}
static void fill(struct mem *mem,page_t page,pages_t pages,unsigned char value) {
    read_wrlock(&mem->lock);
    for(pages_t i=0;i<pages;i++){void *p=mem_ptr(mem,(page+i)*PAGE_SIZE,MEM_WRITE);assert(p);memset(p,value,PAGE_SIZE);}
    read_wrunlock(&mem->lock);
}
static int equals(struct mem *mem,page_t page,pages_t pages,unsigned char value) {
    int ok=1;read_wrlock(&mem->lock);
    for(pages_t i=0;i<pages;i++){
        const unsigned char *p=mem_ptr(mem,(page+i)*PAGE_SIZE,MEM_READ);assert(p);
        for(size_t j=0;j<PAGE_SIZE;j++)if(p[j]!=value)ok=0;
    }
    read_wrunlock(&mem->lock);return ok;
}
static int discard(page_t page,pages_t pages){return (int)sys_madvise(page*PAGE_SIZE,pages*PAGE_SIZE,4);}
struct concurrent_reader { struct mm *mm; atomic_int started,stop,failed; atomic_uint observations; };
static void *read_concurrently(void *argument) {
    struct concurrent_reader *state=argument;struct task task={.mm=state->mm,.mem=&state->mm->mem};current=&task;
    atomic_store(&state->started,1);
    while(!atomic_load(&state->stop)) {
        struct mem *mem=task.mem;read_wrlock_yield_to_writers(&mem->lock);
        for(pages_t i=0;i<4;i++) {
            const unsigned char *bytes=mem_ptr(mem,(base+i)*PAGE_SIZE,MEM_READ);assert(bytes);
            /* The original fallback zeros in place under a shared read lock;
             * old-or-zero bytes are valid here, not whole-range atomicity. */
            for(size_t j=0;j<PAGE_SIZE;j++) {
                /* One observation: two separate reads could legitimately see
                 * old then zero and falsely report an impossible value. */
                unsigned char observed=__atomic_load_n(bytes+j,__ATOMIC_RELAXED);
                if(observed!=0&&observed!=109)atomic_store(&state->failed,1);
            }
        }
        read_wrunlock(&mem->lock);atomic_fetch_add(&state->observations,1);
    }
    return NULL;
}
int main(int argc,char **argv) {
    setvbuf(stdout,NULL,_IONBF,0);
    if(argc!=2 || (strcmp(argv[1],"normal")&&strcmp(argv[1],"fail-second")))return 2;
    int fail=!strcmp(argv[1],"fail-second");unsigned rw=P_READ|P_WRITE;
    struct mem *mem=fresh();map(mem,base,4,rw);fill(mem,base,4,37);
    struct data *before=mem_pt(mem,base)->data;long charged=atomic_load(&anon_page_count);
    unsigned flags=mem_pt(mem,base)->flags;uint64_t generation=mem->mmu.changes;
    check("whole-private-discard-zero",discard(base,4)==0&&equals(mem,base,4,0));
    check("whole-private-backing-replaced",mem_pt(mem,base)->data!=before&&ideck_private_discard_count()==1);
    check("logical-accounting-and-flags-preserved",atomic_load(&anon_page_count)==charged&&mem_pt(mem,base)->flags==flags);
    check("generation-invalidated",mem->mmu.changes>generation);
    fill(mem,base,4,53);check("replacement-writable",equals(mem,base,4,53));finish();

    mem=fresh();map(mem,base,8,rw);fill(mem,base,8,61);before=mem_pt(mem,base)->data;
    check("partial-original-fallback",discard(base,4)==0&&mem_pt(mem,base)->data==before&&equals(mem,base,4,0)&&equals(mem,base+4,4,61));finish();

    mem=fresh();map(mem,base,4,rw);fill(mem,base,4,67);before=mem_pt(mem,base)->data;atomic_fetch_add(&before->refcount,1);
    check("retained-backing-original-fallback",discard(base,4)==0&&mem_pt(mem,base)->data==before&&equals(mem,base,4,0));data_release(before);finish();

    mem=fresh();map(mem,base,4,rw);fill(mem,base,4,69);before=mem_pt(mem,base)->data;
    read_wrlock(&mem->lock);int busy_result=discard(base,4);read_wrunlock(&mem->lock);
    check("busy-writer-lock-original-fallback",busy_result==0&&mem_pt(mem,base)->data==before&&equals(mem,base,4,0));finish();

    mem=fresh();map(mem,base,4,rw);fill(mem,base,4,71);before=mem_pt(mem,base)->data;
    write_wrlock(&mem->lock);assert(pt_set_flags(mem,base,4,P_READ)==0);write_wrunlock(&mem->lock);
    check("readonly-original-fallback",discard(base,4)==0&&mem_pt(mem,base)->data==before&&equals(mem,base,4,71));finish();

    mem=fresh();map(mem,base,4,rw|P_EXEC);fill(mem,base,4,73);before=mem_pt(mem,base)->data;
    check("executable-original-fallback",discard(base,4)==0&&mem_pt(mem,base)->data==before&&equals(mem,base,4,0));finish();

    mem=fresh();map(mem,base,4,rw|P_SHARED);fill(mem,base,4,79);before=mem_pt(mem,base)->data;
    check("shared-original-fallback",discard(base,4)==0&&mem_pt(mem,base)->data==before);finish();

    mem=fresh();map(mem,base,4,rw);fill(mem,base,4,83);before=mem_pt(mem,base)->data;
    /* Only test the metadata refusal. No fake descriptor is used by fd code. */
    before->fd=(struct fd *)(uintptr_t)1;
    for(pages_t i=0;i<4;i++)mem_pt(mem,base+i)->flags&=~P_ANONYMOUS;
    atomic_fetch_sub(&anon_page_count,4);
    check("file-identity-original-fallback",discard(base,4)==0&&mem_pt(mem,base)->data==before&&equals(mem,base,4,83));before->fd=NULL;finish();

    mem=fresh();map(mem,base,4,rw);fill(mem,base,4,89);
    check("unmapped-range-enomem",discard(base,8)==_ENOMEM&&equals(mem,base,4,89));
    check("madv-free-original-contents",sys_madvise(base*PAGE_SIZE,4*PAGE_SIZE,8)==0&&equals(mem,base,4,89));finish();

    mem=fresh();map(mem,base,4,rw);fill(mem,base,4,97);struct mm *parent=owner.mm,*child=mm_copy(parent);assert(child);
    owner.mm=child;owner.mem=&child->mem;
    check("cow-child-discard-zero",discard(base,4)==0&&equals(owner.mem,base,4,0));
    check("cow-parent-retains-data",equals(&parent->mem,base,4,97));finish();owner.mm=parent;owner.mem=&parent->mem;finish();

    mem=fresh();write_wrlock(&mem->lock);assert(pt_map_lazy(mem,base,256,rw)==0);write_wrunlock(&mem->lock);
    map(mem,base,4,rw);fill(mem,base,4,101);struct mem_reservation *reservation=mem_find_reservation(mem,base);assert(reservation);
    check("lazy-reservation-preserved",discard(base,4)==0&&equals(mem,base,4,0)&&mem_find_reservation(mem,base)==reservation&&reservation->start==base&&reservation->pages==256);finish();

    mem=fresh();map(mem,base,4,rw);map(mem,base+4,4,rw);fill(mem,base,8,103);
    struct data *a=mem_pt(mem,base)->data,*b=mem_pt(mem,base+4)->data;charged=atomic_load(&anon_page_count);uint64_t old_count=ideck_private_discard_count();
    check("multi-backing-zero",discard(base,8)==0&&equals(mem,base,8,0));
    check(fail?"allocation-failure-no-partial-commit":"multi-backing-replaced",fail?
        mem_pt(mem,base)->data==a&&mem_pt(mem,base+4)->data==b&&ideck_private_discard_count()==old_count:
        mem_pt(mem,base)->data!=a&&mem_pt(mem,base+4)->data!=b&&ideck_private_discard_count()==old_count+1);
    check("multi-backing-accounting-preserved",atomic_load(&anon_page_count)==charged);finish();
    mem=fresh();map(mem,base,4,rw);struct concurrent_reader reader={.mm=owner.mm};pthread_t thread;
    assert(!pthread_create(&thread,NULL,read_concurrently,&reader));
    while(!atomic_load(&reader.started)||!atomic_load(&reader.observations))sched_yield();
    for(unsigned n=0;n<100;n++) {
        write_wrlock(&mem->lock);
        for(pages_t i=0;i<4;i++) {
            struct pt_entry *entry=mem_pt(mem,base+i);memset((char *)entry->data->data+entry->offset,109,PAGE_SIZE);
        }
        write_wrunlock(&mem->lock);assert(discard(base,4)==0);
    }
    atomic_store(&reader.stop,1);assert(!pthread_join(thread,NULL));
    check("concurrent-reader-no-stale-or-invalid-backing",!atomic_load(&reader.failed)&&atomic_load(&reader.observations)>0);finish();
    check("all-test-mappings-released",atomic_load(&anon_page_count)==0);
    printf("checks=%u replaced_bytes=%llu scope=HOST_ONLY\n",checks,(unsigned long long)ideck_private_discard_replaced_bytes());
    return 0;
}
