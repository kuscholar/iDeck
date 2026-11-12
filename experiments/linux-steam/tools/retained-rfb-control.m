/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * HOST real Steam/backend plus in-process RFB task boundary. No Metal, iPad,
 * login automation, Wine/game or full resource-reclamation claim.
 */
#import <Foundation/Foundation.h>
#import <CoreGraphics/CoreGraphics.h>
#import <ImageIO/ImageIO.h>
#import "RFBClient.h"
#import "LabRFBCompletion.h"
#include "RetainedFrontend.h"
#include "LinuxLabRuntime.h"
#include "NativeKernelLog.h"
#include <assert.h>
#include <pthread.h>
#include <signal.h>
#include <unistd.h>
extern const char *sock_tmp_prefix;
extern void sigusr1_handler(int);
@interface HostRetainedRFB : NSObject
@property(nonatomic,strong) NSString *root,*output,*bundle;
@property(nonatomic,strong) NSData *binary,*discovery,*manifest,*pixels;
@property(nonatomic,strong) LRRFBClient *client;
@property(nonatomic,strong) dispatch_source_t timer;
@property(atomic) unsigned wave;
@property(atomic) BOOL admitting;
@property unsigned clientWave,drains;
@property uint16_t width,height;
@property double lastSaved;
@property int result;
- (int)drain:(int)status;
- (void)tick;
- (void)runOwner;
@end
static int drain(void *c,int status){return [(__bridge HostRetainedRFB *)c drain:status];}
static void *run(void *c){@autoreleasepool{[(__bridge HostRetainedRFB *)c runOwner];}return NULL;}
static pthread_t ownerThread;
@implementation HostRetainedRFB
- (void)saveFrame {
    if(!self.pixels)return;
    CGColorSpaceRef color=CGColorSpaceCreateDeviceRGB();
    CGDataProviderRef provider=CGDataProviderCreateWithCFData((__bridge CFDataRef)self.pixels);
    CGImageRef frame=CGImageCreate(self.width,self.height,8,32,self.width*4,color,kCGBitmapByteOrder32Little|kCGImageAlphaNoneSkipFirst,provider,NULL,false,kCGRenderingIntentDefault);
    NSURL *url=[NSURL fileURLWithPath:[self.output stringByAppendingPathComponent:[NSString stringWithFormat:@"latest-wave-%u.png",self.wave]]];
    NSURL *temporary=[NSURL fileURLWithPath:[url.path stringByAppendingString:@".tmp"]];
    CGImageDestinationRef dest=frame?CGImageDestinationCreateWithURL((__bridge CFURLRef)temporary,CFSTR("public.png"),1,NULL):NULL;
    if(dest){CGImageDestinationAddImage(dest,frame,NULL);assert(CGImageDestinationFinalize(dest));CFRelease(dest);assert(!rename(temporary.fileSystemRepresentation,url.fileSystemRepresentation));}
    if(frame)CGImageRelease(frame);CGDataProviderRelease(provider);CGColorSpaceRelease(color);
    self.lastSaved=NSProcessInfo.processInfo.systemUptime;
}
- (void)tick {
    /* CLI dispatch_main owns this queue but need not retain NSThread's initial
     * thread identity. The actual native state owner here is the queue. */
    dispatch_assert_queue(dispatch_get_main_queue());
    unsigned wave=self.wave;if(!wave||!self.admitting)return;
    if(!self.client){
        struct ideck_frontend_result state;assert(!ideck_retained_frontend_snapshot(&state));
        BOOL running=state.wave==wave&&(state.phase==IDECK_FRONTEND_RUNNING||
            (wave==1&&state.phase==IDECK_FRONTEND_PREPARING&&!strcmp(ideck_linux_lab_stage(),"guest-running")));
        NSString *ready=[self.root stringByAppendingPathComponent:@"data/tmp/ideck-display-ready"];
        if(!running||![NSFileManager.defaultManager fileExistsAtPath:ready])return;
        NSFileHandle *file=[NSFileHandle fileHandleForReadingAtPath:[self.root stringByAppendingPathComponent:@"data/tmp/ideck-vnc-password"]];
        NSData *data=[file readDataOfLength:9];[file closeFile];assert(data.length==8);
        NSString *password=[[NSString alloc]initWithData:data encoding:NSASCIIStringEncoding];assert(password);
        self.clientWave=wave;self.client=[[LRRFBClient alloc]initWithPort:5993 password:password];
        __weak typeof(self) weak=self;__weak LRRFBClient *weakClient=self.client;
        self.client.frameHandler=^(NSData *pixels,uint16_t width,uint16_t height,uint64_t frames,uint64_t bytes){
            (void)frames;(void)bytes;
            dispatch_async(dispatch_get_main_queue(),^{
                typeof(self) self=weak;
                if(!self||!self.admitting||self.wave!=wave||self.client!=weakClient)return;
                self.pixels=pixels;self.width=width;self.height=height;
                if(NSProcessInfo.processInfo.systemUptime-self.lastSaved>=3)[self saveFrame];
            });
        };
        [self.client start];printf("HOST_EMBEDDED_RFB started_wave=%u\n",wave);fflush(stdout);
    }
    NSString *request=[self.output stringByAppendingPathComponent:[NSString stringWithFormat:@"close-inspected-wave-%u",wave]];
    if(self.pixels&&self.clientWave==wave&&[NSFileManager.defaultManager fileExistsAtPath:request]){
        /* Native test operator creates only this fixed marker AFTER inspecting
         * the genuine private image. No keyboard/auth or guest-controlled IPC. */
        assert([NSFileManager.defaultManager removeItemAtPath:request error:nil]);
        assert(self.width==1280&&self.height==800);
        [self saveFrame];
        [self.client pointerX:973 y:196 buttons:1];[self.client pointerX:973 y:196 buttons:0];
        printf("HOST_EMBEDDED_RFB close_queued_wave=%u no_auth=1\n",wave);fflush(stdout);
    }
}
- (int)drain:(int)status {
    dispatch_assert_queue_not(dispatch_get_main_queue());assert(!status);
    struct ideck_frontend_result state;assert(!ideck_retained_frontend_snapshot(&state)&&state.phase==IDECK_FRONTEND_DRAINING);
    assert(!ideck_linux_lab_live_guest_threads()&&!ideck_linux_lab_native_worker_entries());
    struct sigaction action;assert(!sigaction(SIGUSR1,NULL,&action)&&action.sa_handler==sigusr1_handler);
    self.admitting=NO;dispatch_semaphore_t done=dispatch_semaphore_create(0);
    dispatch_async(dispatch_get_main_queue(),^{
        LRRFBClient *client=self.client;assert(client&&self.clientWave==state.wave);
        [client ideckStopWithCompletion:^{
            client.frameHandler=nil;client.statusHandler=nil;self.client=nil;self.pixels=nil;
            self.width=self.height=0;self.drains++;
            printf("HOST_EMBEDDED_RFB drained_wave=%u tasks_returned=1 before_signal_restore=1 gpu_unverified=1\n",state.wave);fflush(stdout);
            dispatch_semaphore_signal(done);
        }];
    });
    dispatch_semaphore_wait(done,DISPATCH_TIME_FOREVER);
    assert(!sigaction(SIGUSR1,NULL,&action)&&action.sa_handler==sigusr1_handler);
    return 0;
}
- (void)runOwner {
    struct ideck_tool_payload tool={self.binary.bytes,self.binary.length,self.discovery.bytes,self.discovery.length,self.manifest.bytes,self.manifest.length};
    struct ideck_frontend_transport_boundary transport={1,drain,(__bridge void *)self};
    for(unsigned wave=1;wave<=2;wave++){
        self.wave=wave;self.admitting=YES;struct ideck_frontend_result result;
        int error=ideck_retained_frontend_run(self.root.fileSystemRepresentation,&tool,&transport,&result);
        printf("HOST_EMBEDDED_FRONTEND returned=%u native_error=%d guest_status=%d phase=%d reaped=%u\n",result.wave,error,result.guest_status,result.phase,result.reaped);fflush(stdout);
        if(error||result.guest_status||result.phase!=IDECK_FRONTEND_DORMANT){self.result=1;break;}
    }
    dispatch_async(dispatch_get_main_queue(),^{
        assert(!pthread_join(ownerThread,NULL));
        if(!self.result)assert(self.drains==2&&!self.client);
        dispatch_source_cancel(self.timer);
        puts("scope=HOST_REAL_BACKEND_AND_EMBEDDED_RFB_ONLY_NOT_METAL_IPAD_WINE_GAME_OR_FULL_HANDOFF");fflush(stdout);
        exit(self.result);
    });
}
@end
int main(int argc,char **argv){@autoreleasepool{
    if(argc!=4)return 2;
    static HostRetainedRFB *control;control=[HostRetainedRFB new];
    control.root=@(argv[1]);control.output=@(argv[2]);control.bundle=@(argv[3]);
    NSArray *names=@[@"ideck-madeira",@"compatibilitytool.vdf",@"toolmanifest.vdf"];
    NSMutableArray<NSData *> *payload=[NSMutableArray new];
    for(NSString *name in names){NSData *data=[NSData dataWithContentsOfFile:[[control.bundle stringByAppendingPathComponent:@"LabCompatibility"]stringByAppendingPathComponent:name]];assert(data.length&&data.length<=262144);[payload addObject:data];}
    control.binary=payload[0];control.discovery=payload[1];control.manifest=payload[2];
    char directory[]="/tmp/ideck-embedded-rfb-XXXXXX";assert(mkdtemp(directory));
    char *prefix=NULL;assert(asprintf(&prefix,"%s/sock",directory)>0);sock_tmp_prefix=prefix;
    assert(!ideck_native_log_start(control.output.fileSystemRepresentation));
    control.timer=dispatch_source_create(DISPATCH_SOURCE_TYPE_TIMER,0,0,dispatch_get_main_queue());
    dispatch_source_set_timer(control.timer,dispatch_time(DISPATCH_TIME_NOW,0),NSEC_PER_SEC/5,NSEC_PER_MSEC*20);
    dispatch_source_set_event_handler(control.timer,^{[control tick];});dispatch_resume(control.timer);
    assert(!pthread_create(&ownerThread,NULL,run,(__bridge void *)control));
    dispatch_main();
}}
