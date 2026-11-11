/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#import "LabRFBCompletion.h"
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
    void (^hold)(void)=^{
        if(atomic_exchange(&entered,true))return;
        dispatch_semaphore_wait(release,DISPATCH_TIME_FOREVER);
        atomic_store(&returned,true);
    };
    client.frameHandler=^(NSData *pixels,uint16_t w,uint16_t h,uint64_t n,uint64_t bytes){
        (void)n;(void)bytes;assert(w==32&&h==16&&pixels.length==2048);
        if(frame)hold();
        if(input)[weakClient key:0xff50 down:NO];
    };
    if(input)client.transportMetricsHandler=^(NSDictionary *event){if([event[@"input_sequence"] unsignedLongLongValue])hold();};
    if([mode isEqual:@"before-start"]){
        [client ideckStopWithCompletion:^{
            assert(dispatch_get_specific(&mainQueueKey)==&mainQueueKey);atomic_store(&notified,true);
            [client start];[client key:0xff50 down:NO];
            puts("RFB_LIFETIME stopped_before_start=1 completion_main=1");exit(0);
        }];
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
