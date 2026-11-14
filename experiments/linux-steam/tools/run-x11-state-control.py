#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Run our state observer against real Xvfb/Xlib in a NEW stopped private root.

Caller must establish that no experiment overlaps and no source fakefs/SQLite
writer is live BEFORE cloning the root. This program never clones an active
root, runs Steam/VNC, touches a device or interprets observer timeout as death.
"""
import argparse
import fcntl
import hashlib
import json
from pathlib import Path
import subprocess
import time

p=argparse.ArgumentParser(description=__doc__)
for name in ('ish','root','elf','output','ld_lld'):p.add_argument(name,type=Path)
a=p.parse_args();ish,root,elf,out=(getattr(a,n).resolve() for n in ('ish','root','elf','output'))
linker=a.ld_lld.absolute();lab=Path(__file__).resolve().parents[1]
assert all(str(x).startswith('/Volumes/easystore/') for x in (ish,root,elf,out,linker))
assert not out.exists() and (root/'meta.db').is_file() and (root/'data').is_dir()
for name in ('Steam/config/loginusers.vdf','Steam/userdata','root/.steam/config/loginusers.vdf','tmp/.X99-lock','tmp/.X11-unix/X99'):
    assert not (root/'data'/name).exists(),'Occupied/authenticated root refused'
out.mkdir(mode=0o700)
library=root/'data/usr/lib/aarch64-linux-gnu';dependencies=[library/'libX11.so.6.4.0',library/'libc.so.6']
for path in dependencies:assert path.read_bytes()[:4]==b'\x7fELF'
build=['xcrun','clang','--target=aarch64-linux-gnu','--ld-path='+str(linker),'-nostdlib','-fPIE',
       '-ffreestanding','-fno-builtin','-fno-stack-protector','-O2','-Wall','-Wextra','-Werror',
       str(lab/'guest/x11-state-fixture.c'),str(lab/'guest/xlib-glibc-start.S'),
       *map(str,dependencies),'-Wl,-pie,-e,_start,-dynamic-linker,/lib/ld-linux-aarch64.so.1',
       '-o',str(out/'fixture.elf')]
with (out/'build.log').open('xb') as log:subprocess.run(build,stdout=log,stderr=log,check=True,timeout=60)
with (root/'.ideck-x11-state.lock').open('x') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    for path,target in ((elf,'/x11-window-state'),(out/'fixture.elf','/x11-state-fixture')):
        payload=path.read_bytes();assert 0<len(payload)<=262144 and payload[:6]==b'\x7fELF\x02\x01' and payload[18:20]==b'\xb7\0'
        # Fixed OWN paths through the guest VFS, never direct fakefs metadata edits.
        script='set -eu; umask 077; test ! -e '+target+'; cat > '+target+'; chmod 700 '+target
        with (out/(path.name+'-install.log')).open('xb') as log:
            subprocess.run([str(ish),'-f',str(root),'/bin/sh','-c',script],input=payload,stdout=log,stderr=log,check=True,timeout=30)
    script='''set -eu
test ! -e /tmp/.X99-lock && test ! -S /tmp/.X11-unix/X99
Xvfb :99 -screen 0 640x480x24 -nolisten tcp -extension MIT-SHM > /tmp/x11-state-server.log 2>&1 & xpid=$!
cleanup(){ kill "$xpid" 2>/dev/null || :; wait "$xpid" 2>/dev/null || :; }; trap cleanup EXIT
n=0; while ! test -S /tmp/.X11-unix/X99; do kill -0 "$xpid"; n=$((n+1)); test "$n" -lt 100; sleep .1; done
timeout 90 /x11-state-fixture
'''
    with (out/'runtime.log').open('xb') as log:
        start=time.monotonic();process=subprocess.Popen([str(ish),'-f',str(root),'/bin/sh','-c',script],stdin=subprocess.DEVNULL,stdout=log,stderr=log)
        (out/'observer.json').write_text(json.dumps(dict(pid=process.pid,root=str(root),scope='Own isolated host X11 state control, no Steam/device'))+'\n')
        try:status=process.wait(timeout=110)
        except subprocess.TimeoutExpired:
            (out/'result.json').write_text(json.dumps(dict(status='observer-timeout-state-unproven',pid=process.pid))+'\n');raise
    assert status==0,('Inspect private logs',status)
    ids=json.loads((root/'data/x11-state-ids.json').read_text());reports=[]
    for i in range(4):
        raw=(root/('data/x11-state-'+str(i)+'.json')).read_bytes();assert len(raw)<16384
        (out/('state-'+str(i)+'.json')).write_bytes(raw);d=json.loads(raw);reports.append(d)
        assert d['status']==0 and d['error']==0 and d['root']==ids['root'] and not d['atomic_snapshot'] and not d['Steam_UI_qualified']
        assert d['root_width']==640 and d['root_height']==480 and not d['root_attributes']['event_mask']&(1<<20)
        windows={w['id']:w for w in d['windows_bottom_to_top_then_extra_focus']}
        assert d['children_total']==(2 if i==3 else 3) and d['focus']==ids['b' if i==1 else 'a']
        for name in ('a','c') if i==3 else ('a','b','c'):
            w=windows[ids[name]];assert w['attributes_valid'] and w['geometry_valid'] and not w['x_error']
            assert w['map_state']==(0 if name=='c' or (name=='a' and i==1) else 2)
        assert windows[ids['a']]['x']==19 and windows[ids['a']]['width']==64 and windows[ids['c']]['x']==-9
        if i==3:assert ids['b'] not in windows
    evidence=dict(scope='HOST real ARM64 LinuxRunner/Xvfb/Xlib own-window state transitions, NOT Air/Steam/CEF/game qualification',
                  exit=status,elapsed_seconds=round(time.monotonic()-start,3),cases=4,ids=ids,reports=reports,
                  dependencies={str(p.relative_to(root/'data')):hashlib.sha256(p.read_bytes()).hexdigest() for p in dependencies},
                  artifacts={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ish,elf,out/'fixture.elf',out/'runtime.log')})
    (out/'evidence.json').write_text(json.dumps(evidence,indent=2)+'\n');print(json.dumps(evidence))
