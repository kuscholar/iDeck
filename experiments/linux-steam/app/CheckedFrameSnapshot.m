/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#import "CheckedFrameSnapshot.h"
#include "RFBProtocol.h"
#include <pthread.h>
#include <stdlib.h>
#include <string.h>
#if defined(IDECK_FRAME_SNAPSHOT_HOST_INJECTION) && defined(__ENVIRONMENT_IPHONE_OS_VERSION_MIN_REQUIRED__)
#error Frame allocation injection is forbidden in iOS builds
#endif
#if IDECK_FRAME_SNAPSHOT_HOST_INJECTION
extern void *ideck_frame_test_alloc(size_t);
extern void ideck_frame_test_free(void *);
#define snapshot_alloc ideck_frame_test_alloc
#define snapshot_free ideck_frame_test_free
#else
#define snapshot_alloc malloc
#define snapshot_free free
#endif
static pthread_mutex_t mutex=PTHREAD_MUTEX_INITIALIZER;
static struct ideck_frame_snapshot_stats stats;
static NSData *failed(void){pthread_mutex_lock(&mutex);stats.failures++;pthread_mutex_unlock(&mutex);return nil;}
NSData *ideck_checked_frame_snapshot(NSData *pixels,uint16_t width,uint16_t height){
    pthread_mutex_lock(&mutex);stats.calls++;pthread_mutex_unlock(&mutex);
    size_t bytes=0;
    if(!pixels||!lr_rfb_dimensions(width,height,&bytes)||pixels.length!=bytes)return failed();
    void *owned=snapshot_alloc(bytes);if(!owned)return failed();
    memcpy(owned,pixels.bytes,bytes);
    /* NSData adopts the allocation: no Foundation large-copy VM allocation.
     * The last consumer owns release, including delayed main/Metal callbacks.
     * Do not reuse this memory while ANY immutable snapshot is retained. */
    pthread_mutex_lock(&mutex);stats.live_frames++;stats.live_bytes+=bytes;
    if(stats.live_bytes>stats.peak_live_bytes)stats.peak_live_bytes=stats.live_bytes;
    pthread_mutex_unlock(&mutex);
    NSData *result=[[NSData alloc] initWithBytesNoCopy:owned length:bytes deallocator:^(void *buffer,NSUInteger length){
        (void)length;snapshot_free(buffer);
        pthread_mutex_lock(&mutex);stats.live_frames--;stats.live_bytes-=bytes;stats.releases++;pthread_mutex_unlock(&mutex);
    }];
    return result;
}
void ideck_frame_snapshot_stats_read(struct ideck_frame_snapshot_stats *out){if(!out)return;pthread_mutex_lock(&mutex);*out=stats;pthread_mutex_unlock(&mutex);}
const char *ideck_frame_snapshot_marker(void){return "IDECK_CHECKED_FRAME_SNAPSHOT_V1";}
