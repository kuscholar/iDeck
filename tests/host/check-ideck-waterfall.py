#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Madeira Converter Exception: see LICENSE-EXCEPTION.md
"""Exercise actual product action ordering against the full prerequisite policy.
Automatic runtime/signing/VA checks cannot be bypassed by the shorter UI.
"""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[2]
s=(root/'app/Madeira/SteamUIExperiment.swift').read_text()
policy=s[s.index('enum IDeckPrerequisite:'):s.index('\n@MainActor\nfinal class SteamUIEvidence')]
# Capacity is an unchanged production dependency of the underlying preflight.
capacity=s[s.index('struct IDeckAddressCapacity {'):s.index('/// Reads only newly appended bytes')]
test=r'''
func checks(_ missing: Set<IDeckPrerequisite> = []) -> [IDeckPrerequisiteResult] {
 IDeckPrerequisite.allCases.map { .init(id:$0,status:missing.contains($0) ? .needsAction : .passed,detail:"fixture") }
}
assert(IDeckSetupStep.allCases == [.steam,.connection,.pairing,.jit])
let empty=IDeckSetupFlow(checks:[])
assert(empty.next == .steam && !empty.launchReady)
// One install action replaces the separate manual runtime + legacy repair actions.
for missing: Set<IDeckPrerequisite> in [[.runtime],[.steam],[.runtime,.steam]] {
 let f=IDeckSetupFlow(checks:checks(missing))
 assert(f.next == .steam && f.actionable(.steam))
 assert(!f.actionable(.connection) && !f.actionable(.pairing) && !f.actionable(.jit))
 assert(!f.launchReady)
}
let network=IDeckSetupFlow(checks:checks([.connection,.pairing,.jit]))
assert(network.next == .connection && network.actionable(.connection))
assert(!network.actionable(.pairing) && !network.actionable(.jit))
let pair=IDeckSetupFlow(checks:checks([.pairing,.jit]))
assert(pair.next == .pairing && pair.actionable(.pairing) && !pair.actionable(.jit))
let jit=IDeckSetupFlow(checks:checks([.jit]))
assert(jit.next == .jit && jit.actionable(.jit) && !jit.launchReady)
let done=IDeckSetupFlow(checks:checks())
assert(done.next == nil && done.launchReady)
for step in IDeckSetupStep.allCases { assert(done.complete(step) && !done.actionable(step)) }
// Already configured/connected actions are automatically skipped, not repeated.
let remembered=IDeckSetupFlow(checks:checks([.steam]))
assert(remembered.complete(.connection) && remembered.complete(.pairing) && remembered.next == .steam)
// Mandatory signing/VA checks still gate both launch and JIT activation.
for missing: Set<IDeckPrerequisite> in [[.signing],[.addressSpace],[.signing,.addressSpace]] {
 let f=IDeckSetupFlow(checks:checks(missing))
 assert(!f.launchReady && !f.automaticallyReady)
 let pending=IDeckSetupFlow(checks:checks(missing.union([.jit])))
 assert(pending.next == .jit && !pending.actionable(.jit))
}
// Selection writes cannot be applied to already running native reservations.
let restart=IDeckSetupFlow(checks:checks(),restartRequired:true)
assert(restart.next == .steam && !restart.complete(.steam) && !restart.launchReady)
for step in IDeckSetupStep.allCases { assert(!restart.actionable(step)) }
// A sequential scan has intermediate results. They never enable launch early.
var scanned:[IDeckPrerequisiteResult]=[]
for id in IDeckPrerequisite.allCases {
 let f=IDeckSetupFlow(checks:scanned);assert(!f.launchReady)
 scanned.append(.init(id:id,status:.passed,detail:"scan"))
}
assert(IDeckSetupFlow(checks:scanned).launchReady)
var checking=checks();checking[0].status = .checking
assert(!IDeckSetupFlow(checks:checking).launchReady)
print("PASS four user actions, sequential gating, automatic skips, scan intermediates, signing/VA/restart guards")
'''
art=root.parent/'.madeira-install/ideck-waterfall145';art.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix='host-',dir=art) as td:
 p=Path(td);(p/'main.swift').write_text('import Foundation\n'+capacity+policy+test)
 subprocess.run(['xcrun','swiftc','-module-cache-path',str(p/'modules'),str(p/'main.swift'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
