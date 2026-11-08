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
    BOOL distro = [NSProcessInfo.processInfo.arguments containsObject:@"linux-distro-diagnostics"];
    self.output.text = distro ? @"iDeck Linux Lab\nPrepared Debian/glibc control\nRunning…\n" : @"iDeck Linux Lab\nARM64 Linux interpreter control\nRunning…\n";
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
        NSURL *root = [lab URLByAppendingPathComponent:distro ? @"DebianRootFS" : @"LinuxRootFS" isDirectory:YES];
        NSError *error = nil;
        [fm createDirectoryAtURL:lab withIntermediateDirectories:YES attributes:nil error:&error];
        if (distro && !error) {
            BOOL directory = NO;
            BOOL ready = [fm fileExistsAtPath:[root URLByAppendingPathComponent:@"data"].path isDirectory:&directory] && directory &&
                [fm fileExistsAtPath:[root URLByAppendingPathComponent:@"meta.db"].path];
            if (!ready) error = [NSError errorWithDomain:@"LinuxLab" code:2 userInfo:@{NSLocalizedDescriptionKey:@"Prepared Debian fakefs is missing; no guest started."}];
        }
        if (!distro && !error) [fm createDirectoryAtURL:root withIntermediateDirectories:YES attributes:nil error:&error];
        NSURL *probe = [root URLByAppendingPathComponent:@"probe"];
        NSString *reportName = distro ? @"distro-probe-results.txt" : @"probe-results.txt";
        NSURL *reportRoot = distro ? [root URLByAppendingPathComponent:@"data" isDirectory:YES] : root;
        [fm removeItemAtURL:[reportRoot URLByAppendingPathComponent:reportName] error:nil];
        NSData *data = [NSData dataWithContentsOfURL:[NSBundle.mainBundle URLForResource:@"probe" withExtension:@"elf"]];
        if (!distro && !error && !data) error = [NSError errorWithDomain:@"LinuxLab" code:2 userInfo:nil];
        if (!distro && !error) [data writeToURL:probe options:NSDataWritingAtomic error:&error];
        if (!distro && !error) [fm setAttributes:@{NSFilePosixPermissions:@0700} ofItemAtPath:probe.path error:&error];
        int result = error ? -1 : distro ? ideck_linux_lab_distro_probe(root.fileSystemRepresentation) : ideck_linux_lab_run(root.fileSystemRepresentation);
        NSString *report = [NSString stringWithContentsOfURL:[reportRoot URLByAppendingPathComponent:reportName] encoding:NSUTF8StringEncoding error:nil] ?: @"No current probe result";
        NSString *summary = [NSString stringWithFormat:@"iDeck Linux Lab\nBackend: interpreter (JIT not compiled)\nStage: %s\nResult (errno or guest wait status): %d\n%@\nSteam UI and Madeira handoff are not tested.\n", ideck_linux_lab_stage(), result, error ? error.localizedDescription : report];
        [summary writeToURL:[lab URLByAppendingPathComponent:distro ? @"last-distro-probe.txt" : @"last-probe.txt"] atomically:YES encoding:NSUTF8StringEncoding error:nil];
        dispatch_async(dispatch_get_main_queue(), ^{ self.output.text = summary; });
    });
    return YES;
}
@end
int main(int argc, char **argv) {
    @autoreleasepool { return UIApplicationMain(argc, argv, nil, NSStringFromClass(LinuxLabDelegate.class)); }
}
