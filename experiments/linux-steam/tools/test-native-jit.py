#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""HOST differential: identical owned ARM64 ELF, real optional JIT vs gadgets.

Requires freshly built --native-jit host archives with matching namespace and
layouts. No device, Steam, account, FEX or system-setting changes. A performance
sample of this tiny arithmetic/memory loop is not a Steam/CEF benchmark.
"""
import argparse,hashlib,json,os,re,subprocess
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
for name in ('artifacts','engine_build','output'):p.add_argument(name,type=Path)
a=p.parse_args();base,build,out=(getattr(a,n).resolve() for n in ('artifacts','engine_build','output'))
repo=Path(__file__).resolve().parents[3];src=repo/'vendor/LinuxRunner';lab=repo/'experiments/linux-steam'
assert str(out).startswith('/Volumes/easystore/') and not out.exists()
evidence=json.loads((build.parent/'evidence.json').read_text())
assert evidence['platform']=='host' and evidence['native_jit_compiled'] is True
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
for name in ('libish.a','libish_emu.a','libfakefs.a'):
    assert sha(build/name)==evidence['archives'][name]['sha256']
out.mkdir(mode=0o700,parents=True);commands=[]
def run(cmd,name,env=None):
    command=[str(x) for x in cmd];commands.append(command)
    with (out/name).open('x') as log:
        result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=60,env=env)
    assert result.returncode==0,(name,result.returncode)
guest=out/'probe.S';total=1000000*1000001//2
constant='\n'.join(f' mov{("z" if shift==0 else "k")} x22, #{(total>>shift)&65535}, lsl #{shift}' for shift in (0,16,32,48))
guest.write_text('''.text
.global _start
_start:
 sub sp,sp,#16
 movz x19,#16960
 movk x19,#15,lsl #16
 mov x20,#0
1:
 add x20,x20,x19
 str x20,[sp]
 ldr x21,[sp]
 cmp x21,x20
 b.ne 3f
 subs x19,x19,#1
 b.ne 1b
'''+constant+'''
 cmp x20,x22
 b.ne 3f
 mov x0,#0
 b 4f
3:
 mov x0,#1
4:
 mov x8,#93
 svc #0
 brk #0
''')
run(['xcrun','clang','--target=aarch64-linux-gnu','--ld-path='+str(base/'tool-bin/ld.lld'),'-nostdlib','-static',guest,'-Wl,-e,_start','-o',out/'probe.elf'],'guest-build.log')
flags=['-DISH_JIT=1','-DIDECK_LAB_LINUX_SYMBOL_NAMESPACE=1','-include',build.parent/'LinuxSymbolNamespace.h','-DGUEST_ARM64=1','-DENGINE_ASBESTOS=1','-DLOG_HANDLER_DPRINTF=1','-DISH_INTERNAL=1','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-I'+str(src),'-I'+str(build),'-I'+str(lab/'app')]
run(['xcrun','clang',*flags,*[lab/'app'/n for n in ('LinuxLabRuntime.c','LabDeviceFS.c','LabBridge.c','LaunchProtocol.c')],lab/'tools/native-jit-control.c',build/'libish.a',build/'libish_emu.a',build/'libfakefs.a','-lsqlite3','-o',out/'control'],'host-build.log')
# Entitlement belongs ONLY to this newly created, disposable host test binary.
entitlements=out/'host-test.entitlements'
entitlements.write_text('<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd"><plist version="1.0"><dict><key>com.apple.security.cs.allow-jit</key><true/></dict></plist>\n')
run(['codesign','--force','--sign','-','--entitlements',entitlements,out/'control'],'sign-host.log')
run(['codesign','--verify','--strict',out/'control'],'verify-host.log')
root=out/'root';root.mkdir(mode=0o700);(root/'probe').write_bytes((out/'probe.elf').read_bytes());(root/'probe').chmod(0o700)
clean={key:value for key,value in os.environ.items() if not key.startswith('ISH_')}
observations=[]
for index,mode in enumerate(('interpreter','native','interpreter','native')):
    env=dict(clean,ISH_JIT='1' if mode=='native' else '0',ISH_AOT_FAMILY='0')
    name=f'{index}-{mode}.log';run([out/'control',root,mode],name,env)
    text=(out/name).read_text();match=re.search(r'guest_status=(\d+) blocks=(\d+) segments=(\d+) code_bytes=(\d+) elapsed_ns=(\d+)',text)
    assert match,(name,'Missing actual counters')
    values=[int(x) for x in match.groups()]
    assert values[0]==0 and (all(value>0 for value in values[1:4]) if mode=='native' else values[1:4]==[0,0,0])
    observations.append(dict(mode=mode,guest_status=values[0],blocks=values[1],segments=values[2],code_bytes=values[3],elapsed_ns=values[4],log_sha256=sha(out/name)))
# Exercise fork/shared mmap, real file/device/socket operations, thread/futex,
# and the explicitly diagnostic125 bridge, not merely an arithmetic hot loop.
run(['xcrun','clang','--target=aarch64-linux-gnu','--ld-path='+str(base/'tool-bin/ld.lld'),'-nostdlib','-static','-ffreestanding','-fno-builtin','-fno-stack-protector','-O2','-Wall','-Wextra','-Werror',lab/'guest/probe.c',lab/'guest/clone.S','-Wl,-e,_start','-o',out/'system-probe.elf'],'system-guest-build.log')
system_observations=[]
for index,mode in enumerate(('interpreter','native')):
    system_root=out/f'system-root-{mode}';system_root.mkdir(mode=0o700)
    (system_root/'probe').write_bytes((out/'system-probe.elf').read_bytes());(system_root/'probe').chmod(0o700)
    env=dict(clean,ISH_JIT='1' if mode=='native' else '0',ISH_AOT_FAMILY='0')
    name=f'system-{index}-{mode}.log';run([out/'control',system_root,mode],name,env)
    results=(system_root/'probe-results.txt').read_text()
    assert '=FAIL' not in results and 'complete=PASS\n' in results
    assert len(results.splitlines())>=15
    (out/f'system-{mode}-results.txt').write_text(results)
    system_observations.append(dict(mode=mode,checks=len(results.splitlines()),all_pass=True,log_sha256=sha(out/name),results_sha256=sha(out/f'system-{mode}-results.txt')))
(out/'evidence.json').write_text(json.dumps(dict(scope='HOST complete pinned optional ARM64 JIT vs gadgets, identical owned arithmetic/memory and syscall ELFs; NOT Steam/CEF/iPad/game/return evidence',linuxrunner=evidence['linuxrunner'],engine_evidence_sha256=sha(build.parent/'evidence.json'),guest_sha256=sha(out/'probe.elf'),system_guest_sha256=sha(out/'system-probe.elf'),control_source_sha256=sha(lab/'tools/native-jit-control.c'),builder_sha256=sha(Path(__file__)),commands=commands,observations=observations,system_observations=system_observations),indent=2)+'\n')
print('HOST identical ARM64 ELF: interpreter/native/interpreter/native results and actual emitter counters PASS')
