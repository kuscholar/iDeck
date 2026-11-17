#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""HOST real Foundation/no-copy immutable snapshot contract and rollback."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);p.add_argument('--rfb-generated',type=Path,help='Explicit copied generated RFB include to test actual decoder');a=p.parse_args()
out=a.output.resolve();lab=Path(__file__).resolve().parents[1];src=lab.parents[1]/'vendor/LinuxRunner/app/LinuxRunner'
assert str(out).startswith('/Volumes/easystore/') and not out.exists();out.mkdir(mode=0o700,parents=True)
cmd=['xcrun','clang','-fobjc-arc','-fblocks','-DIDECK_FRAME_SNAPSHOT_HOST_INJECTION=1','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-sanitize-recover=all','-I'+str(lab/'app'),'-I'+str(src),str(lab/'app/CheckedFrameSnapshot.m'),str(src/'RFBProtocol.c'),str(lab/'tools/frame-snapshot-control.m'),'-framework','Foundation','-o',str(out/'control')]
if a.rfb_generated:
    generated=a.rfb_generated.resolve();assert generated.is_file()
    assert 'ideck_checked_frame_snapshot(_pixels,_width,_height)' in generated.read_text()
    client=out/'Client.m';client.write_text('#include "'+str(generated)+'"\n')
    cmd=[str(lab/'tools/frame-snapshot-rfb-control.m') if x==str(lab/'tools/frame-snapshot-control.m') else x for x in cmd]
    # Unchanged pinned decoder has existing platform deprecation/unused helpers;
    # retain diagnostic output without treating those as new-helper warnings.
    cmd.remove('-Werror');cmd.insert(2,str(client))
with (out/'build.log').open('x') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
with (out/'control.log').open('x') as f:r=subprocess.run([out/'control'],stdout=f,stderr=subprocess.STDOUT,timeout=45,env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0'))
assert not r.returncode,(r.returncode,out/'control.log')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(out/'evidence.json').write_text(json.dumps({'scope':'HOST actual generated RFB rawfull/partial decode+immutable retained frames+allocationNULL/error; no handshake/Metal/device proof' if a.rfb_generated else 'HOST real Foundation snapshots/maximum dimensions/immutable isolation/allocNULL/last consumer releases/8threads512frames. ASanUBSan own helper+fixture+protocol; not OS Foundation internals, iOS/RFB decoder/Metal/device/CEF proof','command':cmd,'generated_sha256':sha(generated) if a.rfb_generated else None,'exit':r.returncode,'log_sha256':sha(out/'control.log'),'sources_sha256':{p.name:sha(p) for p in [lab/'app/CheckedFrameSnapshot.m',lab/'app/CheckedFrameSnapshot.h',lab/'tools/frame-snapshot-control.m',lab/'tools/frame-snapshot-rfb-control.m']}},indent=2)+'\n')
print('HOST real Foundation checked immutable framebuffer snapshot controls PASS')
