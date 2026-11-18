#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""HOST existing-stack ABI/code-only snapshot; not Steam/device proof."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
for n in ('artifacts','archive','output'):p.add_argument(n,type=Path)
a=p.parse_args();base=a.artifacts.resolve();archive=a.archive.resolve();out=a.output.resolve();repo=Path(__file__).resolve().parents[3];lab=repo/'experiments/linux-steam';src=repo/'vendor/LinuxRunner';host=base/'host'
assert str(out).startswith('/Volumes/easystore/') and not out.exists() and archive.is_file();out.mkdir(mode=0o700,parents=True)
cmd=['xcrun','clang','-DGUEST_ARM64=1','-DENGINE_ASBESTOS=1','-DISH_INTERNAL=1','-I'+str(src),'-I'+str(host),'-I'+str(lab/'app'),'-fsanitize=address,undefined','-fno-sanitize-recover=all','-Wall','-Wextra','-Werror',str(lab/'app/BlockedWaitCallers.c'),str(lab/'app/NativeKernelLog.c'),str(lab/'tools/blocked-wait-callers-control.c'),str(archive),'-L'+str(host),'-lish_emu','-lfakefs','-lsqlite3','-o',str(out/'control')]
rows=[]
for bound in (4,8):
    compiled=cmd+[f'-DIDECK_WAIT_CALLER_LIMIT={bound}']
    with (out/f'build{bound}.log').open('x') as f:subprocess.run(compiled,check=True,stdout=f,stderr=subprocess.STDOUT)
    for mode in ('valid','terminal','unaligned','unmapped','nonstack','stack-no-read','code-no-exec','code-no-file','bad-data-bound','noncall','cycle','distant','code-page-cross','busy'):
        log=out/(str(bound)+'-'+mode+'.log')
        with log.open('x') as f:r=subprocess.run([out/'control',mode],stdout=f,stderr=subprocess.STDOUT,timeout=20,env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0'))
        assert not r.returncode,(bound,mode,r.returncode,log)
        rows.append({'bound':bound,'mode':mode,'exit':r.returncode,'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest()})
invalid=subprocess.run(['xcrun','clang','-I'+str(lab/'app'),'-DIDECK_WAIT_CALLER_LIMIT=6','-x','c','-fsyntax-only','-'],input=b'#include "BlockedWaitCallers.h"\n',capture_output=True)
assert invalid.returncode and b'explicit bounded8' in invalid.stderr
(out/'evidence.json').write_text(json.dumps({'scope':'HOST actual pinned PTE/refcount memory, own ABI/code-only helper and fixtures sanitized; no guest arbitrary buffers/strings or page materialization. NOT CEF/Steam/Air evidence','tests':rows,'invalid_bound_refused':True,'command':cmd,'source_sha256':{str(q.relative_to(repo)):hashlib.sha256(q.read_bytes()).hexdigest() for q in [lab/'app/BlockedWaitCallers.c',lab/'app/BlockedWaitCallers.h',lab/'tools/blocked-wait-callers-control.c']}},indent=2)+'\n')
print('HOST28 original4/expanded8 bounded waiter-callers lock/bounds/permissions/no-materialization controls PASS')
