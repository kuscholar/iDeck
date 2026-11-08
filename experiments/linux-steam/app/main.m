/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#import <UIKit/UIKit.h>
#import "LinuxLabRuntime.h"

@interface LinuxLabDelegate : UIResponder <UIApplicationDelegate>
@property(nonatomic, strong) UIWindow *window;
@property(nonatomic, strong) UITextView *output;
@end
@implementation LinuxLabDelegate
- (BOOL)application:(UIApplication *)application didFinishLaunchingWithOptions:(NSDictionary *)options {
    self.window = [[UIWindow alloc] initWithFrame:UIScreen.mainScreen.bounds];
    UIViewController *controller = [UIViewController new];
    controller.view.backgroundColor = UIColor.systemBackgroundColor;
    self.output = [UITextView new];
    self.output.editable = NO;
    self.output.font = [UIFont monospacedSystemFontOfSize:16 weight:UIFontWeightRegular];
    self.output.translatesAutoresizingMaskIntoConstraints = NO;
    self.output.text = @"iDeck Linux Lab\nARM64 Linux interpreter control\nRunning…\n";
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
        NSURL *root = [lab URLByAppendingPathComponent:@"LinuxRootFS" isDirectory:YES];
        NSError *error = nil;
        [fm createDirectoryAtURL:root withIntermediateDirectories:YES attributes:nil error:&error];
        NSURL *probe = [root URLByAppendingPathComponent:@"probe"];
        [fm removeItemAtURL:[root URLByAppendingPathComponent:@"probe-results.txt"] error:nil];
        NSData *data = [NSData dataWithContentsOfURL:[NSBundle.mainBundle URLForResource:@"probe" withExtension:@"elf"]];
        if (!error && !data) error = [NSError errorWithDomain:@"LinuxLab" code:2 userInfo:nil];
        if (!error) [data writeToURL:probe options:NSDataWritingAtomic error:&error];
        if (!error) [fm setAttributes:@{NSFilePosixPermissions:@0700} ofItemAtPath:probe.path error:&error];
        int result = error ? -1 : ideck_linux_lab_run(root.fileSystemRepresentation);
        NSString *report = [NSString stringWithContentsOfURL:[root URLByAppendingPathComponent:@"probe-results.txt"] encoding:NSUTF8StringEncoding error:nil] ?: @"No current probe result";
        NSString *summary = [NSString stringWithFormat:@"iDeck Linux Lab\nBackend: interpreter (JIT not compiled)\nStage: %s\nResult (errno or guest wait status): %d\n%@\nSteam UI and Madeira handoff are not tested.\n", ideck_linux_lab_stage(), result, error ? @"Host preparation failed" : report];
        [summary writeToURL:[lab URLByAppendingPathComponent:@"last-probe.txt"] atomically:YES encoding:NSUTF8StringEncoding error:nil];
        dispatch_async(dispatch_get_main_queue(), ^{ self.output.text = summary; });
    });
    return YES;
}
@end
int main(int argc, char **argv) {
    @autoreleasepool { return UIApplicationMain(argc, argv, nil, NSStringFromClass(LinuxLabDelegate.class)); }
}
