#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""HOST exact regular pread, forced scratch/backend failures, and bytes/offsets."""
import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
for n in ('artifacts','archive','output'):p.add_argument(n,type=Path)
a=p.parse_args();base=a.artifacts.resolve();archive=a.archive.resolve();out=a.output.resolve();repo=Path(__file__).resolve().parents[3];lab=repo/'experiments/linux-steam';src=repo/'vendor/LinuxRunner';host=base/'host'
assert str(out).startswith('/Volumes/easystore/') and not out.exists() and archive.is_file();out.mkdir(mode=0o700,parents=True)
fixture=out/'owned-pattern.bin';pattern=bytes((i*17+3)&255 for i in range(65536));n=0x4ee50f
with fixture.open('xb') as f:
 for _ in range(n//len(pattern)):f.write(pattern)
 f.write(pattern[:n%len(pattern)])
rows=[]
for enabled in (False,True):
 build=out/('bounded' if enabled else 'original')
 cmd=[sys.executable,str(lab/'tools/build-bounded-pread.py'),str(src),str(host),str(archive),str(build),'--host-inject']+(['--enabled'] if enabled else [])
 with (out/(str(int(enabled))+'-build.log')).open('x') as f:subprocess.run(cmd,check=True,stdout=f,stderr=subprocess.STDOUT)
 exe=out/('control'+str(int(enabled)));cmd=['xcrun','clang','-DGUEST_ARM64=1','-DENGINE_ASBESTOS=1','-DISH_INTERNAL=1','-I'+str(src),'-I'+str(host),'-I'+str(lab/'app'),'-fsanitize=address,undefined','-fno-sanitize-recover=all','-Wall','-Wextra','-Werror',str(lab/'tools/regular-pread-control.c'),str(lab/'app/NativeKernelLog.c'),str(build/'libish.a'),'-L'+str(host),'-lish_emu','-lfakefs','-lsqlite3','-o',str(exe)]
 with (out/(str(int(enabled))+'-link.log')).open('x') as f:subprocess.run(cmd,check=True,stdout=f,stderr=subprocess.STDOUT)
 for mode in ['normal','large-refusal','scratch-refusal','backend-refusal','partial-backend-refusal','short','eof','zero','small','boundary','above-boundary','oversize','negative-offset','bad-buffer','bad-fd','pipe','memfd-excluded']:
  log=out/(str(int(enabled))+'-'+mode+'.log')
  with log.open('x') as f:r=subprocess.run([str(exe),str(int(enabled)),mode,str(fixture)],stdout=f,stderr=subprocess.STDOUT,timeout=30,env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0',TMPDIR=str(out)+'/'))
  assert not r.returncode,(enabled,mode,r.returncode,log)
  report=log.read_text();assert 'complete=PASS' in report;rows.append({'enabled':enabled,'mode':mode,'exit':r.returncode,'report':report.strip(),'sha256':hashlib.sha256(log.read_bytes()).hexdigest()})
sha=lambda q:hashlib.sha256(q.read_bytes()).hexdigest()
(out/'evidence.json').write_text(json.dumps({'scope':'HOST real pinned sys_pread/PTE/fd/backend: original large scratch refusal and backend refusal distinguished, bounded bytes/EOF/offset/error/refcount/cleanup controls; NOT actual AirENOMEMsite or CEF/UI fixproof','tests':rows,'source_sha256':{str(q.relative_to(repo)):sha(q) for q in [lab/'tools/bounded_pread_patch.py',lab/'tools/build-bounded-pread.py',lab/'tools/regular-pread-control.c',Path(__file__)]},'owned_fixture_sha256':sha(fixture)},indent=2)+'\n')
print('HOST34 original/bounded regular-pread semantic and failure controls PASS; NOT Air/UI proof')
