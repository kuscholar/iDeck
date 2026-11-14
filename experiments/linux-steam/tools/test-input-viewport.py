#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Reproduce baseline Air tap displacement and execute actual fixed touch mapping."""
import argparse,hashlib,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);a=p.parse_args()
repo=Path(__file__).resolve().parents[3];source=repo/'experiments/linux-steam/app/LinuxSteamViewController.m';current=source.read_text()
baseline_commit='be0de64e1e3ce9a2db41b9150418c675000f07e0'
before=subprocess.check_output(['git','show',baseline_commit+':experiments/linux-steam/app/LinuxSteamViewController.m'],cwd=repo,text=True)
def methods(text):
 result=[]
 for name in ['- (CGRect)guestRect','- (void)sendTouch:(UITouch *)touch buttons:(uint8_t)buttons']:
  start=text.index(name+' {');end=text.index('\n}',start)+2;result.append(text[start:end])
 return '\n'.join(result)
old,new=methods(before),methods(current)
renderer=repo/'vendor/LinuxRunner/app/LinuxRunner/MetalFramebufferView.m';pipeline=repo/'vendor/LinuxRunner/app/LinuxRunner/FramebufferMetalPipeline.h'
assert 'setViewport' not in renderer.read_text()
assert 'float2(-1,1),float2(-1,-1),float2(1,1),float2(1,-1)' in pipeline.read_text()
assert 'float2(0,0),float2(0,1),float2(1,0),float2(1,1)' in pipeline.read_text()
out=a.output.resolve();assert str(out).startswith('/Volumes/easystore/') and not out.exists();out.mkdir(mode=0o700,parents=True)
fixture=r'''#import <Foundation/Foundation.h>
#import <CoreGraphics/CoreGraphics.h>
#include <assert.h>
#include <math.h>
#include <stdint.h>
static unsigned seen;static uint16_t outputX,outputY;
@interface Client:NSObject
@end
@implementation Client
- (void)pointerX:(uint16_t)x y:(uint16_t)y buttons:(uint8_t)buttons {assert(buttons==1);outputX=x;outputY=y;seen++;}
@end
@interface UITouch:NSObject
@property CGPoint point;
@end
@implementation UITouch
- (CGPoint)locationInView:(id)view {(void)view;return self.point;}
@end
@interface Before:NSObject
@property CGRect bounds;
@property CGSize pixels;
@property CGPoint lastPixel;
@property(strong) Client *client;
@end
@implementation Before
'''+old+r'''
@end
@interface Actual:Before
@end
@implementation Actual
'''+new+r'''
@end
int main(void){@autoreleasepool{
Before *old=[Before new];old.bounds=CGRectMake(0,0,1180,820);old.pixels=CGSizeMake(1280,800);old.client=[Client new];
UITouch *touch=[UITouch new];touch.point=CGPointMake(1180*.145,820*.058);
[old sendTouch:touch buttons:1];unsigned beforeY=outputY;assert(abs((int)beforeY-46)>20);
Actual *actual=[Actual new];actual.bounds=old.bounds;actual.pixels=old.pixels;actual.client=[Client new];
[actual sendTouch:touch buttons:1];unsigned afterY=outputY;assert(abs((int)afterY-46)<=1);
CGSize views[]={CGSizeMake(1180,820),CGSizeMake(820,1180),CGSizeMake(1280,800)};
unsigned points=0;
for(unsigned v=0;v<3;v++)for(unsigned x=0;x<=8;x++)for(unsigned y=0;y<=8;y++){
 actual.bounds=CGRectMake(5,7,views[v].width,views[v].height);
 touch.point=CGPointMake(5+views[v].width*x/8.,7+views[v].height*y/8.);seen=0;
 [actual sendTouch:touch buttons:1];assert(seen==1);
 unsigned expectedX=MIN(1279,(unsigned)(1280*x/8.)),expectedY=MIN(799,(unsigned)(800*y/8.));
 assert(abs((int)outputX-(int)expectedX)<=1&&abs((int)outputY-(int)expectedY)<=1);points++;
}
actual.pixels=CGSizeMake(NAN,800);seen=0;[actual sendTouch:touch buttons:1];assert(!seen);
actual.pixels=CGSizeMake(1280,INFINITY);[actual sendTouch:touch buttons:1];assert(!seen);
printf("HOST baseline Air Library y=%u vs full-drawable expected46; fixed y=%u; %u mapped points and nonfinite refusal PASS; RFB sink stubbed, NOT physical input proof\n",beforeY,afterY,points);
return 0;}}
'''
(out/'control.m').write_text(fixture)
cmd=['xcrun','clang','-fobjc-arc','-fsanitize=address,undefined','-Wall','-Wextra','-Werror',str(out/'control.m'),'-framework','Foundation','-framework','CoreGraphics','-o',str(out/'control')]
subprocess.run(cmd,check=True)
with (out/'control.log').open('x') as log:r=subprocess.run([out/'control'],stdout=log,stderr=subprocess.STDOUT,timeout=20)
assert not r.returncode
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(out/'evidence.json').write_text(json.dumps({'scope':'HOST exact baseline/current touch methods and inspected actual full-quad shader; stubbed touch/RFB sink, NOT physical touch/device result','exit':r.returncode,'command':cmd,'baseline_commit':baseline_commit,'baseline_methods_sha256':hashlib.sha256(old.encode()).hexdigest(),'actual_methods_sha256':hashlib.sha256(new.encode()).hexdigest(),'frontend_sha256':sha(source),'renderer_sha256':sha(renderer),'pipeline_sha256':sha(pipeline),'mapped_points':243,'log_sha256':sha(out/'control.log')},indent=2)+'\n')
print((out/'control.log').read_text())
