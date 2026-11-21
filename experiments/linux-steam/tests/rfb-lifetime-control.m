/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#import "LabRFBCompletion.h"
#import "LabRFBWake.h"
#include <assert.h>
#include <stdatomic.h>
#include <unistd.h>
static char mainQueueKey;
int main(int argc,char **argv){@autoreleasepool{
    if(argc!=3)return 2;
    dispatch_queue_set_specific(dispatch_get_main_queue(),&mainQueueKey,&mainQueueKey,NULL);
    NSString *mode=@(argv[2]);
    LRRFBClient *client=[[LRRFBClient alloc]initWithPort:atoi(argv[1]) password:@"Test2345"];
    __weak LRRFBClient *weakClient=client;
    __block atomic_bool entered=false,returned=false,notified=false;
    dispatch_semaphore_t release=dispatch_semaphore_create(0);
    BOOL input=[mode isEqual:@"input-held"],frame=[mode isEqual:@"frame-held"];
    BOOL wake=[mode isEqual:@"wake-wire"],partial=[mode isEqual:@"refresh-partial-reply"];
    BOOL silent=[mode isEqual:@"refresh-silent"],empty=[mode isEqual:@"refresh-empty-reply"];
    BOOL refresh=partial||silent||empty||[mode isEqual:@"full-refresh"];
    __block atomic_bool refreshWritten=false;
    __block atomic_uint seenFrames=0;
    if(refresh)assert(![client ideckRequestFullRefreshWithCompletion:^(BOOL written){(void)written;abort();}]);
    __block atomic_uint wakeWrites=0;
    void (^hold)(void)=^{
        if(atomic_exchange(&entered,true))return;
        dispatch_semaphore_wait(release,DISPATCH_TIME_FOREVER);
        atomic_store(&returned,true);
    };
    client.frameHandler=^(NSData *pixels,uint16_t w,uint16_t h,uint64_t n,uint64_t bytes){
        (void)n;(void)bytes;assert(w==32&&h==16&&pixels.length==2048);
        if(frame)hold();
        if(input)[weakClient key:0xff50 down:NO];
        if(wake&&!atomic_exchange(&entered,true))ideck_rfb_wake(weakClient,15,7);
        if(refresh)atomic_fetch_add(&seenFrames,1);
        if(refresh&&n==1){
            IDECKRFBDecodeProgress initial=[weakClient ideckDecodeProgress];
            assert(initial.started==1&&initial.decoded==1);
            assert([weakClient ideckRequestFullRefreshWithCompletion:^(BOOL written){
                assert(written);atomic_store(&refreshWritten,true);
                if(partial||silent||empty)dispatch_after(dispatch_time(DISPATCH_TIME_NOW,500*NSEC_PER_MSEC),dispatch_get_main_queue(),^{
                    assert(atomic_load(&seenFrames)==1);
                    IDECKRFBDecodeProgress progress=[weakClient ideckDecodeProgress];
                    assert(progress.started==(silent?1:2)&&progress.decoded==(empty?2:1));
                    [weakClient ideckStopWithCompletion:^{
                        assert(atomic_load(&seenFrames)==1);
                        printf("RFB_REFRESH started=%llu decoded=%llu published=1 reader_drained=1\n",
                            (unsigned long long)progress.started,(unsigned long long)progress.decoded);
                        exit(0);
                    }];
                });
            }]);
            assert(![weakClient ideckRequestFullRefreshWithCompletion:^(BOOL written){(void)written;abort();}]);
        }else if(refresh&&n==2){
            assert(!partial&&!silent&&!empty);
            IDECKRFBDecodeProgress progress=[weakClient ideckDecodeProgress];
            assert(progress.started==2&&progress.decoded==2);
            const uint8_t *data=pixels.bytes;
            for(NSUInteger i=0;i<pixels.length;i++)assert(data[i]==0x5a);
            [weakClient ideckStopWithCompletion:^{
                assert(atomic_load(&refreshWritten));
                assert(![weakClient ideckRequestFullRefreshWithCompletion:^(BOOL written){(void)written;abort();}]);
                puts("RFB_REFRESH second_frame=1 same_connection=1 duplicate_refused=1");
                exit(0);
            }];
        }
    };
    if(input)client.transportMetricsHandler=^(NSDictionary *event){if([event[@"input_sequence"] unsignedLongLongValue])hold();};
    if(wake)client.transportMetricsHandler=^(NSDictionary *event){
        if(![event[@"stage"] isEqual:@"rfb_input_write"])return;
        assert([event[@"packet_type"] unsignedIntValue]==5);
        assert([event[@"packet_bytes"] unsignedIntValue]==6);
        assert([event[@"written"] boolValue]);
        if(atomic_fetch_add(&wakeWrites,1)==2){
            [weakClient ideckStopWithCompletion:^{
                assert(atomic_load(&wakeWrites)==3);
                puts("RFB_WAKE move_press_release_written=3");
                exit(0);
            }];
        }
    };
    if([mode isEqual:@"before-start"]){
        [client ideckStopWithCompletion:^{
            assert(dispatch_get_specific(&mainQueueKey)==&mainQueueKey);atomic_store(&notified,true);
            [client start];[client key:0xff50 down:NO];
            puts("RFB_LIFETIME stopped_before_start=1 completion_main=1");exit(0);
        }];
    }else if(wake||refresh){
        [client start];
    }else{
        [client start];
        dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INITIATED,0),^{
            if(frame||input){
                for(unsigned i=0;i<5000&&!atomic_load(&entered);i++)usleep(1000);
                assert(atomic_load(&entered));
            }else usleep(100000); /* peer intentionally withholds handshake */
            [client ideckStopWithCompletion:^{
                assert(dispatch_get_specific(&mainQueueKey)==&mainQueueKey);
                assert(!(frame||input)||atomic_load(&returned));
                assert(!atomic_exchange(&notified,true));
                client.frameHandler=nil;client.transportMetricsHandler=nil;
                puts("RFB_LIFETIME actual_tasks_returned=1 completion_main=1 no_early_completion=1");exit(0);
            }];
            if(frame||input){
                usleep(100000);assert(!atomic_load(&notified));
                dispatch_semaphore_signal(release);
            }
        });
    }
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW,8*NSEC_PER_SEC),dispatch_get_main_queue(),^{puts("RFB_LIFETIME observer_timeout_no_success");exit(9);});
    dispatch_main();
}}
