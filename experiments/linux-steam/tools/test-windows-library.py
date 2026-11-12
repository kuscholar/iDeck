#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Native layout + exact production Dock discovery METHODS, not Valve execution."""
import argparse,hashlib,json,re,subprocess,shutil
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('fixture_root',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
repo=Path(__file__).resolve().parents[3];lab=repo/'experiments/linux-steam';out=a.output.resolve();root=a.fixture_root.resolve();assert all(str(x).startswith('/Volumes/easystore/') for x in (out,root)) and not out.exists()
assert (root/'MadeiraPrefix/drive_c/SteamLibrary/steamapps/common/Bridge Probe/probe.exe').is_file()
value=re.search(r'static let relativeRoot = "([^"\n]+)"',(repo/'app/Madeira/SteamRuntime.swift').read_text());assert value;client=value.group(1)
out.mkdir(mode=0o700,parents=True);commands=[]
fixture_source=root/'MadeiraPrefix/drive_c/SteamLibrary/steamapps/common/Bridge Probe/probe.exe'
root=out/'scratch-root';game=root/'MadeiraPrefix/drive_c/SteamLibrary/steamapps/common/Bridge Probe';game.mkdir(parents=True);shutil.copy2(fixture_source,game/'probe.exe')
def run(cmd):
 commands.append([str(x) for x in cmd]);result=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=180 if str(cmd[0])=="xcrun" else 20)
 if result.returncode:
  (out/'failed-command.log').write_text(result.stdout);raise RuntimeError('Control failed: '+result.stdout[-2000:])
 return result.stdout
flags=['xcrun','clang','-fobjc-arc','-fblocks','-Wall','-Wextra','-Werror','-DIDECK_LAB_STEAM_WINDOWS_ROOT="'+client+'"','-I'+str(lab/'app')]
run([*flags,lab/'app/LabWindowsLibrary.m',lab/'tools/windows-library-control.m','-framework','Foundation','-o',out/'native-control'])
text=run([out/'native-control',root,out]);(out/'native.log').write_text(text)
# Compile exact existing production discovery methods, no permissive replacement.
source=(repo/'app/Madeira/MadeiraDock.swift').read_text()
def extract(anchor):
 start=source.index(anchor);brace=source.index('{',start);depth=0
 for end in range(brace,len(source)):
  if source[end]=='{':depth+=1
  if source[end]=='}':
   depth-=1
   if not depth:return source[start:end+1]
 raise AssertionError(anchor)
parts=[extract('struct DockGame')]
methods=['validAppID','validFolderName','game','depots','games','libraryRelative']
for n in methods:parts.append(extract('static func '+n+'('))
copy='// Exact selected production methods; original GPL/copyright/exception retained.\n// Copyright 2026 125hz. See source LICENSE-EXCEPTION.md.\nimport Foundation\n'+parts[0]+'\nenum SteamRuntimeFiles { static let relativeRoot = '+json.dumps(client)+' }\nenum MadeiraDock {\n'+'\n'.join(parts[1:])+'\n}\n'
fixture=root/'MadeiraPrefix/drive_c/SteamLibrary/steamapps/appmanifest_1879048193.acf';assert not fixture.exists();fixture.write_text('"AppState" { "appid" "1879048193" "name" "Own Windows Probe" "installdir" "Bridge Probe" "StateFlags" "4" }\n')
copy+='''let drive=URL(fileURLWithPath:CommandLine.arguments[1],isDirectory:true)
let list=MadeiraDock.games(drive:drive)
guard let found=list.first(where:{$0.id==1879048193}),found.library=="SteamLibrary/steamapps",found.windowsInstallPath=="C:\\\\SteamLibrary\\\\steamapps\\\\common\\\\Bridge Probe" else { fatalError("actual Dock discovery missed C-contained fixture") }
print("PASS exact production Dock discovery finds C-contained synthetic manifest; NOT Valve licensing/launch")
'''
(out/'main.swift').write_text(copy)
run(['xcrun','swiftc','-module-cache-path',out/'swift-module-cache',repo/'app/Madeira/SteamKeyValues.swift',out/'main.swift','-o',out/'discovery'])
stdout=run([out/'discovery',root/'MadeiraPrefix/drive_c']);(out/'discovery.log').write_text(stdout)
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();(out/'evidence.json').write_text(json.dumps({'scope':'HOST filesystem preparation + exact selected production Dock parser/discovery methods with synthetic fixture; NOT full MadeiraDock runtime, Steam/client/auth/license/game or iPad proof','commands':commands,'native_output':text,'discovery_output':stdout,'production_Dock_source_sha256':h(repo/'app/Madeira/MadeiraDock.swift'),'parser_source_sha256':h(repo/'app/Madeira/SteamKeyValues.swift'),'extracted_source_sha256':h(out/'main.swift'),'native_helper_sha256':h(lab/'app/LabWindowsLibrary.m'),'client_relativeRoot_from_source':client},indent=2)+'\n');print(text+stdout)
