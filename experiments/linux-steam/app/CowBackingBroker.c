/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * Bounded private CoW backing experiment. Never linked in default builds.
 * Data-object/page refcounts remain in the pinned kernel; this component owns
 * only exact native slots and releases a chunk after its LAST slot is freed.
 */
#include "CowBackingBroker.h"
#include <sys/mman.h>
#include <unistd.h>
#include <pthread.h>
#include <errno.h>
#include <string.h>
#include <stdint.h>
#include <stdlib.h>
#if defined(IDECK_COW_BROKER_HOST_INJECTION) && defined(__ENVIRONMENT_IPHONE_OS_VERSION_MIN_REQUIRED__)
#error Host broker injection must never target iOS
#endif
#ifndef IDECK_COW_BROKER_MAX_CHUNKS
#define IDECK_COW_BROKER_MAX_CHUNKS 4096u
#endif
#if IDECK_COW_BROKER_MAX_CHUNKS != 4096 && (!defined(IDECK_COW_BROKER_HOST_INJECTION) || defined(__ENVIRONMENT_IPHONE_OS_VERSION_MIN_REQUIRED__))
#error Alternate registry capacity is a host test only
#endif
#if IDECK_COW_BROKER_MAX_CHUNKS < 1 || IDECK_COW_BROKER_MAX_CHUNKS > 4096
#error Invalid broker registry capacity
#endif
#define IDECK_BROKER_CHUNKS IDECK_COW_BROKER_MAX_CHUNKS
#define IDECK_BROKER_SLOTS 128u
struct chunk {void *base;uint32_t bytes[IDECK_BROKER_SLOTS];unsigned used;};
static struct chunk chunks[IDECK_BROKER_CHUNKS];
/* Sorted active indices permit bounded ownership lookup without allocating
 * registry nodes from the allocator being diagnosed. No pointer tagging. */
static unsigned order[IDECK_BROKER_CHUNKS],active,hint=IDECK_BROKER_CHUNKS;
static size_t native_page,chunk_bytes;
static pthread_mutex_t mutex=PTHREAD_MUTEX_INITIALIZER;
static struct ideck_cow_broker_stats stats;
static int initialize(void){
    if(native_page)return 0;
    long page=sysconf(_SC_PAGESIZE);
    if(page<4096||page>65536||((unsigned long)page&((unsigned long)page-1)))return EINVAL;
    native_page=(size_t)page;chunk_bytes=native_page*IDECK_BROKER_SLOTS;return 0;
}
void *ideck_cow_broker_allocate(size_t bytes){
    pthread_mutex_lock(&mutex);
    int error=initialize();
    if(error||!bytes||bytes>native_page||bytes%4096){
        pthread_mutex_unlock(&mutex);errno=error?error:EINVAL;return MAP_FAILED;
    }
    stats.allocation_calls++;
    unsigned index=hint;
    if(index==IDECK_BROKER_CHUNKS||!chunks[index].base||chunks[index].used==IDECK_BROKER_SLOTS){
        index=IDECK_BROKER_CHUNKS;
        for(unsigned i=0;i<active;i++)if(chunks[order[i]].used<IDECK_BROKER_SLOTS){index=order[i];break;}
    }
    if(index==IDECK_BROKER_CHUNKS){
        for(unsigned i=0;i<IDECK_BROKER_CHUNKS;i++)if(!chunks[i].base){index=i;break;}
        if(index==IDECK_BROKER_CHUNKS){stats.capacity_refusals++;pthread_mutex_unlock(&mutex);errno=ENOMEM;return MAP_FAILED;}
        stats.map_attempts++;
        void *base=mmap(NULL,chunk_bytes,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
        if(base==MAP_FAILED){error=errno;stats.map_failures++;pthread_mutex_unlock(&mutex);errno=error;return MAP_FAILED;}
        /* Check the native mapping contract before admitting any allocation. */
        if(!base||(uintptr_t)base%native_page){
            int saved=EINVAL;if(munmap(base,chunk_bytes))abort();stats.map_failures++;
            pthread_mutex_unlock(&mutex);errno=saved;return MAP_FAILED;
        }
        unsigned at=0;while(at<active&&(uintptr_t)chunks[order[at]].base<(uintptr_t)base)at++;
        uintptr_t begin=(uintptr_t)base;
        if(begin>UINTPTR_MAX-chunk_bytes ||
           (at&&(uintptr_t)chunks[order[at-1]].base+chunk_bytes>begin) ||
           (at<active&&begin+chunk_bytes>(uintptr_t)chunks[order[at]].base)){
            /* A broken backend may have returned an alias of a live grant.
             * Never unmap that address or overwrite its ownership record. */
            stats.overlap_rejections++;pthread_mutex_unlock(&mutex);errno=EFAULT;return MAP_FAILED;
        }
        chunks[index].base=base;
        memmove(order+at+1,order+at,(active-at)*sizeof *order);order[at]=index;active++;
        stats.live_chunks++;stats.reserved_native_bytes+=chunk_bytes;
    }
    struct chunk *c=&chunks[index];unsigned slot=0;while(slot<IDECK_BROKER_SLOTS&&c->bytes[slot])slot++;
    /* Only a chunk with a free slot may reach this branch. */
    if(slot==IDECK_BROKER_SLOTS){pthread_mutex_unlock(&mutex);errno=EFAULT;return MAP_FAILED;}
    void *result=(char *)c->base+slot*native_page;
    c->bytes[slot]=(uint32_t)bytes;c->used++;hint=index;
    stats.live_slots++;stats.live_guest_bytes+=bytes;
    /* Preserve anonymous zero-fill semantics on reuse; never touch spare slots
     * or materialize guest pages outside the requested private CoW object. */
    memset(result,0,bytes);pthread_mutex_unlock(&mutex);return result;
}
int ideck_cow_broker_release_owned(void *address,size_t bytes){
    pthread_mutex_lock(&mutex);uintptr_t pointer=(uintptr_t)address;
    unsigned low=0,high=active;
    while(low<high){unsigned mid=low+(high-low)/2;
        if((uintptr_t)chunks[order[mid]].base<=pointer)low=mid+1;else high=mid;
    }
    if(!low){pthread_mutex_unlock(&mutex);return 0;}
    unsigned at=low-1,index=order[at];struct chunk *c=&chunks[index];
    uintptr_t delta=pointer-(uintptr_t)c->base;
    if(delta>=chunk_bytes){pthread_mutex_unlock(&mutex);return 0;}
    if(delta%native_page||!bytes||bytes>native_page||c->bytes[delta/native_page]!=bytes){
        stats.ownership_errors++;pthread_mutex_unlock(&mutex);return -EINVAL;
    }
    unsigned slot=(unsigned)(delta/native_page);
    if(c->used==1){
        if(munmap(c->base,chunk_bytes)){
            int saved=errno;stats.native_unmap_failures++;pthread_mutex_unlock(&mutex);return -saved;
        }
        stats.unmap_calls++;stats.live_chunks--;stats.reserved_native_bytes-=chunk_bytes;
        c->base=NULL;c->bytes[slot]=0;c->used=0;
        memmove(order+at,order+at+1,(active-at-1)*sizeof *order);active--;
        if(hint==index)hint=IDECK_BROKER_CHUNKS;
    }else{
        /* The last guest/data reference is gone. Advise ONLY this independently
         * aligned owned native page; neighboring live slots keep their data and
         * protection. This is advisory, not proof of reclaimed physical RAM.
         * A failed advice must not prevent normal allocator free/reuse. */
        stats.advice_calls++;
        if(madvise(address,native_page,MADV_FREE))stats.advice_failures++;
        c->bytes[slot]=0;c->used--;hint=index;
    }
    stats.release_calls++;stats.live_slots--;stats.live_guest_bytes-=bytes;
    pthread_mutex_unlock(&mutex);return 1;
}
void ideck_cow_broker_read_stats(struct ideck_cow_broker_stats *out){
    if(!out)return;pthread_mutex_lock(&mutex);*out=stats;pthread_mutex_unlock(&mutex);
}
const char *ideck_cow_broker_marker(void){return "IDECK_OWNED_COW_BACKING_BROKER_V1";}
