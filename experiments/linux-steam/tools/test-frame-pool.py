#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Real Foundation bounded pool, optional actual copied RFB decoder controls."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);p.add_argument('--rfb-generated',type=Path);a=p.parse_args()
out=a.output.resolve();lab=Path(__file__).resolve().parents[1];src=lab.parents[1]/'vendor/LinuxRunner/app/LinuxRunner'
assert str(out).startswith('/Volumes/easystore/') and not out.exists();out.mkdir(mode=0o700,parents=True)
fixture=lab/'tools'/('frame-pool-rfb-control.m' if a.rfb_generated else 'frame-pool-control.m')
command=['xcrun','clang','-fobjc-arc','-fblocks','-DIDECK_FRAME_POOL_HOST_INJECTION=1','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-sanitize-recover=all','-I'+str(lab/'app'),'-I'+str(src),str(lab/'app/FrameSnapshotPool.m'),str(src/'RFBProtocol.c'),str(fixture),'-framework','Foundation','-o',str(out/'control')]
generated=None
if a.rfb_generated:
    generated=a.rfb_generated.resolve();assert '[_ideckFramePool snapshotPixels:' in generated.read_text()
    client=out/'Client.m';client.write_text('#include "'+str(generated)+'"\n')
    # Pinned decoder keeps upstream formatting; own standalone helper retains
    # strict Werror. Do not edit vendor code to silence its existing warning.
    command[2:2]=[str(client),'-Wno-error=deprecated-declarations','-Wno-error=unused-function','-Wno-error=misleading-indentation']
with (out/'build.log').open('x') as f:subprocess.run(command,stdout=f,stderr=subprocess.STDOUT,check=True)
with (out/'control.log').open('x') as f:r=subprocess.run([out/'control'],stdout=f,stderr=subprocess.STDOUT,timeout=45,env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0'))
assert not r.returncode,(r.returncode,out/'control.log')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(out/'evidence.json').write_text(json.dumps({'scope':'HOST actual generated RFB full/partial decode, late allocator refusal, bounded saturation, immutable retained bytes and teardown; NOT Steam/Metal/iOS proof' if generated else 'HOST real Foundation pool preparation rollback/bounds/exhaustion/immutable reuse/delayed owner teardown/512concurrent admissions. ASanUBSan own code; NOT iOS/Metal/Steam proof','command':command,'exit':r.returncode,'generated_sha256':sha(generated) if generated else None,'log_sha256':sha(out/'control.log'),'sources_sha256':{p.name:sha(p) for p in [lab/'app/FrameSnapshotPool.h',lab/'app/FrameSnapshotPool.m',fixture]}},indent=2)+'\n')
print('HOST bounded immutable frame pool controls PASS')
