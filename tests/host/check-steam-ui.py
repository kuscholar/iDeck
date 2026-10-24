#!/usr/bin/env python3
"""Compile production launch policy with synthetic PE headers; never contacts Steam."""
from pathlib import Path
import subprocess, tempfile, os
import plistlib
root = Path(__file__).resolve().parents[2]
src = (root / 'app/Madeira/SteamUIExperiment.swift').read_text()
policy = src[src.index('enum SteamUIExperiment {'):src.index('\n@MainActor\nfinal class SteamUIEvidence')]
main = r'''
assert(SteamUIExperiment.callbackScheme(bundleID: "com.kuschqin.madeira.steamui") == "madeira-steamui")
assert(SteamUIExperiment.callbackScheme(bundleID: "com.kuschqin.madeira.d7kzkwd692") == "madeira")
assert(SteamUIExperiment.callbackScheme(bundleID: nil) == "madeira")
let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
defer { try? FileManager.default.removeItem(at: root) }
let client = root.appendingPathComponent("drive_c/Program Files (x86)/Steam")
func pe(_ path: String, machine: UInt16 = 0x8664) throws {
    let url = client.appendingPathComponent(path)
    try FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
    var d = Data(repeating: 0, count: 256)
    d[0] = 0x4d; d[1] = 0x5a; d[60] = 128
    d[128] = 0x50; d[129] = 0x45; d[132] = UInt8(machine & 255); d[133] = UInt8(machine >> 8)
    try d.write(to: url)
}
func refused(_ flag: String?, _ bundle: String?) {
    do { _ = try SteamUIExperiment.prepare(prefix: root, width: 1408, height: 648, flag: flag, bundleID: bundle); fatalError("unexpected launch") }
    catch {}
}
assert(!SteamUIExperiment.allowed(flag: nil, bundleID: "test.steamui"))
assert(!SteamUIExperiment.allowed(flag: "true", bundleID: "test.steamui"))
assert(!SteamUIExperiment.allowed(flag: "1", bundleID: "test.working"))
refused(nil, "test.steamui"); refused("1", "test.working")
assert(!FileManager.default.fileExists(atPath: root.appendingPathComponent("drive_c/madeira-steam-ui.cmd").path))
refused("1", "test.steamui")
try pe("steam.exe"); try pe("steamclient64.dll"); refused("1", "test.steamui")
try pe("bin/cef/cef.win7x64/steamwebhelper.exe"); refused("1", "test.steamui")
try pe("bin/cef/cef.win7x64/libcef.dll")
let p = try SteamUIExperiment.prepare(prefix: root, width: 1408, height: 648, flag: "1", bundleID: "test.steamui")
assert(p.arguments == "/desktop=steamui,1408x648 cmd /c C:\\madeira-steam-ui.cmd")
assert(p.batch.contains("services.exe") && p.batch.contains("steam.exe\" -no-cef-sandbox -cef-disable-gpu -nocrashmonitor"))
assert(!p.batch.contains("dockhost") && !p.batch.contains("-bigpicture") && !p.batch.contains("-console"))
try pe("steam.exe", machine: 0x14c); refused("1", "test.steamui")
try pe("steam.exe")
let dll = client.appendingPathComponent("steamclient64.dll")
let outside = root.appendingPathComponent("external-client.dll")
try FileManager.default.moveItem(at: dll, to: outside)
try FileManager.default.createSymbolicLink(at: dll, withDestinationURL: outside)
refused("1", "test.steamui")
try FileManager.default.removeItem(at: dll)
try FileManager.default.moveItem(at: outside, to: dll)
do { _ = try SteamUIExperiment.prepare(prefix: root, width: 1, height: 648, flag: "1", bundleID: "test.steamui"); fatalError("invalid size") } catch {}

do { _ = try SteamUIExperiment.prepare(prefix: root, width: 1408, height: 648, flag: "1", bundleID: "test.steamui", x86Client: true); fatalError("must not fall back to x64") } catch {}
for name in ["steam.exe", "steamclient.dll", "bin/cef/cef.win7/steamwebhelper.exe", "bin/cef/cef.win7/libcef.dll"] {
    try pe("x86-fixture/" + name, machine: 0x014c)
}
try FileManager.default.moveItem(at: client.appendingPathComponent("x86-fixture"), to: root.appendingPathComponent("drive_c/Steam32Lab"))
let p32 = try SteamUIExperiment.prepare(prefix: root, width: 1408, height: 648, flag: "1", bundleID: "test.steamui", x86Client: true)
assert(p32.windowsDirectory == "C:\\Steam32Lab")
let dll32 = root.appendingPathComponent("drive_c/Steam32Lab/bin/cef/cef.win7/libcef.dll")
var mixed = try Data(contentsOf: dll32)
mixed[132] = 0x64; mixed[133] = 0x86
try mixed.write(to: dll32)
do { _ = try SteamUIExperiment.prepare(prefix: root, width: 1408, height: 648, flag: "1", bundleID: "test.steamui", x86Client: true); fatalError("mixed CEF architecture refused") } catch {}
mixed[132] = 0x4c; mixed[133] = 0x01
try mixed.write(to: dll32)

assert(!p32.batch.contains("noupdate") && !p32.batch.contains("login"))
assert(!p32.batch.contains("steam://changeuser"))
let account = try SteamUIExperiment.prepare(prefix: root, width: 1408, height: 648, flag: "1", bundleID: "test.steamui", x86Client: true, bigPicture: true, bigPictureFlag: "1", accountChooser: true)
assert(account.batch.contains(" steam://changeuser") && !account.batch.contains("-bigpicture"))
let loginFirst = try SteamUIExperiment.prepare(prefix: root, width: 1408, height: 648, flag: "1", bundleID: "test.steamui", x86Client: true, bigPicture: true, bigPictureFlag: "1", loginFirst: true)
assert(!loginFirst.batch.contains("-bigpicture") && !loginFirst.batch.contains("steam://changeuser"))
assert(!account.batch.contains("-login") && !account.batch.contains("-password"))

let source32 = root.appendingPathComponent("drive_c/Steam32Lab")
do { try SteamUIExperiment.importBundledX86(source: source32, prefix: root, flag: "1", bundleID: "test.working"); fatalError("import isolation") } catch {}
try SteamUIExperiment.importBundledX86(source: source32, prefix: root, flag: "1", bundleID: "test.steamui")
let bundled32 = root.appendingPathComponent("drive_c/Steam32BundleLab")
let sentinel = bundled32.appendingPathComponent("keep-existing-data.txt")
try "preserve".write(to: sentinel, atomically: true, encoding: .utf8)
try SteamUIExperiment.importBundledX86(source: source32, prefix: root, flag: "1", bundleID: "test.steamui")
let preservedText = try String(contentsOf: sentinel, encoding: .utf8)
assert(preservedText == "preserve")
let importedPlan = try SteamUIExperiment.prepare(prefix: root, width: 1408, height: 648, flag: "1", bundleID: "test.steamui", x86Client: true)
assert(importedPlan.windowsDirectory == "C:\\Steam32BundleLab")
for disabledBigPictureFlag: String? in [nil, "0", "true"] {
 do { _ = try SteamUIExperiment.prepare(prefix: root, width: 1408, height: 648, flag: "1", bundleID: "test.steamui", x86Client: true, bigPicture: true, bigPictureFlag: disabledBigPictureFlag); fatalError("Big Picture must be explicitly gated") } catch {}
}
let big = try SteamUIExperiment.prepare(prefix: root, width: 1408, height: 648, flag: "1", bundleID: "test.steamui", x86Client: true, bigPicture: true, bigPictureFlag: "1")
assert(big.batch.contains(" -bigpicture") && big.batch.components(separatedBy: " -bigpicture").count == 2)
let ordinaryWithFlag = try SteamUIExperiment.prepare(prefix: root, width: 1408, height: 648, flag: "1", bundleID: "test.steamui", x86Client: true, bigPictureFlag: "1")
assert(!ordinaryWithFlag.batch.contains("-bigpicture"))
do { _ = try SteamUIExperiment.prepare(prefix: root, width: 1408, height: 648, flag: "1", bundleID: "test.working", x86Client: true, bigPicture: true, bigPictureFlag: "1"); fatalError("working app forbidden") } catch {}


do { _ = try SteamUIExperiment.prepare(prefix: root, width: 1408, height: 648, flag: "1", bundleID: "test.working", x86Client: true); fatalError("working app refused") } catch {}
assert(SteamUIExperiment.milestones(in: "arbitrary account=PRIVATE token=SECRET").isEmpty)
assert(SteamUIExperiment.milestones(in: "ChromeMainDelegate payload=PRIVATE BrowserReady SECRET") == ["cef-initialization-reported", "browser-ready-reported"])
do { _ = try SteamUIExperiment.prepareProbe(prefix: root, flag: nil, bundleID: "test.steamui"); fatalError("disabled probe") } catch {}
do { _ = try SteamUIExperiment.prepareProbe(prefix: root, flag: "1", bundleID: "test.steamui"); fatalError("missing probes") } catch {}
for name in ["steam-ui-atomic-probe.exe", "steam-ui-process-probe.exe"] {
    try pe(name)
    try FileManager.default.moveItem(at: client.appendingPathComponent(name), to: root.appendingPathComponent("drive_c/"+name))
}
try pe("bin/cef/cef.win64/madeira-chrome-elf-probe.exe")
let probeArgs = try SteamUIExperiment.prepareProbe(prefix: root, flag: "1", bundleID: "test.steamui")
assert(probeArgs == "/c C:\\madeira-runtime-probes.cmd")
let probeBatch = try String(contentsOf: root.appendingPathComponent("drive_c/madeira-runtime-probes.cmd"), encoding: .utf8)
assert(probeBatch.contains("echo atomic-exit=%errorlevel%") && probeBatch.contains("echo process-exit=%errorlevel%"))
assert(!probeBatch.contains("steam.exe") && !probeBatch.contains("steamwebhelper"))
assert(probeBatch.contains("echo elf-exit=%errorlevel%"))
try pe("steam-ui-fls-probe.exe")
try FileManager.default.moveItem(at: client.appendingPathComponent("steam-ui-fls-probe.exe"), to: root.appendingPathComponent("drive_c/steam-ui-fls-probe.exe"))
let flsArgs = try SteamUIExperiment.prepareProbe(prefix: root, flag: "1", bundleID: "test.steamui", fls: true)
assert(flsArgs == "/c C:\\madeira-fls-probe.cmd")
let flsBatch = try String(contentsOf: root.appendingPathComponent("drive_c/madeira-fls-probe.cmd"), encoding: .utf8)
assert(flsBatch.contains("fls-exit=%errorlevel%") && !flsBatch.contains("steam.exe"))

do { _ = try SteamUIExperiment.prepareProbe(prefix: root, flag: "1", bundleID: "test.steamui", reservation: true); fatalError("missing reservation probe") } catch {}
try pe("steam-ui-reservation-probe.exe")
let reservationPE = root.appendingPathComponent("drive_c/steam-ui-reservation-probe.exe")
try FileManager.default.moveItem(at: client.appendingPathComponent("steam-ui-reservation-probe.exe"), to: reservationPE)
do { _ = try SteamUIExperiment.prepareProbe(prefix: root, flag: "1", bundleID: "test.working", reservation: true); fatalError("working app must refuse") } catch {}
do { _ = try SteamUIExperiment.prepareProbe(prefix: root, flag: "0", bundleID: "test.steamui", reservation: true); fatalError("flag must be explicit") } catch {}
let reserveArgs = try SteamUIExperiment.prepareProbe(prefix: root, flag: "1", bundleID: "test.steamui", reservation: true)
assert(reserveArgs == "/c C:\\madeira-reservation-probe.cmd")
let reserveBatch = try String(contentsOf: root.appendingPathComponent("drive_c/madeira-reservation-probe.cmd"), encoding: .utf8)
assert(reserveBatch.contains("--isolated-reserve-only") && reserveBatch.contains("reservation-exit=%errorlevel%"))
assert(reserveBatch.unicodeScalars.filter { $0.value == 13 }.count == 4 && reserveBatch.unicodeScalars.filter { $0.value == 10 }.count == 4)
assert(!reserveBatch.contains("steam.exe") && !reserveBatch.contains("steam-ui-fls"))

do { _ = try SteamUIExperiment.prepareProbe(prefix: root, flag: "1", bundleID: "test.steamui", x86CEF: true); fatalError("missing x86 probe") } catch {}
for name in ["madeira-chrome-elf32-probe.exe", "chrome_elf.dll", "libcef.dll"] {
    let relative = "Steam32Probe/bin/cef/cef.win7/" + name
    try pe(relative, machine: 0x014c)
    let target = root.appendingPathComponent("drive_c/" + relative)
    try FileManager.default.createDirectory(at: target.deletingLastPathComponent(), withIntermediateDirectories: true)
    try FileManager.default.moveItem(at: client.appendingPathComponent(relative), to: target)
    assert(SteamUIExperiment.isX86PE(target) && !SteamUIExperiment.isX64PE(target))
}
let x86Args = try SteamUIExperiment.prepareProbe(prefix: root, flag: "1", bundleID: "test.steamui", x86CEF: true)
let x86Batch = try String(contentsOf: root.appendingPathComponent("drive_c/madeira-x86-cef-probe.cmd"), encoding: .utf8)
assert(x86Args.hasSuffix("madeira-x86-cef-probe.cmd"))
assert(x86Batch.contains("madeira-chrome-elf32-probe.exe") && x86Batch.contains("x86-cef-exit=%errorlevel%"))
assert(!x86Batch.contains("steam.exe") && !x86Batch.contains("steamwebhelper"))
assert(x86Batch.unicodeScalars.filter { $0.value == 13 }.count == 4)
do { _ = try SteamUIExperiment.prepareProbe(prefix: root, flag: "1", bundleID: "test.working", x86CEF: true); fatalError("working app must refuse x86") } catch {}


let probeURL = root.appendingPathComponent("drive_c/swiftshader32-probe.exe")
do { _ = try SteamUIExperiment.prepareProbe(prefix: root, flag: "1", bundleID: "test.steamui", swiftshader: true); fatalError("missing probe accepted") } catch {}
try pe("swiftshader-probe-fixture.exe", machine: 0x8664)
try FileManager.default.moveItem(at: client.appendingPathComponent("swiftshader-probe-fixture.exe"), to: probeURL)
do { _ = try SteamUIExperiment.prepareProbe(prefix: root, flag: "1", bundleID: "test.steamui", swiftshader: true); fatalError("x64 probe accepted") } catch {}
var probeData = try Data(contentsOf: probeURL);probeData[132] = 0x4c;probeData[133] = 0x01;try probeData.write(to: probeURL)
let swiftProbeArguments = try SteamUIExperiment.prepareProbe(prefix: root, flag: "1", bundleID: "test.steamui", swiftshader: true)
assert(swiftProbeArguments == "/c C:\\swiftshader32-probe.exe")
do { _ = try SteamUIExperiment.prepareProbe(prefix: root, flag: "1", bundleID: "test.working", swiftshader: true); fatalError("ordinary app accepted probe") } catch {}

print("PASS: feature flag, app isolation, complete x64 client, fixed command, dimensions, sanitized milestones")
'''
info = plistlib.loads((root/'app/Madeira/Info.plist').read_bytes())
assert info['CFBundleURLTypes'][0]['CFBundleURLSchemes'] == ['madeira-steamui']
network = (root/'app/Madeira/JITNetwork.swift').read_text()
assert all('SteamUIExperiment.callbackScheme)://jit-network/'+x in network for x in ('success','error','cancel'))
assert 'url.scheme == SteamUIExperiment.callbackScheme' in network
assert 'localdevvpn://enable?scheme=\\(SteamUIExperiment.callbackScheme)' in (root/'app/Madeira/JITSetup.swift').read_text()
with tempfile.TemporaryDirectory() as td:
    td=Path(td); swift=td/'main.swift'
    swift.write_text('import Foundation\nenum MadeiraConfig { static func get(_ key: String) -> String? { nil } }\n'+policy+main)
    subprocess.run([os.environ.get('SWIFTC','swiftc'), str(swift), '-o', str(td/'check')],check=True)
    subprocess.run([str(td/'check')],check=True)
# Compile the production child event function on the host and assert privacy.
process=(root/'build/ntdll-unix/process_ios.c').read_text()
fn=process[process.index('static void ios_steam_ui_child_event'):process.index('static void *ios_child_thread_entry')]
stubs=r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <unistd.h>
struct ios_child_args { int argc; char **argv; int slot; struct { unsigned short machine; } pe_info; };
'''
ctest=r'''
int main(int argc, char **argv) {
 char *items[]={"wine", "C:\\PRIVATE-ACCOUNT\\steamwebhelper.exe", "TOKEN-SECRET"};
 struct ios_child_args a={3,items,7,{0x8664}};
 if(argc>1) setenv("MADEIRA_STEAM_UI_SESSION","1",1); else unsetenv("MADEIRA_STEAM_UI_SESSION");
 ios_steam_ui_child_event(&a,"start"); ios_steam_ui_child_event(&a,"end");
 return 0;
}
'''
with tempfile.TemporaryDirectory() as td:
    td=Path(td); c=td/'check.c'; c.write_text(stubs+fn+ctest)
    subprocess.run(['cc','-fsanitize=address,undefined',str(c),'-o',str(td/'check')],check=True)
    off=subprocess.run([str(td/'check')],capture_output=True,text=True,check=True)
    on=subprocess.run([str(td/'check'),'on'],capture_output=True,text=True,check=True)
    assert off.stderr == ''
    assert 'kind=cef slot=7 machine=8664' in on.stderr and 'event=end' in on.stderr
    assert 'PRIVATE' not in on.stderr and 'SECRET' not in on.stderr
print('PASS: production pseudo-process diagnostics gated and payload-free (ASan/UBSan)')
