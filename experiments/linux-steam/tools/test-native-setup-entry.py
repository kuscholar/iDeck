#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Exercise the exact native-entry method with count-only host UI/runtime stubs."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('output', type=Path)
a = p.parse_args()
repo = Path(__file__).resolve().parents[3]
source = repo / 'experiments/linux-steam/app/LinuxSteamViewController.m'
body = source.read_text()
start = body.index('- (void)openNativeMadeiraSetup {')
end = body.index('\n}', start) + 2
method = body[start:end]
restart_start = body.index('- (void)restartRetainedSteam {')
restart_end = body.index('\n}', restart_start) + 2
restart = body[restart_start:restart_end]
out = a.output.resolve()
assert str(out).startswith('/Volumes/easystore/') and not out.exists()
out.mkdir(mode=0o700, parents=True)
fixture = r'''#import <Foundation/Foundation.h>
#include <assert.h>
#include "RetainedFrontend.h"
#include <errno.h>
#define IDECK_LAB_NATIVE_SETUP_TRANSITION 1
#define IDECK_LAB_METAL_DRAIN 1
enum { UIModalPresentationFullScreen = 0, UIControlStateNormal = 0 };
@interface UIViewController:NSObject
@property int modalPresentationStyle;
@property BOOL modalInPresentation;
@end
@implementation UIViewController
@end
@interface FakeView:NSObject
@property(strong) NSObject *window;
@end
@implementation FakeView
@end
@interface FakeButton:NSObject
@property BOOL enabled;
@property(copy) NSString *title;
- (void)setTitle:(NSString *)title forState:(int)state;
@end
@implementation FakeButton
- (void)setTitle:(NSString *)title forState:(int)state {assert(state==UIControlStateNormal);self.title=title;}
@end
static int discards,reopens,connects,discardError;
static BOOL reopenAllowed;
static uint64_t expectedDiscard;
static int ideck_game_file_policy_discard(uint64_t sequence){
    assert(sequence==expectedDiscard);
    discards++;
    return discardError;
}
@interface FakeDisplay:NSObject
- (BOOL)ideckReopenMetal;
@end
@implementation FakeDisplay
- (BOOL)ideckReopenMetal {reopens++;return reopenAllowed;}
@end
static struct ideck_frontend_result result;
static int snapshotError,guestThreads,nativeWorkers,factoryCalls,presents,notices,releases,logs;
static uint64_t pendingSequence;
int ideck_retained_frontend_snapshot(struct ideck_frontend_result *out){*out=result;return snapshotError;}
static int ideck_linux_lab_live_guest_threads(void){return guestThreads;}
static int ideck_linux_lab_native_worker_entries(void){return nativeWorkers;}
static uint64_t ideck_lab_pending_dock_sequence(void){return pendingSequence;}
static void *ideck_lab_madeira_setup_controller(void){factoryCalls++;return (__bridge_retained void *)[UIViewController new];}
static void ideck_native_log_line(const char *line){assert(strstr(line,"game_started=0"));logs++;}
@interface Control:NSObject
@property BOOL nativeSetupTransferred,retainedDisplayDrained,guestEnded,acceptsFrames;
@property uint64_t nativeRequestSequence,unstagedRestartSequence;
@property BOOL retainedBackendReady,frontendRequested;
@property unsigned retainedNextWave;
@property(strong) NSCondition *frontendCommands;
@property(strong) NSURL *retainedRoot;
@property(strong) FakeDisplay *display;
@property(copy) NSString *status;
@property(strong) FakeButton *nativeSetupButton,*restartSteamButton;
@property(strong) UIViewController *presentedViewController;
@property(strong) FakeView *view;
@property(strong) NSObject *client;
@end
@implementation Control
- (void)releaseInput {releases++;}
- (void)showStatus:(NSString *)value {self.status=value;}
- (void)connectRetainedDisplay:(NSURL *)root wave:(unsigned)wave {
    assert(root==self.retainedRoot&&wave==self.retainedNextWave&&self.frontendRequested);
    connects++;
}
- (void)presentViewController:(UIViewController *)controller animated:(BOOL)animated completion:(void (^)(void))completion {
    assert(controller.modalInPresentation&&controller.modalPresentationStyle==UIModalPresentationFullScreen);
    assert(animated&&!completion);self.presentedViewController=controller;presents++;
}
''' + method + '\n' + restart + r'''
@end
static Control *ready(void){
    snapshotError=guestThreads=nativeWorkers=0;pendingSequence=7;
    result=(struct ideck_frontend_result){.guest_status=0,.phase=IDECK_FRONTEND_DORMANT};
    Control *c=[Control new];c.nativeSetupButton=[FakeButton new];c.nativeSetupButton.enabled=YES;
    c.restartSteamButton=[FakeButton new];c.restartSteamButton.enabled=NO;
    c.retainedDisplayDrained=c.guestEnded=YES;c.nativeRequestSequence=7;
    c.view=[FakeView new];c.view.window=[NSObject new];return c;
}
static Control *readyRestart(void){
    Control *c=ready();
    pendingSequence=0;discardError=0;reopenAllowed=YES;discards=reopens=connects=0;
    c.nativeRequestSequence=0;c.nativeSetupButton.enabled=NO;
    c.restartSteamButton.enabled=YES;c.retainedBackendReady=YES;c.retainedNextWave=1;
    c.frontendCommands=[NSCondition new];c.display=[FakeDisplay new];
    c.retainedRoot=[NSURL fileURLWithPath:@"/fixture"];
    return c;
}
static void restartCases(void){
    for(int test=0;test<4;test++){
        Control *c=readyRestart();c.unstagedRestartSequence=expectedDiscard=71;
        if(test==0)c.retainedDisplayDrained=NO;
        if(test==1)pendingSequence=72;
        if(test==2)c.nativeSetupTransferred=YES;
        if(test==3)c.restartSteamButton.enabled=NO;
        [c restartRetainedSteam];
        assert(!discards&&!reopens&&!connects&&c.unstagedRestartSequence==71&&!c.frontendRequested);
    }
    Control *c=readyRestart();c.unstagedRestartSequence=expectedDiscard=71;discardError=-ESTALE;
    [c restartRetainedSteam];
    assert(discards==1&&!reopens&&!connects&&c.unstagedRestartSequence==71&&!c.frontendRequested&&c.status.length);
    c=readyRestart();c.unstagedRestartSequence=expectedDiscard=71;reopenAllowed=NO;
    [c restartRetainedSteam];
    assert(discards==1&&reopens==1&&!connects&&!c.unstagedRestartSequence&&!c.frontendRequested);
    c=readyRestart();c.unstagedRestartSequence=expectedDiscard=71;
    [c restartRetainedSteam];
    assert(discards==1&&reopens==1&&connects==1&&!c.unstagedRestartSequence&&c.frontendRequested);
    assert(c.retainedNextWave==2&&!c.retainedBackendReady&&!c.guestEnded&&!c.restartSteamButton.enabled&&c.acceptsFrames);
    [c restartRetainedSteam];
    assert(discards==1&&connects==1);
    c=readyRestart();[c restartRetainedSteam];
    assert(!discards&&reopens==1&&connects==1&&c.frontendRequested);
}
int main(void){@autoreleasepool{
id observer=[NSNotificationCenter.defaultCenter addObserverForName:@"IDeckLinuxMadeiraSetupWillPresent" object:nil queue:nil usingBlock:^(NSNotification *note){(void)note;notices++;}];
for(int variant=0;variant<18;variant++){
    Control *c=ready();
    switch(variant){
    case 0:c.nativeSetupTransferred=YES;break;
    case 1:c.nativeSetupButton.enabled=NO;break;
    case 2:c.presentedViewController=[UIViewController new];break;
    case 3:c.view.window=nil;break;
    case 4:c.retainedDisplayDrained=NO;break;
    case 5:c.guestEnded=NO;break;
    case 6:c.client=[NSObject new];break;
    case 7:c.acceptsFrames=YES;break;
    case 8:snapshotError=-5;break;
    case 9:result.error=-5;break;
    case 10:result.guest_status=42<<8;break;
    case 11:result.phase=IDECK_FRONTEND_RUNNING;break;
    case 12:guestThreads=1;break;
    case 13:guestThreads=-95;break;
    case 14:nativeWorkers=1;break;
    case 15:nativeWorkers=-95;break;
    case 16:c.nativeRequestSequence=0;break;
    case 17:pendingSequence=8;break;
    }
    [c openNativeMadeiraSetup];assert(!factoryCalls&&!presents&&!notices&&!releases&&!logs);
}
Control *c=ready();[c openNativeMadeiraSetup];
assert(factoryCalls==1&&presents==1&&notices==1&&releases==1&&logs==1);
assert(c.nativeSetupTransferred&&!c.nativeSetupButton.enabled&&!c.restartSteamButton.enabled);
[c openNativeMadeiraSetup];assert(factoryCalls==1&&presents==1&&notices==1&&releases==1&&logs==1);
[NSNotificationCenter.defaultCenter removeObserver:observer];
restartCases();
puts("HOST exact native setup entry:18 refusal cases, single presentation, and unstaged restart policy PASS; UI/runtime dependencies are count-only stubs");
return 0;}}
'''
(out / 'control.m').write_text(fixture)
cmd = ['xcrun', 'clang', '-fobjc-arc', '-fblocks', '-fsanitize=address,undefined',
       '-Wall', '-Wextra', '-Werror', '-I', str(source.parent), str(out / 'control.m'),
       '-framework', 'Foundation', '-o', str(out / 'control')]
subprocess.run(cmd, check=True)
with (out / 'control.log').open('x') as log:
    r = subprocess.run([out / 'control'], stdout=log, stderr=subprocess.STDOUT, timeout=20)
assert not r.returncode
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
(out / 'evidence.json').write_text(json.dumps({
    'scope': 'HOST exact native entry method, count-only UI/runtime stubs; NOT UIKit/device/thread-drain/Wine handoff proof',
    'command': cmd, 'exit': r.returncode, 'refusal_cases': 18,
    'actual_frontend_sha256': sha(source),
    'extracted_method_sha256': hashlib.sha256(method.encode()).hexdigest(),
    'extracted_restart_method_sha256': hashlib.sha256(restart.encode()).hexdigest(),
    'fixture_sha256': sha(out / 'control.m'), 'log_sha256': sha(out / 'control.log'),
}, indent=2) + '\n')
print((out / 'control.log').read_text())
