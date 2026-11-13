/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * HOST development observer: one ordinary pointer click in the existing app
 * display, before/after private frames. No text, credentials or guest commands.
 * Packet submission alone does not establish that Steam consumed input.
 */
#import <Foundation/Foundation.h>
#import <ImageIO/ImageIO.h>
#import <CoreGraphics/CoreGraphics.h>
#import "RFBClient.h"
#include <stdatomic.h>

static BOOL saveFrame(NSData *pixels, uint16_t w, uint16_t h, NSURL *url) {
    if (!pixels || pixels.length != (size_t)w*h*4) return NO;
    CGColorSpaceRef color=CGColorSpaceCreateDeviceRGB();
    CGDataProviderRef provider=CGDataProviderCreateWithCFData((__bridge CFDataRef)pixels);
    CGImageRef frame=CGImageCreate(w,h,8,32,w*4,color,
        kCGBitmapByteOrder32Little|kCGImageAlphaNoneSkipFirst,provider,NULL,false,kCGRenderingIntentDefault);
    CGImageDestinationRef output=frame?CGImageDestinationCreateWithURL((__bridge CFURLRef)url,CFSTR("public.png"),1,NULL):NULL;
    BOOL saved=NO;
    if(output){CGImageDestinationAddImage(output,frame,NULL);saved=CGImageDestinationFinalize(output);CFRelease(output);}
    if(frame)CGImageRelease(frame);
    CGDataProviderRelease(provider);CGColorSpaceRelease(color);return saved;
}
static long number(const char *text,long low,long high) {
    char *end=NULL;long n=strtol(text,&end,10);
    return text[0]&&end&&!*end&&n>=low&&n<=high?n:-1;
}
int main(int argc,char **argv) {
    @autoreleasepool {
        if(argc!=6)return 2;
        long port=number(argv[1],1024,65535),x=number(argv[4],0,65534),y=number(argv[5],0,65534);
        if(port<0||x<0||y<0)return 2;
        NSString *key=[NSString stringWithContentsOfFile:@(argv[2]) encoding:NSASCIIStringEncoding error:nil];
        if([key lengthOfBytesUsingEncoding:NSASCIIStringEncoding]!=8)return 2;
        NSURL *out=[NSURL fileURLWithPath:@(argv[3]) isDirectory:YES];
        if([NSFileManager.defaultManager fileExistsAtPath:out.path]||
           ![NSFileManager.defaultManager createDirectoryAtURL:out withIntermediateDirectories:NO attributes:@{NSFilePosixPermissions:@0700} error:nil])return 2;
        dispatch_semaphore_t done=dispatch_semaphore_create(0);NSLock *lock=[NSLock new];
        __block atomic_bool started=false;__block NSData *latest=nil;
        __block uint16_t width=0,height=0;__block BOOL saved=NO;
        LRRFBClient *client=[[LRRFBClient alloc]initWithPort:(uint16_t)port password:key];
        __weak LRRFBClient *weakClient=client;
        client.frameHandler=^(NSData *pixels,uint16_t w,uint16_t h,uint64_t frames,uint64_t bytes){
            (void)frames;(void)bytes;
            [lock lock];latest=pixels;width=w;height=h;[lock unlock];
            if(atomic_exchange(&started,true))return;
            if(x>=w||y>=h||!saveFrame(pixels,w,h,[out URLByAppendingPathComponent:@"before-private.png"])){
                dispatch_semaphore_signal(done);return;
            }
            [weakClient pointerX:(uint16_t)x y:(uint16_t)y buttons:0];
            [weakClient pointerX:(uint16_t)x y:(uint16_t)y buttons:1];
            [weakClient pointerX:(uint16_t)x y:(uint16_t)y buttons:0];
            dispatch_after(dispatch_time(DISPATCH_TIME_NOW,8*NSEC_PER_SEC),dispatch_get_global_queue(QOS_CLASS_UTILITY,0),^{
                [lock lock];NSData *last=latest;uint16_t lastW=width,lastH=height;[lock unlock];
                saved=saveFrame(last,lastW,lastH,[out URLByAppendingPathComponent:@"after-private.png"]);
                printf("RFB_SINGLE_CLICK frames_saved=%d semantic_response=UNVERIFIED no_text_or_guest_commands=1\n",saved);
                dispatch_semaphore_signal(done);
            });
        };
        [client start];
        long timedOut=dispatch_semaphore_wait(done,dispatch_time(DISPATCH_TIME_NOW,30*NSEC_PER_SEC));
        [client stop];client.frameHandler=nil;
        return timedOut||!saved;
    }
}
