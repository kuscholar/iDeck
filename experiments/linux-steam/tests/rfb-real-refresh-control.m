/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#import "LabRFBCompletion.h"
#import "FrameSnapshotPool.h"
#include <stdatomic.h>

@interface LRRFBClient (FixtureMethods)
- (BOOL)write:(const void *)buffer count:(size_t)count;
@property(nonatomic,strong) IDECKFrameSnapshotPool *ideckFramePool;
@end

@interface RefreshFixtureClient : LRRFBClient
@property(nonatomic,readonly) unsigned incrementalWrites;
@end

@implementation RefreshFixtureClient {
    _Atomic unsigned _incrementalWrites;
}
- (BOOL)write:(const void *)buffer count:(size_t)count {
    BOOL written=[super write:buffer count:count];
    const uint8_t *p=buffer;
    if(written&&count==10&&p[0]==3&&p[1]==1)atomic_fetch_add(&_incrementalWrites,1);
    return written;
}
- (unsigned)incrementalWrites {return atomic_load(&_incrementalWrites);}
@end

int main(int argc,char **argv){@autoreleasepool{
    if(argc!=2)return 2;
    NSString *fixturePassword=[NSString stringWithContentsOfFile:@(argv[1]) encoding:NSASCIIStringEncoding error:nil];
    if(fixturePassword.length!=8)return 2;
    RefreshFixtureClient *client=[[RefreshFixtureClient alloc]initWithPort:5993 password:fixturePassword];
    client.ideckFramePool=[[IDECKFrameSnapshotPool alloc]initWithWidth:1280 height:800];
    if(!client.ideckFramePool)return 2;
    __weak RefreshFixtureClient *viewer=client;
    __block NSData *first;
    __block atomic_uint frames=0;
    __block atomic_bool identical=false,writeComplete=false;
    client.frameHandler=^(NSData *frame,uint16_t w,uint16_t h,uint64_t sequence,uint64_t bytes){
        (void)sequence;(void)bytes;
        if(w!=1280||h!=800||frame.length!=4096000)exit(3);
        if(!first){
            first=frame;
            dispatch_after(dispatch_time(DISPATCH_TIME_NOW,800*NSEC_PER_MSEC),dispatch_get_main_queue(),^{
                RefreshFixtureClient *current=viewer;
                unsigned baselineFrames=atomic_load(&frames),incremental=current.incrementalWrites;
                IDECKRFBDecodeProgress baseline=[current ideckDecodeProgress];
                if(baselineFrames!=1||incremental==0||baseline.started!=1||baseline.decoded!=1){
                    printf("fixture_idle_precondition=0 frames=%u incremental=%u started=%llu decoded=%llu\n",baselineFrames,incremental,(unsigned long long)baseline.started,(unsigned long long)baseline.decoded);
                    [current ideckStopWithCompletion:^{exit(4);}];
                    return;
                }
                BOOL accepted=[current ideckRequestFullRefreshWithCompletion:^(BOOL written){atomic_store(&writeComplete,written);}];
                if(!accepted){[current ideckStopWithCompletion:^{exit(5);}];return;}
                dispatch_after(dispatch_time(DISPATCH_TIME_NOW,3*NSEC_PER_SEC),dispatch_get_main_queue(),^{
                    IDECKRFBDecodeProgress after=[viewer ideckDecodeProgress];
                    struct ideck_frame_pool_stats pool;
                    ideck_frame_pool_stats_read(&pool);
                    [viewer ideckStopWithCompletion:^{
                        printf("{\"idle_frames\":%u,\"prior_incremental_writes\":%u,\"full_written\":%u,\"updates_started\":%llu,\"updates_decoded\":%llu,\"frames\":%u,\"identical_second\":%u,\"pool_exhausted\":%llu}\n",
                            baselineFrames,incremental,atomic_load(&writeComplete),(unsigned long long)after.started,
                            (unsigned long long)after.decoded,atomic_load(&frames),atomic_load(&identical),(unsigned long long)pool.exhausted);
                        exit(0);
                    }];
                });
            });
        }else if(atomic_load(&frames)==1)atomic_store(&identical,[first isEqualToData:frame]);
        atomic_fetch_add(&frames,1);
    };
    [client start];
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW,12*NSEC_PER_SEC),dispatch_get_main_queue(),^{
        [viewer ideckStopWithCompletion:^{exit(6);}];
    });
    dispatch_main();
}}
