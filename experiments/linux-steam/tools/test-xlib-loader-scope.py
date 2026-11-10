#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Real ARM64/glibc dlopen scope control; no Steam, credentials or device use.

Caller supplies an inspected stopped unauthenticated fakefs. Clone it, install
only own ELFs through guest VFS, run one fresh Xvfb and report all four statuses.
No timeout auto-kill or success inference from process presence.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

p=argparse.ArgumentParser(description=__doc__)
for name in ('ish','source_root','artifact','output'):p.add_argument(name,type=Path)
a=p.parse_args();ish,source,art,out=(getattr(a,n).resolve() for n in ('ish','source_root','artifact','output'))
assert all(str(x).startswith('/Volumes/easystore/') for x in (source,art,out))
assert not out.exists() and (source/'meta.db').is_file()
for name in ('Steam/config/loginusers.vdf','Steam/userdata','root/.steam/config/loginusers.vdf'):
    assert not (source/'data'/name).exists()
users=subprocess.run(['lsof','-t',str(source/'meta.db')],capture_output=True,text=True)
assert users.returncode in (0,1) and not users.stdout.strip() and not users.stderr.strip(),'Cannot establish stopped source root'
out.mkdir(mode=0o700);root=out/'root'
subprocess.run(['cp','-cpR',str(source),str(root)],check=True,timeout=240)
for original,target in [('scope-plugin.so','ideck-scope-plugin.so'),('scope.elf','ideck-scope-control'),('xlib-window-trace.so','ideck-scope-trace.so')]:
    data=(art/original).read_bytes();assert 0<len(data)<=262144 and data[:4]==b'\x7fELF'
    with (out/(original+'.install.log')).open('xb') as log:
        result=subprocess.run([str(ish),'-f',str(root),'/bin/sh','-c',f'set -eu; umask 077; test ! -e /{target}; cat > /{target}; chmod 700 /{target}'],input=data,stdout=log,stderr=log,timeout=30)
    assert not result.returncode
script='''set -eu; umask 077
test ! -e /tmp/.X97-lock
Xvfb :97 -screen 0 640x480x24 -nolisten tcp -extension MIT-SHM > /tmp/scope-xvfb.log 2>&1 & xpid=$!
cleanup(){ kill "$xpid" 2>/dev/null || :;wait "$xpid" 2>/dev/null || :; };trap cleanup EXIT
n=0;while ! test -S /tmp/.X11-unix/X97;do kill -0 "$xpid";n=$((n+1));test "$n" -lt 200;sleep .1;done
export DISPLAY=:97
for scope in local global;do
 set +e;timeout 30 /ideck-scope-control "$scope";status=$?;set -e;echo SCOPE_RESULT mode=$scope traced=0 status=$status
 set +e;LD_PRELOAD=/ideck-scope-trace.so timeout 30 /ideck-scope-control "$scope";status=$?;set -e;echo SCOPE_RESULT mode=$scope traced=1 status=$status
done
'''
with (out/'runtime.log').open('xb') as log:
    process=subprocess.Popen([str(ish),'-f',str(root),'/bin/sh','-c',script],stdin=subprocess.DEVNULL,stdout=log,stderr=log)
    (out/'observer.json').write_text(json.dumps({'pid':process.pid,'scope':'own host Xlib scope control; timeout is not death proof'})+'\n')
    status=process.wait(timeout=145)
text=(out/'runtime.log').read_text(errors='replace')
rows=[dict(mode=m,traced=int(t),status=int(s)) for m,t,s in re.findall(r'^SCOPE_RESULT mode=(local|global) traced=([01]) status=(\d+)$',text,re.M)]
record={'scope':'HOST actual ARM64/glibc/Xlib local/global loader control, NOT actual Steam cause or iPad success','native_status':status,'results':rows,'runtime_sha256':hashlib.sha256((out/'runtime.log').read_bytes()).hexdigest(),'artifacts':{n:hashlib.sha256((art/n).read_bytes()).hexdigest() for n in ('scope.elf','scope-plugin.so','xlib-window-trace.so')}}
(out/'evidence.json').write_text(json.dumps(record,indent=2)+'\n')
assert status==0 and len(rows)==4 and all(row['status']==0 for row in rows if not row['traced'])
print(json.dumps(record))
