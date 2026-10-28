# Native macOS ARM64 Steam on iOS: evidence matrix

This is an experimental route, separate from the working Windows Steam product.
The full end-to-end goal is **not achieved**. Last reviewed 2026-10-28 against
research parent `147c7a84ed3c6422236f80ffc3908bc1933db295`; all cited device results
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
| Helper can be loaded in-process | Static MH_EXECUTE / LC_MAIN and direct CEF dependency inspected; Build10 loader probe signed and installed | Device probe pending native unlock; no entry call or IPC model |
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

Build10 was initially reported as an installation timeout. A later successful
installed-app query confirms version10, so do not reinstall it blindly. After a
native unlock, revalidate its identity/current installation URL and run only
`IDeckNativeHelperLoadProbe=1`. Its categorical dyld result will establish a
loader prerequisite; constructor exit, successful dlopen or an existing PID
would still not establish login, usable UI, IPC correctness or game execution.

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

The latest exec/fork/spawn incoming-errno and unknown-basename hardening is
host/sanitizer/iOS-compile verified source at147c7a8; installed Build10 predates
it. Do not claim that patch is linked into the installed Mach-O. No tested native
Steam IPA, public binary release, native authentication or end-to-end completion
is claimed.
