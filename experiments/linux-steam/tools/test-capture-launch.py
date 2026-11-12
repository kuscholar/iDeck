#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Actual ARM64 device IPC captures a bounded request using real shared storage.
The own Windows PE fixture is inspected, NEVER executed or treated as a game.
"""
import argparse,hashlib,json,subprocess,shutil,time
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--capture-off',action='store_true',help='Check actual IPC/file observation without request capture')
p.add_argument('--dock-storage',action='store_true',help='Use new physical Windows drive_c shared source and mapped metadata')
p.add_argument('artifacts',type=Path);p.add_argument('output',type=Path);p.add_argument('--ld-lld',type=Path,required=True);p.add_argument('--mingw',type=Path,required=True)
a=p.parse_args();base=a.artifacts.resolve();out=a.output.resolve();repo=Path(__file__).resolve().parents[3];src=repo/'vendor/LinuxRunner';lab=repo/'experiments/linux-steam';host=base/'host';h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert all(str(x).startswith('/Volumes/easystore/') for x in (base,out)) and not out.exists()
assert subprocess.check_output(['git','-C',str(src),'rev-parse','HEAD'],text=True).strip()=='d1419782da2e299fe22f1ddb85c70ae3d1e276b1'
assert not subprocess.check_output(['git','-C',str(src),'status','--porcelain','--untracked-files=no'],text=True).strip()
before={n:h(host/n) for n in ('libish.a','libish_emu.a','libfakefs.a')};out.mkdir(mode=0o700,parents=True);commands=[]
def run(cmd):commands.append([str(x) for x in cmd]);subprocess.run(cmd,check=True)
run([a.mingw.absolute(),'-nostdlib','-Wl,-entry,mainCRTStartup','-Wall','-Wextra','-Werror',lab/'guest/windows-exit-probe.c','-lkernel32','-o',out/'own-windows-probe.exe'])
run(['xcrun','clang','--target=aarch64-linux-gnu','--ld-path='+str(a.ld_lld.absolute()),'-nostdlib','-static','-ffreestanding','-fno-builtin','-fno-stack-protector','-O2','-Wall','-Wextra','-Werror','-I'+str(lab/'app'),lab/'guest/capture-launch-probe.c','-Wl,-e,_start','-o',out/'probe'])
sources=[lab/'app'/n for n in ('LinuxLabRuntime.c','LabDeviceFS.c','LabBridge.c','LaunchProtocol.c','SharedSteamLibrary.c','GameFiles.c','GameFilePolicy.c','WindowsLaunchMap.c')]+[lab/'tools/capture-launch-control.c']
run(['xcrun','clang','-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer','-DGUEST_ARM64=1','-DENGINE_ASBESTOS=1','-DLOG_HANDLER_DPRINTF=1','-DISH_INTERNAL=1','-DIDECK_LAB_DOCK_STORAGE='+str(int(a.dock_storage)),'-DIDECK_LAB_SHARED_LIBRARY=1','-DIDECK_LAB_GAME_FILE_POLICY=1','-DIDECK_LAB_CAPTURE_LAUNCH='+str(int(not a.capture_off)),'-I'+str(src),'-I'+str(host),'-I'+str(lab/'app'),'-Wall','-Wextra','-Werror','-Wno-unused-parameter',*sources,host/'libish.a',host/'libish_emu.a',host/'libfakefs.a','-lsqlite3','-o',out/'control'])
root=out/'scratch-root';(root/'data').mkdir(parents=True);game=root/('MadeiraPrefix/drive_c/SteamLibrary/steamapps/common/Bridge Probe' if a.dock_storage else 'SharedSteamLibrary/steamapps/common/Bridge Probe');game.mkdir(parents=True);shutil.copy2(out/'own-windows-probe.exe',game/'probe.exe');shutil.copy2(out/'probe',root/'probe')
default=root/'data/Steam/steamapps/common/Default Probe';default.mkdir(parents=True);shutil.copy2(out/'own-windows-probe.exe',default/'probe.exe')
t=time.monotonic()
with (out/'control.log').open('xb') as log:r=subprocess.run([out/'control',root],stdout=log,stderr=log,timeout=20)
assert before=={n:h(host/n) for n in before}
e={'scope':'Actual HOST ARM64 ELF -> /dev/ideck-madeira -> native shared-files inspection/capture. Wrapper/helper ASan/UBSan; static deps not instrumented. Own Windows PE NOT executed, NO Steam/game/licensing/iPad proof','dock_storage':a.dock_storage,'capture_enabled':not a.capture_off,'exit_code':r.returncode,'seconds':round(time.monotonic()-t,3),'commands':commands,'input_archives_before_after':before,'source_sha256':{str(x.relative_to(repo)):h(x) for x in [*sources,lab/'guest/capture-launch-probe.c',lab/'guest/windows-exit-probe.c']},'guest_probe_sha256':h(out/'probe'),'Windows_fixture_sha256':h(out/'own-windows-probe.exe'),'log_sha256':h(out/'control.log'),'Windows_fixture_executed':False}
(out/'evidence.json').write_text(json.dumps(e,indent=2)+'\n');print('actual capture-control exit',r.returncode);assert not r.returncode
