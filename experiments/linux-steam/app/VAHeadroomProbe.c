/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#include "VAHeadroomProbe.h"
#include "NativeKernelLog.h"
#include <sys/mman.h>
#include <sys/stat.h>
#include <pthread.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#if IDECK_VA_HEADROOM_HOST_INJECTION
#if defined(__ENVIRONMENT_IPHONE_OS_VERSION_MIN_REQUIRED__)
#error Host injection is forbidden in iOS
#endif
extern void *ideck_va_test_mmap(void *,size_t,int,int,int,off_t);
extern int ideck_va_test_munmap(void *,size_t);
#define own_map ideck_va_test_mmap
#define own_unmap ideck_va_test_munmap
#else
#define own_map mmap
#define own_unmap munmap
#endif
static pthread_mutex_t state_lock=PTHREAD_MUTEX_INITIALIZER;
static unsigned state; /* 0 fresh, 1 prepared, 2 consumed, 3 failed/quarantined */
static void *reservation;
int ideck_va_headroom_prepare(void){
    int saved=errno,result=0;
    pthread_mutex_lock(&state_lock);
    if(state){pthread_mutex_unlock(&state_lock);errno=saved;return -EBUSY;}
    reservation=own_map(NULL,IDECK_VA_HEADROOM_BYTES,PROT_NONE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
    if(reservation==MAP_FAILED){result=-(errno?errno:ENOMEM);reservation=NULL;state=3;}
    else state=1;
    pthread_mutex_unlock(&state_lock);
    char line[224];snprintf(line,sizeof line,"IDECK_VA_HEADROOM_PROBE_V1 phase=prepare bytes=%u prepared=%u error=%d payload_read=0 payload_write=0 fixed_address=0",IDECK_VA_HEADROOM_BYTES,result==0,-result);
    ideck_native_log_line(line);errno=saved;return result;
}
void ideck_va_headroom_probe(int fd,size_t bytes,off_t offset,int prot,int flags,int original_error){
    if(original_error!=ENOMEM || fd<0 || !bytes || bytes>IDECK_VA_HEADROOM_BYTES || offset || flags!=MAP_SHARED || prot!=(PROT_READ|PROT_WRITE))return;
    int saved=errno;struct stat metadata;
    if(fstat(fd,&metadata) || !S_ISREG(metadata.st_mode) || metadata.st_size<0 || (uint64_t)metadata.st_size<bytes){errno=saved;return;}
    pthread_mutex_lock(&state_lock);
    if(state!=1){pthread_mutex_unlock(&state_lock);errno=saved;return;}
    /* No other thread can release or reuse this single owned reservation. No
     * address from a guest, file payload or arbitrary native range is used. */
    state=2;void *owned=reservation;reservation=NULL;
    pthread_mutex_unlock(&state_lock);
    errno=0;int released=own_unmap(owned,IDECK_VA_HEADROOM_BYTES)==0;
    int release_error=released?0:errno,mapped=0,map_error=0,cleaned=1,cleanup_error=0;
    if(!released){
        pthread_mutex_lock(&state_lock);reservation=owned;state=3;pthread_mutex_unlock(&state_lock);
    }else{
        /* OS chooses a NEW address. Never MAP_FIXED, address reuse, pointer
         * mutation or a repair/fallback of the original Steam mapping. */
        errno=0;void *trial=own_map(NULL,bytes,prot,flags,fd,offset);
        mapped=trial!=MAP_FAILED;map_error=mapped?0:errno;
        if(mapped){errno=0;cleaned=own_unmap(trial,bytes)==0;cleanup_error=cleaned?0:errno;}
    }
    char line[352];snprintf(line,sizeof line,"IDECK_VA_HEADROOM_PROBE_V1 phase=trial bytes=%zu reserved_bytes=%u reservation_released=%d release_errno=%d fresh_mapping=%d map_errno=%d trial_released=%d cleanup_errno=%d original_error=%d original_result_preserved=1 payload_read=0 payload_write=0 fixed_address=0",bytes,IDECK_VA_HEADROOM_BYTES,released,release_error,mapped,map_error,cleaned,cleanup_error,original_error);
    ideck_native_log_line(line);errno=saved;
}
