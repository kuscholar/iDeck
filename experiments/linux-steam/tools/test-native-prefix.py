#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Real Lab binding + exact installer destination method, not network/Wine/device."""
import argparse, hashlib, json, subprocess
from pathlib import Path

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('output',type=Path)
a=p.parse_args();out=a.output.resolve();repo=Path(__file__).resolve().parents[3];lab=repo/'experiments/linux-steam'
assert str(out).startswith('/Volumes/easystore/') and not out.exists()
out.mkdir(parents=True,mode=0o700)
source=(repo/'app/Madeira/SteamRuntime.swift').read_text()
start=source.index('    static func validPath(')
end=source.index('\n    // Parse the central directory',start)
methods=source[start:end]
main='''import Foundation
enum SteamRuntimeFiles {
    enum Failure: Error { case conflict }
'''+methods+'''\n}
let base=URL(fileURLWithPath:CommandLine.arguments[1],isDirectory:true)
let root=base.appendingPathComponent("root",isDirectory:true)
let docs=base.appendingPathComponent("documents",isDirectory:true)
let physical=root.appendingPathComponent("MadeiraPrefix",isDirectory:true)
let fm=FileManager.default
try fm.createDirectory(at:physical.appendingPathComponent("drive_c/Program Files (x86)/Steam"),withIntermediateDirectories:true)
try fm.createDirectory(at:docs,withIntermediateDirectories:true)
let logical=docs.appendingPathComponent("wine",isDirectory:true)
try fm.createSymbolicLink(at:logical,withDestinationURL:physical)
let relative="Program Files (x86)/Steam/steam.exe"
do {
    _=try SteamRuntimeFiles.destination(relative,under:logical.appendingPathComponent("drive_c"))
    fatalError("Baseline logical prefix unexpectedly accepted")
} catch SteamRuntimeFiles.Failure.conflict {
    print("REPRODUCED exact installer method rejects the existing Lab prefix alias")
}
let resolved=LabMadeiraPrefix.canonical(logical,documents:docs,linuxRoot:root)
precondition(resolved==physical.resolvingSymlinksInPath().standardizedFileURL)
let destination=try SteamRuntimeFiles.destination(relative,under:resolved.appendingPathComponent("drive_c"))
precondition(destination.path.hasSuffix("/MadeiraPrefix/drive_c/Program Files (x86)/Steam/steam.exe"))
let ordinary=docs.appendingPathComponent("wine-steam64")
precondition(LabMadeiraPrefix.canonical(ordinary,documents:docs,linuxRoot:root)==ordinary)
let other=base.appendingPathComponent("other",isDirectory:true)
try fm.createDirectory(at:other,withIntermediateDirectories:true)
try fm.removeItem(at:logical)
try fm.createSymbolicLink(at:logical,withDestinationURL:other)
precondition(LabMadeiraPrefix.canonical(logical,documents:docs,linuxRoot:root)==logical)
print("PASS known Lab binding resolves to physical prefix; unrelated prefix/binding unchanged; installer checks retained")
'''
(out/'main.swift').write_text(main)
cmd=['xcrun','swiftc','-module-cache-path',str(out/'module-cache'),str(lab/'app/LabMadeiraPrefix.swift'),str(out/'main.swift'),'-o',str(out/'control')]
subprocess.run(cmd,check=True,timeout=180)
r=subprocess.run([str(out/'control'),str(out)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=20)
(out/'control.log').write_text(r.stdout);assert r.returncode==0,r.stdout
h=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
(out/'evidence.json').write_text(json.dumps({'scope':'HOST exact installer destination + native Lab prefix adapter, NOT full installer/auth/Wine/Air proof','command':cmd,'returncode':r.returncode,'output':r.stdout,'production_source_sha256':h(repo/'app/Madeira/SteamRuntime.swift'),'adapter_source_sha256':h(lab/'app/LabMadeiraPrefix.swift'),'extracted_control_sha256':h(out/'main.swift')},indent=2)+'\n')
print(r.stdout)
