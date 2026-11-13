/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * HOST measurement of real pinned COW backing granularity, no allocator patch. */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include "kernel/init.h"
#include "kernel/calls.h"
#include "kernel/mm.h"
#include "fs/real.h"
int main(void) {
    assert(mount_root(&realfs,"/")==0 && become_first_process()==0);
    const page_t first=0x400;const pages_t count=64;
    assert(!pt_map_nothing(current->mem,first,count,P_READ|P_WRITE));
    struct mem child;mem_init(&child);
    assert(!pt_copy_on_write(current->mem,&child,first,count));
    long charged=atomic_load(&anon_page_count);
    unsigned distinct=0;size_t rounded_total=0;struct data *seen[64];
    for(unsigned i=0;i<count;i++){
        unsigned char value=(unsigned char)(i+1);
        assert(!user_write((first+i)*PAGE_SIZE,&value,1));
        struct pt_entry *p=mem_pt(current->mem,first+i);
        assert(p && !(p->flags&P_COW) && *(unsigned char *)((char *)p->data->data+p->offset)==value);
        struct pt_entry *original=mem_pt(&child,first+i);
        assert(original && *(unsigned char *)((char *)original->data->data+original->offset)==0);
        unsigned j=0;while(j<distinct && seen[j]!=p->data)j++;
        if(j==distinct){seen[distinct++]=p->data;rounded_total+=(p->data->size+real_page_size-1)/real_page_size*real_page_size;}
    }
    assert(atomic_load(&anon_page_count)==charged);
    assert(distinct==count && real_page_size>=PAGE_SIZE);
    printf("HOST original_cow_backings=%u guest_bytes=%llu native_page_size=%zu rounded_mapping_bytes=%zu amplification=%zu\n",distinct,(unsigned long long)count*PAGE_SIZE,real_page_size,rounded_total,(size_t)(rounded_total/(count*PAGE_SIZE)));
    mem_destroy(&child);assert(!pt_unmap(current->mem,first,count));assert(atomic_load(&anon_page_count)==0);
    puts("Parent writes isolated from child; accounting returns0; this measures rounded mapping capacity, NOT physical resident bytes or exact VM region count");
    return 0;
}
