/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * Private LinuxRunner overlay; caller owns mem write lock. Anonymous private
 * COW only. No file/memfd/shared/protection crossing; original path otherwise. */
static int ideck_cow_native_group(struct mem *mem,page_t page,int type) {
    if(type!=MEM_WRITE)return 0;
    pages_t group=real_page_size/PAGE_SIZE;
    if(group<=1||group>16||(group&(group-1)))return 0;
    struct pt_entry *entry=mem_pt(mem,page);
    if(!entry||!(entry->flags&P_COW)||!(entry->flags&P_WRITE)||
       !(entry->flags&P_ANONYMOUS)||(entry->flags&P_SHARED)||
       entry->data->fd||entry->data->memfd_maywrite)return 0;
    struct data *old=entry->data;unsigned flags=entry->flags;
    page_t lower=page&~(group-1),upper=lower+group,first=page,end=page+1;
    while(first>lower){
        struct pt_entry *p=mem_pt(mem,first-1);
        if(!p||p->data!=old||p->flags!=flags||p->offset+PAGE_SIZE!=mem_pt(mem,first)->offset)break;
        first--;
    }
    while(end<upper){
        struct pt_entry *p=mem_pt(mem,end);
        if(!p||p->data!=old||p->flags!=flags||p->offset!=mem_pt(mem,end-1)->offset+PAGE_SIZE)break;
        end++;
    }
    if(end-first<2)return 0;
    size_t bytes=(size_t)(end-first)*PAGE_SIZE;
    size_t source=mem_pt(mem,first)->offset;
    if(source>old->size||bytes>old->size-source)return 0;
    void *copy=mmap(NULL,bytes,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,0,0);
    if(copy==MAP_FAILED)return _ENOMEM;
    struct data *replacement=malloc(sizeof(*replacement));
    if(!replacement){munmap(copy,bytes);return _ENOMEM;}
    memset(replacement,0,sizeof(*replacement));
    replacement->data=copy;replacement->size=bytes;replacement->name=old->name;
    atomic_init(&replacement->refcount,(unsigned)(end-first));
    memcpy(copy,(char *)old->data+source,bytes);
    /* No fallible operation after this point. The same charged private pages
     * remain mapped, so anonymous accounting must not be adjusted. Invalidate
     * old translated blocks before the final old reference can be released. */
    asbestos_invalidate_range(mem->mmu.asbestos,first,end);
    for(page_t p=first;p<end;p++){
        struct pt_entry *target=mem_pt(mem,p);
        target->data=replacement;target->offset=(size_t)(p-first)*PAGE_SIZE;
        target->flags=flags&~P_COW;
    }
    for(page_t p=first;p<end;p++)data_release(old);
    mem_changed(mem);
    return 1;
}
const char *ideck_cow_native_group_marker(void){return "IDECK_ANON_COW_NATIVE_GROUP_V1";}
