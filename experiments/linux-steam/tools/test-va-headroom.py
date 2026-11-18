#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""HOST isolated VA-headroom probe ownership/error/refusal/concurrency controls."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);a=p.parse_args();repo=Path(__file__).resolve().parents[3];w=repo/'experiments/linux-steam/app';tools=Path(__file__).resolve().parent;out=a.output.resolve();assert str(out).startswith('/Volumes/easystore/') and not out.exists();out.mkdir(mode=0o700,parents=True)
flags=['-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-sanitize-recover=all','-I'+str(w),'-I'+str(repo/'experiments/linux-steam/app'),'-DIDECK_VA_HEADROOM_HOST_INJECTION=1']
cmd=['xcrun','clang',*flags,w/'VAHeadroomProbe.c',tools/'va-headroom-control.c','-o',out/'control']
with (out/'build.log').open('x') as f:subprocess.run([str(x) for x in cmd],stdout=f,stderr=subprocess.STDOUT,check=True)
rows=[]
for case in ['not-prepared','prepare-fail','release-fail','trial-fail','cleanup-fail','shrunk','normal','concurrent']:
 d=out/case;d.mkdir(mode=0o700);log=d/'log.txt'
 with log.open('x') as f:r=subprocess.run([out/'control',case,d],stdout=f,stderr=subprocess.STDOUT,timeout=20,env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0'))
 assert not r.returncode,(case,r.returncode,log)
 rows.append({'case':case,'exit':0,'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest()})
(out/'evidence.json').write_text(json.dumps({'scope':'HOST real own PROT_NONE reservation and own unlinked regular file; refusal wrappers explicit. Once-only/concurrent/error preservation/gates/cleanup controls, ASanUBSan. NOT actual iPad VA capacity or UI fix proof','rows':rows,'source_sha256':{n:hashlib.sha256(((tools if n.endswith('-control.c') else w)/n).read_bytes()).hexdigest() for n in ['VAHeadroomProbe.h','VAHeadroomProbe.c','va-headroom-control.c']}},indent=2)+'\n')
print('HOST8owned-span headroom probe contract groups PASS')
