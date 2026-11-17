/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#import "CheckedFrameSnapshot.h"
#include "RFBProtocol.h"
#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include <pthread.h>
#include <stdio.h>
static pthread_mutex_t gate=PTHREAD_MUTEX_INITIALIZER;
static unsigned allocs,frees;
static int inject;
void *ideck_frame_test_alloc(size_t bytes){pthread_mutex_lock(&gate);allocs++;int fail=inject;pthread_mutex_unlock(&gate);return fail?NULL:malloc(bytes);}
void ideck_frame_test_free(void *p){pthread_mutex_lock(&gate);frees++;pthread_mutex_unlock(&gate);free(p);}
static struct ideck_frame_snapshot_stats snap(void){struct ideck_frame_snapshot_stats s;ideck_frame_snapshot_stats_read(&s);return s;}
static void *worker(void *unused){(void)unused;for(unsigned i=0;i<64;i++){@autoreleasepool{
    NSMutableData *pixels=[NSMutableData dataWithLength:64*64*4];memset(pixels.mutableBytes,31, pixels.length);
    NSData *copy=ideck_checked_frame_snapshot(pixels,64,64);assert(copy&&copy.length==pixels.length);
    memset(pixels.mutableBytes,99,pixels.length);for(size_t j=0;j<copy.length;j++)assert(((const unsigned char *)copy.bytes)[j]==31);
}}return NULL;}
int main(void){
    @autoreleasepool {
        NSMutableData *pixels=[NSMutableData dataWithLength:64*64*4];memset(pixels.mutableBytes,7,pixels.length);
        assert(!ideck_checked_frame_snapshot(nil,64,64));
        assert(!ideck_checked_frame_snapshot(pixels,0,64));
        assert(!ideck_checked_frame_snapshot(pixels,LR_RFB_MAX_WIDTH+1,64));
        assert(!ideck_checked_frame_snapshot(pixels,32,64));assert(!allocs);
        inject=1;assert(!ideck_checked_frame_snapshot(pixels,64,64));assert(!snap().live_frames);inject=0;
        NSData *first=ideck_checked_frame_snapshot(pixels,64,64);assert(first&&first.bytes!=pixels.bytes);
        memset(pixels.mutableBytes,9,pixels.length);NSData *second=ideck_checked_frame_snapshot(pixels,64,64);assert(second&&second.bytes!=first.bytes);
        for(size_t i=0;i<first.length;i++)assert(((const unsigned char *)first.bytes)[i]==7&&((const unsigned char *)second.bytes)[i]==9);
        NSData *copy=first.copy;assert(copy==first);assert(snap().live_frames==2);
        first=nil;assert(snap().live_frames==2);copy=nil;second=nil;
    }
    assert(!snap().live_frames&&!snap().live_bytes&&snap().releases==2);
    @autoreleasepool {
        size_t bytes=0;assert(lr_rfb_dimensions(LR_RFB_MAX_WIDTH,LR_RFB_MAX_HEIGHT,&bytes));
        NSMutableData *pixels=[NSMutableData dataWithLength:bytes];memset(pixels.mutableBytes,43,bytes);
        NSData *copy=ideck_checked_frame_snapshot(pixels,LR_RFB_MAX_WIDTH,LR_RFB_MAX_HEIGHT);assert(copy&&copy.length==bytes);
        memset(pixels.mutableBytes,13,bytes);for(size_t i=0;i<bytes;i++)assert(((const unsigned char *)copy.bytes)[i]==43);
    }
    pthread_t threads[8];for(unsigned i=0;i<8;i++)assert(!pthread_create(&threads[i],NULL,worker,NULL));
    for(unsigned i=0;i<8;i++)assert(!pthread_join(threads[i],NULL));
    struct ideck_frame_snapshot_stats s=snap();assert(!s.live_frames&&!s.live_bytes&&s.failures==5&&s.releases==515&&allocs==516&&frees==515);
    printf("HOST real Foundation immutable snapshots, max dimensions, failure, retain/coalesce and512concurrent snapshots PASS releases=%llu peak_bytes=%llu NOTdeviceproof=1\n",(unsigned long long)s.releases,(unsigned long long)s.peak_live_bytes);return 0;
}
