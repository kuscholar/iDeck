#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Discriminate a pinned CASP/MM lock inversion with real native lock schedules.

Uses the actual published helper function, with a modeled translation/MM boundary.
No vendor/archive/Steam/device mutation. Baseline intentionally deadlocks and is
terminated by its own observer; passing candidate is NOT ARM64/Linux/device proof.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time
from casp_order_patch import casp_functions
p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);a=p.parse_args()
out=a.output.resolve();assert str(out).startswith('/Volumes/easystore/') and not out.exists()
repo=Path(__file__).resolve().parents[3];src=repo/'vendor/LinuxRunner';pin='d1419782da2e299fe22f1ddb85c70ae3d1e276b1'
assert subprocess.check_output(['git','-C',str(src),'rev-parse','HEAD'],text=True).strip()==pin
assert not subprocess.check_output(['git','-C',str(src),'status','--porcelain','--untracked-files=no'],text=True).strip()
body=(src/'emu/tlb.c').read_text();assert body.encode()==subprocess.check_output(['git','-C',str(src),'show',pin+':emu/tlb.c'])
original,candidate=casp_functions(body)
out.mkdir(mode=0o700);harness=repo/'experiments/linux-steam/tools/casp-lock-order-control.c'
hashof=lambda x:hashlib.sha256(x.read_bytes()).hexdigest();rows=[]
for name,function in [('baseline',original),('candidate',candidate)]:
    build=out/name;build.mkdir();(build/'CaspFunction.inc').write_text('/* Extracted pinned GPL LinuxRunner helper; retain LICENSE.md and LICENSE.IOS. */\n'+function)
    command=['xcrun','clang','-std=c11','-D_DARWIN_C_SOURCE','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer','-I',str(build),str(harness),'-o',str(build/'control')]
    subprocess.run(command,check=True)
    for case in ('semantics','order'):
        began=time.monotonic();intentional=False
        with (build/(case+'.log')).open('xb') as log:
            child=subprocess.Popen([str(build/'control'),case],stdout=log,stderr=subprocess.STDOUT)
            try:status=child.wait(timeout=3)
            except subprocess.TimeoutExpired:intentional=True;child.terminate();status=child.wait(timeout=5)
        output=(build/(case+'.log')).read_text()
        if name=='baseline' and case=='order':
            assert intentional and 'cow-upgrade-waits-for-mm-writer' in output and 'peer-attempts-pair-lock-while-mm-read-held' in output and 'cow-upgrade-returned' not in output
        else:assert status==0 and not intentional,output
        rows.append(dict(variant=name,case=case,status=status,intentionally_terminated=intentional,elapsed_seconds=round(time.monotonic()-began,3),function_sha256=hashof(build/'CaspFunction.inc'),binary_sha256=hashof(build/'control'),log_sha256=hashof(build/(case+'.log'))))
record=dict(scope='HOST ASan/UBSan actual pinned helper plus MODELED MM translation/upgrade. NOT complete Linux/ARM64/Air/Steam fix proof.',linuxrunner=pin,source_sha256=hashof(src/'emu/tlb.c'),harness_sha256=hashof(harness),tests=rows,limitations=['Original CASP mixing with STXP/other atomics not qualified','Original CASP32 misalignment/cross-page semantics not changed or qualified','Candidate not installed into a runtime archive by this test'])
(out/'evidence.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
