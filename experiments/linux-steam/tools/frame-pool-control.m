/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#import "FrameSnapshotPool.h"
#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include <pthread.h>
#include <stdio.h>
static pthread_mutex_t gate=PTHREAD_MUTEX_INITIALIZER;
static unsigned allocs,frees;
static int failAt=-1;
void *ideck_frame_pool_test_alloc(size_t bytes){
    pthread_mutex_lock(&gate);unsigned call=allocs++;BOOL fail=failAt>=0&&call==(unsigned)failAt;pthread_mutex_unlock(&gate);return fail?NULL:malloc(bytes);
}
void ideck_frame_pool_test_free(void *p){pthread_mutex_lock(&gate);frees++;pthread_mutex_unlock(&gate);free(p);}
static struct ideck_frame_pool_stats snap(void){struct ideck_frame_pool_stats s;ideck_frame_pool_stats_read(&s);return s;}
static NSData *filled(IDECKFrameSnapshotPool *pool,unsigned char value){
    NSMutableData *p=[NSMutableData dataWithLength:64*64*4];memset(p.mutableBytes,value,p.length);
    NSData *frame=[pool snapshotPixels:p width:64 height:64];
    if(frame){assert(frame.bytes!=p.bytes);memset(p.mutableBytes,255,p.length);for(size_t i=0;i<frame.length;i++)assert(((const unsigned char *)frame.bytes)[i]==value);}
    return frame;
}
static void *worker(void *context){
    IDECKFrameSnapshotPool *pool=(__bridge IDECKFrameSnapshotPool *)context;
    for(unsigned i=0;i<64;i++){@autoreleasepool{(void)filled(pool,(unsigned char)i);}}
    return NULL;
}
int main(void){
    // Every possible partial prepare failure frees preceding actual allocations.
    for(unsigned slot=0;slot<IDECK_FRAME_POOL_SLOTS;slot++){@autoreleasepool{
        failAt=(int)allocs+(int)slot;
        assert(![[IDECKFrameSnapshotPool alloc]initWithWidth:64 height:64]);
    }assert(!snap().native_buffers&&!snap().native_bytes);}
    failAt=-1;
    @autoreleasepool{assert(![[IDECKFrameSnapshotPool alloc]initWithWidth:0 height:64]);}
    @autoreleasepool{
        IDECKFrameSnapshotPool *pool=[[IDECKFrameSnapshotPool alloc]initWithWidth:1280 height:800];assert(pool);
        assert(snap().native_bytes==4*1280*800*4&&snap().native_buffers==4);
        NSMutableData *invalid=[NSMutableData dataWithLength:4];
        assert(![pool snapshotPixels:nil width:1 height:1]);
        assert(![pool snapshotPixels:invalid width:0 height:1]);
        assert(![pool snapshotPixels:invalid width:2 height:1]);
        NSMutableData *large=[NSMutableData dataWithLength:1280*801*4];
        assert(![pool snapshotPixels:large width:1280 height:801]);
        // An immutable NSData copy retains the same slot. The fifth consumer
        // fails instead of aliasing, reallocating or waiting on a UI thread.
        __strong NSData *held[4]={nil,nil,nil,nil};
        for(unsigned i=0;i<4;i++){@autoreleasepool{held[i]=filled(pool,(unsigned char)(7+i));assert(held[i]);}}
        NSData *extra=held[0].copy;assert(extra==held[0]);
        assert(!filled(pool,19));unsigned before=allocs;
        held[0]=nil;assert(snap().live_slots==4);extra=nil;assert(snap().live_slots==3);
        @autoreleasepool{held[0]=filled(pool,43);assert(held[0]);}assert(allocs==before);
        for(unsigned i=1;i<4;i++)for(size_t j=0;j<held[i].length;j++)assert(((const unsigned char *)held[i].bytes)[j]==7+i);
        // Releasing the controller's pool owner cannot free retained frames.
        pool=nil;assert(snap().native_buffers==4);
        for(unsigned i=0;i<4;i++)held[i]=nil;
    }
    assert(!snap().live_slots&&!snap().native_buffers&&!snap().native_bytes);
    @autoreleasepool{
        IDECKFrameSnapshotPool *pool=[[IDECKFrameSnapshotPool alloc]initWithWidth:64 height:64];assert(pool);
        unsigned before=allocs;struct ideck_frame_pool_stats previous=snap();
        pthread_t threads[8];for(unsigned i=0;i<8;i++)assert(!pthread_create(&threads[i],NULL,worker,(__bridge void *)pool));
        for(unsigned i=0;i<8;i++)assert(!pthread_join(threads[i],NULL));
        assert(allocs==before&&!snap().live_slots);
        assert(snap().calls-previous.calls==512);
        assert(snap().releases-previous.releases+snap().exhausted-previous.exhausted==512);
    }
    struct ideck_frame_pool_stats s=snap();assert(!s.live_slots&&!s.native_buffers&&!s.native_bytes&&s.peak_slots<=4);
    assert(allocs==frees+4); // exactly four injected allocation failures
    printf("HOST four-slot immutable pool partialprepare rollback, bounds, saturation, delayed consumer lifetime, reuse and512concurrent admissions PASS releases=%llu exhausted=%llu allocations=%u frees=%u NOTdeviceproof=1\n",(unsigned long long)s.releases,(unsigned long long)s.exhausted,allocs,frees);
    return 0;
}
