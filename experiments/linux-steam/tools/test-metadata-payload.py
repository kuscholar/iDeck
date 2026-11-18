#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Run synthetic translated ARM64 metadata/guard/payload isolation on HOST.

Read-only prepared qualified kernel archive, fresh private root only. Does not
use Steam files, stop the Air session, rebuild a kernel or change any limits.
"""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
for name in ('artifacts','archive','output'):p.add_argument(name,type=Path)
p.add_argument('--pure-spin',action='store_true',help='Reader/fork sibling waits use bounded pure guest atomic loads, no nanosleep refresh; discard trylock may select original fallback')
a=p.parse_args();repo=Path(__file__).resolve().parents[3];lab=repo/'experiments/linux-steam';base=a.artifacts.resolve();archive=a.archive.resolve();out=a.output.resolve();src=repo/'vendor/LinuxRunner';host=base/'host'
assert str(out).startswith('/Volumes/easystore/') and not out.exists() and archive.is_file()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before=sha(archive)
assert subprocess.check_output(['git','-C',src,'rev-parse','HEAD'],text=True).strip()=='d1419782da2e299fe22f1ddb85c70ae3d1e276b1'
out.mkdir(mode=0o700,parents=True)
guest=['xcrun','clang','--target=aarch64-linux-gnu','--ld-path='+str(base/'tool-bin/ld.lld'),'-nostdlib','-static','-ffreestanding','-fno-builtin','-fno-stack-protector','-O2','-Wall','-Wextra','-Werror',str(lab/'guest/metadata-payload-probe.c'),str(lab/'guest/clone.S'),'-Wl,-e,_start','-o',str(out/'probe.elf')]
if a.pure_spin:guest+=['-DIDECK_METADATA_PURE_SPIN=1']
with (out/'guest-build.log').open('x') as f:subprocess.run(guest,stdout=f,stderr=subprocess.STDOUT,check=True)
flags=['-DIDECK_LAB_GUEST_LIFETIME=1','-DIDECK_LAB_NATIVE_LOG=1','-DIDECK_LAB_LAZY_PAGES=1','-DIDECK_LAB_PRIVATE_DISCARD=1','-fsanitize=address,undefined','-fno-sanitize-recover=all','-DGUEST_ARM64=1','-DENGINE_ASBESTOS=1','-DLOG_HANDLER_DPRINTF=1','-DISH_INTERNAL=1','-I'+str(src),'-I'+str(host),'-I'+str(lab/'app'),'-Wall','-Wextra','-Werror','-Wno-unused-parameter']
if a.pure_spin:flags+=['-DIDECK_METADATA_PURE_SPIN=1']
command=['xcrun','clang',*flags,*[str(lab/'app'/n) for n in ['LinuxLabRuntime.c','LabDeviceFS.c','LabBridge.c','LaunchProtocol.c','NativeKernelLog.c']],str(lab/'tools/metadata-payload-control.c'),str(archive),'-L'+str(host),'-lish_emu','-lfakefs','-lsqlite3','-o',str(out/'control')]
with (out/'host-build.log').open('x') as f:subprocess.run(command,stdout=f,stderr=subprocess.STDOUT,check=True)
root=out/'root';root.mkdir(mode=0o700);logs=out/'logs';logs.mkdir(mode=0o700);(root/'probe').write_bytes((out/'probe.elf').read_bytes());(root/'probe').chmod(0o700)
with (out/'control.log').open('x') as f:r=subprocess.run([out/'control',root,logs],stdout=f,stderr=subprocess.STDOUT,timeout=45,env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0'))
lines=(root/'metadata-payload-results.txt').read_text().splitlines() if (root/'metadata-payload-results.txt').exists() else []
assert sha(archive)==before
(out/'evidence.json').write_text(json.dumps({'scope':'HOST actual ARM64 synthetic VM layout, untouchedmetadata/guard beside payload through privateCoW/advice/protection and concurrent cachedreads. Changed kernel/wrappers sanitizer qualified; not all dependencies/engine. NOT actual Chromium allocator, Air reproduction, CEF fix, UI or game/stability proof','pure_guest_spin_waits':a.pure_spin,'discard_path_qualification':'Pure guest reader may hold read lock, so trylock can select original fallback; actual count reported, no required optimization coverage' if a.pure_spin else 'Actual exclusive replacements required; broker release/advice exercised','exit':r.returncode,'checks':lines,'guest_compile':guest,'host_compile':command,'guest_sha256':sha(out/'probe.elf'),'kernel_archive_sha256':before,'kernel_archive_unchanged':True,'log_sha256':sha(out/'control.log'),'source_sha256':{x.name:sha(x) for x in [lab/'guest/metadata-payload-probe.c',lab/'tools/metadata-payload-control.c']}},indent=2)+'\n')
assert not r.returncode and len(lines)==7 and all(l.endswith('=PASS') for l in lines),(r.returncode,lines)
print('HOST actual ARM64 metadata/guard/payload coherence control PASS; narrow synthetic test, not CEF/Air proof')
