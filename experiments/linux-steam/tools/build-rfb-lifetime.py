#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Generate opt-in pinned RFB completion boundary; never modify upstream.

Keep decoder and input admission under one recursive native lock, track actual
GCD block lifetimes including their autorelease pools, then notify main after
all blocks return. Foreign queued callbacks remain the controller's responsibility.
"""
import argparse,hashlib,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);a=p.parse_args()
repo=Path(__file__).resolve().parents[3];src=repo/'vendor/LinuxRunner';pin='d1419782da2e299fe22f1ddb85c70ae3d1e276b1'
assert subprocess.check_output(['git','-C',str(src),'rev-parse','HEAD'],text=True).strip()==pin
assert not subprocess.check_output(['git','-C',str(src),'status','--porcelain','--untracked-files=no'],text=True).strip()
relative='app/LinuxRunner/RFBClient.m';original=subprocess.check_output(['git','-C',str(src),'show',pin+':'+relative]);assert (src/relative).read_bytes()==original
out=a.output.resolve();assert str(out).startswith('/Volumes/easystore/') and not out.exists();out.mkdir(parents=True)
body=original.decode()
def replace(old,new):
 global body
 assert body.count(old)==1,(old,body.count(old));body=body.replace(old,new)
replace('@implementation LRRFBClient {','@implementation LRRFBClient {\n    NSRecursiveLock *_ideckAdmission;\n    dispatch_group_t _ideckTasks;\n    BOOL _ideckClosing;')
replace('_password=[password copy];_socket=-1;','_password=[password copy];_socket=-1;\n        _ideckAdmission=[NSRecursiveLock new];_ideckTasks=dispatch_group_create();')
replace('- (void)start {','''- (void)start {
    [_ideckAdmission lock];
    if(!_ideckClosing)[self ideckStartOriginal];
    [_ideckAdmission unlock];
}
- (void)ideckStartOriginal {''')
replace('dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INITIATED,0),','dispatch_group_async(_ideckTasks,dispatch_get_global_queue(QOS_CLASS_USER_INITIATED,0),')
replace('- (void)stop {','''- (void)stop {
    [_ideckAdmission lock];_ideckClosing=YES;[self ideckStopOriginal];[_ideckAdmission unlock];
}
- (void)ideckStopWithCompletion:(dispatch_block_t)completion {
    [self stop];
    dispatch_group_notify(_ideckTasks,dispatch_get_main_queue(),^{
        /* Retain self through completion, after all tracked blocks leave. */
        (void)self; if(completion)completion();
    });
}
- (void)ideckStopOriginal {''')
replace('- (void)enqueue:(NSData *)data keySymbols:(BOOL)keySymbols motion:(BOOL)motion {','''- (void)enqueue:(NSData *)data keySymbols:(BOOL)keySymbols motion:(BOOL)motion {
    [_ideckAdmission lock];
    if(!_ideckClosing)[self ideckEnqueue:data keySymbols:keySymbols motion:motion];
    [_ideckAdmission unlock];
}
- (void)ideckEnqueue:(NSData *)data keySymbols:(BOOL)keySymbols motion:(BOOL)motion {''')
replace('dispatch_async(_inputQueue,','dispatch_group_async(_ideckTasks,_inputQueue,')
body='/* Pinned GPL LinuxRunner source, notices retained; own opt-in completion additions. */\n'+body
target=out/'LabRFBJoined.generated.inc';target.write_text(body)
(out/'evidence.json').write_text(json.dumps(dict(scope='Generated copied RFB lifetime component, NOT execution/App/device proof',linuxrunner=pin,original_sha256=hashlib.sha256(original).hexdigest(),generated_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),indent=2)+'\n')
print('Copied RFB completion source generated; original source unchanged')
