#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""HOST actual owned native mappings and contract/failure controls, NOT iOS."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);a=p.parse_args()
out=a.output.resolve();repo=Path(__file__).resolve().parents[3];lab=repo/'experiments/linux-steam'
assert str(out).startswith('/Volumes/easystore/') and not out.exists();out.mkdir(mode=0o700,parents=True)
flags=['-std=c11','-D_DARWIN_C_SOURCE','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-sanitize-recover=all','-g','-I'+str(lab/'app')]
commands=[]
def compile(*args):
    c=['xcrun','clang',*flags,*map(str,args)];commands.append(c);subprocess.run(c,check=True)
compile('-DIDECK_COW_BROKER_HOST_INJECTION=1','-DIDECK_COW_BROKER_MAX_CHUNKS=2','-Dmmap=ideck_broker_test_mmap','-Dmunmap=ideck_broker_test_munmap','-Dmadvise=ideck_broker_test_madvise','-c',lab/'app/CowBackingBroker.c','-o',out/'broker.o')
compile(lab/'tools/cow-broker-control.c',out/'broker.o','-o',out/'control')
rows=[]
for mode in ('baseline','baseline-sparse','dense','sparse','stranded-sparse','invalid-reuse','fail-first','fail-second','overlap','capacity','unmap-fail','advice-fail','concurrency'):
    log=out/(mode+'.log')
    with log.open('x') as f:r=subprocess.run([out/'control',mode],stdout=f,stderr=subprocess.STDOUT,env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0'),timeout=30)
    assert not r.returncode,(mode,r.returncode,log)
    rows.append({'mode':mode,'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest(),'exit':r.returncode})
(out/'evidence.json').write_text(json.dumps({'scope':'HOST broker and fixture ASanUBSan/Werror; actual selected mmap calls, data bytes, ownership/refusal/reuse/cleanup/concurrency. NOT physical RSS, exact VM regions, Linux integration or Air success','tests':rows,'commands':commands,'native_capacity_override':'Host2chunks only; iOS rejects host injection/alternate capacity','source_sha256':{str(p.relative_to(repo)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [lab/'app/CowBackingBroker.c',lab/'app/CowBackingBroker.h',lab/'tools/cow-broker-control.c']}},indent=2)+'\n')
print('HOST 13 actual native broker baseline/ownership/failure/advice/overlap/concurrency controls PASS')
