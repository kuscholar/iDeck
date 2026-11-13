#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Actual fakefs registration + ARM64 guest reads + existing native KV parser."""
import argparse,hashlib,json,subprocess,time
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('artifacts',type=Path);p.add_argument('output',type=Path);p.add_argument('--ld-lld',type=Path,required=True);p.add_argument('--retire-empty-probe',action='store_true')
a=p.parse_args();base=a.artifacts.resolve();out=a.output.resolve();repo=Path(__file__).resolve().parents[3];lab=repo/'experiments/linux-steam';src=repo/'vendor/LinuxRunner';host=base/'host'
assert str(out).startswith('/Volumes/easystore/') and not out.exists();out.mkdir(mode=0o700,parents=True)
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();archives={n:h(host/n) for n in ('libish.a','libish_emu.a','libfakefs.a')};commands=[]
def run(cmd):
 commands.append([str(x) for x in cmd]);subprocess.run(cmd,check=True,timeout=180)
run(['xcrun','clang','--target=aarch64-linux-gnu','--ld-path='+str(a.ld_lld.absolute()),'-nostdlib','-static','-ffreestanding','-fno-builtin','-fno-stack-protector','-O2','-Wall','-Wextra','-Werror',lab/'guest/library-registration-probe.c','-Wl,-e,_start','-o',out/'probe'])
sources=[lab/'app'/n for n in ('SharedLibraryConfig.c','SharedLibraryRegister.c','SharedSteamLibrary.c','LabDeviceFS.c')]+[lab/'tools/library-registration-control.c']
run(['xcrun','clang','-fsanitize=address,undefined','-fno-sanitize-recover=all','-DGUEST_ARM64=1','-DENGINE_ASBESTOS=1','-DISH_INTERNAL=1','-DLOG_HANDLER_DPRINTF=1','-DIDECK_LAB_DOCK_STORAGE=1','-DIDECK_LAB_RETIRE_EMPTY_PROBE='+str(int(a.retire_empty_probe)),'-I'+str(src),'-I'+str(host),'-I'+str(lab/'app'),'-Wall','-Wextra','-Werror','-Wno-unused-parameter',*sources,host/'libish.a',host/'libish_emu.a',host/'libfakefs.a','-lsqlite3','-o',out/'control'])
results=[]
for phase in ('fresh','merge','interrupted'):
 root=out/phase;root.mkdir();start=time.monotonic()
 with (out/(phase+'.log')).open('x') as f:r=subprocess.run([out/'control',root,out/'probe',phase,out/(phase+'.vdf')],stdout=f,stderr=subprocess.STDOUT,timeout=20)
 results.append({'phase':phase,'returncode':r.returncode,'seconds':round(time.monotonic()-start,3),'log_sha256':h(out/(phase+'.log'))})
 if r.returncode:raise RuntimeError((out/(phase+'.log')).read_text()[-2000:])
swift='''import Foundation
for name in ["fresh","merge"] {
    let file=URL(fileURLWithPath:CommandLine.arguments[1]).appendingPathComponent(name+".vdf")
    var parser=try SteamKeyValues(Data(contentsOf:file))
    let libraries=try parser.read()["libraryfolders"]!.fields
    precondition(libraries["0"]?["path"]?.string=="/Steam")
    precondition(libraries.values.contains(where:{$0["path"]?.string=="/mnt/ideck/SteamLibrary"}))
    if name=="merge" { precondition(libraries["2"]?["path"]?.string=="/Other Library");precondition(libraries["2"]?["unknown"]?.string=="keep me") }
}
print("PASS actual existing SteamKeyValues reader sees default, retained and shared library entries; NOT Valve client validation")
''';(out/'main.swift').write_text(swift)
run(['xcrun','swiftc','-module-cache-path',out/'module-cache',repo/'app/Madeira/SteamKeyValues.swift',out/'main.swift','-o',out/'kv-control'])
parser=subprocess.check_output([out/'kv-control',out],text=True);assert archives=={n:h(host/n) for n in archives}
(out/'evidence.json').write_text(json.dumps({'scope':'HOST actual fakefs/realfs registration + own ARM64 ELF read + exact existing native KV parser; own wrappers ASan/UBSan, static dependencies not instrumented; NOT real Steam acceptance/download, iPad or game execution','retire_empty_probe':a.retire_empty_probe,'results':results,'parser_output':parser,'commands':commands,'archives_before_after':archives,'sources_sha256':{str(p.relative_to(repo)):h(p) for p in sources},'probe_sha256':h(out/'probe')},indent=2)+'\n');print(json.dumps(results));print(parser)
