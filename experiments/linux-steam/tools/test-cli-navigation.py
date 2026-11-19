#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Execute the exact Lab navigation admission method with count-only UI/RFB stubs."""
import argparse,hashlib,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);a=p.parse_args()
repo=Path(__file__).resolve().parents[3];source=repo/'experiments/linux-steam/app/LinuxSteamViewController.m';text=source.read_text()
start=text.index('- (void)dispatchCLINavigation:(NSUInteger)action {');end=text.index('\n}',start)+2;method=text[start:end]
out=a.output.resolve();assert str(out).startswith('/Volumes/easystore/') and not out.exists();out.mkdir(mode=0o700,parents=True)
fixture=r'''#import <Foundation/Foundation.h>
#import <CoreGraphics/CoreGraphics.h>
#include <assert.h>
#include <math.h>
#include <stdint.h>
enum {UIApplicationStateActive=0};
@interface UIApplication:NSObject
@property int applicationState;
+ (UIApplication *)sharedApplication;
@end
@implementation UIApplication
+ (UIApplication *)sharedApplication {static UIApplication *app; if(!app)app=[UIApplication new];return app;}
@end
@interface FakeView:NSObject
@property(strong) NSObject *window;
@end
@implementation FakeView
@end
@interface Input:NSObject
@property CGSize pixels;
@property CGPoint lastPixel;
@property(strong) NSObject *activeTouch;
@property(getter=isFirstResponder) BOOL firstResponder;
@end
@implementation Input
@end
static unsigned pointerEvents,keyEvents,downs,logs;
static uint16_t lastX,lastY,xs[3],ys[3];static uint8_t masks[3];
@interface Client:NSObject
@end
@implementation Client
- (void)pointerX:(uint16_t)x y:(uint16_t)y buttons:(uint8_t)buttons {assert(x<1600&&y<1000);lastX=x;lastY=y;assert(pointerEvents<3);xs[pointerEvents]=x;ys[pointerEvents]=y;masks[pointerEvents++]=buttons;downs+=buttons==1;}
- (void)key:(uint32_t)key down:(BOOL)down {assert(key>=0xff00&&key<=0xffff);keyEvents++;downs+=down;}
@end
static void ideck_native_log_line(const char *line){assert(strstr(line,"physical_touch_test=0"));logs++;}
static int ideck_native_note_navigation(unsigned action){assert(action<10);return 0;}
@interface Control:NSObject
@property(strong) FakeView *view;
@property(strong) Input *input;
@property(strong) Client *client;
@property BOOL guestEnded,acceptsFrames;
@property NSTimeInterval cliInputLastEvent;
@end
@implementation Control
'''+method+r'''
@end
static Control *ready(void){
 UIApplication.sharedApplication.applicationState=UIApplicationStateActive;
 pointerEvents=keyEvents=downs=logs=0;
 Control *c=[Control new];c.view=[FakeView new];c.view.window=[NSObject new];
 c.input=[Input new];c.input.pixels=CGSizeMake(1600,1000);c.input.lastPixel=CGPointMake(799,499);c.client=[Client new];c.acceptsFrames=YES;return c;
}
int main(void){@autoreleasepool{
for(unsigned variant=0;variant<17;variant++){
 Control *c=ready();NSUInteger action=0;
 switch(variant){
 case 0:action=10;break;
 case 1:action=NSUIntegerMax;break;
 case 2:c.view.window=nil;break;
 case 3:UIApplication.sharedApplication.applicationState=1;break;
 case 4:c.guestEnded=YES;break;
 case 5:c.acceptsFrames=NO;break;
 case 6:c.client=nil;break;
 case 7:c.input.activeTouch=[NSObject new];break;
 case 8:c.input.firstResponder=YES;break;
 case 9:c.input.pixels=CGSizeMake(0,1000);break;
 case 10:c.input.pixels=CGSizeMake(1600,0);break;
 case 11:c.input.pixels=CGSizeMake(NAN,1000);break;
 case 12:c.input.pixels=CGSizeMake(1600,INFINITY);break;
 case 13:c.input.pixels=CGSizeMake(65536,1000);break;
 case 14:c.input.pixels=CGSizeMake(1600,65536);break;
 case 15:c.input.pixels=CGSizeMake(-1,1000);break;
 case 16:c.cliInputLastEvent=NSProcessInfo.processInfo.systemUptime;break;
 }
 [c dispatchCLINavigation:action];assert(!pointerEvents&&!keyEvents&&!downs&&!logs);
}
for(NSUInteger action=0;action<10;action++){
 Control *c=ready();[c dispatchCLINavigation:action];
 assert(logs==1&&downs==1);
 if(action==9){assert(pointerEvents==3&&!keyEvents&&lastX==799&&lastY==499);assert(masks[0]==0&&masks[1]==1&&masks[2]==0);assert(xs[0]!=xs[1]&&xs[1]==xs[2]&&ys[0]==499&&ys[1]==499&&ys[2]==499);assert(abs((int)xs[0]-(int)xs[1])<=8);}
 else assert(action<2?(pointerEvents==2&&!keyEvents):(keyEvents==2&&!pointerEvents));
 [c dispatchCLINavigation:action];assert(logs==1&&downs==1); /* Immediate flood refused. */
}
/* Wake must move even when the prior cursor already ended at center. */
const unsigned widths[]={2,3,16,1600};
for(unsigned n=0;n<sizeof widths/sizeof widths[0];n++){
 Control *c=ready();unsigned width=widths[n];c.input.pixels=CGSizeMake(width,2);
 c.input.lastPixel=CGPointMake((width-1)/2,0);
 for(unsigned repeat=0;repeat<2;repeat++){
  pointerEvents=keyEvents=downs=logs=0;c.cliInputLastEvent=0;
  [c dispatchCLINavigation:9];
  assert(pointerEvents==3&&!keyEvents&&downs==1&&logs==1);
  assert(xs[0]<width&&xs[1]<width&&xs[2]<width&&xs[0]!=xs[1]&&xs[1]==xs[2]);
  assert(lastX==(width-1)/2&&lastY==0&&c.input.lastPixel.x==lastX&&c.input.lastPixel.y==lastY);
  assert(masks[0]==0&&masks[1]==1&&masks[2]==0);
 }
}
Control *narrow=ready();narrow.input.pixels=CGSizeMake(1,1000);[narrow dispatchCLINavigation:9];
assert(!pointerEvents&&!keyEvents&&!downs&&!logs);
puts("HOST exact CLI navigation admission:17 negative cases,10 paired events,throttle,8 repeated-center movement cases,1 narrow-frame refusal PASS; count-only UI/RFB stubs, NOT physical input proof");return 0;}}
'''
(out/'control.m').write_text(fixture)
cmd=['xcrun','clang','-fobjc-arc','-fsanitize=address,undefined','-Wall','-Wextra','-Werror',str(out/'control.m'),'-framework','Foundation','-framework','CoreGraphics','-o',str(out/'control')]
subprocess.run(cmd,check=True)
with (out/'control.log').open('x') as log:r=subprocess.run([out/'control'],stdout=log,stderr=subprocess.STDOUT,timeout=20)
assert not r.returncode
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(out/'evidence.json').write_text(json.dumps({'scope':'HOST exact admission method with count-only UI/RFB stubs; NOT Darwin delivery/physical input/Steam UI proof','exit':r.returncode,'command':cmd,'negative_cases':17,'paired_actions':10,'repeated_center_movement_cases':8,'wake_narrow_frame_refusals':1,'frontend_source_sha256':sha(source),'extracted_method_sha256':hashlib.sha256(method.encode()).hexdigest(),'fixture_sha256':sha(out/'control.m'),'log_sha256':sha(out/'control.log')},indent=2)+'\n')
print((out/'control.log').read_text())
