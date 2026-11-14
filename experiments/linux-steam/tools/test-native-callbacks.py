#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Execute exact native callback methods with a count-only downstream stub."""
import argparse,hashlib,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);a=p.parse_args()
repo=Path(__file__).resolve().parents[3];source=repo/'experiments/linux-steam/app/main.m';body=source.read_text();out=a.output.resolve()
assert str(out).startswith('/Volumes/easystore/') and not out.exists();out.mkdir(mode=0o700,parents=True)
def method(signature):
 start=body.index(signature+' {');end=body.index('\n}',start)+2;return body[start:end]
methods='\n'.join(method(s) for s in ['- (void)routeSetupURL:(NSURL *)url','- (void)nativeSetupWillPresent:(NSNotification *)note','- (void)coldSetupDidAppear:(NSNotification *)note'])
fixture='''#import <Foundation/Foundation.h>
#include <assert.h>
static int startupMode,seen;
static void ideck_lab_madeira_setup_open_url(const char *bytes){assert(bytes && strlen(bytes)>0);seen++;}
@interface Control:NSObject
@property BOOL nativeSetupPresented;
@property BOOL nativeSetupReady;
@property(strong) NSMutableArray<NSURL *> *pendingSetupURLs;
@end
@implementation Control
'''+methods+'''
@end
int main(void){@autoreleasepool{
Control *c=[Control new];c.pendingSetupURLs=[NSMutableArray new];NSURL *url=[NSURL URLWithString:@"ideck-linux-lab://jit-ready/fixture"];
[c routeSetupURL:url];assert(seen==0&&c.pendingSetupURLs.count==0);
[c nativeSetupWillPresent:nil];assert(c.nativeSetupPresented&&!c.nativeSetupReady);
for(int i=0;i<17;i++)[c routeSetupURL:url];assert(seen==0&&c.pendingSetupURLs.count==16);
[c coldSetupDidAppear:nil];assert(c.nativeSetupReady&&seen==16&&c.pendingSetupURLs.count==0);
[c routeSetupURL:url];assert(seen==17);
Control *cold=[Control new];cold.pendingSetupURLs=[NSMutableArray new];startupMode=1;
[cold routeSetupURL:url];assert(seen==17&&cold.pendingSetupURLs.count==1);
cold.nativeSetupPresented=YES;[cold coldSetupDidAppear:nil];assert(seen==18);
puts("HOST exact native callback methods: ignore/bounded16/wait/ready flush/cold route PASS; no real JIT/login service invoked");
return 0;}}
'''
(out/'control.m').write_text(fixture)
cmd=['xcrun','clang','-fobjc-arc','-fblocks','-fsanitize=address,undefined','-Wall','-Wextra','-Werror',str(out/'control.m'),'-framework','Foundation','-o',str(out/'control')]
subprocess.run(cmd,check=True)
with (out/'control.log').open('x') as log:r=subprocess.run([out/'control'],stdout=log,stderr=subprocess.STDOUT,timeout=20)
assert not r.returncode
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(out/'evidence.json').write_text(json.dumps({'scope':'HOST exact delegate methods Foundation execution, count-only downstream stub; NOT UIKit lifecycle/device/JIT/auth success','command':cmd,'exit':r.returncode,'actual_delegate_sha256':sha(source),'extracted_methods_sha256':hashlib.sha256(methods.encode()).hexdigest(),'fixture_sha256':sha(out/'control.m'),'log_sha256':sha(out/'control.log')},indent=2)+'\n')
print((out/'control.log').read_text())
