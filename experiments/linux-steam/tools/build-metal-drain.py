#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Copy pinned framebuffer source and wire actual command completion, no vendor edit."""
import argparse,hashlib,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);a=p.parse_args()
repo=Path(__file__).resolve().parents[3];src=repo/'vendor/LinuxRunner';out=a.output.resolve()
assert str(out).startswith('/Volumes/easystore/') and not out.exists()
assert subprocess.check_output(['git','-C',str(src),'rev-parse','HEAD'],text=True).strip()=='d1419782da2e299fe22f1ddb85c70ae3d1e276b1'
source=src/'app/LinuxRunner/MetalFramebufferView.m';s=source.read_text()
def replace(old,new):
 global s
 assert s.count(old)==1,old
 s=s.replace(old,new)
replace('#import "FramebufferMetalPipeline.h"','#import "FramebufferMetalPipeline.h"\n#import "LabMetalDrain.h"')
replace('@property BOOL failed;','@property BOOL failed;\n@property LabMetalDrain *ideckDrain;')
replace('        _queue = [device newCommandQueue];','        _ideckDrain=[LabMetalDrain new];\n        _queue = [device newCommandQueue];')
replace('if (_failed || !lr_rfb_dimensions','if (_ideckDrain.closed || _failed || !lr_rfb_dimensions')
replace('if (_failed || !_pixels ||','if (_ideckDrain.closed || _failed || !_pixels ||')
# Strong view retained until real Metal completion AND its main accounting body.
replace('    __weak typeof(self) weak = self;\n    [command addCompletedHandler:^(id<MTLCommandBuffer> completed) {\n        dispatch_async(dispatch_get_main_queue(), ^{\n            typeof(self) self = weak; if (!self) return;',
'''    BOOL tracked=[_ideckDrain trackCommand:command completion:^(id<MTLCommandBuffer> completed) {''')
replace('        });\n    }];\n    [command commit];',
'''    }];
    NSAssert(tracked,@"Closed Metal admission must never commit");
    if(!tracked){_inFlight[slot]--;return;}
    [command commit];''')
replace('- (void)clearFrame {','''- (void)ideckCloseMetalWithCompletion:(dispatch_block_t)completion {
    [self clearFrame];
    [_ideckDrain closeWithCompletion:completion];
}
- (BOOL)ideckReopenMetal {
    return !_failed && [_ideckDrain reopen];
}
- (void)clearFrame {''')
out.mkdir(mode=0o700);target=out/'MetalFramebufferView.m';target.write_text(s)
for name in ('LICENSE.md','LICENSE.IOS'):
 (out/name).write_bytes((src/name).read_bytes())
(out/'evidence.json').write_text(json.dumps({'linuxrunner':subprocess.check_output(['git','-C',str(src),'rev-parse','HEAD'],text=True).strip(),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'generated_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'scope':'Actual command/main completion only; NOT device or driver/global runtime quiescence'},indent=2)+'\n')
