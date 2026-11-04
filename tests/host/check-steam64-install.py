#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Madeira Converter Exception: see LICENSE-EXCEPTION.md
"""Compile actual streaming extractor/transaction on macOS using synthetic fixtures.
Optional --real PACKAGES_DIR also extracts/re-hashes all official packages locally.
No Valve binaries, credentials, or minidumps are added to the repository.
"""
from pathlib import Path
import hashlib, io, json, os, struct, subprocess, sys, tempfile, zipfile
root = Path(__file__).resolve().parents[2]
def pe(machine=0x8664):
    b=bytearray(256);b[:2]=b'MZ';struct.pack_into('<I',b,60,128);b[128:132]=b'PE\0\0';struct.pack_into('<H',b,132,machine);return bytes(b)
artifact=root.parent/'.madeira-install/ideck-steam64-setup/host-tests'
artifact.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory(prefix='install-',dir=artifact) as td:
    t=Path(td)
    policy=(root/'app/Madeira/SteamUIExperiment.swift').read_text().split('// Observations, never a persisted')[0]
    runtime=(root/'app/Madeira/SteamRuntime.swift').read_text().split('#if canImport(CryptoKit)\nprivate final')[0]
    (t/'policy.swift').write_text('import Foundation\nenum MadeiraConfig { static func get(_ key: String) -> String? { nil } }\n' + policy);(t/'runtime.swift').write_text(runtime)
    (t/'components.swift').write_text('import Foundation\nenum Steam64Components { static func composed(_ c:Steam64Catalog) throws -> Steam64Catalog { c }; static func validateBundle() throws {}; static func stage(into:URL) throws {} }')
    fixture={n:pe() for n in ['steam.exe','steamclient64.dll','bin/cef/cef.win64/steamwebhelper.exe','bin/cef/cef.win64/libcef.dll']}
    fixture['steamui/test.txt']=b'hello world'*9000;fixture['public/empty']=b''
    fixture={'Program Files/Steam/'+n:b for n,b in fixture.items()}
    catalog=json.loads((root/'app/Madeira/Steam64Packages.json').read_text())
    catalog['files']={n:dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest()) for n,b in fixture.items()};catalog['expandedBytes']=sum(len(b) for b in fixture.values())
    (t/'fixture.json').write_text(json.dumps(catalog));(t/'source').mkdir()
    for n,b in fixture.items():
        p=t/'source'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
    def archive(name,entries):
        with zipfile.ZipFile(t/name,'w',zipfile.ZIP_DEFLATED) as z:
            for n,b in entries:z.writestr(n.removeprefix('Program Files/Steam/') if isinstance(n,str) else n,b)
    archive('good.zip',fixture.items())
    for i,n in enumerate(['../outside','/outside','a\\..\\b','C:/outside','a/./b','a//b','a./b','config/loginusers.vdf']):archive(f'bad{i}.zip',[(n,b'x')])
    z=zipfile.ZipInfo('steam.exe');z.create_system=3;z.external_attr=0o120777<<16;archive('symlink.zip',[(z,b'../outside')])
    archive('duplicate.zip',[('steam.exe',pe()),('STEAM.EXE',pe())]);archive('hash.zip',[('steam.exe',pe(0x14c))]);archive('incomplete.zip',[('steam.exe',pe())])
    bad=bytearray((t/'good.zip').read_bytes());central=bad.index(b'PK\x01\x02');struct.pack_into('<I',bad,central+24,0x7fffffff);(t/'bomb.zip').write_bytes(bad)
    bad=bytearray((t/'good.zip').read_bytes());bad[central+16]^=1;(t/'crc.zip').write_bytes(bad)
    (t/'main.swift').write_text(r'''
import Foundation
import CryptoKit
let fm = FileManager.default, base = URL(fileURLWithPath: CommandLine.arguments[1])
let decoder = JSONDecoder()
let catalog = try decoder.decode(Steam64Catalog.self, from: Data(contentsOf: base.appendingPathComponent("fixture.json")))
try catalog.validate()
func reject(_ action: () throws -> Void) { do { try action(); fatalError("unsafe fixture accepted") } catch {} }
let source = base.appendingPathComponent("source")
assert(try! Steam64IO.verify(root: source, catalog: catalog))
print("stage synthetic extract"); fflush(stdout)
let output = base.appendingPathComponent("unpacked")
try Steam64ZIP.extract(base.appendingPathComponent("good.zip"), into: output, catalog: catalog)
assert(try! Steam64IO.verify(root: output, catalog: catalog))
for name in try fm.contentsOfDirectory(atPath: base.path) where (name.hasPrefix("bad") || ["symlink.zip","duplicate.zip","hash.zip","bomb.zip","crc.zip"].contains(name)) {
    print("reject",name); reject { try Steam64ZIP.extract(base.appendingPathComponent(name), into: base.appendingPathComponent(UUID().uuidString), catalog: catalog) }
}
let incomplete = base.appendingPathComponent("incomplete")
try Steam64ZIP.extract(base.appendingPathComponent("incomplete.zip"), into: incomplete, catalog: catalog)
assert(!(try! Steam64IO.verify(root: incomplete, catalog: catalog)))
let prefix = base.appendingPathComponent("wine-steam64"), target = prefix.appendingPathComponent("drive_c")
try fm.createDirectory(at: prefix, withIntermediateDirectories: true)
try Data("registry".utf8).write(to: prefix.appendingPathComponent("system.reg"))
reject { try Steam64IO.requireSpace(100, at: prefix, available: 99) }
try Steam64Transaction.install(source: source, prefix: prefix, catalog: catalog)
assert(try! Steam64IO.verify(root: target, catalog: catalog))
for name in ["config/loginusers.vdf", "userdata/user/save.dat", "steamapps/common/game/game.exe", "unknown-local-save.bin", "ssfn123"] {
    let f=target.appendingPathComponent("Program Files/Steam/"+name);try fm.createDirectory(at:f.deletingLastPathComponent(),withIntermediateDirectories:true);try Data("private sentinel".utf8).write(to:f)
}
// A legacy account/game prefix is never enumerated or modified.
let legacy=base.appendingPathComponent("wine/drive_c/Steam32BundleLab/config/loginusers.vdf")
try fm.createDirectory(at:legacy.deletingLastPathComponent(),withIntermediateDirectories:true)
try Data("legacy account sentinel".utf8).write(to:legacy)
let copied=base.appendingPathComponent("public-only")
try Steam64IO.copyPublic(source:target,stage:copied,catalog:catalog)
assert(try! Steam64IO.verify(root:copied,catalog:catalog))
assert(!fm.fileExists(atPath:copied.appendingPathComponent("Program Files/Steam/config/loginusers.vdf").path))
assert(!fm.fileExists(atPath:copied.appendingPathComponent("Program Files/Steam/unknown-local-save.bin").path))
let old=Data("old incompatible client".utf8)
try old.write(to:target.appendingPathComponent("Program Files/Steam/steam.exe"))
reject { try Steam64Transaction.install(source: source, prefix: prefix, catalog: catalog, faultAfter: 3) }
assert(try! Data(contentsOf:target.appendingPathComponent("Program Files/Steam/steam.exe")) == old)
assert(!fm.fileExists(atPath:Steam64Transaction.journal(prefix:prefix).path))
try fm.removeItem(at:target.appendingPathComponent("Program Files/Steam/bin/cef/cef.win64/libcef.dll"))
let extra=target.appendingPathComponent("Program Files/Steam/bin/cef/cef.win7");try fm.createDirectory(at:extra,withIntermediateDirectories:true);try Data("x64".utf8).write(to:extra.appendingPathComponent("libcef.dll"))
try Steam64Transaction.install(source: source, prefix: prefix, catalog: catalog)
assert(try! Steam64IO.verify(root: target, catalog: catalog));assert(!fm.fileExists(atPath:extra.path))
for name in ["config/loginusers.vdf", "userdata/user/save.dat", "steamapps/common/game/game.exe", "unknown-local-save.bin", "ssfn123"] { assert(try! String(contentsOf: target.appendingPathComponent("Program Files/Steam/"+name),encoding:.utf8) == "private sentinel") }
// Simulate process death AFTER the durable plan, before commit; recovery uses real journal.
let pending=prefix.appendingPathComponent("client-rollbacks/steam64-pending")
try fm.createDirectory(at:pending,withIntermediateDirectories:true)
var planned:[Steam64Transaction.Entry]=[]
for name in catalog.files.keys.sorted() {
    let saved=pending.appendingPathComponent(name);try fm.createDirectory(at:saved.deletingLastPathComponent(),withIntermediateDirectories:true)
    try fm.copyItem(at:target.appendingPathComponent(name),to:saved)
    planned.append(.init(name:name,existed:true))
}
try JSONEncoder().encode(Steam64Transaction.Journal(entries:planned,quarantine:[])).write(to:Steam64Transaction.journal(prefix:prefix))
try old.write(to:target.appendingPathComponent("Program Files/Steam/steam.exe"))
assert(fm.fileExists(atPath: Steam64Transaction.journal(prefix:prefix).path))
try Steam64Transaction.recover(prefix:prefix,catalog:catalog)
assert(try! Steam64IO.verify(root:target,catalog:catalog))
let wrong = base.appendingPathComponent("wrong-architecture")
try fm.copyItem(at:source,to:wrong)
var x64=try Data(contentsOf:wrong.appendingPathComponent("Program Files/Steam/steam.exe"));x64[132]=0x4c;x64[133]=0x01
try x64.write(to:wrong.appendingPathComponent("Program Files/Steam/steam.exe"))
var wrongFiles=catalog.files;wrongFiles["Program Files/Steam/steam.exe"] = .init(bytes:Int64(x64.count),sha256:Steam64IO.digest(x64))
let wrongCatalog=Steam64Catalog(schema:catalog.schema,version:catalog.version,manifestSHA256:catalog.manifestSHA256,origin:catalog.origin,expandedBytes:catalog.expandedBytes,packages:catalog.packages,files:wrongFiles)
reject { _ = try Steam64IO.verify(root:wrong,catalog:wrongCatalog) }
let freshFailure=base.appendingPathComponent("fresh-failure")
try fm.createDirectory(at:freshFailure,withIntermediateDirectories:true)
reject { try Steam64Transaction.install(source:source,prefix:freshFailure,catalog:catalog,faultAfter:3) }
assert(!fm.fileExists(atPath:freshFailure.appendingPathComponent("drive_c/steam.exe").path))
assert(!fm.fileExists(atPath:Steam64Transaction.journal(prefix:freshFailure).path))
let original = target.appendingPathComponent("Program Files/Steam/steam.exe")
try fm.removeItem(at:original);try fm.createSymbolicLink(at:original,withDestinationURL:source.appendingPathComponent("Program Files/Steam/steam.exe"))
reject { _ = try Steam64IO.verify(root:target,catalog:catalog) }
reject { try Steam64Transaction.install(source:source,prefix:prefix,catalog:catalog) }
let realCatalog = try Steam64Catalog.load(from:URL(fileURLWithPath:CommandLine.arguments[2]))
let corrupted=base.appendingPathComponent("corrupt.json");try Data("{}".utf8).write(to:corrupted)
reject { _ = try Steam64Catalog.load(from:corrupted) }
let changed = Steam64Catalog(schema:catalog.schema,version:"other",manifestSHA256:catalog.manifestSHA256,origin:catalog.origin,expandedBytes:catalog.expandedBytes,packages:catalog.packages,files:catalog.files)
reject { try changed.validate() }
let partial=Steam64Catalog(schema:catalog.schema,version:catalog.version,manifestSHA256:catalog.manifestSHA256,origin:catalog.origin,expandedBytes:catalog.expandedBytes,packages:Array(catalog.packages.dropLast()),files:catalog.files)
reject { try partial.validate() }
if CommandLine.arguments.count > 3 {
    let packages = URL(fileURLWithPath:CommandLine.arguments[3]), client=base.appendingPathComponent("real-client")
    for p in realCatalog.packages {
        print("extracting",p.name); fflush(stdout)
        let file=packages.appendingPathComponent(p.file)
        assert(try! Steam64IO.regular(file,bytes:p.bytes));assert(try! Steam64IO.hash(file)==p.sha256)
        try Steam64ZIP.extract(file,into:client,catalog:realCatalog)
        print("PASS real package",p.name)
    }
    assert(try! Steam64IO.verify(root:client,catalog:realCatalog));print("PASS full 6233-file official client")
}
for url in ["http://client-update.akamai.steamstatic.com/a", "https://evil.example/a", "https://user:password@client-update.akamai.steamstatic.com/a", "https://client-update.akamai.steamstatic.com:444/a"] { assert(!Steam64DownloadDelegate.authorized(URL(string:url))) }
assert(Steam64DownloadDelegate.authorized(URL(string:Steam64Catalog.origin + "package.zip")))
let progress = Steam64Progress(phase:.browser,bytes:25,total:100)
assert(progress.fraction == 0.25 && Steam64Progress(phase:.verifying).fraction == nil)
assert(try! String(contentsOf:legacy,encoding:.utf8)=="legacy account sentinel")
print("PASS production metadata, integrity, version/package-set, ZIP streaming/traversal/symlink/bomb/CRC, fresh install, x64/missing-file repair, private-data preservation, interrupted journal recovery, fresh rollback and disk-space checks")
Task {
    let cancelled = Task {
        while !Task.isCancelled { await Task.yield() }
        _ = try Steam64IO.hash(source.appendingPathComponent("Program Files/Steam/steam.exe"))
    }
    cancelled.cancel()
    do { try await cancelled.value; fatalError("hash ignored cancellation") } catch is CancellationError {} catch { fatalError("unexpected cancellation error") }
    do {
        _ = try await Steam64Installer.shared.run(prefix:prefix,cache:base.appendingPathComponent("refused-cache"),sessionInactive:{false},progress:{_ in})
        fatalError("active session accepted")
    } catch Steam64InstallError.activeSession {} catch { fatalError("unexpected active-session error") }
    assert(!fm.fileExists(atPath:base.appendingPathComponent("refused-cache").path))
    print("PASS cancellation and active-session refusal before network/filesystem mutation")
    exit(0)
}
dispatchMain()
'''.replace('assert(try! ', 'assert(try! '))
    exe=t/'check'
    subprocess.run(['xcrun','swiftc','-module-cache-path',str(t/'modules'),str(t/'policy.swift'),str(t/'runtime.swift'),str(t/'components.swift'),str(root/'app/Madeira/Steam64ClientInstaller.swift'),str(t/'main.swift'),'-o',str(exe)],check=True)
    args=[str(exe),str(t),str(root/'app/Madeira/Steam64Packages.json')]
    if len(sys.argv)>2 and sys.argv[1]=='--real':args.append(str(Path(sys.argv[2]).resolve()))
    subprocess.run(args,check=True)
