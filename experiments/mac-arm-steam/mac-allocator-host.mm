// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
// UIKit host loads our macOS-compiled, metadata-retargeted allocator bundle.
#import <UIKit/UIKit.h>
#include <dlfcn.h>
#include <cstdio>
#include "mac-compact-allocator.h"
@interface IDeckMacAllocatorScene : UIResponder <UIWindowSceneDelegate>
@property(strong,nonatomic) UIWindow* window;
@end
static NSString* status;
static __weak UILabel* activeLabel;
@implementation IDeckMacAllocatorScene
- (void)scene:(UIScene*)scene willConnectToSession:(UISceneSession*)session options:(UISceneConnectionOptions*)options {
    (void)session;(void)options;
    if(![scene isKindOfClass:UIWindowScene.class])return;
    self.window=[[UIWindow alloc]initWithWindowScene:(UIWindowScene*)scene];
    UIViewController* controller=[UIViewController new];controller.view.backgroundColor=UIColor.systemBackgroundColor;
    UILabel* label=[[UILabel alloc]initWithFrame:controller.view.bounds];label.numberOfLines=0;
    label.textAlignment=NSTextAlignmentCenter;label.autoresizingMask=UIViewAutoresizingFlexibleWidth|UIViewAutoresizingFlexibleHeight;
    activeLabel=label;label.text=status?:@"Testing macOS-compiled allocator…\nSteam and CEF are not running";
    [controller.view addSubview:label];self.window.rootViewController=controller;[self.window makeKeyAndVisible];
    static dispatch_once_t once;
    dispatch_once(&once,^{dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INITIATED,0),^{
        NSString* path=[NSBundle.mainBundle.bundlePath stringByAppendingPathComponent:@"MacCompactAllocator.bundle"];
        fprintf(stderr,"[ideck-mac-pa-host] load=begin build=%ld\n",(long)[NSBundle.mainBundle.infoDictionary[@"CFBundleVersion"] integerValue]);
        void* library=dlopen(path.fileSystemRepresentation,RTLD_NOW|RTLD_LOCAL);
        typedef int(*Run)(IDeckMacAllocatorResult*,uint64_t);
        Run run=library?(Run)dlsym(library,"IDeckRunMacAllocator"):nullptr;
        IDeckMacAllocatorResult result={};int code=run?run(&result,sizeof result):4;
        NSNumber* expected=NSBundle.mainBundle.infoDictionary[@"IDeckMacAllocatorGlued"];
        BOOL pass=code==0 && result.abi==2 && result.compiled_mac==1 && result.allocations==398 && result.frees==398 && result.failures==0 && result.pool_bytes==(256u<<20) && result.disjoint && result.cleaned && result.glued==expected.unsignedLongLongValue;
        fprintf(stderr,"[ideck-mac-pa-host] loaded=%d entry=%d pass=%d code=%d error-text=REDACTED cef-integrated=0\n",library!=nullptr,run!=nullptr,pass,code);
        dispatch_async(dispatch_get_main_queue(),^{
            status=pass?[NSString stringWithFormat:@"Mac allocator PASS\nmacOS ARM64 → iPad\n398 allocations / frees\n2 × 256 MiB pools (glued: %@)\nCEF and Steam NOT tested",result.glued?@"yes":@"no"]:@"Mac allocator FAILED\nSee private device evidence\nCEF and Steam NOT tested";
            activeLabel.text=status;
        });
    });});
}
@end
@interface IDeckMacAllocatorApp : UIResponder <UIApplicationDelegate>
@end
@implementation IDeckMacAllocatorApp
- (UISceneConfiguration*)application:(UIApplication*)app configurationForConnectingSceneSession:(UISceneSession*)session options:(UISceneConnectionOptions*)options {
    (void)app;(void)options;
    UISceneConfiguration* configuration=[[UISceneConfiguration alloc]initWithName:@"Mac allocator" sessionRole:session.role];
    configuration.delegateClass=IDeckMacAllocatorScene.class;return configuration;
}
@end
int main(int argc,char** argv){@autoreleasepool{return UIApplicationMain(argc,argv,nil,NSStringFromClass(IDeckMacAllocatorApp.class));}}
