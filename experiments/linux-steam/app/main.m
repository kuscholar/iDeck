/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#import <UIKit/UIKit.h>
#import "LinuxLabRuntime.h"
#import "LinuxSteamViewController.h"
#ifndef IDECK_LAB_NATIVE_SETUP_TRANSITION
#define IDECK_LAB_NATIVE_SETUP_TRANSITION 0
#endif
#if IDECK_LAB_MADEIRA_SETUP
#import "LabRootFS.h"
#import "LabWindowsLibrary.h"
#include "SharedSteamLibrary.h"
#include "LabStartupMode.h"
#include <string.h>
#if !IDECK_LAB_NATIVE_LOG
#error Cold setup requires native diagnostics in its isolated target
#endif
#include <unistd.h>
static int startupMode;
extern void *ideck_lab_madeira_setup_controller(void);
extern void ideck_lab_madeira_setup_open_url(const char *);
#endif
#if IDECK_LAB_CASP_ORDER
#if !IDECK_LAB_STEAM_FRONTEND || !IDECK_LAB_NATIVE_LOG
#error CASP ordering experiment requires explicit frontend and native logging
#endif
#include <string.h>
extern const char ideck_casp_order_marker[];
#endif
#if IDECK_LAB_RETAINED_FRONTEND
#include "RetainedFrontend.h"
#include <stdio.h>
#endif
#if IDECK_LAB_NATIVE_LOG
#import "NativeKernelLog.h"
#include <unistd.h>
#endif
#if IDECK_LAB_WINE_INITIAL_JOIN
#include "WineInitialJoin.h"
#endif

@interface LinuxLabDelegate : UIResponder <UIApplicationDelegate>
@property(nonatomic, strong) UIWindow *window;
@property(nonatomic, strong) UITextView *output;
@property(nonatomic, copy) NSString *nativeLogError;
#if IDECK_LAB_MADEIRA_SETUP
@property(nonatomic) BOOL nativeSetupPresented;
@property(nonatomic) BOOL nativeSetupReady;
@property(nonatomic,strong) NSMutableArray<NSURL *> *pendingSetupURLs;
- (void)routeSetupURL:(NSURL *)url;
- (void)coldSetupDidAppear:(NSNotification *)note;
- (void)nativeSetupWillPresent:(NSNotification *)note;
- (void)startColdMadeiraSetup;
#endif
#if IDECK_LAB_NATIVE_LOG
@property(nonatomic, strong) NSTimer *nativeResourceTimer;
#if IDECK_LAB_WINE_INITIAL_JOIN
@property(nonatomic, strong) NSURL *wineInitialReceiptURL;
#endif
- (void)writeNativeHealth;
#endif
- (void)connectWindowScene:(UIWindowScene *)scene;
@end
@implementation LinuxLabDelegate
- (BOOL)application:(UIApplication *)application didFinishLaunchingWithOptions:(NSDictionary *)options {
#if IDECK_LAB_MADEIRA_SETUP
    if(startupMode>0 || IDECK_LAB_NATIVE_SETUP_TRANSITION){self.pendingSetupURLs=[NSMutableArray new];[[NSNotificationCenter defaultCenter]addObserver:self selector:@selector(coldSetupDidAppear:) name:@"IDeckLinuxMadeiraSetupReady" object:nil];}
#if IDECK_LAB_NATIVE_SETUP_TRANSITION
    [[NSNotificationCenter defaultCenter]addObserver:self selector:@selector(nativeSetupWillPresent:) name:@"IDeckLinuxMadeiraSetupWillPresent" object:nil];
#endif
#endif
#if IDECK_LAB_NATIVE_LOG
    NSFileManager *fm=NSFileManager.defaultManager;
    NSURL *support=[fm URLsForDirectory:NSApplicationSupportDirectory inDomains:NSUserDomainMask].firstObject;
    NSURL *lab=[support URLByAppendingPathComponent:@"iDeckLinuxLab" isDirectory:YES];
    NSURL *logs=[lab URLByAppendingPathComponent:@"NativeDiagnostics" isDirectory:YES];
    NSError *error=nil;
    BOOL ready=[fm createDirectoryAtURL:logs withIntermediateDirectories:YES attributes:@{NSFilePosixPermissions:@0700} error:&error];
    int result=ready?ideck_native_log_start(logs.fileSystemRepresentation):-1;
    if(result||!ideck_native_log_name())self.nativeLogError=@"Private diagnostics unavailable. No Linux session started.";
    else {
        NSMutableDictionary *receipt=[@{@"file":[NSString stringWithUTF8String:ideck_native_log_name()],@"schema":@1,
            @"health_file":[NSString stringWithUTF8String:ideck_native_health_name()],
            @"byte_limit":@(IDECK_NATIVE_LOG_LIMIT),@"pid":@(getpid()),@"physical_memory_bytes":@(NSProcessInfo.processInfo.physicalMemory),
            @"build":[NSBundle.mainBundle objectForInfoDictionaryKey:@"CFBundleVersion"]?:@"unknown"} mutableCopy];
#if IDECK_LAB_WINE_INITIAL_JOIN
        NSString *wineFile=[NSString stringWithFormat:@"wine-initial-%s.json",ideck_native_log_name()];
        receipt[@"wine_initial_file"]=wineFile;
        self.wineInitialReceiptURL=[logs URLByAppendingPathComponent:wineFile];
#endif
        NSData *data=[NSJSONSerialization dataWithJSONObject:receipt options:NSJSONWritingPrettyPrinted error:nil];
        if(![data writeToURL:[lab URLByAppendingPathComponent:@"last-native-log.json"] options:NSDataWritingAtomic error:&error])
            self.nativeLogError=@"Private diagnostics receipt unavailable. No Linux session started.";
        if(!self.nativeLogError){
#if IDECK_LAB_CASP_ORDER
            if(strcmp(ideck_casp_order_marker,"IDECK_CASP_TRANSLATION_BEFORE_PAIR_LOCK_V1"))
                self.nativeLogError=@"Experimental engine identity mismatch. No Linux session started.";
            else ideck_native_log_line(ideck_casp_order_marker);
#endif
            ideck_native_log_resources();
            int coldChoice=0;
#if IDECK_LAB_MADEIRA_SETUP
            coldChoice=startupMode;
#endif
            char selection[160];snprintf(selection,sizeof selection,"IDECK_LAB_STARTUP_V1 retained_argument=%u cold_selection=%d",[NSProcessInfo.processInfo.arguments containsObject:@"linux-steam-retained-frontend"]?1u:0u,coldChoice);
            ideck_native_log_line(selection);
            [self writeNativeHealth];
            self.nativeResourceTimer=[NSTimer timerWithTimeInterval:1.0 target:self selector:@selector(sampleNativeResources) userInfo:nil repeats:YES];
            [NSRunLoop.mainRunLoop addTimer:self.nativeResourceTimer forMode:NSRunLoopCommonModes];
        }
    }
#endif
    return YES;
}
#if IDECK_LAB_NATIVE_LOG
- (void)sampleNativeResources {
    ideck_native_log_resources();
    static unsigned count;if(++count%10==0){ideck_linux_lab_log_tasks();[self writeNativeHealth];}
}
- (void)writeNativeHealth {
    unsigned build=[[NSBundle.mainBundle objectForInfoDictionaryKey:@"CFBundleVersion"] unsignedIntValue];
#if IDECK_LAB_RETAINED_FRONTEND
    /* Legacy stage describes only the original one-shot call. Report the
     * independent retained-owner state explicitly; never reset old stage to
     * pretend the original runtime became reusable. No account/argv payload. */
    struct ideck_frontend_result retained;
    if(!ideck_retained_frontend_snapshot(&retained)){
        char line[200];snprintf(line,sizeof line,"RETAINED_BACKEND_STATE wave=%u phase=%d native_error=%d guest_status=%d",retained.wave,retained.phase,retained.error,retained.guest_status);
        ideck_native_log_line(line);

    }
#endif
 #if IDECK_LAB_WINE_INITIAL_JOIN
    struct ideck_wine_initial_snapshot wine;
    int joinError=ideck_lab_wine_initial_snapshot(&wine);
    if(!joinError){
        char line[320];snprintf(line,sizeof line,"WINE_INITIAL_JOIN_STATE_V1 generation=%llu phase=%u created=%u initial_joined=%u create_error=%d observer_error=%d body_result_source=%u body_exit_code=%u all_Wine_workers_qualified=0",(unsigned long long)wine.generation,wine.phase,wine.initial_created,wine.initial_joined,wine.create_error,wine.observer_error,wine.body_result_source,wine.body_exit_code);
        ideck_native_log_line(line);
        // One bounded session-specific receipt survives the kernel append cap.
        // An observed initial-body exit code is not a child-game completion or
        // proof that Wine workers, signals, storage or rendering are drained.
        NSDictionary *body=@{@"schema":@1,@"pid":@(getpid()),@"build":@(build),
            @"native_log":[NSString stringWithUTF8String:ideck_native_log_name()],
            @"generation":@(wine.generation),@"phase":@(wine.phase),
            @"initial_created":@(wine.initial_created),@"initial_joined":@(wine.initial_joined),
            @"create_error":@(wine.create_error),@"observer_error":@(wine.observer_error),
            @"body_result_source":@(wine.body_result_source),@"body_exit_code":@(wine.body_exit_code),
            @"all_Wine_workers_qualified":@NO,@"game_exit_qualified":@NO};
        NSData *data=[NSJSONSerialization dataWithJSONObject:body options:0 error:nil];
        if(!self.wineInitialReceiptURL||!data||![data writeToURL:self.wineInitialReceiptURL options:NSDataWritingAtomic error:nil])
            ideck_native_log_line("WINE_INITIAL_RECEIPT_WRITE failed=1");
    }
 #endif
    if(ideck_native_health(build,ideck_linux_lab_stage(),ideck_linux_lab_live_guest_threads(),ideck_linux_lab_native_worker_entries()))
        ideck_native_log_line("NATIVE_HEALTH_WRITE failed=1");
}
- (void)applicationDidBecomeActive:(UIApplication *)application {(void)application;ideck_native_log_line("APP_STATE active");ideck_native_log_resources();}
- (void)applicationWillResignActive:(UIApplication *)application {(void)application;ideck_native_log_line("APP_STATE resign_active");ideck_native_log_resources();}
- (void)applicationDidEnterBackground:(UIApplication *)application {(void)application;ideck_native_log_line("APP_STATE background");ideck_native_log_resources();}
- (void)applicationWillEnterForeground:(UIApplication *)application {(void)application;ideck_native_log_line("APP_STATE foreground");ideck_native_log_resources();}
- (void)applicationWillTerminate:(UIApplication *)application {(void)application;ideck_native_log_line("APP_STATE terminate");ideck_native_log_resources();}
- (void)applicationDidReceiveMemoryWarning:(UIApplication *)application {(void)application;ideck_native_log_line("APP_MEMORY_WARNING");ideck_native_log_resources();}
#endif
#if IDECK_LAB_MADEIRA_SETUP
- (void)routeSetupURL:(NSURL *)url {
    if(startupMode<=0&&!self.nativeSetupPresented)return;
    if(self.nativeSetupReady)ideck_lab_madeira_setup_open_url(url.absoluteString.UTF8String);
    else if(self.pendingSetupURLs.count<16)[self.pendingSetupURLs addObject:url];
}
- (void)nativeSetupWillPresent:(NSNotification *)note {
    (void)note;NSAssert(NSThread.isMainThread,@"Native setup callbacks belong to main");
    self.nativeSetupPresented=YES;self.nativeSetupReady=NO;
}
- (void)coldSetupDidAppear:(NSNotification *)note {
    (void)note;if(!self.nativeSetupPresented)return;self.nativeSetupReady=YES;
    NSArray<NSURL *> *pending=[self.pendingSetupURLs copy];[self.pendingSetupURLs removeAllObjects];
    for(NSURL *url in pending)ideck_lab_madeira_setup_open_url(url.absoluteString.UTF8String);
}
- (void)startColdMadeiraSetup {
    UIViewController *placeholder=[UIViewController new];UILabel *label=[[UILabel alloc]initWithFrame:UIScreen.mainScreen.bounds];
    label.text=@"Preparing the isolated Madeira setup. Linux will remain stopped.";label.numberOfLines=0;placeholder.view=label;self.window.rootViewController=placeholder;
    if(strcmp(ideck_linux_lab_stage(),"idle")){label.text=@"Cold setup requires a fresh app process. Existing runtime preserved.";return;}
    dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INITIATED,0),^{
        NSFileManager *fm=NSFileManager.defaultManager;
        NSURL *support=[fm URLsForDirectory:NSApplicationSupportDirectory inDomains:NSUserDomainMask].firstObject;
        NSURL *lab=[support URLByAppendingPathComponent:@"iDeckLinuxLab" isDirectory:YES];
        NSURL *documents=[fm URLsForDirectory:NSDocumentDirectory inDomains:NSUserDomainMask].firstObject;
        NSURL *input=[documents URLByAppendingPathComponent:@"LinuxLabInput/steam-rootfs.tar.gz"];
        NSString *pin=[NSBundle.mainBundle objectForInfoDictionaryKey:@"LinuxLabRootFSSHA256"];
        NSError *error=nil;NSURL *root=LabPrepareSteamRoot(lab,input,pin,&error);
        BOOL ready=NO,created=NO;
        if(root){int shared=ideck_shared_steam_prepare(root.fileSystemRepresentation);if(shared>=0){close(shared);ready=LabBindWindowsLibrary(root,documents,&created,&error);}}
        BOOL idle=!strcmp(ideck_linux_lab_stage(),"idle");
        NSDictionary *state=@{@"mode":@"cold-madeira-setup",@"prefix_bound":@(ready),@"created_library_metadata":@(created),@"linux_stage_idle":@(idle),@"Windows_game_started":@NO};
        [[NSJSONSerialization dataWithJSONObject:state options:0 error:nil]writeToURL:[lab URLByAppendingPathComponent:@"last-cold-setup.json"] options:NSDataWritingAtomic error:nil];
        dispatch_async(dispatch_get_main_queue(),^{
            if(!ready||!idle){label.text=error.localizedDescription?:@"Isolated prefix setup failed. Existing data retained; no runtime started.";return;}
            self.nativeSetupPresented=YES;
            self.window.rootViewController=(__bridge_transfer UIViewController *)ideck_lab_madeira_setup_controller();
            ideck_native_log_line("IDECK_COLD_MADEIRA_SETUP_V1 linux_stage_idle=1 setup_presented=1 user_auth_and_JIT_required=1 game_started=0");
        });
    });
}
#endif
- (void)connectWindowScene:(UIWindowScene *)scene {
#if IDECK_LAB_NATIVE_LOG
    ideck_native_log_line("IDECK_LAB_STARTUP_V1 route=scene_connect");
#endif
    /* Keep the one Linux runtime/controller across scene reconnects. */
    UIViewController *existing = self.window.rootViewController;
    self.window = [[UIWindow alloc] initWithWindowScene:scene];
    if (existing) {
#if IDECK_LAB_NATIVE_LOG
        ideck_native_log_line("IDECK_LAB_STARTUP_V1 route=existing_root");
#endif
        self.window.rootViewController=existing; [self.window makeKeyAndVisible]; return;
    }
    if(self.nativeLogError){
#if IDECK_LAB_NATIVE_LOG
        ideck_native_log_line("IDECK_LAB_STARTUP_V1 route=native_log_refusal");
#endif
        UIViewController *controller=[UIViewController new];UILabel *label=[[UILabel alloc]initWithFrame:UIScreen.mainScreen.bounds];
        label.text=self.nativeLogError;label.numberOfLines=0;controller.view=label;self.window.rootViewController=controller;
        [self.window makeKeyAndVisible];return;
    }
#if IDECK_LAB_MADEIRA_SETUP
    if(startupMode){
#if IDECK_LAB_NATIVE_LOG
        ideck_native_log_line("IDECK_LAB_STARTUP_V1 route=cold_or_conflicting_selection");
#endif
        if(startupMode>0)[self startColdMadeiraSetup];
        else {UIViewController *c=[UIViewController new];UILabel *l=[[UILabel alloc]initWithFrame:UIScreen.mainScreen.bounds];l.text=@"Select one isolated startup mode. No runtime started.";l.numberOfLines=0;c.view=l;self.window.rootViewController=c;}
        [self.window makeKeyAndVisible];return;
    }
#endif
    unsigned steamModes=0;
#if IDECK_LAB_RETAINED_FRONTEND
    /* Joined-provider configuration is a separate explicit experiment. Other
     * modes must not enter its archives without their owning registries. */
    if(![NSProcessInfo.processInfo.arguments containsObject:@"linux-steam-retained-frontend"]){
#if IDECK_LAB_NATIVE_LOG
        ideck_native_log_line("IDECK_LAB_STARTUP_V1 route=missing_retained_argument");
#endif
        UIViewController *error=[UIViewController new];UILabel *label=[[UILabel alloc]initWithFrame:UIScreen.mainScreen.bounds];
        label.text=@"This experimental build requires linux-steam-retained-frontend. No Linux session started.";
        label.textColor=UIColor.labelColor;label.backgroundColor=UIColor.systemBackgroundColor;
        label.numberOfLines=0;error.view=label;self.window.rootViewController=error;[self.window makeKeyAndVisible];return;
    }
#endif
    for(NSString *mode in @[@"linux-steam-desktop",@"linux-steam-install-dependencies",@"linux-steam-compatibility-diagnostics",@"linux-steam-window-trace",@"linux-steam-retained-frontend"])
        if([NSProcessInfo.processInfo.arguments containsObject:mode])steamModes++;
    if (steamModes) {
        BOOL conflict=steamModes!=1;
        for(NSString *argument in @[@"linux-distro-diagnostics",@"linux-packet-pipe-diagnostics",@"linux-tcp-diagnostics"])
            if([NSProcessInfo.processInfo.arguments containsObject:argument])conflict=YES;
        if(conflict) {
            UIViewController *error=[UIViewController new];UILabel *label=[[UILabel alloc]initWithFrame:UIScreen.mainScreen.bounds];
            label.text=@"Select exactly one Linux Lab mode; no guest started.";label.numberOfLines=0;error.view=label;self.window.rootViewController=error;
        } else {
#if IDECK_LAB_NATIVE_LOG
            ideck_native_log_line("IDECK_LAB_STARTUP_V1 route=linux_frontend_selected");
#endif
            self.window.rootViewController=[LinuxSteamViewController new];
        }
        [self.window makeKeyAndVisible];return;
    }
    UIViewController *controller = [UIViewController new];
    controller.view.backgroundColor = UIColor.systemBackgroundColor;
    self.output = [UITextView new];
    self.output.editable = NO;
    self.output.font = [UIFont monospacedSystemFontOfSize:16 weight:UIFontWeightRegular];
    self.output.translatesAutoresizingMaskIntoConstraints = NO;
    BOOL distro = [NSProcessInfo.processInfo.arguments containsObject:@"linux-distro-diagnostics"];
    BOOL tcp = [NSProcessInfo.processInfo.arguments containsObject:@"linux-tcp-diagnostics"];
    BOOL packet = [NSProcessInfo.processInfo.arguments containsObject:@"linux-packet-pipe-diagnostics"];
    self.output.text = tcp ? @"iDeck Linux Lab\nLinux TCP ownership control\nRunning…\n" : packet ? @"iDeck Linux Lab\nLinux packet pipe control\nRunning…\n" : distro ? @"iDeck Linux Lab\nPrepared Debian/glibc control\nRunning…\n" : @"iDeck Linux Lab\nARM64 Linux interpreter control\nRunning…\n";
    [controller.view addSubview:self.output];
    [NSLayoutConstraint activateConstraints:@[
        [self.output.leadingAnchor constraintEqualToAnchor:controller.view.safeAreaLayoutGuide.leadingAnchor constant:16],
        [self.output.trailingAnchor constraintEqualToAnchor:controller.view.safeAreaLayoutGuide.trailingAnchor constant:-16],
        [self.output.topAnchor constraintEqualToAnchor:controller.view.safeAreaLayoutGuide.topAnchor constant:12],
        [self.output.bottomAnchor constraintEqualToAnchor:controller.view.safeAreaLayoutGuide.bottomAnchor constant:-12]]];
    self.window.rootViewController = controller;
    [self.window makeKeyAndVisible];
    dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INITIATED, 0), ^{
        NSFileManager *fm = NSFileManager.defaultManager;
        NSURL *support = [fm URLsForDirectory:NSApplicationSupportDirectory inDomains:NSUserDomainMask].firstObject;
        NSURL *lab = [support URLByAppendingPathComponent:@"iDeckLinuxLab" isDirectory:YES];
        NSURL *root = [lab URLByAppendingPathComponent:distro ? @"DebianRootFS" : tcp ? @"TCPRootFS" : packet ? @"PacketRootFS" : @"LinuxRootFS" isDirectory:YES];
        NSError *error = nil;
        [fm createDirectoryAtURL:lab withIntermediateDirectories:YES attributes:nil error:&error];
        if((int)distro + (int)packet + (int)tcp > 1) error=[NSError errorWithDomain:@"LinuxLab" code:22 userInfo:@{NSLocalizedDescriptionKey:@"Select exactly one diagnostic mode; no guest started."}];
        if (distro && !error) {
            BOOL directory = NO;
            BOOL ready = [fm fileExistsAtPath:[root URLByAppendingPathComponent:@"data"].path isDirectory:&directory] && directory &&
                [fm fileExistsAtPath:[root URLByAppendingPathComponent:@"meta.db"].path];
            if (!ready) error = [NSError errorWithDomain:@"LinuxLab" code:2 userInfo:@{NSLocalizedDescriptionKey:@"Prepared Debian fakefs is missing; no guest started."}];
        }
        if (!distro && !error) [fm createDirectoryAtURL:root withIntermediateDirectories:YES attributes:nil error:&error];
        NSURL *probe = [root URLByAppendingPathComponent:@"probe"];
        NSString *reportName = distro ? @"distro-probe-results.txt" : tcp ? @"tcp-probe-results.txt" : packet ? @"packet-probe-results.txt" : @"probe-results.txt";
        NSURL *reportRoot = distro ? [root URLByAppendingPathComponent:@"data" isDirectory:YES] : root;
        [fm removeItemAtURL:[reportRoot URLByAppendingPathComponent:reportName] error:nil];
        NSData *data = [NSData dataWithContentsOfURL:[NSBundle.mainBundle URLForResource:tcp ? @"tcp-probe" : packet ? @"packet-probe" : @"probe" withExtension:@"elf"]];
        if (!distro && !error && !data) error = [NSError errorWithDomain:@"LinuxLab" code:2 userInfo:nil];
        if (!distro && !error) [data writeToURL:probe options:NSDataWritingAtomic error:&error];
        if (!distro && !error) [fm setAttributes:@{NSFilePosixPermissions:@0700} ofItemAtPath:probe.path error:&error];
        int result = error ? -1 : distro ? ideck_linux_lab_distro_probe(root.fileSystemRepresentation) : ideck_linux_lab_run(root.fileSystemRepresentation);
        NSString *report = [NSString stringWithContentsOfURL:[reportRoot URLByAppendingPathComponent:reportName] encoding:NSUTF8StringEncoding error:nil] ?: @"No current probe result";
        NSString *summary = [NSString stringWithFormat:@"iDeck Linux Lab\nBackend: interpreter (JIT not compiled)\nStage: %s\nResult (errno or guest wait status): %d\n%@\nSteam UI and Madeira handoff are not tested.\n", ideck_linux_lab_stage(), result, error ? error.localizedDescription : report];
        [summary writeToURL:[lab URLByAppendingPathComponent:distro ? @"last-distro-probe.txt" : tcp ? @"last-tcp-probe.txt" : packet ? @"last-packet-probe.txt" : @"last-probe.txt"] atomically:YES encoding:NSUTF8StringEncoding error:nil];
        dispatch_async(dispatch_get_main_queue(), ^{ self.output.text = summary; });
    });
 }
@end

@interface LinuxLabSceneDelegate : UIResponder <UIWindowSceneDelegate>
@end
@implementation LinuxLabSceneDelegate
#if IDECK_LAB_NATIVE_LOG
- (void)sceneDidBecomeActive:(UIScene *)scene {(void)scene;ideck_native_log_line("SCENE_STATE active");ideck_native_log_resources();}
- (void)sceneWillResignActive:(UIScene *)scene {(void)scene;ideck_native_log_line("SCENE_STATE resign_active");ideck_native_log_resources();}
- (void)sceneDidEnterBackground:(UIScene *)scene {(void)scene;ideck_native_log_line("SCENE_STATE background");ideck_native_log_resources();}
- (void)sceneWillEnterForeground:(UIScene *)scene {(void)scene;ideck_native_log_line("SCENE_STATE foreground");ideck_native_log_resources();}
#endif
#if IDECK_LAB_MADEIRA_SETUP
- (void)scene:(UIScene *)scene openURLContexts:(NSSet<UIOpenURLContext *> *)contexts {
    (void)scene;LinuxLabDelegate *owner=(LinuxLabDelegate *)UIApplication.sharedApplication.delegate;
    for(UIOpenURLContext *context in contexts)[owner routeSetupURL:context.URL];
}
#endif
- (void)scene:(UIScene *)scene willConnectToSession:(UISceneSession *)session options:(UISceneConnectionOptions *)options {
    if ([scene isKindOfClass:UIWindowScene.class])
        [(LinuxLabDelegate *)UIApplication.sharedApplication.delegate connectWindowScene:(UIWindowScene *)scene];
#if IDECK_LAB_MADEIRA_SETUP
    for(UIOpenURLContext *context in options.URLContexts)[(LinuxLabDelegate *)UIApplication.sharedApplication.delegate routeSetupURL:context.URL];
#endif
}
@end
int main(int argc, char **argv) {
#if IDECK_LAB_MADEIRA_SETUP
    startupMode=ideck_lab_startup_mode(argc,(const char *const *)argv);
#endif
    @autoreleasepool { return UIApplicationMain(argc, argv, nil, NSStringFromClass(LinuxLabDelegate.class)); }
}
