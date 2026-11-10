/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * HOST ONLY fixed noncredential insertion/deletion control. Requires manual
 * visual confirmation of this 1280x800 genuine Steam login field beforehand.
 * No account/password input, submit, Return, Tab or authentication operation.
 */
#import <Foundation/Foundation.h>
#import "RFBClient.h"
#include <stdatomic.h>
#include <string.h>
int main(int argc,char **argv) {
    @autoreleasepool {
        if(argc!=3||(strcmp(argv[2],"insert")&&strcmp(argv[2],"erase")))return 2;
        BOOL erase=!strcmp(argv[2],"erase");
        NSString *password=[NSString stringWithContentsOfFile:@(argv[1]) encoding:NSUTF8StringEncoding error:nil];
        password=[password stringByTrimmingCharactersInSet:NSCharacterSet.newlineCharacterSet];
        if([password lengthOfBytesUsingEncoding:NSUTF8StringEncoding]!=8)return 2;
        LRRFBClient *client=[[LRRFBClient alloc] initWithPort:5993 password:password];
        dispatch_semaphore_t done=dispatch_semaphore_create(0);
        __block atomic_bool sent=false;__block atomic_uint writes=0;
        __weak LRRFBClient *weakClient=client;
        client.transportMetricsHandler=^(NSDictionary *event){
            if([event[@"stage"] isEqual:@"rfb_input_write"]&&[event[@"written"] boolValue])atomic_fetch_add(&writes,1);
        };
        client.frameHandler=^(NSData *pixels,uint16_t width,uint16_t height,uint64_t frames,uint64_t bytes){
            (void)pixels;(void)frames;(void)bytes;
            if(width!=1280||height!=800||atomic_exchange(&sent,true))return;
            [weakClient pointerX:500 y:320 buttons:1];
            [weakClient pointerX:500 y:320 buttons:0];
            dispatch_after(dispatch_time(DISPATCH_TIME_NOW,NSEC_PER_SEC),dispatch_get_global_queue(QOS_CLASS_UTILITY,0),^{
                const char fixture[]="ideck-test";
                for(size_t i=0;i<sizeof fixture-1;i++){
                    uint32_t key=erase?0xff08:(unsigned char)fixture[i];
                    [weakClient key:key down:YES];[weakClient key:key down:NO];
                }
            });
            dispatch_after(dispatch_time(DISPATCH_TIME_NOW,8*NSEC_PER_SEC),dispatch_get_global_queue(QOS_CLASS_UTILITY,0),^{dispatch_semaphore_signal(done);});
        };
        [client start];
        long timeout=dispatch_semaphore_wait(done,dispatch_time(DISPATCH_TIME_NOW,30*NSEC_PER_SEC));
        [client stop];
        printf("HOST_FIXED_FIXTURE mode=%s written_packets=%u consumed=UNVERIFIED submit=NO\n",argv[2],atomic_load(&writes));
        return timeout||!atomic_load(&sent);
    }
}
