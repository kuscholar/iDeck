#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""HOST actual ARM64 cached adjacent-page reads across private CoW; no device."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
for n in ('artifacts','archive','output'):p.add_argument(n,type=Path)
a=p.parse_args();repo=Path(__file__).resolve().parents[3];base=a.artifacts.resolve();archive=a.archive.resolve();out=a.output.resolve()
assert str(out).startswith('/Volumes/easystore/') and not out.exists() and archive.is_file()
src=repo/'vendor/LinuxRunner';host=base/'host';lab=repo/'experiments/linux-steam';out.mkdir(mode=0o700)
assert subprocess.check_output(['git','-C',src,'rev-parse','HEAD'],text=True).strip()=='d1419782da2e299fe22f1ddb85c70ae3d1e276b1'
guest=['xcrun','clang','--target=aarch64-linux-gnu','--ld-path='+str(base/'tool-bin/ld.lld'),'-nostdlib','-static','-ffreestanding','-fno-builtin','-fno-stack-protector','-O2','-Wall','-Wextra','-Werror',str(lab/'guest/cow-adjacent-probe.c'),str(lab/'guest/clone.S'),'-Wl,-e,_start','-o',str(out/'probe.elf')]
subprocess.run(guest,check=True)
flags=['-DIDECK_LAB_GUEST_LIFETIME=1','-DIDECK_LAB_NATIVE_LOG=1','-DIDECK_LAB_LAZY_PAGES=1','-fsanitize=address,undefined','-DGUEST_ARM64=1','-DENGINE_ASBESTOS=1','-DLOG_HANDLER_DPRINTF=1','-DISH_INTERNAL=1','-I'+str(src),'-I'+str(host),'-I'+str(lab/'app'),'-Wall','-Wextra','-Werror','-Wno-unused-parameter']
cmd=['xcrun','clang',*flags,*[str(lab/'app'/n) for n in ['LinuxLabRuntime.c','LabDeviceFS.c','LabBridge.c','LaunchProtocol.c','NativeKernelLog.c']],str(lab/'tools/cow-guest-control.c'),str(archive),'-L'+str(host),'-lish_emu','-lfakefs','-lsqlite3','-o',str(out/'control')]
subprocess.run(cmd,check=True);root=out/'root';root.mkdir(mode=0o700);logs=out/'logs';logs.mkdir(mode=0o700)
(root/'probe').write_bytes((out/'probe.elf').read_bytes());(root/'probe').chmod(0o700)
with (out/'control.log').open('x') as f:r=subprocess.run([out/'control',root,logs],stdout=f,stderr=subprocess.STDOUT,env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0'),timeout=40)
lines=(root/'cow-adjacent-results.txt').read_text().splitlines() if (root/'cow-adjacent-results.txt').exists() else []
assert not r.returncode and len(lines)==4 and all(x.endswith('=PASS') for x in lines),(r.returncode,lines)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(out/'evidence.json').write_text(json.dumps({'scope':'HOST actual ARM64 interpreter concurrent cached adjacent reads/CoW/fork. Changed memory and wrappers sanitized, engine not; NOT CEF/Air/stability proof','guest_compile':guest,'host_compile':cmd,'guest_sha256':sha(out/'probe.elf'),'archive_sha256':sha(archive),'log_sha256':sha(out/'control.log'),'exit':r.returncode,'checks':lines},indent=2)+'\n')
print('HOST actual ARM64 adjacent cached reads/CoW/fork/joins PASS')
