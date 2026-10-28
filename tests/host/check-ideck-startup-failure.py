#!/usr/bin/env python3
"""Compile actual capacity and startup observer policies; no simulated device claim."""
from pathlib import Path
import subprocess,tempfile,os
root=Path(__file__).resolve().parents[2]
s=(root/'app/Madeira/SteamUIExperiment.swift').read_text()
policy=s[s.index('struct IDeckAddressCapacity'):s.index('// Observations, never a persisted')]
test=r'''
let gib: UInt64 = 1 << 30
assert(!IDeckAddressCapacity(mapEnd: 63*gib, freeBytes: 639 << 20).allowsWindow)
assert(!IDeckAddressCapacity(mapEnd: 63*gib, freeBytes: 639 << 20, minFreeGB: 0).allowsWindow)
assert(!IDeckAddressCapacity(mapEnd: 47*gib, freeBytes: 20*gib).allowsWindow)
assert(!IDeckAddressCapacity(mapEnd: 63*gib, freeBytes: 12*gib-1).allowsWindow)
assert(IDeckAddressCapacity(mapEnd: 63*gib, freeBytes: 12*gib).allowsWindow)
assert(IDeckAddressCapacity(mapEnd: 512*gib, freeBytes: 100*gib).allowsWindow)
assert(!IDeckAddressCapacity(mapEnd: 63*gib, freeBytes: 20*gib, minFreeGB: UInt64.max).allowsWindow)
assert(!IDeckAddressCapacity(mapEnd: 63*gib, freeBytes: 20*gib, minMapGB: UInt64.max).allowsWindow)
let file=FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
defer { try? FileManager.default.removeItem(at:file) }
let fail="[Wine child] BOOT FAILED at stage 'guest-window-reserve': guest window reserve returned 0xc0000017 - a 32-bit child cannot start without one\n"
try fail.write(to:file,atomically:true,encoding:.utf8)
var observer=IDeckStartupObservation(file:file)
assert(!observer.failed()) // Ignore prior session failure.
func append(_ text:String) throws {
 let h=try FileHandle(forWritingTo:file);defer{try? h.close()};try h.seekToEnd();try h.write(contentsOf:Data(text.utf8))
}
try append("[steam-ui] host-surface-present\n")
assert(!observer.failed()) // A present is neither CEF success nor failure.
try append(String(repeating:"noise\n",count:20000)+String(fail.prefix(50)))
assert(!observer.failed())
try append(String(fail.dropFirst(50)))
assert(observer.failed()) // Across chunks, after >64KiB of busy logs.
assert(!observer.failed())
try "rotated\n".write(to:file,atomically:true,encoding:.utf8)
assert(!observer.failed())
try append(fail)
assert(observer.failed())
assert(!IDeckStartupObservation.failedWindow("[Wine child] BOOT FAILED at stage 'other': 0xc0000017"))
assert(!IDeckStartupObservation.failedWindow("[Wine child] BOOT FAILED at stage 'guest-window-reserve': 0xc0000005"))
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'main.swift').write_text('import Foundation\n'+policy+test)
 subprocess.run(['swiftc',str(p/'main.swift'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
assert 'mach_port_deallocate' in (root/'app/Madeira/EntitlementChecker.swift').read_text()
assert 'if x86Client, !IDeckRules.steamClientReady(prefix: prefix)' in (root/'app/Madeira/ContentView.swift').read_text()
print('PASS: reported 639MiB refusal, margins/overflow, current-session chunked failure, busy log and rotation; no entitlement bypass')
