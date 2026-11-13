#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Actual fakefs empty-probe retirement and realfs mount; no Steam/device claim."""
import argparse,hashlib,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('artifacts',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
repo=Path(__file__).resolve().parents[3];lab=repo/'experiments/linux-steam';host=a.artifacts.resolve()/'host';src=repo/'vendor/LinuxRunner';out=a.output.resolve();assert str(out).startswith('/Volumes/easystore/') and not out.exists();out.mkdir(mode=0o700,parents=True)
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();before={n:h(host/n) for n in ('libish.a','libish_emu.a','libfakefs.a')};commands=[];results=[]
sources=[lab/'app/SharedSteamLibrary.c',lab/'app/LabDeviceFS.c',lab/'tools/empty-probe-control.c']
for enabled,modes in [(0,['legacy','empty']),(1,['legacy','partial','empty','file','other'])]:
 exe=out/('control'+str(enabled));cmd=['xcrun','clang','-fsanitize=address,undefined','-fno-sanitize-recover=all','-DGUEST_ARM64=1','-DENGINE_ASBESTOS=1','-DLOG_HANDLER_DPRINTF=1','-DISH_INTERNAL=1','-DIDECK_LAB_DOCK_STORAGE=1','-DIDECK_LAB_RETIRE_EMPTY_PROBE='+str(enabled),'-I'+str(src),'-I'+str(host),'-I'+str(lab/'app'),'-Wall','-Wextra','-Werror','-Wno-unused-parameter',*[str(x) for x in sources],*[str(host/n) for n in before],'-lsqlite3','-o',str(exe)]
 commands.append(cmd);subprocess.run(cmd,check=True,timeout=120)
 for mode in modes:
  root=out/(str(enabled)+'-'+mode);native=root/'MadeiraPrefix/drive_c/SteamLibrary';native.mkdir(parents=True);(native/'native-sentinel').write_text('native-library');log=out/(root.name+'.log')
  with log.open('x') as f:r=subprocess.run([exe,root,mode,str(enabled)],stdout=f,stderr=subprocess.STDOUT,timeout=15)
  results.append({'enabled':enabled,'case':mode,'returncode':r.returncode,'log_sha256':h(log)});assert r.returncode==0,log.read_text()[-2000:]
assert before=={n:h(host/n) for n in before}
(out/'evidence.json').write_text(json.dumps({'scope':'HOST actual fakefs/VFS empty-directory cleanup + realfs source mount; ASan/UBSan own wrappers, static deps not sanitizer rebuilt; NO files removed, no Steam/iPad/game validation','results':results,'commands':commands,'input_archives_before_after':before,'source_sha256':{str(x.relative_to(repo)):h(x) for x in sources}},indent=2)+'\n');print(json.dumps(results))
