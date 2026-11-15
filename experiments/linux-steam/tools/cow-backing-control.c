/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * HOST measurement of real pinned COW backing granularity, no allocator patch. */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "kernel/init.h"
#include "kernel/calls.h"
#include "kernel/mm.h"
#include "fs/real.h"
#if IDECK_LAB_COW_BROKER
#include "CowBackingBroker.h"
#endif
#ifndef IDECK_COW_GROUPED
#define IDECK_COW_GROUPED 0
#endif
#ifndef IDECK_COW_NATIVE_PAGES
#define IDECK_COW_NATIVE_PAGES 1
#endif
int ideck_cow_inject_failure;
int main(int argc,char **argv) {
    assert(argc==2 && (!strcmp(argv[1],"dense") || !strcmp(argv[1],"sparse")));
    const unsigned stride=!strcmp(argv[1],"dense")?1:8;
    assert(mount_root(&realfs,"/")==0 && become_first_process()==0);
    const page_t first=0x400;const pages_t count=256;
    assert(!pt_map_nothing(current->mem,first,count,P_READ|P_WRITE));
    struct mem child;mem_init(&child);
    assert(!pt_copy_on_write(current->mem,&child,first,count));
    long charged=atomic_load(&anon_page_count);
    unsigned distinct=0;size_t rounded_total=0;struct data *seen[256];
    for(unsigned i=0;i<count;i+=stride){
        unsigned char value=(unsigned char)(i+1);
        assert(!user_write((first+i)*PAGE_SIZE,&value,1));
        struct pt_entry *p=mem_pt(current->mem,first+i);
        assert(p && !(p->flags&P_COW) && *(unsigned char *)((char *)p->data->data+p->offset)==value);
        struct pt_entry *original=mem_pt(&child,first+i);
        assert(original && *(unsigned char *)((char *)original->data->data+original->offset)==0);
        unsigned j=0;while(j<distinct && seen[j]!=p->data)j++;
        if(j==distinct){seen[distinct++]=p->data;rounded_total+=(p->data->size+real_page_size-1)/real_page_size*real_page_size;}
    }
    /* Check EVERY byte, including materialized-but-unwritten adjacent pages. */
    for(unsigned i=0;i<count;i++){
        struct pt_entry *p=mem_pt(current->mem,first+i),*c=mem_pt(&child,first+i);
        assert(p && c && (p->flags&P_WRITE) && (c->flags&P_COW));
        for(unsigned b=0;b<PAGE_SIZE;b++){
            unsigned char expected=(!b && !(i%stride))?(unsigned char)(i+1):0;
            assert(*((unsigned char *)p->data->data+p->offset+b)==expected);
            assert(*((unsigned char *)c->data->data+c->offset+b)==0);
        }
    }
    assert(atomic_load(&anon_page_count)==charged);
    unsigned group=IDECK_COW_GROUPED?(unsigned)(real_page_size/PAGE_SIZE)*IDECK_COW_NATIVE_PAGES:1;
    unsigned expected=stride>=group?(unsigned)(count/stride):(unsigned)(count/group);
    assert(distinct==expected && real_page_size>=PAGE_SIZE);
    size_t expected_bytes=(size_t)distinct*((group*PAGE_SIZE+real_page_size-1)/real_page_size*real_page_size);
    assert(rounded_total==expected_bytes);
    printf("HOST mode=%s cow_backings=%u guest_bytes=%llu native_page_size=%zu native_pages_per_group=%d rounded_mapping_bytes=%zu\n",argv[1],distinct,(unsigned long long)count*PAGE_SIZE,real_page_size,IDECK_COW_NATIVE_PAGES,rounded_total);
#if IDECK_LAB_COW_BROKER
    struct ideck_cow_broker_stats stats;ideck_cow_broker_read_stats(&stats);
    assert(stats.live_slots==distinct&&stats.live_guest_bytes==distinct*(real_page_size/PAGE_SIZE)*PAGE_SIZE);
    assert(stats.live_chunks==1&&stats.map_attempts==1);
    printf("HOST actual_broker_native_maps=%llu reserved_bytes=%llu logical_backings=%u NOT_RSS=1\n",(unsigned long long)stats.map_attempts,(unsigned long long)stats.reserved_native_bytes,distinct);
#endif
    mem_destroy(&child);assert(!pt_unmap(current->mem,first,count));assert(atomic_load(&anon_page_count)==0);
#if IDECK_LAB_COW_BROKER
    ideck_cow_broker_read_stats(&stats);assert(!stats.live_slots&&!stats.live_chunks&&!stats.live_guest_bytes&&!stats.reserved_native_bytes);
#endif
    puts("Parent writes isolated from child; accounting returns0; this measures rounded mapping capacity, NOT physical resident bytes or exact VM region count");
    return 0;
}
