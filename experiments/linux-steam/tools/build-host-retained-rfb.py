#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Build actual HOST retained-backend + embedded RFB control, never launch it.

Reuses immutable copied runtime archive and the own-source startup diagnostic.
Does not change the vendor tree, ordinary app or any device installation.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
p=argparse.ArgumentParser(description=__doc__)
for name in ('artifacts','archive','output'):p.add_argument(name,type=Path)
p.add_argument('--engine',type=Path,help='Explicit copied experimental engine; original by default')
a=p.parse_args();base,archive,out=(getattr(a,n).resolve() for n in ('artifacts','archive','output'))
assert all(str(x).startswith('/Volumes/easystore/') for x in (base,archive,out)) and not out.exists()
repo=Path(__file__).resolve().parents[3];lab=repo/'experiments/linux-steam';vendor=repo/'vendor/LinuxRunner'
out.mkdir(mode=0o700)
engine=(a.engine or base/'host/libish_emu.a').resolve()
extra=['--engine',str(engine)] if a.engine else []
subprocess.run([sys.executable,str(lab/'tools/build-host-startup-diagnostics.py'),str(base),str(archive),str(out/'backend'),*extra],check=True)
e=json.loads((out/'backend/evidence.json').read_text());cmd=e['build_command']
start=next(i for i,x in enumerate(cmd) if x.endswith('/LinuxLabRuntime.c'))
end=cmd.index(str(archive));flags=cmd[2:start];objects=[]
for source in cmd[start:end]:
    if source.endswith('/retained-backend-control.c'):continue
    obj=out/(Path(source).stem+'.o')
    subprocess.run(['xcrun','clang',*flags,'-c',source,'-o',str(obj)],check=True);objects.append(str(obj))
subprocess.run([sys.executable,str(lab/'tools/build-rfb-lifetime.py'),str(out/'rfb')],check=True)
headers=vendor/'app/LinuxRunner';protocol=out/'RFBProtocol.o'
subprocess.run(['xcrun','clang','-O2','-I',str(headers),'-c',str(headers/'RFBProtocol.c'),'-o',str(protocol)],check=True)
sources=[lab/'tools/retained-rfb-control.m',lab/'app/LabRFBClient.m']
link=['xcrun','clang','-fobjc-arc','-fblocks','-O2','-Wall','-Wextra','-Werror',
      # Exact inherited unused-static/indentation warnings, no assertion disable.
      '-Wno-unused-function','-Wno-misleading-indentation','-DIDECK_LAB_RFB_LIFETIME=1',
      '-I',str(headers),'-I',str(lab/'app'),'-I',str(out/'rfb'),*[str(x) for x in sources],
      *objects,str(protocol),str(archive),str(engine),'-L',str(base/'host'),'-lfakefs','-lsqlite3',
      '-framework','Foundation','-framework','ImageIO','-framework','CoreGraphics','-o',str(out/'control')]
subprocess.run(link,check=True)
hashof=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
assert e['archive_sha256']==hashof(archive)
(out/'evidence.json').write_text(json.dumps({'scope':'HOST real backend+in-process RFB task boundary; NOT Metal/device/game proof',
 'archive_sha256':hashof(archive),'archive_unchanged':True,'engine_sha256':hashof(engine),'explicit_engine':bool(a.engine),'source_sha256':{str(s.relative_to(repo)):hashof(s) for s in sources},
 'startup_build_evidence_sha256':hashof(out/'backend/evidence.json'),'rfb_build_evidence_sha256':hashof(out/'rfb/evidence.json'),
 'control_sha256':hashof(out/'control'),'link_command':link},indent=2)+'\n')
print('Built genuine host backend plus embedded RFB control; NOT launched/device validated')
