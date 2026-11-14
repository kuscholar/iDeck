#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Real Dock manifest parser/model + Lab request selection, no login or runtime."""
import argparse,hashlib,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);a=p.parse_args()
out=a.output.resolve();repo=Path(__file__).resolve().parents[3];lab=repo/'experiments/linux-steam';dock=repo/'app/Madeira/MadeiraDock.swift'
assert str(out).startswith('/Volumes/easystore/') and not out.exists();out.mkdir(mode=0o700,parents=True)
source=dock.read_text()
def extract(signature,end):
 start=source.index(signature);stop=source.index(end,start)+len(end);return source[start:stop]
model=extract('struct DockGame:', '\n}')
appid_line=next(line for line in source.splitlines() if line.startswith('    static func validAppID('))
methods=appid_line+'\n'+'\n'.join(extract(s,'\n    }') for s in ['    static func validFolderName(', '    static func game(manifest'])
generated='// Pinned iDeck Madeira Dock GPL source; Copyright2026 125hz; Converter Exception retained.\nimport Foundation\n'+model+'\nenum MadeiraDock {\n'+methods+'\n}\n'
(out/'DockManifest.swift').write_text(generated)
option_source=repo/'app/Madeira/SwiftSteam/Library/SteamAppInfo.swift'
option_text=option_source.read_text();start=option_text.index('struct SteamLaunchOption:');end=option_text.index('\n}',start)+2
(out/'SteamLaunchOption.swift').write_text('// GPL-3.0-or-later; Copyright2026 125hz; Converter Exception retained.\nimport Foundation\n'+option_text[start:end]+'\n')
main=r'''import Foundation
let manifest = #"""
"AppState" { "appid" "480" "name" "Fixture" "installdir" "Game Folder" "StateFlags" "4" "CheckGuid" { "fixture" "1" } }
"""#.data(using:.utf8)!
let game=MadeiraDock.game(manifest:manifest,library:"SteamLibrary/steamapps")!
precondition(game.installed && game.customExecutables)
let install=game.windowsInstallPath,exe=install+"\\Game.exe"
let args=[exe,"--label","two words","",#"literal \"quote\""#,"你好"]
let plan=try LabDockSelection.resolve(appID:480,install:install,executable:exe,workingDirectory:install,arguments:args,installedGames:[game])
precondition(plan.game==game && plan.arguments==args && plan.executable==exe)
var cases=0
func rejects(_ id:UInt32=480,_ path:String?=nil,_ executable:String?=nil,_ working:String?=nil,_ arguments:[String]?=nil,_ games:[DockGame]?=nil) {
    do { _=try LabDockSelection.resolve(appID:id,install:path ?? install,executable:executable ?? exe,workingDirectory:working ?? install,arguments:arguments ?? args,installedGames:games ?? [game]);fatalError("Contradictory request accepted") }
    catch { cases+=1 }
}
rejects(0);rejects(UInt32.max);rejects(481);rejects(games:[])
rejects(480,nil,nil,nil,nil,[game,game])
let pending=MadeiraDock.game(manifest:Data(String(data:manifest,encoding:.utf8)!.replacingOccurrences(of:"\"4\"",with:"\"2\"").utf8),library:game.library)!
rejects(480,nil,nil,nil,nil,[pending])
rejects(480,install+"other");rejects(480,nil,exe+".txt")
rejects(480,nil,install+"\\..\\Other.exe")
rejects(480,nil,nil,install+"\\..")
rejects(480,nil,nil,nil,[]);rejects(480,nil,nil,nil,[exe+"wrong"])
rejects(480,nil,nil,nil,[exe,String(repeating:"x",count:4096)])
rejects(480,nil,nil,nil,[exe,"a\0b"])
let ordinary=MadeiraDock.game(manifest:manifest,library:"Program Files (x86)/Steam/steamapps")!
rejects(480,nil,nil,nil,nil,[ordinary])
let mixed=try LabDockSelection.resolve(appID:480,install:install.lowercased(),executable:exe,workingDirectory:install,arguments:args,installedGames:[game])
precondition(mixed.arguments==args && mixed.game.customExecutables)
print("HOST exact real Dock manifest/model;1 matched request,15 contradictions rejected; arguments/custom-executable metadata retained PASS")
precondition(cases==15)
let tail=#"--label "two words" "" "literal \\\"quote\\\"" 你好"#
precondition(LabDockSelection.argumentVector(tail)==Array(args.dropFirst()))
let options=SteamLaunchOption.parse(["7":["executable":"Game.exe","arguments":tail,"workingdir":".","config":["oslist":"windows"]],"19":["executable":"Other.exe"]])
let selectedIndex=try plan.launchOption(appID:480,options:options)
precondition(selectedIndex==7)
var wrong=options[0];wrong.arguments="--wrong"
var legacy=options[0];legacy.index=nil
var linux=options[0];linux.oslist="linux"
var beta=options[0];beta.betaKey="beta"
var dlc=options[0];dlc.requiredDLC="123"
var folder=options[0];folder.workingDir="subfolder"
var duplicate=options[0];duplicate.index=29
var rejected=0
for list in [[wrong],[legacy],[linux],[beta],[dlc],[folder],[options[0],duplicate]] {
    do { _=try plan.launchOption(appID:480,options:list);fatalError("Mismatched launch option selected") } catch { rejected+=1 }
}
precondition(rejected==7 && LabDockSelection.argumentVector("\"unfinished")==nil)
precondition(LabDockSelection.argumentVector(#""a""b""#)==["a\"b"])
func quoteWindows(_ value:String)->String {
    var out="\"",slashes=0
    for c in value {
        if c=="\\" { slashes+=1;continue }
        if c=="\"" { out+=String(repeating:"\\",count:2*slashes+1)+"\"" }
        else { out+=String(repeating:"\\",count:slashes)+String(c) }
        slashes=0
    }
    return out+String(repeating:"\\",count:2*slashes)+"\""
}
let vectors=["","two words","tab\tvalue","你好",#"C:\trailing\"#,#"a\\\"b"#,#""quote""#]
for a in vectors { for b in vectors {
    precondition(LabDockSelection.argumentVector(quoteWindows(a)+" "+quoteWindows(b))==[a,b])
}}
precondition(LabDockSelection.argumentVector("line\nnext")==nil)
precondition(LabDockSelection.argumentVector(String(repeating:"a ",count:32))==nil)
print("HOST real Valve config.launch parser: sparse index7 matched,7 contradictions rejected, no array-offset/default-index fallback PASS")
print("HOST49 argument-tail round trips preserve Unicode/empty/tab/space/quotes/trailing-backslashes PASS")
func fixed<T>(_ string:String,_ field:inout T) {
    withUnsafeMutableBytes(of:&field) { bytes in
        let encoded=Array(string.utf8)+[UInt8(0)];precondition(encoded.count<=bytes.count)
        bytes.initializeMemory(as:UInt8.self,repeating:0)
        bytes.copyBytes(from:encoded)
    }
}
var input=ideck_launch_request();input.magic=0x314b4449;input.version=1;input.appid=480;input.verb=1;input.argc=4
let guestInstall="/mnt/ideck/SteamLibrary/steamapps/common/Game Folder",guestExe=guestInstall+"/Game.exe"
fixed(guestInstall,&input.install);fixed(guestExe,&input.executable);fixed(guestInstall,&input.working)
let guestArgs=[guestExe,"--label","two words",""];let bytes=guestArgs.map{$0+"\0"}.joined()
fixed(bytes,&input.arguments);input.argument_bytes=UInt32(bytes.utf8.count)
let frame=withUnsafeBytes(of:input){Data($0)}
let decoded=try LabDockRequest(frame:frame)
precondition(decoded.verb==1 && decoded.appID==480 && decoded.arguments==[exe,"--label","two words",""])
let realSelection=try decoded.select(installedGames:[game]);precondition(realSelection.game==game)
var mutated=frame;mutated[8]=0;mutated[9]=0;mutated[10]=0;mutated[11]=0
for bad in [mutated,frame.dropLast(),frame+Data([0])] {
    do { _=try LabDockRequest(frame:Data(bad));fatalError("Invalid raw request accepted") } catch {}
}
precondition(decoded.appID==480 && decoded.arguments==realSelection.arguments)
let receive: (Data,UInt64)->Int32 = { bytes,sequence in bytes.withUnsafeBytes { ideck_test_call_dock_receiver($0.baseAddress,$0.count,sequence) } }
precondition(ideckLabReceiveDockRequest(nil,8216,1) == -22)
precondition(receive(frame,0) == -22 && receive(mutated,1) == -22)
precondition(receive(frame,1) == 0 && receive(frame,1) == -116 && receive(frame,2) == -16)
precondition(ideck_lab_pending_dock_sequence()==1)
precondition(LabDockPending.shared.snapshot()?.request.arguments == decoded.arguments)
precondition(LabDockPending.shared.discard(sequence:2) == -116)
precondition(LabDockPending.shared.discard(sequence:1) == 0)
precondition(receive(frame,1) == -116 && receive(frame,2) == 0)
precondition(LabDockPending.shared.discard(sequence:2) == 0)
precondition(ideck_lab_pending_dock_sequence()==0)
let dispatcher=LabDockPending()
let untouched=try dispatcher.launchOption(for:game,options:nil,fallback:19,installedGames:{fatalError("Ordinary fallback must not query shared files")})
precondition(untouched==19 && dispatcher.stage(decoded,sequence:1)==0)
let nativeOptions=SteamLaunchOption.parse(["11":["executable":"Game.exe","arguments":#"--label "two words" """#,"workingdir":".","config":["oslist":"windows"]]])
let exact=try dispatcher.launchOption(for:game,options:nativeOptions,fallback:19,installedGames:{[game]})
precondition(exact==11 && dispatcher.snapshot()?.sequence==1)
var refusals=0
for entry in [0,1,2] {
    do {
        _=try dispatcher.launchOption(for:game,options:entry==0 ? nil : entry==1 ? options : nativeOptions,fallback:0,installedGames:{entry==2 ? [] : [game]})
        fatalError("Native Dock must not fallback for a captured mismatched request")
    }catch{refusals+=1}
}
precondition(refusals==3 && dispatcher.snapshot()?.sequence==1)
let slot=LabDockPending(),raceLock=NSLock();var results:[Int32]=[]
DispatchQueue.concurrentPerform(iterations:8) { i in
    let result=slot.stage(decoded,sequence:UInt64(i+1))
    raceLock.lock();results.append(result);raceLock.unlock()
}
precondition(results.filter{$0==0}.count == 1 && slot.snapshot()?.request.appID==480)
print("HOST real8216byteCrequest->productionCmapper->ownedSwiftrequest->realDockmanifest selection PASS; source mutation cannot change owned snapshot")
print("HOST native C ABI staging, duplicate/stale/busy checks and eight-writer single-slot ownership PASS; no game dispatch")
print("HOST existing Dock option-dispatch adapter preserves ordinary fallback, selects real key11 and refuses missing/mismatched metadata before auth transfer PASS")
'''
# Swift labels are omitted by this local helper to keep table cases compact.
main=main.replace('rejects(games:[])','rejects(480,nil,nil,nil,nil,[])')
(out/'main.swift').write_text(main)
objects=[]
for unit in ['LaunchProtocol','WindowsLaunchMap']:
 obj=out/(unit+'.o');subprocess.run(['xcrun','clang','-Wall','-Wextra','-Werror','-fsanitize=undefined','-I'+str(lab/'app'),'-c',str(lab/'app'/(unit+'.c')),'-o',str(obj)],check=True);objects.append(str(obj))
caller=out/'caller.o';subprocess.run(['xcrun','clang','-Wall','-Wextra','-Werror','-fsanitize=undefined','-I'+str(lab/'app'),'-c',str(lab/'tools/dock-request-call-control.c'),'-o',str(caller)],check=True);objects.append(str(caller))
header=out/'Control-Bridging-Header.h';header.write_text('#include "'+str(lab/'app/WindowsLaunchMap.h')+'"\n#include "'+str(lab/'app/LabDockRequestBridge.h')+'"\nint32_t ideck_test_call_dock_receiver(const void *,size_t,uint64_t);\n')
cmd=['xcrun','swiftc','-sanitize=undefined','-import-objc-header',str(header),'-module-cache-path',str(out/'module-cache'),str(out/'DockManifest.swift'),str(out/'SteamLaunchOption.swift'),str(repo/'app/Madeira/SteamKeyValues.swift'),str(lab/'app/LabDockSelection.swift'),str(lab/'app/LabDockRequest.swift'),str(out/'main.swift'),*objects,'-o',str(out/'control')]
subprocess.run(cmd,check=True,timeout=180)
r=subprocess.run([out/'control'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=20);(out/'control.log').write_text(r.stdout);assert not r.returncode,r.stdout
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(out/'evidence.json').write_text(json.dumps({'scope':'HOST real8216byte C frame/production C protocol+mapper->owned Swift request->production Dock model/option parsing; not files/ownership/auth/runtime/writer lease/game proof','exit':r.returncode,'command':cmd,'production_dock_sha256':sha(dock),'parser_sha256':sha(repo/'app/Madeira/SteamKeyValues.swift'),'production_option_sha256':sha(option_source),'extracted_option_sha256':sha(out/'SteamLaunchOption.swift'),'selection_sha256':sha(lab/'app/LabDockSelection.swift'),'request_adapter_sha256':sha(lab/'app/LabDockRequest.swift'),'protocol_sha256':sha(lab/'app/LaunchProtocol.c'),'mapping_sha256':sha(lab/'app/WindowsLaunchMap.c'),'fixture_sha256':sha(out/'main.swift'),'log_sha256':sha(out/'control.log')},indent=2)+'\n')
print(r.stdout)
