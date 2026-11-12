#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Actual ARM64 ELF/fakefs->realfs/native roundtrip; scratch data, no Steam ownership."""
import argparse,hashlib,json,subprocess,time
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--runtime-entry',action='store_true',help='Exercise actual LinuxLabRuntime entry on a scratch realfs root')
p.add_argument('artifacts',type=Path);p.add_argument('output',type=Path);p.add_argument('--ld-lld',type=Path,required=True)
a=p.parse_args();base=a.artifacts.resolve();out=a.output.resolve();repo=Path(__file__).resolve().parents[3];src=repo/'vendor/LinuxRunner';lab=repo/'experiments/linux-steam';host=base/'host'
assert all(str(x).startswith('/Volumes/easystore/') for x in (base,out)) and not out.exists()
assert subprocess.check_output(['git','-C',str(src),'rev-parse','HEAD'],text=True).strip()=='d1419782da2e299fe22f1ddb85c70ae3d1e276b1'
assert not subprocess.check_output(['git','-C',str(src),'status','--porcelain','--untracked-files=no'],text=True).strip()
out.mkdir(mode=0o700,parents=True);commands=[]
hashof=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
input_hashes={name:hashof(host/name) for name in ('libish.a','libish_emu.a','libfakefs.a')}
def run(cmd):commands.append([str(x) for x in cmd]);subprocess.run(cmd,check=True)
run(['xcrun','clang','--target=aarch64-linux-gnu','--ld-path='+str(a.ld_lld.absolute()),'-nostdlib','-static','-ffreestanding','-fno-builtin','-fno-stack-protector','-O2','-Wall','-Wextra','-Werror',lab/'guest/shared-library-probe.c','-Wl,-e,_start','-o',out/'probe'])
control_sources=[lab/'app/SharedSteamLibrary.c',lab/'app/LabDeviceFS.c']
if a.runtime_entry:control_sources += [lab/'app/LinuxLabRuntime.c',lab/'app/LabBridge.c',lab/'app/LaunchProtocol.c',lab/'tools/host-embed.c']
else:control_sources += [lab/'tools/shared-library-control.c']
run(['xcrun','clang','-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer','-DGUEST_ARM64=1','-DENGINE_ASBESTOS=1','-DLOG_HANDLER_DPRINTF=1','-DISH_INTERNAL=1','-DIDECK_LAB_SHARED_LIBRARY=1','-I'+str(src),'-I'+str(host),'-I'+str(lab/'app'),'-Wall','-Wextra','-Werror','-Wno-unused-parameter',*control_sources,host/'libish.a',host/'libish_emu.a',host/'libfakefs.a','-lsqlite3','-o',out/'control'])
root=out/'scratch-root';root.mkdir();shared=root/'SharedSteamLibrary';shared.mkdir();results=[]
if a.runtime_entry:
 import shutil
 shutil.copy2(out/'probe',root/'probe')
for phase,seed,installed,result in [('first',b'native-first',b'guest-first!',b'first-pass!!'),('again',b'native-again',b'guest-again!',b'again-pass!!')]:
 (shared/'native-seed').write_bytes(seed);t=time.monotonic()
 with (out/(phase+'.log')).open('xb') as log:r=subprocess.run([out/'control',root] if a.runtime_entry else [out/'control',root,out/'probe'],stdout=log,stderr=log,timeout=20)
 row={'phase':phase,'native_status':r.returncode,'seconds':round(time.monotonic()-t,3)};results.append(row)
 if not r.returncode:
  assert (shared/'Guest Download/installed').read_bytes()==installed
  assert not (shared/'Guest Download/staging').exists()
  assert (shared/'child-write').read_bytes()==b'child-joined'
  assert (shared/'roundtrip-pass').read_bytes()==result
  row['native_reads_guest_writes_and_rename']=True
 else:break
h=hashof
assert input_hashes=={name:hashof(host/name) for name in input_hashes},'Static dependencies changed during test'
e={'scope':'Actual HOST ARM64 ELF with separate realfs library; runtime-entry uses realfs root, custom control fakefs root; wrappers ASan/UBSan, static dependencies not sanitizer rebuilt. Two serial NATIVE processes, NOT same-app runtime restart, iPad, Steam depot/ownership, game or Wine proof','results':results,'commands':commands,'runtime_entry':a.runtime_entry,'input_archive_hashes_before_and_after':input_hashes,'probe_sha256':h(out/'probe'),'source_sha256':{str(x.relative_to(repo)):h(x) for x in [*control_sources,lab/'guest/shared-library-probe.c']},'logs':{phase:h(out/(phase+'.log')) for phase in ['first','again'] if (out/(phase+'.log')).exists()}}
(out/'evidence.json').write_text(json.dumps(e,indent=2)+'\n')
assert len(results)==2 and all(x['native_status']==0 for x in results),results
print(json.dumps(results))
