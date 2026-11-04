#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Madeira Converter Exception: see LICENSE-EXCEPTION.md
"""Exercise production profile/receipt logic and optional real staged-client hashes.
--real OFFICIAL_CLIENT_OR_PACKAGE_CACHE OPEN_COMPONENTS additionally validates the full composed
client, then activates/restores a disposable config. No Wine session is started.
"""
from pathlib import Path
import os,subprocess,tempfile,json
root=Path(__file__).resolve().parents[2]
art=root.parent/'.madeira-install/ideck-steam64-setup/host-tests';art.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory(prefix='profile-',dir=art) as td:
 t=Path(td)
 policy=(root/'app/Madeira/SteamUIExperiment.swift').read_text().split('// Observations, never a persisted')[0]
 runtime=(root/'app/Madeira/SteamRuntime.swift').read_text().split('#if canImport(CryptoKit)\nprivate final')[0]
 # Use the real MadeiraConfig parser, avoiding a duplicate implementation in the test.
 config=(root/'app/Madeira/MadeiraConfig.swift').read_text()
 start=config.index('    static func parse(');end=config.index('\n    ///',start)
 stub='import Foundation\nenum MadeiraConfig { static func get(_ key:String)->String? {nil}\n'+config[start:end]+'\n}\n'
 (t/'policy.swift').write_text(stub+policy)
 (t/'runtime.swift').write_text(runtime)
 (t/'main.swift').write_text(r'''
import Foundation
let fm=FileManager.default, base=URL(fileURLWithPath:CommandLine.arguments[1])
func rejects(_ action:()throws->Void) { do {try action();fatalError("unexpected success")} catch {} }
assert(!Steam64Profile.eligible(mapEnd:nil))
assert(!Steam64Profile.eligible(mapEnd:48 << 30))
assert(!Steam64Profile.eligible(mapEnd:0x7fffffffff))
assert(Steam64Profile.eligible(mapEnd:0x8000000000))
let cfg=base.appendingPathComponent("madeira.cfg"), record=base.appendingPathComponent(Steam64Profile.receiptName)
let before=Data("# user's comment\nsteam-runtime = steam32\nuser-pref = keep\npool = 512\n".utf8)
let after=try Steam64Profile.editing(before,values:Steam64Profile.settings,removing:Set(Steam64Profile.settings.keys))
assert(String(decoding:after,as:UTF8.self).contains("# user's comment"))
let selected=MadeiraConfig.parse(String(decoding:after,as:UTF8.self))
assert(selected["steam-runtime"]=="steam64" && selected["user-pref"]=="keep")
assert(selected["steam64.env.MADEIRA_STEAM64_DIRECT_CEF32"]=="0")
assert(selected["steam64.env.MADEIRA_CEF64_EXTERNAL_CRASHPAD"]=="1")
try JSONEncoder().encode(Steam64Profile.Receipt(before:before,after:after,schema:1)).write(to:record)
try (String(decoding:after,as:UTF8.self)+"later-pref = survive\n").write(to:cfg,atomically:true,encoding:.utf8)
try Steam64Profile.restore(config:cfg)
let restored=MadeiraConfig.parse(try String(contentsOf:cfg,encoding:.utf8))
assert(restored["steam-runtime"]=="steam32" && restored["pool"]=="512" && restored["later-pref"]=="survive")
assert(!fm.fileExists(atPath:record.path))
// Refuse to overwrite a later user edit to the controlled profile.
try JSONEncoder().encode(Steam64Profile.Receipt(before:before,after:after,schema:1)).write(to:record)
try (String(decoding:after,as:UTF8.self)+"pool = 123\n").write(to:cfg,atomically:true,encoding:.utf8)
let changed=try Data(contentsOf:cfg)
rejects {try Steam64Profile.restore(config:cfg)}
assert(try Data(contentsOf:cfg)==changed);try fm.removeItem(at:record)
// Death before config activation, including no preexisting config, is recoverable.
try fm.removeItem(at:cfg)
try JSONEncoder().encode(Steam64Profile.Receipt(before:nil,after:after,schema:1)).write(to:record)
try Steam64Profile.restore(config:cfg)
assert(!fm.fileExists(atPath:cfg.path) && !fm.fileExists(atPath:record.path))
let link=base.appendingPathComponent("alias.cfg")
try before.write(to:cfg);try fm.createSymbolicLink(at:link,withDestinationURL:cfg)
rejects {_ = try Steam64Profile.read(link)}
let catalog=try Steam64Catalog.load(from:URL(fileURLWithPath:CommandLine.arguments[2]))
let prefix=base.appendingPathComponent("wine-steam64")
rejects {try Steam64Profile.activate(config:cfg,expected:before,mapEnd:48 << 30,prefix:prefix,catalog:catalog)}
rejects {try Steam64Profile.activate(config:cfg,expected:Data(),mapEnd:0x8000000000,prefix:prefix,catalog:catalog)}
rejects {try Steam64Profile.activate(config:cfg,expected:before,mapEnd:0x8000000000,prefix:prefix,catalog:catalog)}
assert(try Data(contentsOf:cfg)==before && !fm.fileExists(atPath:record.path))
rejects {try Steam64Components.validateBundle(root:base.appendingPathComponent("missing"))}
rejects {try Steam64Components.validateRuntime(root:base)}
let composed=try Steam64Components.composed(catalog)
assert(composed.files["Program Files/Steam/bin/cef/cef.win64/libcef.dll"]?.sha256==catalog.files["Program Files/Steam/bin/cef/cef.win64/libcef.dll"]?.sha256)
assert(composed.files["Program Files/Steam/bin/cef/cef.win64/chrome_elf.dll"]?.sha256 != catalog.files["Program Files/Steam/bin/cef/cef.win64/chrome_elf.dll"]?.sha256)
assert(composed.files.keys.allSatisfy {!Steam64IO.isPrivate($0)})
if CommandLine.arguments.count==4 {
 let components=URL(fileURLWithPath:CommandLine.arguments[3])
 try Steam64Components.validateBundle(root:components)
 try Steam64Components.validateRuntime(root:components.deletingLastPathComponent())
 print("PASS actual pinned open component and released translator bundle checks")
}
if CommandLine.arguments.count==5 {
 let official=URL(fileURLWithPath:CommandLine.arguments[3]), components=URL(fileURLWithPath:CommandLine.arguments[4])
 try Steam64Components.validateBundle(root:components)
 try Steam64Components.validateRuntime(root:components.deletingLastPathComponent())
 let client=prefix.appendingPathComponent("drive_c/Program Files/Steam")
 try fm.createDirectory(at:client,withIntermediateDirectories:true)
 let drive=prefix.appendingPathComponent("drive_c")
 if fm.fileExists(atPath:official.appendingPathComponent("steam.exe").path) {
  // Only public inventoried files; never auth caches, games or unknown files.
  for name in catalog.files.keys {
   let relative=String(name.dropFirst("Program Files/Steam/".count)), from=official.appendingPathComponent(relative), to=client.appendingPathComponent(relative)
   try fm.createDirectory(at:to.deletingLastPathComponent(),withIntermediateDirectories:true)
   try fm.linkItem(at:from,to:to) // Stock source is never modified in-place.
  }
 } else {
  for package in catalog.packages {
   print("Verifying/extracting official package",package.name);fflush(stdout)
   let archive=official.appendingPathComponent(package.file)
   assert(try! Steam64IO.regular(archive,bytes:package.bytes));assert(try! Steam64IO.hash(archive)==package.sha256)
   try Steam64ZIP.extract(archive,into:drive,catalog:catalog)
  }
 }
 print("Checking 6,229 official client file hashes…");fflush(stdout)
 assert(try! Steam64IO.verify(root:drive,catalog:catalog))
 try Steam64Components.stage(into:drive,resources:components) // replace uses rename, never writes through stock hardlinks
 assert(try Steam64IO.verify(root:drive,catalog:composed))
 try Steam64Profile.activate(config:cfg,expected:before,mapEnd:0x8000000000,prefix:prefix,catalog:catalog)
 assert(MadeiraConfig.parse(try! String(contentsOf:cfg,encoding:.utf8))["steam-runtime"]=="steam64")
 // A second setup/repair keeps the original legacy rollback, not the new64 config.
 let firstReceipt=try JSONDecoder().decode(Steam64Profile.Receipt.self,from:Data(contentsOf:record))
 let current=try Data(contentsOf:cfg)
 try Steam64Profile.activate(config:cfg,expected:current,mapEnd:0x8000000000,prefix:prefix,catalog:catalog)
 let retryReceipt=try JSONDecoder().decode(Steam64Profile.Receipt.self,from:Data(contentsOf:record))
 assert(firstReceipt.before==before && retryReceipt.before==before)
 try Steam64Profile.restore(config:cfg)
 assert(MadeiraConfig.parse(try! String(contentsOf:cfg,encoding:.utf8))["steam-runtime"]=="steam32")
 // Wrong component hash is rejected before any use, even with an AMD64 header.
 let bad=base.appendingPathComponent("bad-components");try fm.copyItem(at:components,to:bad)
 var bytes=try Data(contentsOf:bad.appendingPathComponent("chrome_elf.dll"));bytes[bytes.count-1] ^= 1
 try bytes.write(to:bad.appendingPathComponent("chrome_elf.dll"))
 rejects {try Steam64Components.validateBundle(root:bad)}
 print("PASS full pinned official+open component hashes, composed client activation, restore, wrong component refusal")
}
print("PASS address gates, config preservation, atomic activation prerequisites, interruption recovery, rollback, user edits, symlinks, no auth transfer")
'''.replace('assert(try ','assert(try! '))
 exe=t/'check';subprocess.run(['xcrun','swiftc','-module-cache-path',str(t/'modules'),str(t/'policy.swift'),str(t/'runtime.swift'),str(root/'app/Madeira/Steam64ClientInstaller.swift'),str(root/'app/Madeira/Steam64Setup.swift'),str(t/'main.swift'),'-o',str(exe)],check=True)
 import sys
 args=[str(exe),str(t),str(root/'app/Madeira/Steam64Packages.json')]
 if len(sys.argv)==4 and sys.argv[1]=='--real':args+=sys.argv[2:]
 if len(sys.argv)==3 and sys.argv[1]=='--components':args.append(sys.argv[2])
 subprocess.run(args,check=True)
