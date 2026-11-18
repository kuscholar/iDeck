#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Actual HOST ARM64 engine growth failure -> existing flush -> guest resumes."""
import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
for name in ('artifacts','kernel','engine','output'):p.add_argument(name,type=Path)
a=p.parse_args();base,kernel,engine,out=(getattr(a,n).resolve() for n in ('artifacts','kernel','engine','output'))
repo=Path(__file__).resolve().parents[3];lab=repo/'experiments/linux-steam';host=base/'host';src=repo/'vendor/LinuxRunner'
assert str(out).startswith('/Volumes/easystore/') and not out.exists();out.mkdir(mode=0o700,parents=True)
commands=[]
def run(cmd,log):
    cmd=[str(x) for x in cmd];commands.append(cmd)
    with log.open('x') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=60,env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0'))
    assert not r.returncode,(r.returncode,log)
run([sys.executable,lab/'tools/build-fiber-hash-guard.py',src,host,engine,out/'engine','--host-inject'],out/'engine-build.log')
# Indirect register branches prevent the decoder from following adjacent
# immediate targets into one block. Two passes prove progress after the flush.
guest=out/'probe.S';guest.write_text('''.text
.global _start
_start:
 mov x19, #2
1:
.rept 4096
 adr x0,.+8
 br x0
.endr
 subs x19,x19,#1
 b.ne 1b
 mov x0,#0
 mov x8,#93
 svc #0
 brk #0
''')
run(['xcrun','clang','--target=aarch64-linux-gnu','--ld-path='+str(base/'tool-bin/ld.lld'),'-nostdlib','-static',guest,'-Wl,-e,_start','-o',out/'probe.elf'],out/'guest-build.log')
flags=['-DIDECK_LAB_GUEST_LIFETIME=1','-DIDECK_LAB_NATIVE_LOG=1','-DIDECK_LAB_LAZY_PAGES=1','-DGUEST_ARM64=1','-DENGINE_ASBESTOS=1','-DLOG_HANDLER_DPRINTF=1','-DISH_INTERNAL=1','-fsanitize=address,undefined','-fno-sanitize-recover=all','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-I'+str(src),'-I'+str(host),'-I'+str(lab/'app')]
run(['xcrun','clang',*flags,*[lab/'app'/n for n in ['LinuxLabRuntime.c','LabDeviceFS.c','LabBridge.c','LaunchProtocol.c','NativeKernelLog.c']],lab/'tools/hash-growth-guest-control.c',kernel,out/'engine/libish_emu.a','-L'+str(host),'-lfakefs','-lsqlite3','-o',out/'control'],out/'host-build.log')
root=out/'root';root.mkdir(mode=0o700);logs=out/'logs';logs.mkdir(mode=0o700);(root/'probe').write_bytes((out/'probe.elf').read_bytes());(root/'probe').chmod(0o700)
run([out/'control',root,logs],out/'control.log')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(out/'evidence.json').write_text(json.dumps({'scope':'HOST actual complete copied engine runs own ARM64 branch ELF, one-shot real hash allocator failure triggers existing flush, guest completes; own engine/wrappers sanitized not all dependencies. NOT iPad/CEF/UI/game/stability proof','exit':0,'commands':commands,'guest_sha256':sha(out/'probe.elf'),'kernel_sha256':sha(kernel),'engine_evidence_sha256':sha(out/'engine/evidence.json'),'log_sha256':sha(out/'control.log')},indent=2)+'\n')
print('HOST real ARM64 engine hash growth allocationNULL -> existing flush -> guest exit0 PASS')
