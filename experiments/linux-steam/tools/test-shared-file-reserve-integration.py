#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
import argparse,hashlib,json,os,subprocess
from pathlib import Path
p=argparse.ArgumentParser(description='HOST real Linux PTE/file lifetime reserve controls; requires a host-injected copied archive')
for name in ('artifacts','archive','output'):p.add_argument(name,type=Path)
a=p.parse_args()
repo=Path(__file__).resolve().parents[3];lab=repo/'experiments/linux-steam';src=repo/'vendor/LinuxRunner'
base=a.artifacts.resolve();host=base/'host';out=a.output.resolve()
assert str(out).startswith('/Volumes/easystore/') and not out.exists();out.mkdir(parents=True,mode=0o700)
control=Path(__file__).with_name('shared-file-reserve-integration-control.c');archive=a.archive.resolve()
assert archive.is_file() and str(archive).startswith('/Volumes/easystore/')
cmd=['xcrun','clang','-DGUEST_ARM64=1','-DENGINE_ASBESTOS=1','-DISH_INTERNAL=1','-I'+str(src),'-I'+str(host),'-I'+str(lab/'app'),'-fsanitize=address,undefined','-fno-sanitize-recover=all','-Wall','-Wextra','-Werror',str(lab/'app/SharedFileReserve.c'),str(control),str(archive),'-L'+str(host),'-lish_emu','-lfakefs','-lsqlite3','-o',str(out/'control')]
cmd.insert(cmd.index(str(control)),str(lab/'app/NativeKernelLog.c'))
with (out/'build.log').open('x') as f:subprocess.run(cmd,check=True,stdout=f,stderr=subprocess.STDOUT)
rows=[]
for mode in ('ordinary','unprepared','shared','aliases','fork','readonly','private','offset','unaligned','data-failure','pte-failure','memfd','memfd-close'):
    directory=out/mode;directory.mkdir(mode=0o700);log=directory/'test.log'
    with log.open('x') as f:r=subprocess.run([out/'control',mode,directory/'fixture'],stdout=f,stderr=subprocess.STDOUT,timeout=20,env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0'))
    rows.append({'mode':mode,'exit':r.returncode,'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest()})
    assert not r.returncode,(mode,r.returncode,log)
(out/'evidence.json').write_text(json.dumps({'scope':'HOST actual pinned Linux realfs/sys_mmap64/PTE/fd backing integration; generated changed realfs/memory plus own helper/test sanitized. Original native ENOMEM and metadata failures injected. NOT iOS VA pressure, device UI/game proof','tests':rows,'command':cmd,'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'sources_sha256':{str(q):hashlib.sha256(q.read_bytes()).hexdigest() for q in [control,lab/'app/SharedFileReserve.c',lab/'app/SharedFileReserve.h']}},indent=2)+'\n')
print('HOST13 actual Linux mmap/PTE/file lifetime controls PASS; NOT device proof')
