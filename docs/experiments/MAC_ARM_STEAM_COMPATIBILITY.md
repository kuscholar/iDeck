# Native macOS ARM64 Steam on iOS: evidence matrix

This is an experimental route, separate from the working Windows Steam product.
The full end-to-end goal is **not achieved**. Last reviewed 2026-10-28 against
research parent `b6212bdae6d64aaac5e6dc6cb59916e739fc81b1` plus local iPad/Helper adaptation; all cited device results
belong to the isolated native lab on iPhone 15 Pro Max, iOS 27.0 (24A435), using
standard Personal Team development signing. Results do not generalize to other
hardware, iOS versions or signing configurations.

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
