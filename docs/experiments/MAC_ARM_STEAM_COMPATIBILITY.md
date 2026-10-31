# Native macOS ARM64 Steam on iOS: evidence matrix

This is an experimental route, separate from the working Windows Steam product.
The full end-to-end goal is **not achieved**. Latest review: 2026-10-31, research
parent `02697f38e198eecdb012849471a537407d130377` plus local scoped changes.
The opening historical table concerns the isolated iPhone15ProMax/iOS27.0 lab;
the dated sections below separately record physical iPad Pro26.7.1 and Air27.2
results. All use ordinary Personal Team signing. Do not generalize observations
across these hardware/OS/input configurations.

| Requirement or contract | Verified evidence | Status / remaining gate |
| --- | --- | --- |
| macOS ARM64 code executes on phone | Minimal AppKit/Metal triangle renders; user touch reaches AppKit callback | Device pass for that probe only |
| Genuine native Steam main executes | Official manifest 1792618285; native main, steamui and SDL startup observed | Partial, no interactive Steam UI |
| Named-font compatibility | Build7 passes earlier `maximumAdvancement` exception; CoreText metric host contracts pass | Bounded fix; full AppKit fonts unverified |
| Optional root-domain power registration | Build8 documented failure marker; earlier dummy-port dispatch crash absent in 25s trace | Bounded fix; unsupported service is declined |
| Real Helper process launch | Build6/8 observer sees flags0xa, 25 arguments, unchanged return0 / errno1; native fork site tier0+0xbe80 | Fails with EPERM; no fake PID or successful process |
| Stock CEF loads | Direct framework probe enters constructors and requests16GiB, then ENOMEM/fatal before dlopen returns | Fails before initialization; debug attach did not resolve it |
| Large normal VM reservation | Build9 vm_map1GiB succeeds;8/16GiB KERN_NO_SPACE; mmap8GiB ENOMEM; full cleanup | Changing normal allocation API did not solve it |
| Smaller-pool geometry fits | Build5 two real no-access chunks, each with guarded/aligned256MiB subrange, disjoint/masks/cleanup1 | Geometry only; NOT PartitionAlloc or CEF integration |
| Compatible source-built CEF | Pinned public6478 source API hashes mismatch actual framework; seven candidate custom exports differ | Matching ABI/source baseline not located in checked sources |
| Helper can be loaded in-process | Build11 verifies native path and ARM64 MH_EXECUTE header, then normal dlopen returns NULL with executable-rejection category | Device failure for this normal load; no entry call or IPC model |
| Loadable-bundle design on phone | Build12 own Mac ARM64 fixture: executable refused, metadata-adapted signed bundle loads; constructor1/main0, instructions unchanged | Device pass for own fixture only; genuine Helper/CEF/IPC not tested by this probe |
| Official login and Steam Guard | No credentials or auth caches used in native lab | Unverified; do not borrow working app login |
| Native library / Big Picture | Build8 observed black display, fps0 | Unverified |
| Windows depot selection | Reference projects inspected; native client UI not working | Unverified; no downloaded macOS files counted as Windows success |
| Windows game launch and return | Existing Madeira execution path preserved; native bridge not integrated | Unverified for native route |
| Performance improvement | No comparable completed UI/game workload | No measured benefit claim |

## Current decision and next discriminating test

**NO-GO for an unchanged stock Mac Steam/CEF drop-in in the measured free-signed
lab.** This is not proof that every source-based native architecture is
impossible. A usable route still needs both a compatible genuinely smaller-pool
CEF implementation and real Helper IPC/lifecycle integration. The user has no
paid team and selected research without Extended Virtual Addressing; do not
repeat that provisioning request or treat it as sufficient to solve processes.

Build10 eventually installed and its probe ran, but its NSBundle-derived target
was invalidated by the compatibility shim's redirected bundle root; it lacked
file preflight. Its unknown failure is NOT evidence about loading the actual
Helper. Build11 corrects the target using real libSystem executable path and
checks ARM64 MH_EXECUTE before dlopen. The actual phone refuses that load, with
an executable-rejection category; a missing-image category also appears, so
error-substring categories are not mutually exclusive. No entry/CEF/authentication
is called. A future loadable Helper adaptation needs an isolated copy/relink or
metadata design and independent IPC ownership tests; the measured stock CEF
constructor capacity failure remains separate.

Do not replace the actual framework with a mismatched generic CEF, spoof API
hashes, modify allocator masks in proprietary instructions, return a smaller
mapping for a larger request, suppress assertions, or fabricate native process
success. Keep production iDeck, its credentials/games/saves and other ongoing
branches intact.

## Evidence and reproduction

- [Research log](MAC_ARM_STEAM_IOS.md): exact experiments, hypotheses and results.
- [Redacted evidence index](MAC_ARM_STEAM_EVIDENCE.json): private artifact hashes
  and source fingerprints; raw reports remain outside Git.
- [Probe/build instructions](../../experiments/mac-arm-steam/README.md): local
  contracts, generated-copy staging and explicit diagnostic switches.

The exec/fork/spawn incoming-errno and unknown-basename hardening at147c7a8 is
host/sanitizer/iOS-compile verified and rebuilt into installed Build11. This
diagnostic exits before native process calls; do not claim real-call regression
validation from its successful build or probe marker. No tested native
Steam IPA, public binary release, native authentication or end-to-end completion
is claimed.

## Loadable own-fixture discriminator (Build12)

A normal signed iPhone load succeeds for our metadata-adapted Mac ARM64 bundle,
while its executable-form counterpart does not load. The identical instruction
bytes run one constructor; the explicit fixture getter verifies main0. No Steam
entry, CEF, UI, accounts or process emulation participate. The host Mac happens
to load the original executable too; do not infer iOS behavior from host dyld.

An initial synthetic conversion removed PAGEZERO and invalidated chained-fixup
segment indices. The corrected synthetic transformation preserves the segment
ordinal with an empty PAGEZERO. A genuine Helper adaptation requires a separately
audited exact-version private-copy tool and dependency layout; the synthetic-only
tool must never be applied to Valve binaries. Such an adaptation would still
face the measured CEF constructor capacity and Helper process/IPC gates.

## Physical iPad results (2026-10-29, supersedes installation gate)

Verified physical iPad Pro11-inch(iPad8,1), iPadOS26.7.1(23H30), ordinary Personal
Team profile. User removed HomePad; fresh inventory verified the free slot.
Working HomeViewPad and iDeck97 remain intact. Isolated12 installed, then upgraded
to isolated13; no credential/cache/game/save transfer or new entitlement.

| iPad discriminator | Actual result |
| --- | --- |
| VM range | 127 regions; largest observed unmapped gap5771362304bytes; vm_map1GiB succeeds/cleans,8/16GiB KERN_NO_SPACE; mmap8GiB ENOMEM |
| Own executable/bundle | Executable refuses load; metadata-adapted own bundle loads with constructor1/main0, no Steam/CEF entry |
| Unchanged real Helper | Native path/MH_EXECUTE preflight succeeds; normal dlopen fails with overlapping executable/missing-image categories |
| Direct actual CEF |16GiB PROT_NONE request fails ENOMEM; EXC_BREAKPOINT/SIGTRAP at CEF+0x3b4dda0 during dyld constructors; load never returns |
| Separate exact Helper bundle candidate | Normal signatures and original Helper hash verified; metadata/relative CEF path adaptation reaches actual CEF constructors, then same16GiB fatal; no completed dlopen or Helper entry |
| Actual native process APIs | Signed self-posix_spawn returnsEPERM1, no child; Steam's tier0 fork returns-1/EPERM1 at+0xbe80 |

Build13 candidate is a separate private file beside native libraries; original
Helper app/full binary hash remains unchanged. The exact-version preparer checks
five segment ordinals, LC_DYLD_INFO_ONLY streams, section bounds, full input hash,
and unchanged instruction/post-command payload before signing; final signed text
hash verified again. No generic binary conversion or auth/DRM check modifications.
A successful loader metadata change does not imply native process isolation or
CEF compatibility. Full native UI/login/library/Windows depots/games/return remain
unverified. No performance benefit has been demonstrated.

The bounded native process observer timeout was not app death: fresh exact
app-path/PID identity was checked before terminating only the lab. Raw device and
crash reports are private; redacted hashes are in the evidence index. Source
changes remain local outside the authorized Git window. Next useful work needs
compatible source-wide smaller CEF pools and real Helper IPC/lifecycle design;
repeating unchanged stock CEF reservations or fake spawn success is not a fix.

## Real small-pool allocator, physical iPad Build14

Unmodified Chromium126.0.6478.183 PartitionAlloc source now compiles and runs in
a standalone UIKit probe under the same standard lab profile, without EVA/JIT.
Actual upstream iOS `Runner` test-process selection initializes two disjoint
256MiB pools; 398 allocations/frees including2MiB direct maps, four workers,
content/isolation checks and final pool teardown complete with zero failures.
BRP support/slow checks and ordinary/expensive DCHECK remain enabled. This is
stronger than the earlier iDeck-authored geometric reservation test.

The direct-clang harness generates a documented standalone subset of GN flags;
it is not Valve's CEF configuration or a complete Chromium build. Thread cache,
malloc interposition, StarScan, MTE, pointer compression and full raw_ptr lifetime
semantics are not validated. This is iOS-compiled allocator code, not a converted
stock macOS CEF. Actual CEF custom API/hash compatibility, other browser address
reservations and real Helper process/IPC remain unresolved. Native Steam UI and
end-to-end mission remain NO-GO for the unchanged stock binary route; this result
supports further **source-build** research, not a smaller fake mmap return.

Build14 replaces only the isolated lab app and has no Valve payload. Working
iDeck97 remains separate. The preserved converted Steam13 host app was not
modified by this probe. Do not restore13 or repeat failed stock CEF merely to
fill a run. Next discriminator requires a reproducibly compatible CEF source
build/interface, followed by a real browser initialization and IPC experiment.

## New physical iPad Air4, iPadOS27.2 (Build15)

Official developer pairing and ordinary Personal Team provisioning now succeed
for the specifically requested iPad13,1/27.2(24B119); no old Pro/simulator result
substitution. User-authorized native developer trust completed via Device Hub.
Trusted14 then traps in UIKit's missing-scene-lifecycle check before allocator
entry. Own harness15 adopts UIScene/configuration/window manifest; upstream
Chromium source/config and test operations unchanged. Actual Air15 console and
visible UI confirm two256MiB disjoint pools,398 allocations/frees,4 workers,
zero failures and final pool teardown. No EVA/JIT required. Native Steam/CEF
is still not integrated or validated; scene-reconnect behavior not device-tested.
Subsequent source inspection confirms the native AppKit shim already has its own
scene delegate/manifest; copying the standalone fix into it is unnecessary.

## Requested Air native16–18: distinct faults and bounded regression

Native AppKit already adopts UIScene. Actual Air16 runs scene callbacks/steamui,
but self-spawn/fork fail EPERM;1GiB VM succeeds while8/16GiB fail. A reused16
process exposed recursive VGUI order-front/shim makeMainWindow and stack-guard
protection failure; that attempt was not a new CEF test. Own focus17 correction
passes synthetic subclass/reentry sanitizer tests. A genuinely fresh17 CEF load
then proves the same16GiB ENOMEM/SIGTRAP at CEF+0x3b4dda0 on this Air.

Normal17 reaches a different missing-NSEvent-factory nil-array exception at~121s.
Own18 factory stores the real scalar ABI fields without suppressing invalid-type
exceptions. Actual18 logs the factory marker and continues through150s sampling;
prior nil-array exception absent in that trace. It still renders0fps and starts
an update download. Later inventory has a different lab PID; no same-session
survival/reentry or update-completion claim. Crash collection later times out,
not proof of a crash. No native Steam browser/login/library success; API/source
CEF and real native Helper IPC gates remain. See evidence index for hashes.

## Custom CEF symbols are required by the observed Helper loader

The newer static audit of the actual official ARM64 Helper verifies all seven
previously identified custom APIs have required dlsym lookups: each null pointer
branches to the shared loader return-zero epilogue. They are not optional in
that observed initialization path. Fourteen synthetic negative/positive tests
and the actual read-only audit pass. No CEF constructor or device process runs
for this check. Original official file hashes differ from installed converted
Helper hashes; both are separately recorded.

A compatible source build therefore needs real semantics for these extensions,
plus full structure/callback ABI compatibility; a matching symbol list alone is
insufficient. No matching custom source was located in checked public sources.
The [open source request](https://github.com/ValveSoftware/steam-for-linux/issues/12226)
is context, not proof of global absence. Do not stub missing APIs or forge hashes.

## Full public source fingerprint control

The entire pinned public CEF extension repository is now inspected locally;
this is still not Chromium or a built browser. Its real hash calculator
reproduces the expected upstream hashes. Changing only one function parameter
identifier changes those hashes while Clang reports an identical function type.
Thus differing hashes establish different header fingerprints, not by themselves
an exhaustive structural-ABI incompatibility proof. Actual Helper explicitly
compares the platform hash before execution/initialization; checks stay intact.

The full public126 source candidate still lacks7 required declarations and fails
its two fingerprint comparisons. Own source-surface checker plus9 tests and full
local regressions pass; passing a future surface check would still require
semantic/layout/ownership and actual device tests. No matching custom source
was located in bounded public or authenticated GitHub code searches. Native
Steam remains incomplete; these host checks add no login or browser proof.

## Native19 updater confound and host control

Actual Air19 reads steam.cfg successfully twice but still checks/downloads the
background manifest after~122s; installed/pending versions are0. This key is not
a proven lab version pin, and cached packages do not prove installed code. All
180s samples remain0fps; no CEF/login UI success. Later process identity changes
without an explanatory new report in the visible crash list; cause unknown.

A private normally ad-hoc-signed Mac copy of the same official CEF loads and
returns correct version/hashes without cef_initialize. ARM64 instructions and
original source remain unchanged. Host loading success distinguishes this from
a generally invalid download, but does not establish iPad address capacity,
native Helper IPC or interactive browser success. See evidence index for limits.

## Actual macOS-compiled compact allocator, Air20/21

The allocator component now compiles as macOS ARM64 (IS_MAC1/IS_IOS0), then loads
after instruction-preserving metadata retargeting in an ordinary signed UIKit
host on the physical Air. This differs from the earlier iOS Runner configuration.
All62 allocator units use one explicit opt-in and shared dynamic-mask headers;
only3 pinned files are changed in a disposable copy, with original BSD notices.
Original362 source blobs remain unmodified. Checks, BRP support and slow checks
remain enabled; no fake map or precompiled Valve allocator changes.

| Source configuration | Actual Mac host | Actual physical Air | Remaining limit |
| --- | --- | --- | --- |
| Independent compact pools | 398 alloc/free,4workers,0failures | Intermediate20 ABI1: load/entry/pass, two256MiB disjoint pools, cleanup1 | Current ABI2 default rebuild host-pass; do not conflate fingerprints |
| Glued compact pools | 398 alloc/free,4workers,0failures | Final21 ABI2: same workload, adjacent pools and combined mask checks, cleanup1 | Component only; CEF/V8/IPC not integrated |

The first glued link failed because a shared inline method called a size-selector
definition hidden in another TU. Compact-Mac selectors are now defined inline
in the shared header; other platform selection remains unchanged. No check
suppression. Both configurations pass host tests and final21 device artifacts
confirm true Mac-compiled code execution without EVA/JIT entitlements.

Actual Air19 normal-debug attach/detach also preserves CS_DEBUGGED yet still
fails two16GiB requests and traps at CEF+0x3b4dda0. This removes an untested
normal-debug condition on this specific Air; it is not continuous-attached UI
validation. Full source-compatible CEF/browser and actual Helper lifecycle remain
necessary. Do not inject this compact component into stock CEF's fixed-mask code.
No native Steam login/library/depot/gameplay/return or speedup claim follows.

## Actual bounded raw_ptr BRP lifetime, Air22

The source-compiled Mac allocator now optionally builds real upstream raw_ptr
BRP (64units, same consistent dynamic masks), with checks still enabled. Actual
Air22 passes407 allocation/free requests and five bounded lifetime cases, including
copy/move/interior references,2MiB direct maps and final release on a worker.
Quarantine counters prove a retained slot stays unavailable after allocator free
and is released after its final wrapper. No freed payload is dereferenced.
Default no-wrapper and independent-pool BRP configurations pass on Mac only;
actual device22 uses glued pools. ResultABI3/80bytes; historical21 staysABI2.

This extends the component evidence only. Dangling-report callbacks, full
raw_ptr/race semantics, thread cache and complete browser allocation patterns
remain untested. Matching Valve custom source/ABI, full browser rebuild and
native Helper IPC/lifecycle remain blocking gates; no native Steam UI follows.
