#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Bounded OWN host Steam test, with parent kept alive for UI observations.

Never targets a device or preexisting process. No authentication automation.
An exclusive stop-request file in this NEW private output ends ONLY this child
via SIGTERM; the deadline does the same. This is intentional test shutdown,
never a claim of guest crash or clean Linux teardown/Wine handoff.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time

p=argparse.ArgumentParser(description=__doc__)
for name in ('control','root','bundle','output'):p.add_argument(name,type=Path)
p.add_argument('--seconds',type=int,default=600)
p.add_argument('--native-sample-after',type=int,action='append',default=[],
               help='Optional read-only 2-second samples of this exact unreaped child; at most four')
a=p.parse_args();control,root,bundle,out=(getattr(a,n).resolve() for n in ('control','root','bundle','output'))
assert all(str(x).startswith('/Volumes/easystore/') for x in (control,root,bundle,out))
assert 60<=a.seconds<=900 and control.is_file() and (root/'meta.db').is_file() and not out.exists()
sample_times=sorted(set(a.native_sample_after))
assert len(sample_times)<=4 and all(1<=t<a.seconds-10 for t in sample_times)
for name in ('Steam/config/loginusers.vdf','Steam/userdata','root/.steam/config/loginusers.vdf'):
    assert not (root/'data'/name).exists(),'Recognizable account data; preserved'
users=subprocess.run(['lsof','-t',str(root/'meta.db')],capture_output=True,text=True)
assert users.returncode in (0,1) and not users.stdout.strip() and not users.stderr.strip(),'Cannot establish unused root'
out.mkdir(mode=0o700);logs=out/'logs';logs.mkdir(mode=0o700)
command=[str(control),str(root),str(logs),str(bundle)]
start=time.monotonic();reason='natural-child-exit';stop=out/'stop-request';samples=[]
with (out/'console.log').open('xb') as log:
    child=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=log,stderr=log)
    (out/'owner.json').write_text(json.dumps({'pid':child.pid,'command':command,'start_epoch':time.time(),'control_sha256':hashlib.sha256(control.read_bytes()).hexdigest(),'scope':'OWN unauthenticated host test, not Air/UI/game proof'},indent=2)+'\n')
    print('Owned host test PID',child.pid,flush=True)
    while child.poll() is None:
        if stop.exists() or time.monotonic()-start>=a.seconds:
            reason='intentional-own-test-stop' if stop.exists() else 'intentional-own-test-deadline'
            # This exact unreaped child was created here; no stale stored PID,
            # process search, process group or device/other-app signal.
            child.terminate();break
        if sample_times and time.monotonic()-start>=sample_times[0]:
            when=sample_times.pop(0);name='native-sample-%03d'%when
            # poll returned None and this sole owner has not reaped the child:
            # its PID cannot be recycled while sample opens the task.
            with (out/(name+'-receipt.log')).open('xb') as receipt:
                try:
                    result=subprocess.run(['sample',str(child.pid),'2','-file',str(out/(name+'.txt'))],
                                          stdout=receipt,stderr=subprocess.STDOUT,timeout=15).returncode
                except subprocess.TimeoutExpired:result='sample-observer-timeout'
            samples.append({'after_seconds':when,'status':result})
            (out/'sample-receipts.json').write_text(json.dumps(samples,indent=2)+'\n')
        time.sleep(.25)
    try:status=child.wait(timeout=15)
    except subprocess.TimeoutExpired:
        (out/'result.json').write_text(json.dumps({'reason':reason,'status':'termination-not-confirmed','pid':child.pid})+'\n')
        raise
(out/'result.json').write_text(json.dumps({'reason':reason,'native_status':status,'elapsed_seconds':round(time.monotonic()-start,3),'pid':child.pid,'native_samples':samples,'UI_and_game_success':False},indent=2)+'\n')
print('Owned host observer ended:',reason,status)
