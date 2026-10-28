#!/usr/bin/env python3
"""Exercise production iDeck readiness and auto-start gates against real files."""
from pathlib import Path
import subprocess, tempfile
root = Path(__file__).resolve().parents[2]
s = (root / 'app/Madeira/SteamUIExperiment.swift').read_text()
policy = s[s.index('enum SteamUIExperiment {'):s.index('\n@MainActor\nfinal class SteamUIEvidence')]
test = r'''

func flight(runtime: Bool = true, steam: Bool = true, signing: Bool? = true,
            builtIn: Bool = true, helper: Bool = true, paired: Bool = true,
            external: Bool = false, connection: Bool = true, jit: Bool = true,
            fresh: Bool = true) -> IDeckPreflight {
    IDeckPreflight(runtime: runtime, steam: steam, signing: signing, builtIn: builtIn,
        helper: helper, paired: paired, externalJIT: external, connection: connection,
        jitReady: jit, freshSession: fresh)
}
assert(flight().canLaunch)
var noVA = flight()
noVA.capacity = IDeckAddressCapacity(mapEnd: 63 << 30, freeBytes: 639 << 20)
assert(!noVA.canLaunch)
assert(noVA.results.last?.id == .addressSpace && noVA.results.last?.status == .needsAction)

assert(!flight(runtime: false).canLaunch)
assert(!flight(steam: false).canLaunch)
assert(!flight(jit: false).canLaunch)
assert(!flight(fresh: false).canLaunch)
assert(flight(connection: false).canLaunch) // Active JIT needs no second loopback connection.
assert(flight(helper: false, paired: false, connection: false).canLaunch) // Observed active JIT is evidence.
assert(!flight(signing: nil, jit: false).canLaunch)
assert(flight(signing: nil, jit: false).results[2].status == .needsAction)
assert(flight(signing: false, jit: false).results[2].status == .needsAction)
assert(flight(builtIn: false, helper: false, paired: false, external: true, jit: false).results[3].status == .needsAction)
assert(flight(builtIn: true, helper: true, paired: true, jit: false).results[3].status == .passed)
assert(flight(builtIn: true, helper: false, paired: true, jit: false).results[3].status == .needsAction)
assert(flight(builtIn: true, helper: true, paired: false, jit: false).results[3].status == .needsAction)
assert(flight(connection: false, jit: false).results[4].status == .needsAction)
assert(flight().results.map(\.id) == IDeckPrerequisite.allCases)
let screen=CGSize(width:932,height:430)
let corner=IDeckOverlayPosition.center(size:screen,saved:CGPoint(x:-1,y:-1),left:59,top:0,right:59,bottom:21)
assert(corner.x==841 && corner.y==32)
let moved=IDeckOverlayPosition.center(size:screen,saved:CGPoint(x:0.5,y:0.6),left:59,top:0,right:59,bottom:21)
assert(abs(moved.x-466)<0.001 && abs(moved.y-258)<0.001)
let edge=IDeckOverlayPosition.center(size:screen,saved:CGPoint(x:4,y:5),left:59,top:0,right:59,bottom:21)
assert(edge.x==841 && edge.y==377)
assert(IDeckCommand(rawValue:"change-account") == .changeAccount)
assert(IDeckCommand(rawValue:"exit-game") == .exitGame)
assert(IDeckCommand(rawValue:"menu") == .steamMenu)
assert(IDeckCommand(rawValue:"shell rm") == nil)
assert(IDeckCommand(rawValue:"big-picture") == .bigPicture)
let loginURL = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
defer { try? FileManager.default.removeItem(at: loginURL) }
let success = "[2026-10-24 10:26:03] [ WaitingForLibraryReady ] SetLoginState: Success - OK\n"
try success.write(to: loginURL, atomically: true, encoding: .utf8)
var observer = IDeckLoginObservation(file: loginURL)
assert(!observer.succeeded()) // An earlier account's historical success is ignored.
let writer = try FileHandle(forWritingTo: loginURL)
try writer.seekToEnd()
try writer.write(contentsOf: Data("[2026-10-24 10:26:04] [ None ] SetLoginState: WaitingForCredentials - OK\n".utf8))
assert(!observer.succeeded())
let split = success.index(success.startIndex, offsetBy: 40)
try writer.write(contentsOf: Data(success[..<split].utf8))
assert(!observer.succeeded())
try writer.write(contentsOf: Data(success[split...].utf8))
assert(observer.succeeded()) // Split writes and CRLF do not cause premature auth success.
assert(!observer.succeeded())
try writer.close()
assert(!IDeckRules.loginSucceeded("payload SetLoginState: Success - OK"))
assert(!IDeckRules.loginSucceeded("[2026-10-24 10:26:03] [ None ] SetLoginState: Success - Failure"))
try success.write(to: loginURL, atomically: true, encoding: .utf8)
assert(observer.succeeded()) // A replaced/rotated log is read from its new identity.
let args = ["/Applications/iDeck"]
assert(IDeckRules.shouldAutoStart(setup: true, ready: true, automatic: true, arguments: args))
for probe in ["madeira-runtime-diagnostics", "madeira-steam-big-picture-x86-experiment", "madeira-fls-diagnostics"] {
 assert(!IDeckRules.shouldAutoStart(setup: true, ready: true, automatic: true, arguments: args + [probe]))
}
for setup in [false, true] { for ready in [false, true] { for automatic in [false, true] {
 assert(IDeckRules.shouldAutoStart(setup: setup, ready: ready, automatic: automatic, arguments: args) == (setup && ready && automatic))
}}}
let prefix = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
defer { try? FileManager.default.removeItem(at: prefix) }
let client = prefix.appendingPathComponent("drive_c/Steam32BundleLab")
try FileManager.default.createDirectory(at: client, withIntermediateDirectories: true)
assert(!IDeckRules.clientReady(prefix: prefix))
try Data().write(to: prefix.appendingPathComponent("system.reg"))
let files = ["steam.exe", "steamclient.dll", "bin/cef/cef.win7/steamwebhelper.exe", "bin/cef/cef.win7/libcef.dll"]
func pe(_ name: String, machine: UInt16) throws {
 let file = client.appendingPathComponent(name)
 try FileManager.default.createDirectory(at: file.deletingLastPathComponent(), withIntermediateDirectories: true)
 var d = Data(repeating: 0, count: 256)
 d[0] = 77; d[1] = 90; d[60] = 128; d[128] = 80; d[129] = 69
 d[132] = UInt8(machine & 255); d[133] = UInt8(machine >> 8)
 try d.write(to: file)
}
for file in files.dropLast() { try pe(file, machine: 0x14c) }
assert(!IDeckRules.clientReady(prefix: prefix))
try pe(files.last!, machine: 0x8664)
assert(!IDeckRules.clientReady(prefix: prefix))
try pe(files.last!, machine: 0x14c)
assert(IDeckRules.clientReady(prefix: prefix))
try FileManager.default.removeItem(at: prefix.appendingPathComponent("system.reg"))
assert(!IDeckRules.clientReady(prefix: prefix))
assert(IDeckRules.steamClientReady(prefix: prefix)) // Registry and Steam checks are independent.
try Data().write(to: prefix.appendingPathComponent("system.reg"))
let fallback = prefix.appendingPathComponent("drive_c/Steam32Lab")
try FileManager.default.moveItem(at: client, to: fallback)
assert(IDeckRules.clientReady(prefix: prefix)) // The real launcher's second supported location.
try FileManager.default.createDirectory(at: client, withIntermediateDirectories: true)
let splitCEF = client.appendingPathComponent(files.last!)
try FileManager.default.createDirectory(at: splitCEF.deletingLastPathComponent(), withIntermediateDirectories: true)
try FileManager.default.moveItem(at: fallback.appendingPathComponent(files.last!), to: splitCEF)
assert(!IDeckRules.steamClientReady(prefix: prefix)) // Never combine files from different clients.
'''
with tempfile.TemporaryDirectory() as temp:
    p = Path(temp); (p/'main.swift').write_text('import Foundation\nenum MadeiraConfig { static func get(_ key: String) -> String? { nil } }\n' + policy + test)
    subprocess.run(['swiftc','-module-cache-path',str(p/'module-cache'),str(p/'main.swift'),'-o',str(p/'check')],check=True)
    subprocess.run([str(p/'check')],check=True)
print('PASS: production iDeck complete-client readiness, architecture and no-overlap auto-start gates')
