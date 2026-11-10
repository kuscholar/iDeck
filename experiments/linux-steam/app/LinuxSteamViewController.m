/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#import "LinuxSteamViewController.h"
#if IDECK_LAB_STEAM_FRONTEND
#import "LabRootFS.h"
#import "LabSocketPrefix.h"
#import "LinuxLabRuntime.h"
#import "ToolInstall.h"
#if IDECK_LAB_X11_TRACE
#import "X11TraceInstall.h"
#endif
#import "RFBClient.h"
#import "MetalFramebufferView.h"
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
    if(self.pixels.width<=0||self.pixels.height<=0)return CGRectZero;
    CGFloat scale=MIN(self.bounds.size.width/self.pixels.width,self.bounds.size.height/self.pixels.height);
    CGSize size=CGSizeMake(self.pixels.width*scale,self.pixels.height*scale);
    return CGRectMake((self.bounds.size.width-size.width)/2,(self.bounds.size.height-size.height)/2,size.width,size.height);
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
@end
@implementation LinuxSteamViewController
- (void)viewDidLoad {
    [super viewDidLoad];self.view.backgroundColor=UIColor.blackColor;self.frameLock=[NSLock new];
    self.input=[[LabSteamInput alloc]initWithFrame:self.view.bounds];self.input.autoresizingMask=UIViewAutoresizingFlexibleWidth|UIViewAutoresizingFlexibleHeight;self.input.secureTextEntry=YES;
    __weak typeof(self) weakSelf=self;
    self.display=[[LRMetalFramebufferView alloc]initWithFailure:^(NSString *reason){[weakSelf showStatus:reason];}];
    self.display.frame=self.input.bounds;self.display.autoresizingMask=UIViewAutoresizingFlexibleWidth|UIViewAutoresizingFlexibleHeight;
    if(self.display)[self.input addSubview:self.display];[self.view addSubview:self.input];
    self.status=[[UILabel alloc]init];self.status.textColor=UIColor.whiteColor;self.status.backgroundColor=[UIColor colorWithWhite:0 alpha:.7];self.status.numberOfLines=0;self.status.translatesAutoresizingMaskIntoConstraints=NO;
    [self.view addSubview:self.status];
    UIButton *keyboard=[UIButton buttonWithType:UIButtonTypeSystem];[keyboard setTitle:@"⌨" forState:UIControlStateNormal];keyboard.backgroundColor=UIColor.secondarySystemBackgroundColor;keyboard.layer.cornerRadius=18;keyboard.translatesAutoresizingMaskIntoConstraints=NO;[keyboard addTarget:self action:@selector(toggleKeyboard) forControlEvents:UIControlEventTouchUpInside];[self.view addSubview:keyboard];
    [NSLayoutConstraint activateConstraints:@[
        [keyboard.topAnchor constraintEqualToAnchor:self.view.safeAreaLayoutGuide.topAnchor constant:8],
        [keyboard.trailingAnchor constraintEqualToAnchor:self.view.safeAreaLayoutGuide.trailingAnchor constant:-8],
        [keyboard.widthAnchor constraintEqualToConstant:44],[keyboard.heightAnchor constraintEqualToConstant:44],
        [self.status.leadingAnchor constraintEqualToAnchor:self.view.safeAreaLayoutGuide.leadingAnchor constant:8],
        [self.status.trailingAnchor constraintLessThanOrEqualToAnchor:keyboard.leadingAnchor constant:-8],
        [self.status.topAnchor constraintEqualToAnchor:self.view.safeAreaLayoutGuide.topAnchor constant:8]]];
    [[NSNotificationCenter defaultCenter]addObserver:self selector:@selector(releaseInput) name:UIApplicationWillResignActiveNotification object:nil];
    if(!self.display){[self showStatus:@"Metal framebuffer unavailable; no Linux session started."];return;}
    [self showStatus:@"iDeck Linux Lab — preparing verified install image (interpreter)."];
    dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INITIATED,0),^{[weakSelf startFrontend];});
}
- (void)dealloc {[[NSNotificationCenter defaultCenter]removeObserver:self];[self.client stop];}
- (void)showStatus:(NSString *)value {dispatch_async(dispatch_get_main_queue(),^{self.status.text=value;self.status.hidden=NO;});}
- (void)toggleKeyboard {if(self.input.isFirstResponder)[self.input resignFirstResponder];else[self.input becomeFirstResponder];}
- (void)releaseInput {[self.input releaseInput];}
- (void)acceptPixels:(NSData *)pixels width:(uint16_t)width height:(uint16_t)height {
    // At most one pending main-queue delivery and one latest immutable frame.
    [self.frameLock lock];self.latest=pixels;self.latestSize=CGSizeMake(width,height);BOOL schedule=!self.deliveryQueued;self.deliveryQueued=YES;[self.frameLock unlock];
    if(!schedule)return;
    dispatch_async(dispatch_get_main_queue(),^{
        [self.frameLock lock];NSData *latest=self.latest;CGSize size=self.latestSize;self.latest=nil;self.deliveryQueued=NO;[self.frameLock unlock];
        self.input.pixels=size;[self.display presentPixels:latest width:(uint16_t)size.width height:(uint16_t)size.height];self.status.hidden=YES;
    });
}
- (void)startFrontend {
    @autoreleasepool {
        static atomic_bool requested;
        if(atomic_exchange(&requested,true)){[self showStatus:@"A frontend lifetime was already requested. Existing state was preserved."];return;}
        BOOL windowTrace=[NSProcessInfo.processInfo.arguments containsObject:@"linux-steam-window-trace"];
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
        int policy=dataDirectory<0?-1:ideck_game_file_policy_start(dataDirectory);
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
            [weakSelf showStatus:[NSString stringWithFormat:@"Linux session ended (status %d). Restart the Lab before another runtime session.",result]];
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
        LRRFBClient *client=[[LRRFBClient alloc]initWithPort:5993 password:secret];self.client=client;
        client.frameHandler=^(NSData *pixels,uint16_t w,uint16_t h,uint64_t frames,uint64_t bytes){(void)frames;(void)bytes;[weakSelf acceptPixels:pixels width:w height:h];};
        client.statusHandler=^(NSString *status){if([status hasPrefix:@"Display error:"])[weakSelf showStatus:status];};
        // Never enable inputTraceHandler: it can expose typed keys.
        dispatch_async(dispatch_get_main_queue(),^{self.input.client=client;});[client start];
    }
}
@end
#else
@implementation LinuxSteamViewController
- (void)viewDidLoad {[super viewDidLoad];self.view.backgroundColor=UIColor.systemBackgroundColor;UILabel *label=[[UILabel alloc]initWithFrame:self.view.bounds];label.text=@"Linux Steam frontend is not enabled in this build.";label.numberOfLines=0;[self.view addSubview:label];}
@end
#endif
