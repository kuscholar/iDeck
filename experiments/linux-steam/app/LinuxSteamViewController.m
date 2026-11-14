/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#import "LinuxSteamViewController.h"
#include <math.h>
#if IDECK_LAB_CLI_INPUT
#include <notify.h>
#if !IDECK_LAB_RFB_LIFETIME || !IDECK_LAB_NATIVE_LOG
#error Lab CLI navigation requires real RFB lifetime and native diagnostics
#endif
#endif
#if IDECK_LAB_NATIVE_SETUP_TRANSITION && !IDECK_LAB_STAGE_DOCK_REQUEST
#error Native setup transition requires the explicit request-staging experiment
#endif
#if IDECK_LAB_STEAM_FRONTEND
#import "LabRootFS.h"
#import "LabSocketPrefix.h"
#import "LinuxLabRuntime.h"
#import "ToolInstall.h"
#if IDECK_LAB_X11_TRACE
#import "X11TraceInstall.h"
#endif
#import "RFBClient.h"
#if IDECK_LAB_RFB_LIFETIME
#import "LabRFBCompletion.h"
#endif
#if IDECK_LAB_RETAINED_FRONTEND
#if !IDECK_LAB_RFB_LIFETIME || !IDECK_LAB_NATIVE_LOG || !IDECK_LAB_COMPAT_TOOL
#error Retained frontend requires viewer completion, native logs and tool payload
#endif
#include "RetainedFrontend.h"
#endif
#if IDECK_LAB_STAGE_DOCK_REQUEST
#if !IDECK_LAB_DOCK_STORAGE || !IDECK_LAB_CAPTURE_LAUNCH || !IDECK_LAB_METAL_DRAIN
#error Native request staging requires captured request, Dock storage and real display drain
#endif
#include "LabDockRequestBridge.h"
#endif
#import "MetalFramebufferView.h"
#if IDECK_LAB_METAL_DRAIN
#import "LabMetalFramebufferDrain.h"
#endif
#if IDECK_LAB_NATIVE_LOG
#import "NativeKernelLog.h"
#endif
#include <unistd.h>
#include <stdatomic.h>
#if IDECK_LAB_GAME_FILE_POLICY
#if !IDECK_LAB_COMPAT_TOOL || !IDECK_LAB_NATIVE_LOG
#error Native game-file diagnostics require compatibility-tool and native-log opt-ins
#endif
#include "GameFilePolicy.h"
#include "LaunchProtocol.h"
#if IDECK_LAB_DOCK_STORAGE
#include "WindowsLaunchMap.h"
#import "LabWindowsLibrary.h"
#endif
#if IDECK_LAB_SHARED_LIBRARY
#include "SharedSteamLibrary.h"
#endif
#include <fcntl.h>
#endif
static NSDictionary *LabIdentifiedResult(NSDictionary *fields) {
    NSMutableDictionary *result=[fields mutableCopy];result[@"schema"]=@2;result[@"pid"]=@(getpid());
    result[@"build"]=[NSBundle.mainBundle objectForInfoDictionaryKey:@"CFBundleVersion"]?:@"unknown";
#if IDECK_LAB_NATIVE_LOG
    const char *name=ideck_native_log_name();if(name)result[@"native_log"]=[NSString stringWithUTF8String:name];
#endif
    return result;
}

@interface LabSteamInput : UIView <UIKeyInput,UITextInputTraits>
@property(nonatomic,strong) LRRFBClient *client;
@property(nonatomic) CGSize pixels;
@property(nonatomic,strong) UITouch *activeTouch;
@property(nonatomic) CGPoint lastPixel;
@property(nonatomic,getter=isSecureTextEntry) BOOL secureTextEntry;
@end
@implementation LabSteamInput
- (BOOL)canBecomeFirstResponder {return YES;}
- (BOOL)hasText {return YES;}
- (UIKeyboardType)keyboardType {return UIKeyboardTypeASCIICapable;}
- (UITextAutocorrectionType)autocorrectionType {return UITextAutocorrectionTypeNo;}
- (UITextAutocapitalizationType)autocapitalizationType {return UITextAutocapitalizationTypeNone;}
- (void)insertText:(NSString *)text {
    // Forward human keystrokes without storing a native account/password field.
    NSData *utf32=[text dataUsingEncoding:NSUTF32LittleEndianStringEncoding];
    if(utf32.length>4096)return;
    uint32_t symbols[1024];size_t count=utf32.length/4;
    memcpy(symbols,utf32.bytes,count*4);
    for(size_t i=0;i<count;i++){
        if(symbols[i]=='\n')symbols[i]=0xff0d;
        else if(symbols[i]=='\t')symbols[i]=0xff09;
        else if(symbols[i]>255)symbols[i]|=0x01000000;
    }
    [self.client typeKeysyms:symbols count:count];
}
- (void)deleteBackward {[self.client key:0xff08 down:YES];[self.client key:0xff08 down:NO];}
- (CGRect)guestRect {
    if(!isfinite(self.pixels.width)||!isfinite(self.pixels.height)||self.pixels.width<=0||self.pixels.height<=0)return CGRectZero;
    // LRFramebufferPipeline covers the full drawable, with top-left UV(0,0).
    // Match that drawn rectangle; an aspect-fit input rectangle offsets taps
    // on an iPad even though the image itself is stretched to these bounds.
    return self.bounds;
}
- (void)sendTouch:(UITouch *)touch buttons:(uint8_t)buttons {
    CGRect image=[self guestRect];if(CGRectIsEmpty(image))return;
    CGPoint point=[touch locationInView:self];
    CGFloat x=(point.x-image.origin.x)/image.size.width*self.pixels.width;
    CGFloat y=(point.y-image.origin.y)/image.size.height*self.pixels.height;
    self.lastPixel=CGPointMake(MAX(0,MIN(self.pixels.width-1,x)),MAX(0,MIN(self.pixels.height-1,y)));
    [self.client pointerX:(uint16_t)self.lastPixel.x y:(uint16_t)self.lastPixel.y buttons:buttons];
}
- (void)touchesBegan:(NSSet<UITouch *> *)touches withEvent:(UIEvent *)event {
    (void)event;if(self.activeTouch)return;UITouch *touch=touches.anyObject;
    if(!CGRectContainsPoint([self guestRect],[touch locationInView:self]))return;
    self.activeTouch=touch;[self sendTouch:touch buttons:1];
}
- (void)touchesMoved:(NSSet<UITouch *> *)touches withEvent:(UIEvent *)event {(void)event;if(self.activeTouch&&[touches containsObject:self.activeTouch])[self sendTouch:self.activeTouch buttons:1];}
- (void)touchesEnded:(NSSet<UITouch *> *)touches withEvent:(UIEvent *)event {(void)event;if(self.activeTouch&&[touches containsObject:self.activeTouch]){[self sendTouch:self.activeTouch buttons:0];self.activeTouch=nil;}}
- (void)touchesCancelled:(NSSet<UITouch *> *)touches withEvent:(UIEvent *)event {[self touchesEnded:touches withEvent:event];}
- (void)releaseInput {
    [self.client pointerX:(uint16_t)self.lastPixel.x y:(uint16_t)self.lastPixel.y buttons:0];
    self.activeTouch=nil;[self resignFirstResponder];
}
@end

@interface LinuxSteamViewController ()
@property(nonatomic,strong) UILabel *status;
@property(nonatomic,strong) LabSteamInput *input;
@property(nonatomic,strong) LRMetalFramebufferView *display;
@property(nonatomic,strong) LRRFBClient *client;
@property(nonatomic,strong) NSLock *frameLock;
@property(nonatomic,strong) NSData *latest;
@property(nonatomic) CGSize latestSize;
@property(nonatomic) BOOL deliveryQueued;
@property(atomic) BOOL guestEnded;
#if IDECK_LAB_CLI_INPUT
@property(nonatomic,strong) NSMutableArray<NSNumber *> *cliInputTokens;
@property(nonatomic) NSTimeInterval cliInputLastEvent;
#endif
#if IDECK_LAB_RETAINED_FRONTEND
@property(nonatomic,strong) NSThread *frontendOwner;
@property(nonatomic,strong) NSCondition *frontendCommands;
@property(nonatomic) BOOL frontendRequested;
@property(nonatomic) BOOL retainedBackendReady;
@property(nonatomic) BOOL retainedDisplayDrained;
@property(atomic) unsigned retainedNextWave;
@property(nonatomic,strong) NSURL *retainedRoot;
@property(nonatomic,strong) UIButton *restartSteamButton;
@property(nonatomic) unsigned automaticUpdateRestarts;
#if IDECK_LAB_NATIVE_SETUP_TRANSITION
@property(nonatomic,strong) UIButton *nativeSetupButton;
@property(nonatomic) uint64_t nativeRequestSequence;
@property(nonatomic) BOOL nativeSetupTransferred;
#endif
#endif
#if IDECK_LAB_RFB_LIFETIME
@property(atomic) BOOL acceptsFrames;
#endif
@end
#if IDECK_LAB_RETAINED_FRONTEND
static int LabDrainRetainedTransport(void *context,int guestStatus);
#endif
@implementation LinuxSteamViewController
- (void)viewDidLoad {
#if IDECK_LAB_NATIVE_LOG
    ideck_native_log_line("IDECK_LAB_FRONTEND_ENTRY_V1 step=view_did_load");
#endif
    [super viewDidLoad];self.view.backgroundColor=UIColor.blackColor;self.frameLock=[NSLock new];
#if IDECK_LAB_RFB_LIFETIME
    self.acceptsFrames=YES;
#endif
    self.input=[[LabSteamInput alloc]initWithFrame:self.view.bounds];self.input.autoresizingMask=UIViewAutoresizingFlexibleWidth|UIViewAutoresizingFlexibleHeight;self.input.secureTextEntry=YES;
    __weak typeof(self) weakSelf=self;
    self.display=[[LRMetalFramebufferView alloc]initWithFailure:^(NSString *reason){[weakSelf showStatus:reason];}];
#if IDECK_LAB_NATIVE_LOG
    ideck_native_log_line(self.display?"IDECK_LAB_FRONTEND_ENTRY_V1 step=metal_ready":"IDECK_LAB_FRONTEND_ENTRY_V1 step=metal_unavailable");
#endif
    self.display.frame=self.input.bounds;self.display.autoresizingMask=UIViewAutoresizingFlexibleWidth|UIViewAutoresizingFlexibleHeight;
    if(self.display)[self.input addSubview:self.display];[self.view addSubview:self.input];
    self.status=[[UILabel alloc]init];self.status.textColor=UIColor.whiteColor;self.status.backgroundColor=[UIColor colorWithWhite:0 alpha:.7];self.status.numberOfLines=0;self.status.translatesAutoresizingMaskIntoConstraints=NO;
    [self.view addSubview:self.status];
    UIButton *keyboard=[UIButton buttonWithType:UIButtonTypeSystem];[keyboard setTitle:@"⌨" forState:UIControlStateNormal];keyboard.backgroundColor=UIColor.secondarySystemBackgroundColor;keyboard.layer.cornerRadius=18;keyboard.translatesAutoresizingMaskIntoConstraints=NO;[keyboard addTarget:self action:@selector(toggleKeyboard) forControlEvents:UIControlEventTouchUpInside];[self.view addSubview:keyboard];
#if IDECK_LAB_RETAINED_FRONTEND
    if([NSProcessInfo.processInfo.arguments containsObject:@"linux-steam-retained-frontend"]){
        self.restartSteamButton=[UIButton buttonWithType:UIButtonTypeSystem];
        [self.restartSteamButton setTitle:@"Restart Steam" forState:UIControlStateNormal];
        self.restartSteamButton.enabled=NO;self.restartSteamButton.backgroundColor=UIColor.secondarySystemBackgroundColor;
        self.restartSteamButton.translatesAutoresizingMaskIntoConstraints=NO;
        [self.restartSteamButton addTarget:self action:@selector(restartRetainedSteam) forControlEvents:UIControlEventTouchUpInside];
        [self.view addSubview:self.restartSteamButton];
#if IDECK_LAB_NATIVE_SETUP_TRANSITION
        self.nativeSetupButton=[UIButton buttonWithType:UIButtonTypeSystem];
        [self.nativeSetupButton setTitle:@"Open Madeira game setup" forState:UIControlStateNormal];
        self.nativeSetupButton.hidden=YES;self.nativeSetupButton.enabled=NO;
        self.nativeSetupButton.backgroundColor=UIColor.secondarySystemBackgroundColor;
        self.nativeSetupButton.translatesAutoresizingMaskIntoConstraints=NO;
        [self.nativeSetupButton addTarget:self action:@selector(openNativeMadeiraSetup) forControlEvents:UIControlEventTouchUpInside];
        [self.view addSubview:self.nativeSetupButton];
        [NSLayoutConstraint activateConstraints:@[[self.nativeSetupButton.trailingAnchor constraintEqualToAnchor:self.view.safeAreaLayoutGuide.trailingAnchor constant:-8],
            [self.nativeSetupButton.bottomAnchor constraintEqualToAnchor:self.view.safeAreaLayoutGuide.bottomAnchor constant:-8]]];
#endif
        [NSLayoutConstraint activateConstraints:@[[self.restartSteamButton.leadingAnchor constraintEqualToAnchor:self.view.safeAreaLayoutGuide.leadingAnchor constant:8],
            [self.restartSteamButton.bottomAnchor constraintEqualToAnchor:self.view.safeAreaLayoutGuide.bottomAnchor constant:-8]]];
    }
#endif
    [NSLayoutConstraint activateConstraints:@[
        [keyboard.topAnchor constraintEqualToAnchor:self.view.safeAreaLayoutGuide.topAnchor constant:8],
        [keyboard.trailingAnchor constraintEqualToAnchor:self.view.safeAreaLayoutGuide.trailingAnchor constant:-8],
        [keyboard.widthAnchor constraintEqualToConstant:44],[keyboard.heightAnchor constraintEqualToConstant:44],
        [self.status.leadingAnchor constraintEqualToAnchor:self.view.safeAreaLayoutGuide.leadingAnchor constant:8],
        [self.status.trailingAnchor constraintLessThanOrEqualToAnchor:keyboard.leadingAnchor constant:-8],
        [self.status.topAnchor constraintEqualToAnchor:self.view.safeAreaLayoutGuide.topAnchor constant:8]]];
    [[NSNotificationCenter defaultCenter]addObserver:self selector:@selector(releaseInput) name:UIApplicationWillResignActiveNotification object:nil];
    if(!self.display){[self showStatus:@"Metal framebuffer unavailable; no Linux session started."];return;}
#if IDECK_LAB_CLI_INPUT
    ideck_native_log_line("IDECK_LAB_FRONTEND_ENTRY_V1 step=register_cli_navigation");
    [self registerCLINavigation];
#endif
    [self showStatus:@"iDeck Linux Lab — preparing verified install image (interpreter)."];
    dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INITIATED,0),^{[weakSelf startFrontend];});
}
- (void)dealloc {
#if IDECK_LAB_CLI_INPUT
    for(NSNumber *token in self.cliInputTokens)notify_cancel(token.intValue);
#endif
    [[NSNotificationCenter defaultCenter]removeObserver:self];[self.client stop];
}
#if IDECK_LAB_CLI_INPUT
- (void)registerCLINavigation {
    // Explicit development-build opt-in. No text, request data, shell command,
    // credentials or native game-launch API is accepted by these notifications.
    NSArray<NSString *> *names=@[@"library",@"big-picture",@"left",@"right",@"up",@"down",@"activate",@"back",@"page-down"];
    self.cliInputTokens=[NSMutableArray new];__weak typeof(self) weakSelf=self;
    for(NSUInteger i=0;i<names.count;i++){
        int token=-1;NSString *name=[@"com.kuschqin.ideck.linuxlab.test-input." stringByAppendingString:names[i]];
        uint32_t error=notify_register_dispatch(name.UTF8String,&token,dispatch_get_main_queue(),^(int received){
            (void)received;[weakSelf dispatchCLINavigation:i];
        });
        if(error){
            for(NSNumber *registered in self.cliInputTokens)notify_cancel(registered.intValue);
            [self.cliInputTokens removeAllObjects];
            ideck_native_log_line("IDECK_LAB_CLI_INPUT_V1 registration_failed=1 navigation_disabled=1");return;
        }
        [self.cliInputTokens addObject:@(token)];
    }
    ideck_native_log_line("IDECK_LAB_CLI_INPUT_V1 registered=1 dispatch_is_not_UI_success=1");
}
- (void)dispatchCLINavigation:(NSUInteger)action {
    NSAssert(NSThread.isMainThread,@"Lab navigation belongs to main");
    if(action>8||!self.view.window||UIApplication.sharedApplication.applicationState!=UIApplicationStateActive||
       self.guestEnded||!self.acceptsFrames||!self.client||self.input.activeTouch||self.input.isFirstResponder)return;
    CGSize pixels=self.input.pixels;
    if(!isfinite(pixels.width)||!isfinite(pixels.height)||pixels.width<1||pixels.height<1||pixels.width>65535||pixels.height>65535)return;
    NSTimeInterval now=NSProcessInfo.processInfo.systemUptime;
    if(now-self.cliInputLastEvent<0.35)return;self.cliInputLastEvent=now;
    if(action<2){
        // Two known desktop Steam chrome controls, in guest framebuffer space.
        // Verify the actual screen before use; never use on an authentication UI.
        CGFloat x=(action==0?0.145:0.905)*(pixels.width-1);
        CGFloat y=(action==0?0.058:0.024)*(pixels.height-1);
        self.input.lastPixel=CGPointMake(x,y);
        [self.client pointerX:(uint16_t)x y:(uint16_t)y buttons:1];
        [self.client pointerX:(uint16_t)x y:(uint16_t)y buttons:0];
    }else{
        const uint32_t keys[]={0xff51,0xff53,0xff52,0xff54,0xff0d,0xff1b,0xff56};
        uint32_t key=keys[action-2];[self.client key:key down:YES];[self.client key:key down:NO];
    }
    (void)ideck_native_note_navigation((unsigned)action);
    char line[128];snprintf(line,sizeof line,"IDECK_LAB_CLI_INPUT_V1 action=%u dispatch_only=1 physical_touch_test=0",(unsigned)action);
    ideck_native_log_line(line);
}
#endif
- (void)showStatus:(NSString *)value {dispatch_async(dispatch_get_main_queue(),^{self.status.text=value;self.status.hidden=NO;});}
- (void)toggleKeyboard {if(self.input.isFirstResponder)[self.input resignFirstResponder];else[self.input becomeFirstResponder];}
- (void)releaseInput {[self.input releaseInput];}
#if IDECK_LAB_RFB_LIFETIME
- (void)endDisplayForGuestStatus:(int)status {
    [self endDisplayForGuestStatus:status completion:nil];
}
- (void)endDisplayForGuestStatus:(int)status completion:(dispatch_block_t)completion {
    dispatch_async(dispatch_get_main_queue(),^{
        self.acceptsFrames=NO;[self.input releaseInput];self.input.client=nil;
        LRRFBClient *client=self.client;
        dispatch_block_t finished=^{
            client.frameHandler=nil;client.statusHandler=nil;
            [self.frameLock lock];self.latest=nil;[self.frameLock unlock];
            self.input.pixels=CGSizeZero;[self.display clearFrame];
            if(self.client==client)self.client=nil;
#if IDECK_LAB_RETAINED_FRONTEND
            self.restartSteamButton.enabled=self.retainedBackendReady;
#endif
#if IDECK_LAB_NATIVE_LOG
            #if IDECK_LAB_METAL_DRAIN
            ideck_native_log_line("IDECK_METAL_COMMAND_DRAIN_V1 tracked_rfb_tasks_returned=1 tracked_gpu_and_main_bodies_completed=1 driver_storage_Wine_boundary_unverified=1");
#else
            ideck_native_log_line("NATIVE_VIEWER_CLOSED tracked_rfb_tasks_returned=1 gpu_completion_unverified=1 no_linux_or_game_quiescence_claim=1");
#endif
#endif
            [self showStatus:[NSString stringWithFormat:@"Linux session ended (status %d). Display connection closed. No other runtime was started.",status]];
            if(completion)completion();
        };
        dispatch_block_t transportFinished=^{
#if IDECK_LAB_METAL_DRAIN
            [self.display ideckCloseMetalWithCompletion:finished];
#else
            finished();
#endif
        };
        if(client)[client ideckStopWithCompletion:transportFinished];else transportFinished();
    });
}
#endif
- (void)acceptPixels:(NSData *)pixels width:(uint16_t)width height:(uint16_t)height {
#if IDECK_LAB_RFB_LIFETIME
    if(!self.acceptsFrames)return;
#endif
    // At most one pending main-queue delivery and one latest immutable frame.
    [self.frameLock lock];self.latest=pixels;self.latestSize=CGSizeMake(width,height);BOOL schedule=!self.deliveryQueued;self.deliveryQueued=YES;[self.frameLock unlock];
    if(!schedule)return;
    dispatch_async(dispatch_get_main_queue(),^{
        [self.frameLock lock];NSData *latest=self.latest;CGSize size=self.latestSize;self.latest=nil;self.deliveryQueued=NO;[self.frameLock unlock];
#if IDECK_LAB_RFB_LIFETIME
        if(!self.acceptsFrames)return;
#endif
        self.input.pixels=size;[self.display presentPixels:latest width:(uint16_t)size.width height:(uint16_t)size.height];self.status.hidden=YES;
    });
}
#if IDECK_LAB_RETAINED_FRONTEND
- (int)drainRetainedTransportStatus:(int)status {
    NSAssert(!NSThread.isMainThread,@"Native owner waits, never main");
    dispatch_semaphore_t done=dispatch_semaphore_create(0);self.guestEnded=YES;
    [self endDisplayForGuestStatus:status completion:^{self.retainedDisplayDrained=YES;dispatch_semaphore_signal(done);}];
    dispatch_semaphore_wait(done,DISPATCH_TIME_FOREVER);return 0;
}
- (void)connectRetainedDisplay:(NSURL *)root wave:(unsigned)wave {
    __weak typeof(self) weakSelf=self;
    dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INITIATED,0),^{
        NSURL *ready=[root URLByAppendingPathComponent:@"data/tmp/ideck-display-ready"];
        BOOL found=NO;
        for(unsigned i=0;i<600;i++){
            if(self.guestEnded||self.retainedNextWave!=wave)return;
            struct ideck_frontend_result state;
            if(!ideck_retained_frontend_snapshot(&state)&&state.wave==wave&&
               (state.phase==IDECK_FRONTEND_RUNNING || (wave==1&&state.phase==IDECK_FRONTEND_PREPARING&&!strcmp(ideck_linux_lab_stage(),"guest-running")))&&
               [NSFileManager.defaultManager fileExistsAtPath:ready.path]){found=YES;break;}
            [NSThread sleepForTimeInterval:.2];
        }
        if(!found){if(self.retainedNextWave==wave&&!self.guestEnded)[self showStatus:@"Retained Steam display readiness timed out. Existing session was preserved."];return;}
        NSURL *url=[root URLByAppendingPathComponent:@"data/tmp/ideck-vnc-password"];
        NSFileHandle *file=[NSFileHandle fileHandleForReadingAtPath:url.path];NSData *password=[file readDataOfLength:9];[file closeFile];
        NSString *secret=password.length==8?[[NSString alloc]initWithData:password encoding:NSASCIIStringEncoding]:nil;
        if(!secret){[self showStatus:@"Guest display authentication material is unavailable."];return;}
        LRRFBClient *client=[[LRRFBClient alloc]initWithPort:5993 password:secret];
        client.frameHandler=^(NSData *p,uint16_t w,uint16_t h,uint64_t f,uint64_t b){(void)f;(void)b;[weakSelf acceptPixels:p width:w height:h];};
        client.statusHandler=^(NSString *status){if([status hasPrefix:@"Display error:"])[weakSelf showStatus:status];};
        dispatch_async(dispatch_get_main_queue(),^{
            if(self.guestEnded||!self.acceptsFrames||self.retainedNextWave!=wave)return;
            self.client=client;self.input.client=client;[client start];
        });
    });
}
- (void)restartRetainedSteam {
    NSAssert(NSThread.isMainThread,@"Retained UI admission belongs to main");
#if IDECK_LAB_NATIVE_SETUP_TRANSITION
    if(self.nativeSetupTransferred)return; // No Linux revival over a native session.
#endif
    if(!self.restartSteamButton.enabled||!self.retainedBackendReady||!self.guestEnded||self.client)return;
#if IDECK_LAB_METAL_DRAIN
    if(![self.display ideckReopenMetal]){[self showStatus:@"Display cleanup is incomplete or the GPU reported a failure. Session preserved."];return;}
#endif
    self.restartSteamButton.enabled=NO;self.retainedBackendReady=NO;self.retainedDisplayDrained=NO;
    self.guestEnded=NO;self.acceptsFrames=YES;self.retainedNextWave++;
    [self.frontendCommands lock];self.frontendRequested=YES;[self.frontendCommands signal];[self.frontendCommands unlock];
    [self showStatus:@"Restarting Steam in the retained Linux environment."];
    [self connectRetainedDisplay:self.retainedRoot wave:self.retainedNextWave];
}
#if IDECK_LAB_NATIVE_SETUP_TRANSITION
- (void)openNativeMadeiraSetup {
    NSAssert(NSThread.isMainThread,@"Native setup presentation belongs to main");
    struct ideck_frontend_result state;
    if(self.nativeSetupTransferred||!self.nativeSetupButton.enabled||self.presentedViewController||!self.view.window||
       !self.retainedDisplayDrained||!self.guestEnded||self.client||self.acceptsFrames||
       ideck_retained_frontend_snapshot(&state)||state.error||state.guest_status||state.phase!=IDECK_FRONTEND_DORMANT||
       ideck_linux_lab_live_guest_threads()!=0||ideck_linux_lab_native_worker_entries()!=0||
       !self.nativeRequestSequence||ideck_lab_pending_dock_sequence()!=self.nativeRequestSequence)return;
    self.nativeSetupTransferred=YES;self.nativeSetupButton.enabled=NO;self.restartSteamButton.enabled=NO;
    [self releaseInput];
    [[NSNotificationCenter defaultCenter]postNotificationName:@"IDeckLinuxMadeiraSetupWillPresent" object:nil];
    UIViewController *controller=(__bridge_transfer UIViewController *)ideck_lab_madeira_setup_controller();
    controller.modalPresentationStyle=UIModalPresentationFullScreen;
    controller.modalInPresentation=YES;
    [self presentViewController:controller animated:YES completion:nil];
    ideck_native_log_line("IDECK_NATIVE_SETUP_PRESENT_REQUEST_V1 captured_request=1 linux_restarts_disabled=1 game_started=0");
    // Native user signs in/enables JIT/chooses Play normally. Do not resume
    // Linux merely because this UI disappears or the initial Wine game exits.
}
#endif
- (void)startRetainedOwnerRoot:(NSURL *)root lab:(NSURL *)lab binary:(NSData *)binary discovery:(NSData *)discovery manifest:(NSData *)manifest {
    /* One process-lifetime owner thread. Do not cancel it or recreate the Linux
     * kernel on scene changes. Its loop waits only while backend is dormant. */
    dispatch_sync(dispatch_get_main_queue(),^{
        self.retainedRoot=root;self.retainedNextWave=1;self.frontendCommands=[NSCondition new];self.frontendRequested=YES;
        self.frontendOwner=[[NSThread alloc]initWithBlock:^{
            for(;;){@autoreleasepool{
                [self.frontendCommands lock];while(!self.frontendRequested)[self.frontendCommands wait];
                self.frontendRequested=NO;[self.frontendCommands unlock];
                struct ideck_tool_payload tool={binary.bytes,binary.length,discovery.bytes,discovery.length,manifest.bytes,manifest.length};
                struct ideck_frontend_result result;
                struct ideck_frontend_transport_boundary transport={1,LabDrainRetainedTransport,(__bridge void *)self};
                int error=ideck_retained_frontend_run(root.fileSystemRepresentation,&tool,&transport,&result);
                NSMutableDictionary *fields=[@{@"native_error":@(error),@"guest_status":@(result.guest_status),@"wave":@(result.wave),
                    @"backend_phase":@(result.phase),@"reaped":@(result.reaped),@"actual_game":@NO} mutableCopy];
                fields[@"steam_update_restart_requested"]=@(ideck_frontend_update_exit(result.guest_status));
                BOOL capturedRequestReady=NO;
#if IDECK_LAB_CAPTURE_LAUNCH
                struct ideck_launch_request capturedRequest;uint64_t capturedSequence=0;
                int captureError=ideck_game_file_policy_pending(&capturedRequest,&capturedSequence);
                capturedRequestReady=!captureError;
                fields[@"capture_error"]=@(captureError);fields[@"captured_request_not_started"]=@(capturedRequestReady);
                if(capturedRequestReady){fields[@"captured_sequence"]=@(capturedSequence);fields[@"captured_appid"]=@(capturedRequest.appid);}
#if IDECK_LAB_DOCK_STORAGE
                if(capturedRequestReady&&!error&&!result.guest_status&&result.phase==IDECK_FRONTEND_DORMANT){
                    struct ideck_windows_launch_map mapped;
                    int mapping=ideck_windows_launch_map(&capturedRequest,&mapped);
                    fields[@"windows_mapping_error"]=@(mapping);
                    if(!mapping){
                        BOOL created=NO;NSError *bindingError=nil;
                        NSURL *documents=[NSFileManager.defaultManager URLsForDirectory:NSDocumentDirectory inDomains:NSUserDomainMask].firstObject;
                        BOOL bound=LabBindWindowsLibrary(root,documents,&created,&bindingError);
                        fields[@"windows_prefix_bound"]=@(bound);fields[@"windows_library_vdf_created"]=@(created);
                        fields[@"windows_prefix_error"]=@(bound?0:bindingError.code);fields[@"mapped_argc"]=@(mapped.argc);
                    }
                    // Metadata preparation only: no Wine startup, auth or writer permission.
#if IDECK_LAB_STAGE_DOCK_REQUEST
                    if(!mapping&&[fields[@"windows_prefix_bound"] boolValue]){
                        int staged=ideck_lab_receive_dock_request(&capturedRequest,sizeof capturedRequest,capturedSequence);
                        fields[@"native_request_stage_error"]=@(staged);
                        if(!staged)fields[@"native_request_stage_sequence"]=@(capturedSequence);
                    }
#endif
                }
#endif
                // No raw argument/frame serialization. This does not grant Wine or licensing permission.
#endif
                NSData *report=[NSJSONSerialization dataWithJSONObject:LabIdentifiedResult(fields) options:NSJSONWritingPrettyPrinted error:nil];
                [report writeToURL:[lab URLByAppendingPathComponent:@"last-retained-frontend.json"] options:NSDataWritingAtomic error:nil];
                dispatch_async(dispatch_get_main_queue(),^{
                    self.guestEnded=YES;self.retainedBackendReady=!error&&ideck_frontend_restart_ready(&result);
                    if(self.retainedDisplayDrained){
                        self.restartSteamButton.enabled=self.retainedBackendReady;
#if IDECK_LAB_NATIVE_SETUP_TRANSITION
                        if(self.retainedBackendReady&&!result.guest_status&&capturedRequestReady&&
                           [fields[@"native_request_stage_sequence"] unsignedLongLongValue]){
                            self.nativeRequestSequence=[fields[@"native_request_stage_sequence"] unsignedLongLongValue];
                            self.nativeSetupButton.hidden=NO;self.nativeSetupButton.enabled=YES;
                            self.restartSteamButton.enabled=NO; // Captured request owns this experimental transition.
                        }
#endif
                        BOOL update=ideck_frontend_update_exit(result.guest_status);
                        NSString *message=self.retainedBackendReady?(update?@"Steam update completed. Ready to restart.":(capturedRequestReady?@"Steam closed. Play request captured; Windows has not started.":@"Steam closed. Ready to restart in the retained environment.")):
                            (error?@"Backend cleanup failed. Existing state was preserved.":@"Steam exited unexpectedly. Existing state was preserved; no automatic retry.");
                        [self showStatus:message];
                        // Honor exactly one documented updater restart, only after
                        // the real backend and viewer drains. Repeated 42 requires
                        // an explicit tap; errors and game requests never retry.
                        if(self.retainedBackendReady&&update&&!capturedRequestReady&&self.automaticUpdateRestarts==0){
                            self.automaticUpdateRestarts++;
                            ideck_native_log_line("IDECK_STEAM_UPDATE_RESTART_V1 decoded_exit=42 automatic_count=1 backend_and_viewer_drained=1 game_started=0");
                            [self restartRetainedSteam];
                        }
                    }else [self endDisplayForGuestStatus:error?error:result.guest_status];
                });
            }}
        }];
        self.frontendOwner.name=@"iDeck Linux frontend owner";[self.frontendOwner start];
    });
    [self connectRetainedDisplay:root wave:1];
}
#endif
- (void)startFrontend {
    @autoreleasepool {
        static atomic_bool requested;
        if(atomic_exchange(&requested,true)){[self showStatus:@"A frontend lifetime was already requested. Existing state was preserved."];return;}
        BOOL windowTrace=[NSProcessInfo.processInfo.arguments containsObject:@"linux-steam-window-trace"];
        BOOL retained=[NSProcessInfo.processInfo.arguments containsObject:@"linux-steam-retained-frontend"];
#if !IDECK_LAB_RETAINED_FRONTEND
        if(retained){[self showStatus:@"Retained frontend is not enabled; no session started."];return;}
#endif
#if !IDECK_LAB_X11_TRACE
        if(windowTrace){[self showStatus:@"Window diagnostics are not enabled in this build; no guest started."];return;}
#endif
        NSFileManager *fm=NSFileManager.defaultManager;
        NSURL *support=[fm URLsForDirectory:NSApplicationSupportDirectory inDomains:NSUserDomainMask].firstObject;
        NSURL *lab=[support URLByAppendingPathComponent:@"iDeckLinuxLab" isDirectory:YES];
        NSURL *documents=[fm URLsForDirectory:NSDocumentDirectory inDomains:NSUserDomainMask].firstObject;
        NSURL *input=[documents URLByAppendingPathComponent:@"LinuxLabInput/steam-rootfs.tar.gz"];
        NSString *expected=[NSBundle.mainBundle objectForInfoDictionaryKey:@"LinuxLabRootFSSHA256"];
        NSError *error=nil;NSURL *root=LabPrepareSteamRoot(lab,input,expected,&error);
        if(!root){[self showStatus:error.localizedDescription?:@"Root preparation failed; no guest started."];return;}
        // realfs_mknod(FIFO) can change native cwd. A relative socket prefix
        // therefore breaks existing X11 listeners; retain an absolute prefix.
        char *ownedPrefix=LabCopyNativeSocketPrefix(NSTemporaryDirectory());
        if(!ownedPrefix){[self showStatus:@"App temporary IPC path is unavailable or too long; no guest started."];return;}
        // Global guest threads outlive this autorelease pool and controller. Keep
        // the one malloc copy for this single native runtime lifetime; no
        // safe all-descendant teardown/free is claimed yet.
        extern const char *sock_tmp_prefix;sock_tmp_prefix=ownedPrefix;
        if([NSProcessInfo.processInfo.arguments containsObject:@"linux-steam-install-dependencies"]) {
            [self showStatus:@"Installing the pinned Debian Steam dependency in this Lab only."];
            int result=ideck_linux_lab_dependencies(root.fileSystemRepresentation);
            NSDictionary *report=@{@"status":@(result),@"stage":@(ideck_linux_lab_stage()),@"native_guest_threads":@(ideck_linux_lab_live_guest_threads()),
                @"linux_worker_entries":@(ideck_linux_lab_native_worker_entries())};
            NSData *data=[NSJSONSerialization dataWithJSONObject:LabIdentifiedResult(report) options:NSJSONWritingPrettyPrinted error:nil];
            [data writeToURL:[lab URLByAppendingPathComponent:@"last-dependency-setup.json"] options:NSDataWritingAtomic error:nil];
            [self showStatus:[NSString stringWithFormat:@"Dependency control ended (status %d). Restart the Lab for Steam.",result]];
            return;
        }
#if IDECK_LAB_GAME_FILE_POLICY
        // Register only the native app-prepared data capability, before any
        // Linux task exists. No guest path, descriptor, auth or command enters
        // this registration API. Libraries may be created by Steam later.
        int rootDirectory=open(root.fileSystemRepresentation,O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
        int dataDirectory=rootDirectory<0?-1:openat(rootDirectory,"data",O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
#if IDECK_LAB_SHARED_LIBRARY
        int sharedDirectory=ideck_shared_steam_prepare(root.fileSystemRepresentation);
        int policy=dataDirectory<0||sharedDirectory<0?-1:ideck_game_file_policy_start_shared(dataDirectory,sharedDirectory);
        if(sharedDirectory>=0)close(sharedDirectory);
#else
        int policy=dataDirectory<0?-1:ideck_game_file_policy_start(dataDirectory);
#endif
        if(dataDirectory>=0)close(dataDirectory);if(rootDirectory>=0)close(rootDirectory);
        if(policy){[self showStatus:@"Native game-file diagnostics could not bind this Lab root. No guest started."];return;}
        ideck_native_log_line("IDECK_GAME_FILE_POLICY_V1 diagnostic_only=1 wrapper_exit=125 game_launched=0");
#endif
        BOOL compatibilityProbe=[NSProcessInfo.processInfo.arguments containsObject:@"linux-steam-compatibility-diagnostics"];
#if IDECK_LAB_COMPAT_TOOL
        NSURL *resource=[NSBundle.mainBundle.resourceURL URLByAppendingPathComponent:@"LabCompatibility" isDirectory:YES];
        if(!resource){[self showStatus:@"Compatibility resource directory is unavailable; no guest started."];return;}
        NSData *toolBinary=[NSData dataWithContentsOfURL:[resource URLByAppendingPathComponent:@"ideck-madeira"]];
        NSData *toolDiscovery=[NSData dataWithContentsOfURL:[resource URLByAppendingPathComponent:@"compatibilitytool.vdf"]];
        NSData *toolManifest=[NSData dataWithContentsOfURL:[resource URLByAppendingPathComponent:@"toolmanifest.vdf"]];
        if(!toolBinary.length||toolBinary.length>262144||!toolDiscovery.length||toolDiscovery.length>4096||!toolManifest.length||toolManifest.length>4096){
            [self showStatus:@"Bundled compatibility tool is missing or exceeds its bounds; no guest started."];return;
        }
        if(compatibilityProbe){
            struct ideck_tool_payload payload={toolBinary.bytes,toolBinary.length,toolDiscovery.bytes,toolDiscovery.length,toolManifest.bytes,toolManifest.length};
            int result=ideck_linux_lab_compatibility_tool_probe(root.fileSystemRepresentation,&payload);
            extern unsigned ideck_lab_bridge_requests(void);
            NSDictionary *report=@{@"status":@(result),@"native_bridge_requests":@(ideck_lab_bridge_requests()),@"diagnostic_only":@YES,
                @"native_guest_threads":@(ideck_linux_lab_live_guest_threads()),@"linux_worker_entries":@(ideck_linux_lab_native_worker_entries())};
            NSData *data=[NSJSONSerialization dataWithJSONObject:LabIdentifiedResult(report) options:NSJSONWritingPrettyPrinted error:nil];
            [data writeToURL:[lab URLByAppendingPathComponent:@"last-compatibility-control.json"] options:NSDataWritingAtomic error:nil];
            [self showStatus:[NSString stringWithFormat:@"Compatibility diagnostic ended (status %d). No game was launched. Restart the Lab for Steam.",result]];return;
        }
#else
        if(compatibilityProbe){[self showStatus:@"Compatibility tool is not enabled; no guest started."];return;}
#endif
        // This is a separate diagnostic launch, never live injection. These
        // immutable bytes are retained by the launch block until preboot VFS
        // installation has returned. CodeSignature covers the bundle resource.
#if IDECK_LAB_X11_TRACE
        NSData *x11Trace=nil;
        if(windowTrace){
            NSURL *traceURL=[NSBundle.mainBundle.resourceURL URLByAppendingPathComponent:@"LabDiagnostics/xlib-window-trace.so"];
            x11Trace=[NSData dataWithContentsOfURL:traceURL];
            if(x11Trace.length<64||x11Trace.length>262144){[self showStatus:@"Bundled window diagnostic is unavailable; no guest started."];return;}
            ideck_native_log_line("IDECK_X11_TRACE_V3 requested=1 guest_activation=unverified");
        }
#endif
        [self showStatus:@"Starting genuine ARM64 Linux Steam; waiting for its display."];
#if IDECK_LAB_RETAINED_FRONTEND
        if(retained){[self startRetainedOwnerRoot:root lab:lab binary:toolBinary discovery:toolDiscovery manifest:toolManifest];return;}
#endif
#if IDECK_LAB_NATIVE_LOG
#if IDECK_LAB_CEF_DISABLE_GPU
        ideck_native_log_line("UI_GRAPHICS_POLICY cef_disable_gpu=1");
#else
        ideck_native_log_line("UI_GRAPHICS_POLICY cef_disable_gpu=0");
#endif
#endif
        __weak typeof(self) weakSelf=self;
        dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INITIATED,0),^{
#if IDECK_LAB_COMPAT_TOOL
            // Capturing the NSData objects here keeps their bytes alive until
            // the synchronous preboot installer and initial session return.
            struct ideck_tool_payload payload={toolBinary.bytes,toolBinary.length,toolDiscovery.bytes,toolDiscovery.length,toolManifest.bytes,toolManifest.length};
#if IDECK_LAB_X11_TRACE
            int result;
            if(windowTrace){struct ideck_x11_trace_payload trace={x11Trace.bytes,x11Trace.length};result=ideck_linux_lab_steam_frontend_with_trace(root.fileSystemRepresentation,&payload,&trace);}
            else result=ideck_linux_lab_steam_frontend_with_tool(root.fileSystemRepresentation,&payload);
#else
            int result=ideck_linux_lab_steam_frontend_with_tool(root.fileSystemRepresentation,&payload);
#endif
#else
            int result=ideck_linux_lab_steam_frontend(root.fileSystemRepresentation);
#endif
            NSDictionary *snapshot=@{@"status":@(result),@"stage":@(ideck_linux_lab_stage()),
                @"native_guest_threads":@(ideck_linux_lab_live_guest_threads()),@"linux_worker_entries":@(ideck_linux_lab_native_worker_entries()),@"window_trace_requested":@(windowTrace)};
            NSData *report=[NSJSONSerialization dataWithJSONObject:LabIdentifiedResult(snapshot) options:NSJSONWritingPrettyPrinted error:nil];
            [report writeToURL:[lab URLByAppendingPathComponent:@"last-runtime-session.json"] options:NSDataWritingAtomic error:nil];
            weakSelf.guestEnded=YES;
#if IDECK_LAB_RFB_LIFETIME
            [weakSelf endDisplayForGuestStatus:result];
#else
            [weakSelf showStatus:[NSString stringWithFormat:@"Linux session ended (status %d). Restart the Lab before another runtime session.",result]];
#endif
        });
        NSURL *ready=[root URLByAppendingPathComponent:@"data/tmp/ideck-display-ready"];
        NSURL *passwordURL=[root URLByAppendingPathComponent:@"data/tmp/ideck-vnc-password"];
        BOOL found=NO;
        for(unsigned i=0;i<600;i++){
            if(self.guestEnded)return;
            if(!strcmp(ideck_linux_lab_stage(),"guest-running")&&[fm fileExistsAtPath:ready.path]){found=YES;break;}
            [NSThread sleepForTimeInterval:.2];
        }
        if(!found){[self showStatus:@"Guest display readiness timed out. No automatic restart was attempted."];return;}
        NSFileHandle *file=[NSFileHandle fileHandleForReadingAtPath:passwordURL.path];NSData *password=[file readDataOfLength:9];[file closeFile];
        NSString *secret=password.length==8?[[NSString alloc]initWithData:password encoding:NSASCIIStringEncoding]:nil;
        if(!secret){[self showStatus:@"Guest display authentication material is unavailable."];return;}
        LRRFBClient *client=[[LRRFBClient alloc]initWithPort:5993 password:secret];
#if !IDECK_LAB_RFB_LIFETIME
        self.client=client;
#endif
        client.frameHandler=^(NSData *pixels,uint16_t w,uint16_t h,uint64_t frames,uint64_t bytes){(void)frames;(void)bytes;[weakSelf acceptPixels:pixels width:w height:h];};
        client.statusHandler=^(NSString *status){if([status hasPrefix:@"Display error:"])[weakSelf showStatus:status];};
        // Never enable inputTraceHandler: it can expose typed keys.
#if IDECK_LAB_RFB_LIFETIME
        dispatch_async(dispatch_get_main_queue(),^{
            if(self.guestEnded||!self.acceptsFrames)return;
            self.client=client;self.input.client=client;[client start];
        });
#else
        dispatch_async(dispatch_get_main_queue(),^{self.input.client=client;});[client start];
#endif
    }
}
@end
#if IDECK_LAB_RETAINED_FRONTEND
static int LabDrainRetainedTransport(void *context,int guestStatus){
    LinuxSteamViewController *controller=(__bridge LinuxSteamViewController *)context;
    return [controller drainRetainedTransportStatus:guestStatus];
}
#endif
#else
@implementation LinuxSteamViewController
- (void)viewDidLoad {[super viewDidLoad];self.view.backgroundColor=UIColor.systemBackgroundColor;UILabel *label=[[UILabel alloc]initWithFrame:self.view.bounds];label.text=@"Linux Steam frontend is not enabled in this build.";label.numberOfLines=0;[self.view addSubview:label];}
@end
#endif
