/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#import "FrameSnapshotPool.h"
#include "RFBProtocol.h"
#include <pthread.h>
#include <stdlib.h>
#include <string.h>
#if defined(IDECK_FRAME_POOL_HOST_INJECTION) && defined(__ENVIRONMENT_IPHONE_OS_VERSION_MIN_REQUIRED__)
#error Frame pool allocation injection is forbidden in iOS builds
#endif
#if IDECK_FRAME_POOL_HOST_INJECTION
extern void *ideck_frame_pool_test_alloc(size_t);
extern void ideck_frame_pool_test_free(void *);
#define pool_alloc ideck_frame_pool_test_alloc
#define pool_free ideck_frame_pool_test_free
#else
#define pool_alloc malloc
#define pool_free free
#endif
static pthread_mutex_t statsLock=PTHREAD_MUTEX_INITIALIZER;
static struct ideck_frame_pool_stats stats;
void ideck_frame_pool_stats_read(struct ideck_frame_pool_stats *out){
    if(!out)return;pthread_mutex_lock(&statsLock);*out=stats;pthread_mutex_unlock(&statsLock);
}
@implementation IDECKFrameSnapshotPool {
    void *_buffers[IDECK_FRAME_POOL_SLOTS];
    BOOL _busy[IDECK_FRAME_POOL_SLOTS];
    size_t _capacity;
    pthread_mutex_t _lock;
    BOOL _lockReady;
}
- (instancetype)initWithWidth:(uint16_t)width height:(uint16_t)height {
    if(!(self=[super init]))return nil;
    pthread_mutex_lock(&statsLock);stats.preparations++;pthread_mutex_unlock(&statsLock);
    if(!lr_rfb_dimensions(width,height,&_capacity))return nil;
    if(pthread_mutex_init(&_lock,NULL))return nil;
    _lockReady=YES;
    for(unsigned i=0;i<IDECK_FRAME_POOL_SLOTS;i++){
        _buffers[i]=pool_alloc(_capacity);
        pthread_mutex_lock(&statsLock);
        if(_buffers[i]){stats.native_buffers++;stats.native_bytes+=_capacity;}
        else stats.allocation_failures++;
        pthread_mutex_unlock(&statsLock);
        if(!_buffers[i])return nil; // ARC tears down previously allocated slots.
    }
    return self;
}
- (void)dealloc {
    /* A frame deallocator retains this pool. All slots are free when the last
     * pool owner disappears, even when the controller went away much earlier. */
    for(unsigned i=0;i<IDECK_FRAME_POOL_SLOTS;i++)if(_buffers[i]){
        pool_free(_buffers[i]);
        pthread_mutex_lock(&statsLock);stats.native_buffers--;stats.native_bytes-=_capacity;pthread_mutex_unlock(&statsLock);
    }
    if(_lockReady)pthread_mutex_destroy(&_lock);
}
- (NSData *)snapshotPixels:(NSData *)pixels width:(uint16_t)width height:(uint16_t)height {
    pthread_mutex_lock(&statsLock);stats.calls++;pthread_mutex_unlock(&statsLock);
    size_t bytes=0;
    if(!pixels||!lr_rfb_dimensions(width,height,&bytes)||pixels.length!=bytes||bytes>_capacity){
        pthread_mutex_lock(&statsLock);stats.invalid++;pthread_mutex_unlock(&statsLock);return nil;
    }
    unsigned slot=IDECK_FRAME_POOL_SLOTS;
    pthread_mutex_lock(&_lock);
    for(unsigned i=0;i<IDECK_FRAME_POOL_SLOTS;i++)if(!_busy[i]){_busy[i]=YES;slot=i;break;}
    pthread_mutex_unlock(&_lock);
    if(slot==IDECK_FRAME_POOL_SLOTS){
        pthread_mutex_lock(&statsLock);stats.exhausted++;pthread_mutex_unlock(&statsLock);return nil;
    }
    pthread_mutex_lock(&statsLock);stats.live_slots++;if(stats.live_slots>stats.peak_slots)stats.peak_slots=stats.live_slots;pthread_mutex_unlock(&statsLock);
    void *owned=_buffers[slot];memcpy(owned,pixels.bytes,bytes);
    return [[NSData alloc] initWithBytesNoCopy:owned length:bytes deallocator:^(void *buffer,NSUInteger length){
        (void)buffer;(void)length;
        pthread_mutex_lock(&self->_lock);
        pthread_mutex_lock(&statsLock);stats.live_slots--;stats.releases++;pthread_mutex_unlock(&statsLock);
        self->_busy[slot]=NO;pthread_mutex_unlock(&self->_lock);
    }];
}
@end
