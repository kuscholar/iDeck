# Genuine Steam UI PoC results

Updated 2026-10-23. Current phase: Phase 0 complete; Phase 1 controlled launcher
implemented and exercised; first CEF load failed due to JIT pool capacity. Build 10 rejected fixed secondary preparation and later exhausted image space. Build 11 validated region C but hit a chrome_elf refcount assertion before pool exhaustion. Build 13 isolated diagnostics pass; real CEF login remains blocked. Main remains
the playable Build 8 baseline. This document is the recurring task's resume point.

## What has actually been established

- Baseline ee9fd2f; Phase 0 audit committed as f3d1e92. Exact current and historical
  submodule revisions, publication checks, architecture and missing resources:
  BIG_PICTURE_ARCHITECTURE.md.
- The historical handoff reports an interactive real Steam login window. This
  branch has NOT independently reproduced it and has not fixed its open bugs.
- The current native process source already permits initial CEF startup in
  single-process mode. Dock intentionally takes a different headless path.
- A separate off-by-default Steam UI route now requires a `.steamui` bundle,
  flag exactly 1, a fresh/JIT-enabled session and complete x64 client files. It
  rejects symlinked client resources rather than using the working prefix.
- It closes the native library's competing Steam connection through the existing
  gate, without transferring a token. It launches Valve's real steam.exe through
  existing services/explorer/cmd, without fixed game identity or Big Picture yet.
- New pseudo-process start/end events contain only fixed role, slot and machine;
  the experiment disables Wine's payload-wide debug channels. A bounded reader
  emits categorical new Steam-log readiness events, never raw credential text.
  Window presentation continues through existing Winios/Metal, not a UI replica.

## Experiment 1: isolated launch-policy feasibility

Observed gap: the existing Steam Testing action starts real Steam but enables
unrelated historical probes and shares the ordinary application's context.
Hypothesis: reuse current startup machinery with a fixed isolated launch policy
before modifying low-level CEF compatibility code.
Discriminating tests: flag-off and normal bundle refuse; complete synthetic x64
client passes; missing/32-bit/symlinked client fails; only fixed arguments and
categorical milestones are emitted. Compile actual native lifecycle diagnostic
function with private-looking paths/arguments and assert none are emitted.
Evidence: both production policy and C diagnostics pass; C uses ASan/UBSan.
Minimal patch: SteamUIExperiment.swift, ContentView route, scoped bridge identity/
logging handling and scoped native child events. No Dock/FEX/DXMT edits.
Regression: Dock contract and frontend host checks pass.

## Build evidence (not execution evidence)

Native ntdll: 37 compile units succeeded, 0 failed; the changed process object is
in the newly built experimental archive. Full iOS Debug target built successfully
with bundle ID com.kuschqin.madeira.steamui and version 9. The first attempt found
missing fmt headers in the new worktree; the pinned fmt/range-v3/unordered_dense
sources were then checked out independently and compilation succeeded.
Final Mach-O markers and symbols were checked in Madeira.debug.dylib, not just
in the intermediate archive or small executable trampoline. Artifact hashes and
commands are recorded in STEAM_UI_LOCAL_EVIDENCE.json and the reproducibility guide.
The source/worktree dependency reuse is described in tests/steam-ui/README.md.

The synthetic x86-64 CreateProcess/shared-map/child-exit diagnostic was compiled
and its AMD64 PE headers/imports inspected in the initial local-only milestone.
It subsequently passed on device in Build 12/13, recorded below; Windows
control is still unavailable.

## Actual device gate (updated after Xcode account sign-in)

Official Xcode UI provisioning generated matching isolated app and helper
profiles. Code signatures and embedded profile IDs were checked, and final
Build 9 was successfully installed and launched as Steam UI Lab. Its unique
`madeira-steamui` scheme also receives LocalDevVPN and Shortcuts callbacks,
so the working Madeira app does not receive the experiment's JIT callbacks.
The first installation was rejected by the free-profile three-app limit. The
user chose to back up/remove LongDine themselves; subsequent device inventory
no longer showed it and installation succeeded. No app was uninstalled by us.
Main and the original Madeira app/data remain unchanged.

An on-device startup log confirms `v0.1.3 (9)`, developer interface from config,
and increased-memory-limit granted. `allow-jit` and extended-VA were false at
startup; the existing debugger workflow is still required. A launch is NOT a
CEF or JIT success. The user has been asked to enable JIT and press the new
Steam UI Experiment button; runtime/interaction results are pending.

Read-only inventory showed the working headless client's bin directory had no
CEF tree. It was not used as a full-client source. Instead, 18 matching public
Valve win64 packages from saved manifest version 1792618285 were fetched over
HTTPS and checked against every listed size and SHA-256. The staged set has
6,558 files, 829,728,769 expanded bytes. Core binaries have AMD64 PE headers.
Manifest signatures were NOT independently verified. See
STEAM_UI_CLIENT_EVIDENCE.json and the saved manifest. No client binaries or
account caches are committed. The complete client and synthetic PE were copied
into the isolated app's prefix; device file inventory confirms webhelper and
libcef presence, but device file hashes have not been independently read back.
Valve's updater can subsequently change these resources; re-inventory after a run.

Before authentication, an inherited logging issue was found: the existing
webhelper path forced Chromium VLOG and echoed the inherited command tail.
The experimental-session-only policy now uses warning-level logging and a fixed
categorical policy event instead. Ordinary launches retain their existing
behavior. The native archive was rebuilt and the final linked Mach-O checked.
Steam's own logs remain app-private; the evidence observer never exports raw
lines. Human Steam Guard completion is required if Valve requests it. No claimed
networking, pixel, controller, login, Big Picture, library, persistence or
game-return validation yet. The synthetic PE is staged but NOT executed.

## Experiment 2: first real-client device run and allocation failure

Build 9 / source 4293afb ran the controlled Steam UI route on Kusch. The user
captured Steam's real "steamwebhelper is not responding" dialog. The private
host log confirms the route and repeated helper creation/termination. This is
NOT an interactive CEF/login success. No libcef fault RVA or KERN_MEMORY_ERROR
was observed in this run: CEF's code image failed to load before initialization.

Observed failure: primary JIT pool shrank from the requested 896 MiB to 464 MiB.
The upper run existed (325 MiB), but the second debugger allocation returned a
lower address and was released by the existing placement guard. At first CEF
failure the image allocator requested 0xd3d0000 bytes (about 212 MiB), while
main virgin space was 0x8134000 (about 129 MiB), with only small reusable ranges.
The loader returned STATUS_NO_MEMORY. Steam's own subsequent retries did not
change this. cef_log.txt was empty. Raw logs remain outside Git; hashes and
categorical findings are in STEAM_UI_RUN1_EVIDENCE.json.

Hypothesis: precise reservation of the measured upper run, followed by the
existing debugger's supported non-null-address prepare operation, will retain
the second region instead of relying on first-fit allocation and temporary
plugs. This addresses capacity/placement, not CEF memory-protection faults.

Discriminating test: on Build 10 require an exact-secondary RX verification
line and retained split-pool capacity; check whether libcef's image loads rather
than failing STATUS_NO_MEMORY. If it still fails, retain the new evidence and
do not treat a dialog/restart as progress. No protection overrides or retries
were added. A failed exact reservation, mismatched response or non-RX mapping
is released and rejected; occupied mappings are never overwritten.

Minimal patch: only SteamUIExperiment.enabled selects the exact secondary
reservation in StikJITHelper; the normal game allocation path is unchanged.
The entire returned region is queried for actual READ+EXECUTE permission before
acceptance. Local tests exercise real host Mach VM with a mock debugger:
occupied mappings retain their bytes and invoke no debugger; null/mismatched/
non-RX preparations release their allocations; a complete RX preparation passes.
These tests do not prove iOS debugserver will prepare caller-reserved memory.
Pool split/placement tests, JIT integration and Steam UI policy checks pass.
Build 10 compiled, was signed/verified, installed and launched. Its final linked
Mach-O contains the new diagnostic. Device execution of this candidate is
pending; the user has been asked to repeat Enable JIT and Steam UI Experiment.
The original working app/main remain unchanged.

## Experiment 3: Build 10 rejects fixed reservation; test existing region C

Build 10 / source 29f5f6f confirms that the requested exact secondary region did
NOT satisfy the complete RX verification. It was correctly released. The
caller-reserved-memory hypothesis is not supported on this device; the host
mock-debugger test did not predict iOS preparation. Build 11 removes that path
and its obsolete mock test, restoring the prior allocator. The rejected
candidate/test remain reproducible at commit 29f5f6f; no mprotect override or
relaxed permission check was added.

The first helper got further because this launch's primary region was 592 MiB
rather than 464 MiB, NOT because the candidate succeeded. libcef.dll loaded and
cef_log reported Chrome 126.0.6478.183. Later libglesv2.dll requested 0x7c8000
bytes with only 0x134000 main virgin bytes available, failing STATUS_NO_MEMORY;
more image failures followed. A helper then raised breakpoint 0x80000003 at
libcef+0x59ef905. Allocation failures precede this, but their causal relationship
to the breakpoint is not proved. No BrowserReady or interactive login observed.
See STEAM_UI_RUN2_EVIDENCE.json; raw logs stay outside Git.

The JIT badge turned orange because it only queried debugger attachment. The
log shows intentional early detach AFTER pool readiness; this is distinct from
losing the prepared executable pool. Background thread/FEX statistics continuing
to update are not Steam UI readiness. Build 11's badge accepts either an attached
debugger or the existing successfully prepared poolTaken state.

Next single-hypothesis test: enable existing `pool-low = 1` only in the lab cfg,
keeping the previous `pool-split = 1`. Region C already supports placing FEX
code buffers in a separate debugger-created region below the executable window,
leaving more main-pool room for images. No allocator, Chromium or FEX source
change is introduced for this experiment. Require actual region-C RX/RW alias
acceptance, reduced main-pool tail consumption and successful libglesv2/import
loads. A missing C region or fresh memory exhaustion rejects this hypothesis;
further CEF errors must be diagnosed separately. Do not assume smaller primary
layouts will fit. The default 128 MiB low-image margin is unchanged.

Host pool-low/split, JIT-method, Steam policy and frontend regressions pass.
Build 11 compiled, passed strict signature verification, and was installed and
launched. Region-C execution remains pending. This experiment
still has no interactive login, authentication, Big Picture or controller result.

## Experiment 4: capacity confirmed, first failure is a refcount assertion

Build 11 / source bbcd7ce accepted region C (352 MiB, matching RX/RW alias),
624+256 = 880 MiB in A/B, and actual FEX EC_CODE carves in C. The main image
pool's code tail reservation stayed zero. This validates this run's capacity
mechanism; it does not guarantee the same A/B sizes under another address slide.

The first helper still raised 0x80000003 at chrome_elf.dll+0xd7e3e. The existing
brp-contain diagnostic reports offender=0 and caller=chrome_elf+0x65bb4.
The first assertion is at log line 14776 (zero based); first EXHAUSTED is 17529.
Later automatic helper restarts fragment/exhaust the pool. Do not mistake this
secondary exhaustion for the cause of the first assertion.

The actual device chrome_elf.dll was read back: SHA-256 matches the downloaded
binary (6358830f96f36efa7516b3277cf69c1f132f97d4d93c365ccf061a7cf11e1e39).
Offline disassembly confirms a locked cmpxchg clear-bit loop in the caller,
which branches to a helper recording the fixed string refcount, then executes
int3/int3/ud2. The refcount is not held by the allocator at that check (zero in
the saved diagnostic). The stack includes a non-null-pointer free callback at
chrome_elf+0x9c1e0 and ntdll teardown. This is a lifetime/FLS lead, NOT proof of
an incorrect atomic, a Wine double-free or a FEX defect. Do not remove the check.
This resembles the historical chrome_elf assertion family; it is not the
historical libcef+0x41258FB KERN_MEMORY_ERROR signature.

## Experiments 5 and 6: actual device diagnostic results

Build 12 added an isolated orange Runtime Diagnostics route. It requires the
experimental app/flag, fresh JIT session and x64 test executables. Fixed batch
commands redirect stdout and exit codes to drive_c/madeira-probe-results.txt;
no Steam client, login or credentials are involved. The user started this run:

- Atomic probe: 4 threads, 200,000 successful shared-counter increments, plus
  failed CAS result/ZF and private clear-held-bit CAS checks; failures=0, exit=0.
- Process probe: CreateProcess, named shared mapping, child write, parent wait
  and child exit all pass: wait=0 child_exit=0 shared_match=1, exit=0.

Build 13 added a PE importing the user's matching official chrome_elf.dll. It
ran beside that DLL, reached entry/GetHandleVerifier, and completed four rounds
of four worker threads with Win32/CRT heap writes/frees and teardown: failures=0,
exit=0. Atomic and process tests passed again in that run. The DLL is not embedded
in the probe or committed. Source, import definition and build commands are in
tests/steam-ui. This covers import/heap/thread plumbing; it does NOT reproduce
all CEF allocator or FLS lifetimes, so a pass cannot exonerate those generally.

Build 13 also accepts the explicit developer launch argument
madeira-runtime-diagnostics only when the Steam UI isolation flag is enabled.
It reuses the existing paired JIT coordinator and starts only these diagnostics.
The remote launch successfully enabled built-in JIT and completed the tests
without another phone tap. Ordinary app launch and real Steam launch do not
change. The baseline app/main were not changed. Future controlled diagnostics
can use this path while pairing/VPN/device availability remain valid.

Host launch/isolation/privacy tests, JIT-method and frontend checks pass. The
x86-64 PE files and actual final signed Mach-O were inspected/hashed. A macOS
x86-64 control compiled but could not execute (Bad CPU type); no Windows
control was available. Device passes are real, narrow results, not a general
emulator/allocator correctness claim. See STEAM_UI_RUN3_EVIDENCE.json for hashes
and exact output categories. The user still has no working real Steam login UI.

## Experiment 7: FLS callback lifetime and process isolation (Build 14)

On 2026-10-23 the user explicitly requested direct phone operation. The existing
paired automatic JIT route is reused; no repeated app-button interaction is
required. A new explicit `madeira-fls-diagnostics` developer argument selects
one FLS-only probe. It checks worker teardown once, no repeated callback on
freeing an empty slot, and parent/child FLS namespace isolation while the child
is alive. Static records track PID/call counts without freeing foreign memory.

This discriminator tests the basic lifetime/ownership lead from the actual
chrome_elf free-callback stack before any Wine/FEX runtime modification. The
expectation is Microsoft's documented per-process FLS contract, not an actual
Windows control result. Probe source and commands: tests/steam-ui/README.md.

Host launch/isolation/privacy checks, JIT-method and frontend regressions pass.
Build 14 compiled, passed strict signing verification, installed and received
the x64 probe. The first automated launch was refused by iOS: device Locked,
passcodeRequired=true. Device execution is PENDING; a native unlock is required.
The user was asked only to unlock/keep the phone awake, not to operate app
buttons. Do not count installation or the probe's compilation as a pass. Exact
artifact hashes and current gate: STEAM_UI_FLS_EVIDENCE.json. No security setting,
lock bypass, Wine/FEX implementation change or baseline app change occurred.

## Heartbeat state check: 2026-10-23 04:46 UTC

Resumed at experiment commit 1b9016b70df0a95b9329292c4b6a1bff0071ddf5.
Origin branch matches that exact remote revision; origin/main and the clean
primary checkout remain ee9fd2f4c21229dfce31a25c211d44df267336d8. No overlapping
experiment or unrelated local change found. Phase remains real CEF login;
Build 14 FLS device execution is still pending.

One read-only lock-state check still reports passcodeRequired=true and
unlockedSinceBoot=true. Evidence: ignored artifact
.madeira-install/steam-ui-fls-run1/heartbeat-lock.json and heartbeat-lock.log.
No launch, reinstall, signing retry or runtime modification attempted. Previous
regression/build results remain unchanged; no new device pass claimed. The
user already received the unlock request, so no duplicate notification is needed.

The recurring prompt was refreshed from the obsolete Build 9 signing gate to
the installed Build 14/FLS gate, preserving its 305-minute schedule and target
thread. Next: after native unlock, run the staged FLS-only diagnostic and collect
its result file before changing the runtime. No source/build/test result changed.

## Heartbeat state check: 2026-10-23 09:50 UTC

Resumed at e39e42bb3cb45abe55453ed3c8f9daf5618a9fa6, matching the fork's
remote experiment branch. Both worktrees are clean; primary/main and remote
main remain ee9fd2f4c21229dfce31a25c211d44df267336d8. Phase 1's current
uncompleted discriminator is still the installed Build 14 FLS probe.

A single read-only device check again returned passcodeRequired=true,
unlockedSinceBoot=true. Private evidence:
.madeira-install/steam-ui-fls-run1/heartbeat-0950-lock.json (SHA-256
d846bec12141d5e86463c54a5a8a91401198e6cc4fe1ac87e9bff3af7395235d) and heartbeat-0950-lock.log.
No launch/install/signing retry was attempted. No new device result or code
change exists; previous tests are unchanged. The probe's parent/child handshake
and bounded waits were reviewed without altering its contract or treating that
review as execution. No independent Windows control is available locally.

The native unlock gate is unchanged and was already reported; no repeat user
notification. The next step remains the staged FLS-only launch after native
unlock, followed by result-file and private-log capture. Do not claim a runtime
fix, remove the refcount check, or start another CEF retry while this test is
unexecuted. No further build/tests warranted for this documentation-only update.

## Manual test handoff candidate (Build 15)

The user asked to operate the test manually. Build 15 adds an explicit orange
FLS Diagnostics button to the isolated developer interface; it calls the same
FLS-only route as the Build 14 command-line argument. Ordinary manual launch
does not auto-run diagnostics or Steam. Probe/runtime code and previous
validation results are unchanged.

The full iOS build succeeded; strict signing verification passed and the
FLS Diagnostics marker was checked in the final linked debug dylib. Hash is
recorded in STEAM_UI_FLS_EVIDENCE.json under manual_candidate. This two-line
UI addition required no new runtime tests; it has no new device execution claim.
Initial install failed with IXRemoteErrorDomain 6 / Connection interrupted;
the subsequent app-list query timed out after 15 seconds. A single install
retry then succeeded (install-retry.json/log). The actual device probe was read
back and its SHA-256 matched the recorded Build 14 PE. Build 15 is installed,
with manual execution still pending; no FLS result is inferred from installation.
The prepared Build 14/probe state must not be erased to work around the link.

Verified-install handoff: open Steam UI Lab, Enable JIT, then orange FLS
Diagnostics; collect madeira-fls-results.txt and private device log. Do not
instruct the user to start full Steam or the earlier three-test Runtime
Diagnostics route for this discriminator. Working baseline remains untouched.

## Experiment 7 result: Build 15 FLS test passes on device

The user manually started FLS Diagnostics on installed Build 15 / source
c11d633. The private device log identifies version 15, successful paired JIT,
and the FLS-only launch. Result file reports thread-exit-once=PASS,
parent_once=1 wrong_owner=0 child_exit=0 wait=0, result=PASS and fls-exit=0.
Hashes and exact categorical output are in STEAM_UI_FLS_EVIDENCE.json; raw
artifacts are outside Git at .madeira-install/steam-ui-fls-run2/.

This rejects a simple always-repeated worker callback or basic parent/child
FLS namespace interference in the tested configuration. It does not exclude
CEF-specific allocator/FLS lifetime issues, callback reentrancy or another
owner/context error. No Windows control has executed. No Wine/FEX implementation
patch or assertion suppression is justified by this pass. No Steam login/UI
success is claimed. Previous host regressions are unchanged; this run changed
only recorded results/docs, with no rebuild or overlapping guest experiment.

A follow-up read-only attempt to retrieve the prefix's sysx64/ntdll.dll through
CoreDevice failed to open the path (POSIX 62). It did not produce a device PE
hash, so source/bundle-version equivalence is not asserted. Existing loaded
module metadata and official chrome_elf readback remain the available evidence.

Next: obtain bounded allocation/release and callback ownership evidence in the
actual CEF workload, accounting for the existing zero-refcount/free-callback
stack, before changing lifetime behavior. Reproduce a specific suspected
condition in an isolated PE/control when possible. Do not repeat the now-passing
basic FLS test or the locked-device gate. main/baseline app remain untouched.


## Build 16: actual CEF FLS ownership trace (2026-10-23)

Phase 1, based on parent `29643eea314284c2d5888f29a3eda73fe441edb9`;
Wine remains pinned to `9129e9684daaeae70da9435e7c6060e59392634e`.
Observed failure: real Steam still reaches the chrome_elf +0xd7e3e refcount
assertion (caller +0x65bb4, recorded offender=0), before interactive login.
Hypothesis: the CRT PTD destructor could receive a repeated FLS callback.
Discriminating test: observe alloc/set/callback begin/end, with PID, TID,
PEB/TEB and pointer identities, during the actual CEF workload. Do not change
callback ordering or suppress the assertion.

Minimal patch: a separate Wine PE observer patch, gated by BOTH
MADEIRA_STEAM_UI_SESSION=1 and MADEIRA_STEAM_UI_FLS_TRACE=1; at most 4096
metadata records per loaded observer instance, no dereferenced payload.
The pinned original Wine checkout and the primary baseline are unchanged.
ContentView additionally accepts explicit `madeira-steam-ui-experiment` to
reuse the already-paired JIT coordinator in the isolated flagged lab.

Validation: host policy/JIT/frontend checks PASS. Observer patch behavior
comparison and gating/bounds/privacy checks PASS under ASan/UBSan. Full unsigned
Build 16 PASS; final debug dylib contains the explicit launch marker. The custom
ARM64EC ntdll has the same 1473 named exports/order as the baseline, was placed
ONLY in the generated app, and the resulting app was re-signed and passed strict
verification. Device install and both explicit launch routes succeeded.
The synthetic FLS test with this actual observer-loaded PE still PASSes
(thread-exit-once; parent_once=1, wrong_owner=0, child_exit=0, wait=0, exit=0).

Actual CEF trace contains 3821 records; the failing pseudo-process reaches seq
1301, below the cap. For its FLS index 2, value 0x7800280200: one set at seq60
by tid012c, then its first recorded thread-exit-begin at seq1301 by the same
thread, with the same PEB and FLS storage. Callback resolves to
chrome_elf.dll+0x9c1e0. The refcount assertion occurs inside this callback;
there is no corresponding end or earlier callback for that value. An adjacent
thread's different PTD value completes the same callback normally. This argues
against simple repeated FLS delivery in this run. It does not rule out an earlier
non-FLS free, an invalid allocation, corruption or a translation defect.

Raw artifacts remain private at `.madeira-install/steam-ui-trace-build16`;
redacted metadata, exact component hashes and evidence file hashes are in
`docs/STEAM_UI_FLS_TRACE_EVIDENCE.json`. Two live-file downloads failed with
CoreDevice socket closure; after terminating only the lab process, the stable
2.3 MB log downloaded successfully. No app reinstall/restart loop was used.
The installed PE was not independently read back: final signed bundle hash plus
actual device observer records establish inclusion, not device byte equivalence.
Instrumentation changes timing/layout; no Windows control or allocator history
exists. BrowserReady, interactive login and Big Picture remain unverified.

Next: bounded metadata for chrome_elf CRT PTD allocation/free on this same thread,
compared with the FIRST FLS callback. Preserve the assertion; do not repeat the
basic FLS probe without a new instrumentation change. Reproduction is documented
in tests/steam-ui/README.md. main and the installed working game app are preserved.


## Builds 17–19: allocator metadata and overlapping pool grants (2026-10-23)

Phase 1, parent a10687c64f525b4aadfa99faad7403167ad525c1. Submodule pins
are unchanged. Observed failure/hypothesis: an official CRT path requests a
128-byte PTD, but the previous fatal site's preserved metadata-register points
to PTD+8192-4. Test whether allocator metadata is already inconsistent before
its FIRST FLS callback, rather than suppressing that callback or its assertion.

Build 17 adds fault-reporting, exact-length metadata reads to the separate Wine
PE observer. Exact 31-byte callback fingerprint pins interpretation to the
inspected official chrome_elf. No PTD contents are read. Its 33-second real CEF
run has no refcount assertion, and presents continue through #1219. However,
there are NO metadata snapshots, no BrowserReady and no interaction artifact;
this is not a fix/login success. Its PE SHA256 is
a94a82c58591e8a81d3f40a043a764c77b140790de8ed7228f8e2dcbedc6faa5.
The first sandboxed Xcode attempt could not query Metal; the normal authorized
Xcode toolchain build succeeded. JIT/frontend/policy and observer host tests pass.

Build 18 reuses Build 17's compiled Mach-O and changes only the diagnostic PE
and version, then re-signs/installs. It adds bounded categorical read exclusions.
At tid012c's callback begin, actual metadata reports slot_size=8192,
ref=0x78002821fc and ref_value=0 for PTD 0x7800280200; the original
chrome_elf+0xd7e3e assertion then occurs. Initial metadata for THIS object is
not recorded, so no claim that its state was correct at allocation is supported.
Some nearby callbacks report BRP root flag 0. Trace gaps/initial missing records
also limit chronology. No allocation/free history or Windows control exists.

More direct evidence: the native log first grants a REAL 16 GiB pool at
0x7800000000, then grants an unbacked soft guard-prefixed range returned at
0x77ffff0000, size 0x400010000, covering the same pool. Source inspection finds
that the emergency soft-grant path only excludes prior SOFT entries/furniture;
the comment claiming a real-pool probe remains, but its probe was removed.
Thus two allocator requests can own overlapping intervals. This supports a
specific aliasing hypothesis; Build 17 also had duplicate grants without the
same assertion inside its capture, so overlap alone is not a deterministic
proof of that crash's sole cause.

Minimal experimental patch: dual-gated by MADEIRA_STEAM_UI_SESSION=1 and
MADEIRA_STEAM_UI_STRICT_RESERVATIONS=1, inspect the whole returned soft range
against current Wine views under virtual_mutex; reject intersecting candidates
and retain allocation failure if no candidate remains. No remap, extra backing,
protection workaround or Chromium change. Default gaming path is unchanged.
This check is not a complete broker for native/soft/cage future allocations.

Build 19: all 37 native units and full Xcode build pass. The final Mach-O contains
the reject-soft-overlap marker; the unchanged Build 18 diagnostic PE is staged
ONLY into the generated app, which passes strict signing and device install.
The real-device ~57.79-second trace records 12 rejected overlaps, zero soft pool
grants, and STATUS_NO_MEMORY for 16 GiB/~32 GiB fallback reservations. CEF now
fails at libcef.dll+0x6923404 after allocation failure, before interactive login.
The earlier chrome_elf+0xd7e3e site is not observed. The existing [brp-contain]
message also labels this unrelated fatal pattern as a refcount assertion:
its generic CC CC 0F 0B matcher is NOT a reliable classifier. Module/RVA and
context distinguish these failures. Pool/JIT layout also varies between runs;
this result exposes the capacity gate, not a proven final repair.

Regression: actual overlap lookup/grant code exercised with partial/interior,
guard-prefix, boundary/disjoint, tree-branch, exact dual-flag and balanced-lock
tests under ASan/UBSan; PASS. Observer fingerprint/partial-read/privacy tests
PASS. Policy/JIT/frontend checks PASS. No FEX or original Wine checkout edits.
Private raw artifacts: .madeira-install/steam-ui-pa-build17,
steam-ui-pa-build18 and steam-ui-reserve-build19. Redacted evidence and hashes:
docs/STEAM_UI_ALLOCATOR_EVIDENCE.json. A first stable-log download after SIGTERM
closed its socket; one retry succeeded. Only lab processes were terminated;
working main at ee9fd2f and playable app/data are preserved.

Next: inventory actual real/soft/cage interval ownership, reproduce the overlap
contract in an isolated reservation test, and determine a disjoint backed layout
before any new broker patch. Do not restore silent aliasing to make initialization
appear successful. No interactive login/Big Picture milestone is achieved.


## Offline interval audit and reservation probe (2026-10-23 14:53 UTC run)

Phase 1, parent 026dfde456f9b5015ba5d9ab38d3d4dbb14a194f. Origin/remote
experiment and main match; both working trees are clean at the start. All four
submodule pins remain those of the architecture audit. No concurrent build or
device launch was found. One device availability check fails with CoreDevice
4016: required trusted-connectivity/power assertions unavailable. It does NOT
establish that Kusch is locked. No install, launch, repeated poll or credential
operation follows. The installed latest candidate is still Build 19.

Observed failure: Build 19's honest overlap rejection exposes reservation
capacity failure. Hypothesis: even before furniture, the current high-band
policy cannot pack all four full advertised pool claims disjointly with its
existing FEX and cage ranges. Discriminating test: inventory numeric intervals
from already-hashed Build 18/19 logs, distinguish historical intersections from
live-view blockers, calculate reservation extent, and prepare an independent
reserve-only PE contract test before designing a broker.

Evidence: tools/analyze-steam-ui-pools.py extracts only known numeric fields;
docs/STEAM_UI_POOL_INVENTORY.json records original artifact hashes/line numbers.
Build 18 has two real pool claims and two soft claims with three historical
intersections (one is a 64 KiB guard-prefix intersection). Build 19 has two real
pool claims, zero soft grants and 12 live-view rejections. Lifecycle/releases
are NOT reconstructed by this parser; historical intersections alone do not
prove simultaneous ownership. Source definitions and observed boot holds are
inventoried in docs/STEAM_UI_ADDRESS_SPACE.md.

The full four requests total 64 GiB+128 KiB. Existing FEX (16 GiB) plus cage
(8 GiB-64 KiB) give at least 88 GiB+64 KiB of disjoint address claims before
furniture, against a 64 GiB current high-band policy. This invalidates simple
packing or FEX-shrinking alone under those assumptions; it does not establish
that genuine UI is impossible on this iPhone. Lower gaps, native capabilities,
actual backing and allocator-instance lifetimes remain incompletely measured.
The Social Club partial-backing layout is not automatically applicable to Steam.

Minimal change: offline numeric-only inventory tool, isolated x64 PE
reservation-ownership probe and a fixed opted-in diagnostic launch route. No
allocator policy changed this run; strict Build 19 guard retained. Probe makes
at most four plain/guard-shaped
MEM_RESERVE/PAGE_NOACCESS calls with explicit opt-in. It never commits, accesses
or frees their ranges. Distinct results separate overlap (40), capacity gate
(70), overflow (41), opt-in refusal (64), and four reported disjoint grants (0).
A 0 result would not prove backing/CEF. Whole isolated Lab termination is required
afterward because pseudo-process exit can retain mappings.

Validation: actual probe logic passes host API fixtures for all five outcomes
under ASan/UBSan. It compiles as x86-64 PE with the prepared LLVM-MinGW toolchain.
Parser tests pass guard-prefix/interior/half-open boundaries, failure filtering,
redaction and explicit lifecycle limitations. Existing strict-reservation host
regression also passes. This is NOT a device or Windows control execution;
Build 20 full unsigned Xcode build and local strict signing PASS. Its final
Mach-O includes both `madeira-reservation-diagnostics` and
reject-soft-overlap markers. The original source-farm ARM64EC ntdll was explicitly
staged into the generated app, replacing the optional CEF observer, and hashed.
The fixed route uses paired automatic JIT, isolated bundle/flag and fresh-session
gates, validates x64 PE and writes drive_c/madeira-reservation-results.txt; no
Steam client is launched. Host policy checks include its explicit opt-in and
actual CRLF batch. No Build 20 install or device execution is claimed. Compiled
PE, signed candidate and private availability record are under .madeira-install;
run artifacts are in steam-ui-pool-inventory-20261023;
probe/evidence hashes are docs/STEAM_UI_RESERVATION_PROBE_EVIDENCE.json.

Next: install prepared Build 20 when device availability returns, stage the
compiled PE at the lab drive_c root and use madeira-reservation-diagnostics;
collect reserve/VirtualQuery result and end the whole Lab. Obtain independent Windows control if available. Then
measure disjoint native Mach mappings in unprobed gaps using non-overwriting
requests before any new layout/broker patch. Do not repeat the basic FLS suite,
re-enable aliases, infer UI success, or assume unavailable means locked.


## Builds 20/21: direct Kusch reservation and native capability tests

User explicitly requested direct phone testing. Phase 1, source parent
8225668ef16692dd087abf79ba26a7e6cd1428cc; submodule pins unchanged. Fork
remote/branch and prepared Build 20/probe hashes were verified. Fresh device
check now succeeds, passcodeRequired=false. The earlier CoreDevice 4016 gate is
obsolete. No credential automation or manual button request was needed.

Observed failure/hypothesis: strict CEF startup could be failing due to Wine
placement policy or because lower native slots are already occupied. First
separate the allocation contract from Steam; then test native mappings before
Wine/FEX bootstrap, with current-region context, before proposing a layout fix.

Build 20 device test: signed bundle installs; automatic paired JIT succeeds.
The x64 reserve-only PE grants 0x7800000000+0x400000000, then
0x73ffff0000+0x400010000. VirtualQuery confirms both as MEM_RESERVE (0x2000).
The third 16 GiB request returns NULL, Win32 error 487; the probe classifies
CAPACITY_GATE and exits 70. Two live-view overlap candidates are rejected.
This is not a Windows ERROR_NOT_ENOUGH_MEMORY claim: error 487 and the probe's
capacity category are recorded separately. Whole lab PID was terminated after
collecting results, releasing the intentionally retained guest reservations.
See updated STEAM_UI_RESERVATION_PROBE_EVIDENCE.json and private raw files
.madeira-install/steam-ui-reservation-run20/.

Minimal new diagnostic: Build 21 explicit madeira-native-vm-diagnostics argument
uses the paired JIT flow, but never starts Wine/FEX. It requires isolated bundle,
experimental flag, live debugger and a fresh session. Using SDK-declared 64-bit
vm_map/vm_deallocate and vm_region_64, it tries 64 KiB and 16 GiB PROT_NONE/NONE
mappings at each nonzero 16 GiB boundary from 16 to 496 GiB (62 requests).
VM_FLAGS_FIXED without OVERWRITE preserves existing mappings. Only successful
own mappings are deallocated, immediately; queried object-name ports are also
released. Failed cleanup or an unexpected returned address stops the sweep.
The first compile used unsupported iOS mach_vm.h; it was replaced with public
SDK interfaces and 64-bit size assertions, then the full build succeeded.

Build 21 host fixture passes ASan/UBSan: 62 requests, fixed/no-overwrite/NONE
protections, no release after failed allocation, null/non-null query-port
cleanup, early stop for mapping/port cleanup failure and unexpected address.
Policy/JIT/frontend checks PASS. Final Mach-O contains launch/probe/strict-guard
markers; deep strict signing and isolated device install PASS. Actual device
log confirms version21, automatic JIT enabled and native entry completed code0;
there is no Wine bootstrap in this run.

Native device result: 8 successful requests and 54 failures (all kr=3).
Both sizes succeed only at 0x7000000000, 0x7400000000, 0x7800000000 and
0x7c00000000. All successful mappings and query ports are cleaned up (code0).
Lower samples query existing native regions: [0x2ea000000,0xfc0000000),
protection1, and [0x1000000000,0x7000000000), protection0. Ownership/backing of
these pre-existing ranges is NOT established; do not unmap or re-protect them.
This is stronger than a Wine-only slot-walk failure, but is a pre-Wine app
snapshot, not a bare-kernel guarantee. It does not exclude smaller/unaligned
holes or prove simultaneous packability/committed/JIT-executable capacity.

Redacted numeric samples: docs/STEAM_UI_NATIVE_VM_SAMPLES.csv; component and raw
artifact hashes/limits: docs/STEAM_UI_NATIVE_VM_EVIDENCE.json. Private raw data:
.madeira-install/steam-ui-native-vm-build21/. Only the lab process was terminated
after collection; main at ee9fd2f and working game's app/data remain unchanged.
No new allocator behavior, assertion suppression or foreign-map reclamation.

Assessment: NO-GO for simply packing the four full aligned pool claims plus
existing FEX/cage into the measured high band. No interactive Steam login or
Big Picture success. Global feasibility remains UNDETERMINED: next identify
the genuine client's four request roles, allocator instances, exact alignment
and lifetime contracts before testing a correct demand-reduction/ownership
model. Do not repeat this grid, blindly shrink requested reservations, apply
the Social Club partial-backing path, or restore overlapping soft grants.

## Builds 22/23 — canonical pool ownership and genuine x86 probe

Research parent revision: f2de51718b629116325e4f4795ab8b5efc29f8fd.
Build 22 fixes a diagnostic-only impossible guard-size comparison and scans
bounded writable PE sections using fault-safe reads. Strict overlap rejection
remains enabled; no reservation or allocator behavior is changed. Host ASan/UBSan
scanner tests, launcher policy checks, all 37 native units and full iOS build
passed. Final Mach-O diagnostic and strict-guard markers were inspected before
signing/installing the isolated lab.

Actual Kusch log identifies adjacent canonical chrome_elf.dll data globals at
RVAs 0x13ae80/0x13ae88 containing 0x7800000000/0x7400000000. The JIT copy had no
matching cluster. This attributes the first regular/guarded pool pair to the
canonical chrome_elf image. It does not establish the later pair's ownership;
the saved libcef nrip is not a reliable allocation caller. Private 134-second
log: .madeira-install/steam-ui-pool-owner-build22/madeira-log.txt, SHA256
b4a59292de6f99a52edfe4ce1e4a14aa6d568c2beaf83d9d52462a7ab3004085.
SIGTERM did not end this Wine session; the identified lab PID was subsequently
killed and its absence verified before the next installation.

Upstream Chromium tag 126.0.6478.183 source was actually retrieved and inspected
(private .madeira-install/chromium126-contracts/). Its Windows 64-bit pool
contract uses 16 GiB pools and a guard-offset BRP reservation. Smaller iOS pool
constants are compile-time platform choices, not a demonstrated Windows runtime
switch. This is a comparator for Valve's matching-version custom CEF, not proof
of all Valve build flags. No pool-size patch, assertion suppression, foreign-map
reclamation or FEX edit was applied.

Next hypothesis: genuine Valve x86 components may avoid the 64-bit pool contract.
Official frozen win32 manifest 1769731672 and its CEF/webhelper packages were
retrieved and their manifest hashes checked. The DLLs are actual i386 PE files,
CEF 126.0.6478.183. Valve ended 32-bit Windows client support January 1, 2026;
this route is an explicitly limited compatibility experiment, not a supported
current-client solution or an authentication/update bypass.

Build 23 adds the isolated madeira-x86-cef-diagnostics launch argument. It
validates three i386 PE files and runs the existing chrome-elf heap/thread probe
compiled for i686 against the genuine chrome_elf import library. Result path:
C:\madeira-x86-cef-results.txt. Probe SHA256:
0c469683f47e484c06e9f72888f99b0d61b4ea0e5389cb8cb455ceb86b1a65da.
Production Swift fixture checks and full unsigned build passed; the final
Mach-O launch marker and bundled i386 ntdll were verified. Build 23 was signed
and installed. Resource transfer failed with a closed network socket (CoreDevice7000/POSIX54);
configuration copy timed out. One lock check confirmed passcodeRequired=true.
No launch was attempted on the locked phone. Staging/device execution remains
pending; no x86 runtime
PASS, full libcef startup, BrowserReady, login or Big Picture result is claimed.
Private artifacts: .madeira-install/steam-ui-x86-probe-build23/ and
.madeira-install/steam-ui-client32-candidate/inspection.json.

## Assessment

GO to continue the controlled Phase 1 experiment: architecture and local build
support a real-client test without rewriting the engine. NO-GO for claiming a
working Big Picture PoC or distributing this experiment as usable. Technical
feasibility on this device remains UNDETERMINED: a correct nonoverlapping
CEF memory model and interactive login have not been demonstrated. The current
four-full-pool high-band model is NO-GO based on Builds 20/21.
Do not infer impossibility from a missing signing account, or success from a
successful build. The three historical failure families remain untested here.

## Next discriminating experiments

0. Build 20 reserve-only contract test and Build 21 native grid are COMPLETED
   on Kusch; do not repeat them or the obsolete 4016 gate. Installed latest
   candidate is Build 26; real x86 CEF login is rendered and BrowserReady observed.
   Preserve the live session pending user sign-in; read the latest Build26 section. Read native VM evidence/samples, then attribute the
   four actual CEF requests and their alignment/allocator/lifetime contracts
   before changing a layout or broker. Preserve strict overlap rejection.
1. Preserve the passing Build 12/13 synthetic results and artifact hashes.
   Obtain an independent Windows control when available; do not claim it ran.
2. Inventory a full legitimate x64 Steam/CEF set in that prefix; no login cache or
   arbitrary client flags. Launch the login-only route. Capture native role
   lifecycle, CEF initialization, BrowserReady, window creation, screenshots and
   actual hover/click responses. Record meaningful negative results too.
3. If it faults, record Mach exception class/code and the actual libcef build/RVA.
   For kr=10 inspect backing-object and section lifetime, not blind protection
   retries. If it draws wrongly, capture source/destination checksums before
   blaming FEX. If CM fails, separate TCP/TLS/WebSocket/auth layers.
4. Only after interactive reliable CEF, add a distinct Big Picture flag and test
   Bluetooth navigation, library/account persistence, game launch and return.

Keep all experiment commits on experiment/steam-big-picture; do not merge them
into main. Resume from these gates rather than redoing the completed audit.

The recurring 305-minute task was updated to resume Phase 1 from this document,
rather than restarting the completed audit. No Windows Wine executable was found
on this Mac for the guest probe control; that execution remains pending.


### Build 23 continuation: locked-device gate and reproducible probe

A fresh continuation lock query again returned passcodeRequired=true; no device
launch or new installation was attempted. The worktree was clean at 6c880c0.
Added tools/build-steam-ui-x86-probe.py to make the precise i686 build command
reusable without publishing Valve files. Running it with the pinned toolchain
reproduced the candidate SHA256
0c469683f47e484c06e9f72888f99b0d61b4ea0e5389cb8cb455ceb86b1a65da.
The script verifies i386 PE output and refuses overwriting an existing result.
Remaining discriminator is unchanged: after native unlock, finish staging the
candidate/config and launch madeira-x86-cef-diagnostics once, then inspect its
result and private app log. No x86 execution or interactive CEF claim.


## Actual Build 23 result after Device Hub reconnection

Device Hub restored development access; initial lock check confirmed unlocked.
Config and genuine x86 resources were copied successfully. Explicit diagnostic
launch produced a fresh result: import-entry-reached, verifier-ready, all four
thread rounds with zero failures, result PASS and x86-cef-exit=0. Device log
confirms WoW64 guest window 0x7900000000. See STEAM_UI_X86_EVIDENCE.json for
hashes and limits; private files are in steam-ui-x86-probe-build23.

The native log subsequently reports an unhandled jit26_detach protocol breakpoint
after the guest result was written. This does not invalidate the recorded narrow
result, but is not evidence of clean session teardown. First kill attempt had a
remote-service connection error; a fresh process inventory confirmed the same
lab PID still alive, then a second kill succeeded and process absence was verified.
No overlapping lab launch or ordinary gaming app termination occurred.

Next hypothesis: a genuine i386 full-client CEF path may avoid the measured x64
pool capacity gate. Build24 adds an explicit madeira-steam-ui-x86-experiment
argument, requiring the same experiment flag and .steamui bundle. It selects only
Steam32Lab, verifies i386 Steam/client/webhelper/libcef headers and reuses the
existing fixed login-only command, without update or authentication bypass flags.
Default x64 launch is unchanged. Full official win32 manifest1769731672 (19
packages) was staged separately with size/SHA256 checks. The staging utility now
accepts an explicit win32 architecture, defaulting to the original win64 behavior.
Both real manifests parsed successfully. Production Swift fixture checks cover
missing/mixed architecture and working-bundle refusal. Full Build24 succeeded;
final launch marker inspected, signed and installed. Full-client device result
is pending; unsupported 32-bit client limitations still apply.


Build24 resource transfer did not complete: directory copy timed out at120s;
key steam.exe was absent on readback, a single-file retry also timed out. A
subsequent directory listing showed only partial files. The phone was unlocked
and app control worked; opening Build24 without experiment arguments succeeded.
No full-client launch was attempted on incomplete resources.

Build25 addresses this deployment gate only: an optional Steam32OfficialClient
folder inside the privately generated signed app can be imported to the new
Steam32BundleLab directory. The importer is .steamui/feature gated, checks i386
entry files, stages through a unique temporary directory and never overwrites
an existing target. Main game data and partial Steam32Lab are untouched. A host
fixture verifies import isolation and preservation of existing target data.
Default app launches still import/start nothing. Resource files are absent from
Git; all bundled file sizes/hashes were compared against the official package
inventory before re-signing. No Steam/auth/updater code is patched by import.


Build25 full unsigned build, final launch marker, bundled resource hash audit
and deep strict signature verification PASS. Its 120-second installation
command timed out; a subsequent authoritative apps inventory still reports
installed Build24. Build25 must NOT be described as installed. Device Hub screen
session was stopped and reconnected once without rebooting/unpairing the phone.
Small-file transport is being rechecked; no full x86 Steam launch has occurred.
Private Build24/25 logs and inventory files reside outside Git. Main remains
clean at ee9fd2f. Next: restore data transport or complete the already signed
Build25 install, verify the actual installed version, then launch the explicit
x86 experiment and collect authentic Steam/CEF evidence.


### Build25 authoritative install and first full-client device result

A later apps inventory after reconnect confirmed Build25: installation completed
on-device after the CLI timeout. Do not infer failure solely from a command
observation timeout. No duplicate install was started. Explicit x86 launch
imported the full client successfully and enabled automatic paired JIT. Actual
trace shows steam.exe running as machine014c, bootstrap updater Jan29,2026,
then guest exit0xc0000005 before any steamwebhelper/BrowserReady.

Mach failure is kr2 PROTECTION_FAILURE, guest read0x53e007be (host0x7953e007be),
not the historical libcef offset/KERN_MEMORY_ERROR. Reconstructed EIP0x7ba0ff61
and module base gdi32=0x7b9f0000 identify RVA0x1ff61. Actual bundled i386 gdi32
disassembly names get_gdi_client_ptr+0x41, a byte read from the GDI shared table.
The native trace earlier allocated the master at0x7053e00000; truncation/window
translation is a plausible cause, not yet proven by a successful fix.

Existing Wine source explicitly provides MADEIRA_GDI_SHARED_SECTION=1 for a
64-bit launcher that later creates 32-bit children. No [gdi-shared] marker was
observed in the first run, although its code exists in the final native image.
Next single-variable test enables that existing option only in the private lab
config; no new Wine/FEX/runtime patch. First attempt stopped before Wine because
JIT pool allocation failed at its safe-address check, so it is an INVALID GDI
comparison. Its PID was already gone on termination query. One subsequent fresh
launch keeps the identical config; evaluate it separately. Private bootstrap,
native traces and launch/install inventories: steam-ui-x86-client-build25/.


### Valid GDI single-variable comparison: updater reached

The subsequent same-config run entered Wine successfully. Actual log confirms
[gdi-shared] section-backed master0x70553a0000 and child guest-view0x7901a40000
for peb0x7900310000/pid0058. The previous get_gdi_client_ptr protection fault
was not observed in the bounded captured interval. Real Steam updater window
was visible in Device Hub. Valve bootstrap log reports downloading229240KB,
download complete, then extracting package. Authentication/licensing/update
checks were left intact; no credentials were entered. This supports the GDI
publication hypothesis for the earlier fault, not a complete allocator/CEF fix.
The official updater may change client files; pin post-update hashes before
attributing any later result to the original staged manifest. CEF/helper/login
is still pending at this checkpoint. No runtime patch was needed for this gate:
only existing MADEIRA_GDI_SHARED_SECTION=1 in the private experimental config.


## Build26 — required genuine Crashpad child discriminator

The valid Build25 run finished the official update and verification. Actual
helper/libcef/chrome_elf files were read back: SHA256 values in
STEAM_UI_X86_EVIDENCE.json match the originally verified official x86 packages.
CEF126 logs chrome_main_delegate initialization. Then native stderr explicitly
reports crashpad_client_win.cc144: crash server failed to launch, self-terminating;
helper exits -36863, with the existing generic --type child refusal immediately
before it. No BrowserReady or interactive login. WSALookupServiceBegin error8 is
also present but does not by itself establish the exit cause.

Hypothesis: the generic single-process gate incorrectly denies the genuine
required crash reporter. Minimal parent integration patch admits only one exact
--type=crashpad-handler argument when both MADEIRA_STEAM_UI_SESSION=1 and
MADEIRA_STEAM_UI_ALLOW_CRASHPAD=1. It does not rewrite that child's command line;
renderer/GPU/utility/ambiguous types retain refusal. No Chromium checks, crash
monitoring, authentication or licensing are disabled by this change. The previous
app command and other launch paths stay unchanged.

Production gate ASan/UBSan checks cover both flags, exact/quoted type, suffixes,
duplicate/ambiguous types and renderer/GPU/utility refusal. Existing SC CEF gate
regression suite passed; all37 native units and full iOS Build26 passed. Final
Mach-O contains the experimental Crashpad admission marker. Deep strict signing
and actual device installation succeeded. Explicit x86 experiment was launched
with GDI shared sections and strict reservations preserved. Device result pending.
Private artifacts: steam-ui-x86-client-build26/. No FEX/submodule edits.


Build26 device checkpoint: install succeeded, config transferred, and explicit
x86 launch returned PID13931. Later process inventory independently confirmed
that PID and JITHelper13933 still alive; phone lock query returned unlocked.
Two reads of Documents/madeira-log.txt failed CoreDevice7000/POSIX60 and yielded
zero-byte files, not runtime evidence. Do NOT infer a Crashpad PASS/failure from
them and do NOT restart the still-live experiment merely because observation
failed. Device Hub was attempting to connect display. During screen-session
recovery the computer-use tool reported the Mac locked with automatic unlock
paused due to physical input. User was asked to unlock the Mac manually. No
lock bypass, phone reboot/unpair or new overlapping experiment was attempted.
Resume by observing PID13931/current state and collecting its log after the
connection is available. Stage/launch already completed; no reinstall required.


### Build26 actual milestone: real login rendered and BrowserReady

After the user manually unlocked the Mac, the SAME installed Build26 session
was observed again without restarting it. Device Hub showed the genuine Steam
login window with account/password fields and an official QR code. Private
actual native log contains the exact Crashpad admission marker and GDI section
publication. Valve's steamui_html log contains BrowserReady (2 occurrences in
the collected log); CEF logs report chrome_main_delegate initialization. Exact
private artifact/Mach-O hashes are recorded in STEAM_UI_X86_EVIDENCE.json.
Prior zero-byte transfer failures were observer failures, not test failures.

This establishes real CEF login rendering on this phone, a material advance over
the previous capacity gate. It is NOT yet full Phase1 interactive login success:
field/button interaction and authenticated account/library remain unverified.
The user was asked to complete genuine Steam login/Steam Guard themselves,
without sending passwords/codes. No credentials were entered by the agent.
The live lab PID13931 is preserved pending user login; do not reinstall or
terminate it merely to collect missing observations. No screenshot/QR, raw log,
Valve binary or login cache is published. Ordinary game app/main remain intact.

Next: once user confirms login, verify interaction, authenticated Steam UI and
account persistence before a separately flagged -bigpicture experiment. Keep
32-bit unsupported-client limits explicit; Bluetooth navigation and licensed
game launch/return still require actual device evidence. Overall Big Picture
PoC remains INCOMPLETE, not a final GO.


## Build27 — iPhone software keyboard with an enumerated remote keyboard

User reports the iPhone on-screen keyboard cannot type into the real Steam login.
Source inspection found UIKeyInput insertText/deleteBackward unconditionally
returning whenever GCKeyboard is enumerated. Actual private input inventory
shows Device Hub's Generic Keyboard connected; no driver key events were recorded.
The enumeration-only deduplication rule can therefore discard software text.

Minimal lab-only routing fix: the focused Metal UIKeyInput responder owns text
when SteamUIExperiment is enabled. GCKeyboard no longer duplicates printable/
text-control key downs in that mode; releases still run and Ctrl/Alt/Win shortcuts
keep the raw route. Shift already held physically is preserved. Lab hasText now
keeps backspace available for externally held guest text. Ordinary game routing
is unchanged. Individual key payload logging in the bridge, event drain, driver
and optional hardware diagnostics is suppressed/redacted for the Steam session;
only a categorical text-route marker is emitted.

Production policy tests and existing hardware mapping/scan-code/focus regression
suite PASS; launcher/privacy regression PASS. Native win32u build passed with
FreeType merged. The worktree initially lacked FreeType build resources: a
read-only temporary symlink to the prepared primary build was used for compilation
and removed afterward; it is not a Git dependency or a change to the primary app.
Full Build27 passed. Final Mach-O text-route marker, policy symbols and FreeType
symbol checked; signed/installed, existing experimental configuration preserved.
The original PID13931 was absent and a full process inventory showed no Madeira
process before install. Explicit x86 launch succeeded. Device validation pending;
first log-read failed CoreDevice7000/POSIX60, not a runtime failure. Private
artifacts: .madeira-install/steam-ui-keyboard-build27/. Do not enter credentials
for testing; use harmless text and clear it without submitting sign-in.


Build27 device checkpoint: genuine Steam login re-rendered in the same session
at14:47 after a slower startup; no restart was used to obtain it. Device Hub
remote pointer actions did not summon the software keyboard, so no input success
is claimed from those attempts. The user was asked to tap the iPhone keyboard
physically, enter harmless test text and delete it without sign-in. Evidence
and limitations: STEAM_UI_KEYBOARD_EVIDENCE.json. Key payloads are not published.


Build27 input result: user explicitly reports the iPhone screen keyboard can
now insert and delete text. This is USER-REPORTED device validation; no typed
payload, password or screenshot of test contents was collected. Host policy/
hardware regressions and final component checks remain PASS. Login interaction
is now supported by the user report plus visible real Steam login/BrowserReady
from the preceding runs; successful authentication/library/Big Picture/game
launch remain separate uncompleted gates. Preserve the installed Build27 for
user sign-in; no additional build is needed just to log in.


## Build27 authenticated Steam library observed

After user keyboard/Steam Guard interaction, a fresh Device Hub observation of
the still-preserved session showed Valve's genuine desktop Steam game library,
account UI and populated game list. No account identifier or library screenshot
is published. This is direct visual evidence of authenticated real-client UI,
beyond the earlier login-only rendering and USER-REPORTED text entry. Account
persistence across a new session is not tested, and Big Picture/controller/game
launch are not inferred from the library view.

Remote pointer attempts at the Steam Big Picture entry had no visible effect,
as with the preceding software-keyboard toggle. Device Hub remote input was
observed moving a pointer without a successful click in the guest. Madeira's
existing iPhone mouse hint requires AssistiveTouch. User was asked to enable
Settings > Accessibility > Touch > AssistiveTouch before further direct mouse
tests. No accessibility setting was changed by the agent, no credential entered,
and no authenticated session restart/reinstall was attempted.

Next: after remote pointer interaction works, enter Valve's actual Big Picture
from its own client, capture navigation/render evidence, then test a separately
flagged launcher and Bluetooth input. Existing installed game discovery and
launch/return remain separate gates. Overall PoC remains incomplete.


## Phase3 first genuine Big Picture transition / Build28 discriminator

User reports AssistiveTouch enabled and manual entry into Big Picture; actual
Device Hub observation shows Valve's real Big Picture startup background and
loading indicator, remaining unchanged across several minutes. The native PID
14195 was independently confirmed alive. Valve logs record new BrowserReady and
controller-UI initialization events. No Big Picture navigation/library success
is claimed. CEF warnings include invalid browser dimensions0x0 and unsupported
FFmpeg pixel format-1, but their causal role is NOT established; an earlier
browser-info response timeout predates this transition. Official staged JS/assets
were inspected read-only; no Valve files were patched. Source deck/movie assets
do not establish what the currently visible loading component is.

Discriminating hypothesis: transition from desktop in this single-process/shared
CEF context may behave differently from starting directly in Big Picture. Build28
adds an explicit madeira-steam-big-picture-x86-experiment argument plus
MADEIRA_EXPERIMENTAL_BIG_PICTURE=1 configuration gate, in addition to the existing
SteamUI/.steamui gate. It adds only Valve's genuine -bigpicture to the otherwise
identical fixed launch command. Default login-only mode remains unchanged.
Host production Swift checks cover missing/false flags, wrong bundle, opt-in
command and ordinary-mode preservation. Full build passed; final Mach-O entry,
flag, keyboard-route marker and FreeType verified. Deep strict signing passed.
PID14195 was ended and absence verified before installation. Same authenticated
prefix/data is preserved; no auth cache is exported or replaced. Installation and actual direct-start completed; see results below. Private artifacts: steam-ui-big-picture-build28/;
redacted evidence: STEAM_UI_BIG_PICTURE_EVIDENCE.json.


### Build28 actual-device direct-start result

Installed Build28 into the isolated lab bundle, preserving its authenticated
prefix. Official Steam startup confirms `forcing gamepadui`, with `-bigpicture`
in its bootstrap command. The guest view remains black; direct startup has NOT
resolved the transition hang. No Big Picture navigation or game launch is claimed.

A bounded, strictly serial suspend/copy/SIGCONT sequence acquired the native log
and resumed the same lab process (PID14452). Three crashpad child traps share
guest PC0x6df3def3. Actual per-process module records place libcef at0x6aeb0000;
RVA0x308def3 matches an on-disk INT3 followed by UD2 in the exact device-readback
CEF. These are deliberate fatal traps, not evidence that their reported host
KERN_INVALID_ADDRESS is a guest memory-mapping failure. The precise assertion
and caller remain unknown. Two later browser logs say crash server did not
respond and self-terminate. This establishes a concrete failure chain to inspect,
not sole causation for every Big Picture hang. Separate native protection faults
read guest offset0xffffffff; saved guest PC maps to an NtReleaseKeyedEvent return
stub, which may be stale across the native syscall boundary.

No assertion, memory protection, FEX or Valve binary was changed. Redacted hashes
and exact scope are in STEAM_UI_BIG_PICTURE_EVIDENCE.json; raw logs stay private.
Next discriminator: identify the fatal caller/failed crashpad contract, reproduce
that contract in an isolated i386 test, and distinguish cleanup faults from the
initial browser failure. Bluetooth, usable Big Picture and game launch/return
remain unverified. Main/working gaming baseline remains untouched.


### Build29 fatal-caller discriminator

Observed Build28 INT3 belongs to a widely shared CEF fatal helper, so its address
alone cannot identify the failed check. Build29 adds a read-only native handler
probe gated by the lab session and the exact verified CEF126 i386 trap. It resolves
the faulting thread's PEB/WoW window, walks at most eight increasing EBP frames
with a one-MiB per-frame bound, and emits only CEF code RVAs; no stack payload,
credentials or exception/protection behavior is changed. Parent native source
only; no FEX/submodule edits. All37 native units and full Xcode build pass. Marker
verified in final Madeira.debug.dylib (the main executable is its debug shim),
plus deep strict signature verification. Device result pending. Private artifacts:
steam-ui-fatal-build29/. Next read the caller and inspect the corresponding
conditional/API contract before proposing a behavioral patch.


Build29 actual result: genuine populated Big Picture home rendered after launch,
with recent-game cards and news. Later a real game details/download page appeared;
input source attribution and successful navigation require further validation.
The authenticated session persisted across the app upgrade/restart without any
agent credential entry. A stable snapshot through75.9seconds contains no guest
INT3, no fatal-caller marker and no Crashpad no-response message. This contrasts
with Build28 but the probe only reads memory: it is NOT evidence of a causal fix
or reliable startup. Private logs/hash are in the redacted evidence file. Initial
isolated steamapps inventory contains no installed-game appmanifest; the normal
app's games/saves remain untouched. Awaiting direct user input check because
Device Hub input delivery is still not established. Game execution/return and
Bluetooth remain separate unverified gates.

## iDeck product integration — Build30

User explicitly confirms games run and changes the objective to an integrated
iDeck app: first-run setup, Big Picture entry, persisted Steam login/auto-start,
controller-first/direct-touch operation, floating keyboard/controller/options.
This supersedes treating research diagnostics as the final end state.

Build29 device observations additionally show Hot Roads' Unity splash and game
menu, Steam tracked `hr.exe` as app1819280, and its private manifest has StateFlags4,
build7695775, installed size221125214bytes. Game play is USER-REPORTED; menu and
launch are artifact/visual observations. Return and Bluetooth are not verified.

Build30 implements the isolated iDeck product shell and branding, explicit runtime
preparation, existing JIT setup, readiness checks for registry plus four genuine
32-bit PE components, persisted auto-start gated against every explicit diagnostic,
full-screen landscape session and direct-touch mode. A window-level floating
menu reuses keyboard, controller overlays/layout editing and settings. Existing
controller routing owns input in launcher/menus and releases it in Steam. Login
state remains in Valve's existing prefix, never exported or replaced.

Production lifecycle/client-architecture tests, original launcher gates and
keyboard routing pass locally. Full Xcode build passed; final signing/link checks
are recorded in the private ideck-build30 artifacts. During the availability
check, CoreDevice refused service/power assertions with error4016; installation
and product UI validation remain pending. No phone restart, lock bypass or
working-app changes were attempted. See IDECK.md for reproducible build/user flow
and the full outstanding acceptance list. Main remains at ee9fd2f; research work
continues on the isolated experiment branch.


Build30 pre-install continuation: CoreDevice still rejects service assertions4016;
Device Hub independently reports the Mac locked and requires manual unlock. User
asked once to unlock Mac/iPhone and connect it. No lock bypass or repeated install
attempt. A local lifecycle review found that LibraryModel.refreshFlag could reset
controller ownership when returning from JIT into the iDeck launcher; iDeck now
restores its own launcher/menu ownership instead, leaving ordinary Madeira logic
unchanged. Device validation remains pending this external connection gate.

### Build30 external-gate audit

A further independent CoreDevice inventory still marks the exact target iPhone
unavailable. This is the same connection/manual-unlock gate across three
consecutive goal turns; no install/launch handle exists to poll. The prepared
Build30 debug Mach-O SHA256 matches IDECK_BUILD_EVIDENCE.json. Deep strict
signature verification succeeds with normal authorized keychain access (a
sandbox-only trust evaluation failed; it does not establish a bad signature).
Primary checkout remains clean. Installation and ordinary-launch setup, JIT,
full-screen/controller/direct-touch/menu/keyboard/overlay, automatic-login reopen,
game play and Steam return remain unverified for Build30. Do not manufacture
new runtime fixes or claim product completion from local tests. The next useful
step requires physical connection/unlock, then identify any live lab process and
install only the isolated bundle. Raw availability JSON stays private at
ideck-build30/device-availability-final.json. Goal is blocked on that external
gate until the user/device makes it available; recurring task may revalidate it.


## 2026-10-24 — Build30 installation gate cleared

Scheduled availability check found Kusch paired/available, no passcode required.
Full process inventory contained no Madeira.app session (the attempted CLI
CONTAINS predicate was invalid for its URL type; a complete inventory replaced
that failed observation). Existing Build30 signature verified. Isolated install
completed, installed app inventory confirms display iDeck/version30. Ordinary
launch with no extra arguments succeeded; PID17464 independently remains alive.
A private1172-byte startup log has build marker but no experimental/Steam/JIT
launch markers, consistent with first-run launcher rather than diagnostic bypass;
this is not visual launcher verification. Hash and limits in IDECK_BUILD_EVIDENCE.

Device Hub still reports Mac locked; no manual unlock or credentials automated.
Current app session preserved. Next: after manual Mac unlock, inspect launcher,
complete setup/JIT through its own UI, validate fullscreen Big Picture and floating
keyboard/controller/options, direct touch/controller navigation, auto-login reopen
and game/return. Earlier gameplay remains user-reported/Build29 evidence, not a
Build30 product validation. No runtime patch this run; original gaming app/main
unchanged. Private artifacts: ideck-build30/install.json, installed-app.json,
ordinary-launch.json, ordinary-process-alive.json and ordinary-launch-log.txt.


## Build30 black screen / Build31 library freeze / Build32 discriminator

User reports a black screen after completing iDeck setup. Exact live PID17464
was preserved while private native/Valve logs were copied. JIT, native pool and
Steam gamepadui startup were confirmed; CEF child fatal now has an8-frame EBP
chain. Build31 adds only an exact-version/lab-gated numeric constant classifier
at the existing fatal probe; final Mach-O verified,37 native units/full Xcode and
deep strict signing passed. Old process termination/absence checked, isolated
install and ordinary launch succeeded. Saved iDeck setup automatically obtained
JIT and started genuine Big Picture with no diagnostic argument. PID17634 remained
alive. Assertion classified as vector-front-empty at libcef+0x308def3, direct
caller+0x82553a9, with repeated identical ancestors.

Pinned official Chromium126.0.6478.183 Crashpad minidump_memory_writer.cc SHA256
00c803844af5e50cb49671d4972ff28163a5a780530e2cfabcc3008ff8719322: its
CoalesceOwnedMemory filters zero-size ranges then takes the first remaining item.
Binary control flow and exact assertion match this sequence. This is strong
source/disassembly correspondence, not symbol/PDB proof or sole-root-cause proof.
It points to a secondary report-writer failure; do not suppress the assertion or
claim it explains every hang. Dump inventory: Steam assert dumps32bytes and
Crashpad report files0bytes, so they do not contain an original exception stream.
No useful exception code can be inferred from those incomplete dumps.

User then reports Build31 successfully entered Big Picture and browsed Library,
but later froze while the native iDeck menu still opened. This is USER-REPORTED
UI validation, not remote visual verification. Current log samples show no
STATUS_NO_MEMORY/bad_alloc/pool-exhaustion marker; that does not exclude memory
pressure. CrBrowserMain samples wait in native read/select. Mac control tool still
reports locked despite user's unlock report; no lock bypass attempted. Read-only
CLI collection continued, preserving the frozen process until bounded capture.

Build32 hypothesis: Crashpad's remote read of the original EXCEPTION_RECORD32
can distinguish the initiating browser exception from report-writer failure.
A lab-only,16-sample bounded filter emits only recognized public exception codes
and PC, never parameters, arbitrary strings or buffers; ordinary read semantics
unchanged. Production size/code/parameter-count filter passes ASan/UBSan tests;
launcher/readiness regressions and full37-unit/native/Xcode build pass. Final
Mach-O marker and signature verified. No Valve/FEX/submodule edits. PID17634
terminated only after capture; Build32 isolated installation underway at this
checkpoint. Private artifacts ideck-build30/black-*, ideck-build31/, ideck-build32/;
redacted evidence IDECK_CEF_FREEZE_EVIDENCE.json. Next obtain original exception
metadata and discriminate a minimal compatibility correction before claiming a
black-screen/library-freeze fix. Game return/Bluetooth/product stability still
unverified; original app/main unchanged.


Build32 install/ordinary launch completed, PID17759 independently verified alive.
Stable serial suspend/copy/SIGCONT capture completed and process resumed. The
original remote exception record is0xe06d7363 at guest0x7bc52f79, before the
secondary vector-front-empty trap. This identifies a Windows C++ exception, not
its type, throw origin or cause. No memory-fault/failed-allocation conclusion is
justified by this metadata. Build33 extends this same discriminator with bounded
read-only x86 MSVC RTTI traversal inside the target's WoW window, emitting only
a fixed standard exception category or unknown. No exception object, arbitrary
type name or message is logged. Native37/full Xcode/deep signing and final marker
checks pass; isolated installation underway. Previous hung lab PID terminated
only after evidence capture. This is diagnosis, not a claimed library-freeze fix.

### iDeck Builds34–36: discriminate and repair pseudo-process default keyed events

Base parent74eef9e; Wine9129e968 pinned, main ee9fd2f remains clean.
Build34's actual original remote exception is0xc0000005 at guest0xfff926a0:
i386 ntdll RtlRunOnceComplete+0x90 dereferences the next waiter node. This
is stronger evidence than attributing a saved native return PC to NtReleaseKeyedEvent.
The earlier C++ exception and later report-writer failure are separate observations.

Hypothesis: native Wine keyed_event is one shared global, while wineserver handles
are process-local. Main creates a non-inheritable handle; the minimal iOS child
boot does not create its own. RtlRunOnceBeginInitialize ignores a failed default
NtWaitForKeyedEvent after linking its stack node, potentially leaving a dangling
waiter. No FEX/Valve edits or assertion suppression were used.

Discriminating isolated i386 PE, keyed-event32-probe.c: compare null/default and
fresh explicit handles with a zero timeout, then only if that contract passes run
four contending InitOnceExecuteOnce workers. Build35 actual device default
wait/release both return STATUS_OBJECT_TYPE_MISMATCH(0xc0000024); fresh explicit
handle returns expected STATUS_TIMEOUT(0x102). Test stops safely before contention.
Build36 same PE/device: all four operations0x102, creation0, all workers join,
exactly one callback and zero failures: PASS. Private result hashes and redacted
metadata: IDECK_CEF_FREEZE_EVIDENCE.json; raw artifacts outside Git ideck-build35/
and ideck-build36/.

Minimal patch: parent-owned sync_ios.c includes the unchanged pinned Wine source,
then resolves implicit/null keyed events per PEB and WinPID only for isolated
MADEIRA_STEAM_UI_SESSION=1. Explicit handles and ordinary gaming delegate unchanged.
Native pthread mutex covers lookup/creation, never blocking keyed wait/release.
128 identities retained for one native session; no reuse/foreign-handle fallback;
capacity/create failure returns an actual error. Wine closes process handles at
exit, but identity reuse and >128 process lifetime are not product-validated.
ASan/UBSan production-resolver harness passes concurrent lookup, process isolation,
ordinary/explicit bypass, creation failure and bounded capacity. All37 native units,
full Xcode Build36, final Madeira.debug.dylib linked marker and deep strict signing
pass. Existing iDeck readiness/launcher/keyboard/hardware/touch regressions pass.
Initial host Swift cache sandbox failures were resolved using explicit /tmp caches.

Build36 is signed and installed into the existing isolated iDeck bundle, preserving
Steam auth/games/saves. Probe launch then fresh ordinary app-open launch completed,
PID17843 independently verified. Native Steam trace still records original C++
system_error (public RTTI hash0fa757d1) and secondary vector-front-empty assertion.
Thus the keyed-event defect is fixed and device-tested, but it does NOT establish
that library freeze/black screen is fully fixed. A later live log transfer failed
CoreDevice7000/POSIX60 while exact lab PID stayed alive; do not infer termination.
Mac CUA still reports locked. User library-navigation regression is pending.
Next discriminate system_error public code/throw caller with bounded metadata,
and verify actual Big Picture library/menu/game-return behavior. Bluetooth remains
unverified. Do not repeat login or replace the primary app.

Read-only exact official CEF PE inspection locates public
.?AVsystem_error@__Cr@std@@ RTTI, catchable-type size20 and copy constructor
preferred VA0x158dca90(RVA0x58dca90). Its disassembly copies the8-byte error_code
from object offset12 (runtime_error base occupies12 bytes). This gives a precise
next diagnostic: after exact type/version/size checks, read only numeric error
value and public category identity, never runtime_error text. No such device
error-code reading has been performed yet; no guess of EPERM/ENOMEM is evidence.

### Build36 startup regression and bounded system_error discriminator

User reports Build36 did not enter Big Picture. Actual current PID17843 remained
alive; private failed-start.txt records repeated C++ system_error. This supersedes
the pending navigation question, and is not a stable-launch pass. Build37 exact
copy-address gate emitted no error value despite successful RTTI decoding. Build38
instead verifies the actual10-byte public copy instruction pattern after exact
type and20-byte catchable-size checks, avoiding a fixed guest load address. It
reads only the8-byte numeric error_code, never exception message/credentials.
Actual device Build38 reports value87 (Windows ERROR_INVALID_PARAMETER); no
particular failing API is identified by that number alone. Build39 adds bounded
original i386 CONTEXT/EBP return-address capture for the known RaiseException PC;
only code addresses, at most8contexts/12frames, no stack arguments/text. All37
native units/fullXcode and final linked diagnostic/signature checks pass.
Do not conflate this with a runtime fix or suppress the secondary Crashpad trap.

### Build39 module ownership and Build40 browser-only software-3D A/B

Build39 original CONTEXT return chain matches vk_swiftshader.dll, actual guest
base0x67e10000, NOT libcef: returns include SwiftShader+0x2803b (thread constructor)
and+0x338c63/+0x338ca4 (system_error throw helpers). Exact official DLL SHA256
9eadc24a8993b354a76b92d794a7804f34400357a0a826b105d294054ed05529.
PE disassembly at+0x27fe6 calls thread helper+0x339b70, branches on nonzero error,
then throws. The CRT helper invokes CreateThread and may also fail before it.
Thus87 is not yet proof of NtCreateThreadEx's actual failing status; GetLastError
could be stale after an earlier CRT allocation failure. No sole root cause claim.

CORRECTION: Build39's inferred cef_base0x62857c30 was invalid. libc++ types and copy
patterns are shared across modules; subtracting a CEF-specific RVA from a
SwiftShader constructor cannot identify its module. Removed that inferred field
in Build40. Public numeric error87 remains valid under type/size/copy verification;
module ownership now comes from loader evidence and exact PE code correspondence.

One hypothesis / discriminator: browser 3D software fallback triggers this failing
SwiftShader initialization. Build40 appends Chromium126's official
--disable-software-rasterizer only under MADEIRA_STEAM_UI_SESSION=1. Existing
software composition and ordinary game GPU paths are preserved in source; actual
Steam UI availability is NOT assumed. env.MADEIRA_STEAM_UI_NO_SWIFTSHADER=0 opts
out for A/B. Official source content/public/common/content_switches.cc revision
126.0.6478.183 defines this as disabling a3D software rasterizer; source SHA256
b344a019e583dca32550a14e39792487c1ebbf73635940db3fa96034685da947.
No Valve files or FEX were modified. The original failing thread API is still
unrepaired; this is an isolated browser policy experiment, not a general fix.

All37 native units/full Xcode Build40/final debug dylib marker/deep strict signing
pass. Host ASan/UBSan executes the production policy fragment for ordinary path,
isolated default, explicit opt-out and preservation of existing switches. Launcher,
exception metadata and Crashpad policy checks pass. Build40 installed successfully
in existing isolated iDeck, retaining Steam login/games/saves. Its ordinary launch
was refused by the device lock (CoreDevice10002/FBS Locked); do not repeat it while
locked. No device UI/rendering/switch-effect validation exists for Build40 yet.
Private evidence ideck-build37..40/, redacted hashes in IDECK_CEF_FREEZE_EVIDENCE.json.
Primary main remains ee9fd2f; scoped parent a428172, no submodule edits.

Independent next fallback: swiftshader32-probe.c loads the existing official DLL
and invokes Vulkan1.0 instance/device creation without CEF/network/login. Win32 ABI
static assertions and i686 compile with -Wall -Wextra -Werror pass; PE i386 verified.
It only observes exception codes and never handles/suppresses them. It has NOT
run on phone. After unlock first test already-installed Build40 once; check policy
marker, SwiftShader load/throw and real Big Picture navigation. If ineffective,
run isolated Vulkan probe and instrument early CreateThread/CRT failure with numeric
status only. Do not call build success a rendering or stability result.

### 2026-10-24 11:15 UTC checkpoint — existing device gate unchanged

Research HEAD/origin experiment f8a7511cddc14ab07752d30ee7327e84715c4038;
origin/main and clean primary ee9fd2f4c21229dfce31a25c211d44df267336d8.
Read latest freeze evidence and checked lockState once: passcodeRequired=true,
unlockedSinceBoot=true. Private ideck-build40/heartbeat-lock.json SHA256
fb166a2234f762db1ebcd5688e166a82aad2b0cd66419783d3ba7dabe969e300.
No launch/install, credential entry, lock bypass, or overlapping experiment was
attempted. Build40 remains the already-installed pending browser-policy test;
there is no new device or UI result. No runtime patch or repeated build/test was
justified before that discriminator. Next after native unlock: launch Build40
once, verify actual policy/module/exception evidence and genuine UI behavior;
only if ineffective proceed to the prepared isolated Vulkan probe. No repeated
user notification for this unchanged gate.

### 2026-10-24 user-requested Build40 installation

Device now reports passcodeRequired=false. Signature deep/strict verification and
exact final debug Mach-O hash d4310543442c25e650c4ef1ba50f1cc6c81602b1bb6bf41c9cec54583b06c3d9
match the prepared Build40; no source rebuild was needed after doc-only eceddd0.
No lab process was running before install. Reinstallation into the existing lab
bundle succeeded; ordinary no-argument launch succeeded, PID20471. Initial live
log confirms actual build40 but is too early for policy/CEF/UI conclusions.
Private user-install/user-launch/user-first-log evidence in ideck-build40/.
Main/working app/auth/games preserved. Next collect policy/module/error evidence
and user-visible Big Picture/library behavior before claiming a fix.
Subsequent startup log remains at native startup/frontend configuration, without
Steam/JIT/policy markers; no automatic Steam launch is established. Mac CUA still
reports locked, so direct GUI inspection is unavailable. Leave installed PID20471
undisturbed for the user to open iDeck/start Big Picture. This is successful app
installation/launch, not successful CEF or game validation.

### Build40 actual black-screen result; Build41 isolated Vulkan reproduction

User reports entered then black/unresponsive. Actual live lab PID20471 native
trace confirms both new policy markers, no SwiftShader module or system_error in
this bounded trace, then guest breakpoint708daaa1. Actual libcef base6afb0000
makes RVA592aaa1: exact official PE has INT3/UD2 after shared string_view assertion
branches. This is not the old fixed-base report-writer fatal. Exact branch among
three checks is not captured; do not assert it is definitively a null string.
Steam/CEF process exit events occur while host app remains alive/black. Native
pool also shrank to560MiB, peak phys4028MiB; these are observations, not sole cause.
Private ideck-build40/black-screen/native.txt hash in freeze evidence.

Decision: reject default disabling3D software fallback as a fix. Build41 restores
old default; disabling now requires explicit env.MADEIRA_STEAM_UI_NO_SWIFTSHADER=1.
This is a controlled A/B only, not a general runtime correction. Add explicit
madeira-swiftshader-diagnostics entry, gated isolated bundle/flag, i386 probe PE,
fresh JIT session; generic madeira-arg exclusion prevents concurrent Steam start.
Host production policy/launcher tests pass missing/x64/non-isolated rejection,
exact i386 command, ordinary path, opt-in/out and readiness.37 native/full Xcode,
linked entry, deep strict signature and isolated install pass.

Actual device probe PID20544: vkCreateInstance=0, enumerate=0/one physical device;
before vkCreateDevice family0 then e06d7363 observed and NOT handled/suppressed.
Result and private native log in ideck-build41/. This reproduces the driver failure
without Steam/CEF/network/auth. Underlying Win32/NT failure still unknown.
Build42 adds isolated bounded observation of EVERY NtCreateThreadEx return,
including early server/attribute failures, with numeric status/flags/stack sizes
only. Original arguments, handles and return status are delegated unchanged.
Next re-run this same Vulkan probe to distinguish a native thread-create failure
from a CRT allocation failure before the native call. Do not blame FEX or bypass
assertions without discriminating evidence. Main baseline remains untouched.

Build42 actual native results: all seven observed thread requests failed with
c000000d INVALID_PARAMETER or c000000b INVALID_CID; zero_bitsffffffff is the WoW
mask, not itself evidence of failure. Build43 records precise stage: first
c000000d occurs in output-attributes AFTER native thread creation; later CID
failures occur at server-new-thread. self=1/processffffffffffffffff refutes the
pseudohandle-truncation hypothesis. Native logs private ideck-build42/43/.

Source discriminator: pinned WoW ps_attributes_32to64 GROUP_AFFINITY widens the
pointer but preserves12-byte struct/Size and incorrectly claims both layouts
match. Win32 mask4+group2+reserved6=12; native mask8+group2+reserved6=16.
update_attr_list dereferences it as native and invokes NtSetInformationThread,
which rejects invalid group/reserved/mask and terminates the new thread.
Build44 minimal fix is parent-owned native update_attr_list: only lab session,
WoW target and Size12 decode each field into native structure, then SAME original
validation/API. Invalid reserved/group values remain invalid; no status spoofing,
affinity bypass, assertion suppression, Valve/FEX/submodule edit. Production helper
ASan/UBSan harness passes exact unaligned12-byte read, zero extension, preservation
of all fields, input immutability and ordinary/native/malformed rejection gates.
Actual Vulkan re-test is required before claiming this corrected device behavior.

### Build44 actual Vulkan PASS after minimal ABI correction

All37 native/full Xcode/final linked conversion marker/deep strict signing and
isolated installation pass. Same staged i386 Vulkan probe on actual Kusch:
instance0, enumerate0/one physical device, device0, PASS including device/instance
destruction. Six converted affinity structures group0/mask3f; all seven observed
NtCreateThreadEx return00000000 rather than c000000d/c000000b. Exact private
results/native/final debug Mach-O hashes in IDECK_CEF_FREEZE_EVIDENCE.json.
This is artifact-backed device validation of the ABI/SwiftShader initialization
correction, not proof of full Steam/library/game-return stability. Probe PID20639
identity revalidated and terminated after capture, fresh explicit genuine Big
Picture launch started in same prefix/auth. GUI result still pending; no agent
credential entry and no claim that ordinary auto-start was exercised this time.

Build44 real Steam regression: PID20656 fresh explicit Big Picture launch;
strictly serial short suspend/copy/SIGCONT succeeded and process resumed. Bounded
native sample at+59.31s:128 observed thread-create successes/zero failures (cap128),
six correct affinity conversions, no system_error/remote-exception/old fatal marker
and no Steam-exit event. Prior failed disabling policy absent. These are numeric
runtime observations, NOT UI/interaction or long-term stability proof. Snapshot
perturbs timing; user Library-navigation question is pending. Leave this live
session undisturbed while awaiting UI report. No fresh login required.

USER regression result after Build44: "可以进入并浏览" in response to whether
Big Picture opens and Library browsing works. This is explicit user-confirmed
interface/navigation success, separate from agent visual verification. Combined
with exact Vulkan before/after and native thread evidence, the current black-screen
report has a concrete verified correction. Do not claim all long-term/product gates
complete: controller/direct touch, licensed game launch/return, ordinary restart
with saved login and Bluetooth remain to be separately validated. Preserve live
session and do not repeat the fixed diagnostic loop without new failure evidence.

### Build45 user-requested iDeck interaction changes

User requests draggable top-right HUD, game exit/return, working Steam menu,
virtual controller recognition and account switching. Main remains untouched.
Fix centering by explicit screen-sized HUD layout/position; persist safe-area
clamped normalized location. Menu scrolls on landscape screens and preserves
controller selection. Replace Esc-only Steam action with a fixed local Windows
helper focusing Steam and sending Ctrl+1. Graceful game exit only WM_CLOSE to
foreground/unambiguous standard Steam library game window, wait for real process
exit then open genuine Big Picture. No forced kill. Account confirmation opens
Valve's own steam://changeuser (also observed in exact official Steam UI JS);
no cache deletion, token copy or credentials. Helper has three fixed commands,
UUID acknowledgements, bounded native timeouts, and no network/arbitrary shell.

Virtual controller now reserves slot0 before Steam even when hidden, and exposes
generic HID plus XInput only for Steam UI sessions. Existing ordinary controller
mode/default reservation policy is preserved. Enabling overlay loads Xbox if
saved layout has no pad controls. Full Xcode45/helper i386 Werror/deep signing,
final debug Mach-O/bundled helper markers, production position/command policy and
existing input/touch/gamepad/launcher/keyboard checks pass. Native44 compatibility
archive unchanged. Build45 installed in existing isolated bundle and explicit Big
Picture launch succeeds. Actual Windows helper result ready/ready and controller
status xinput1/hid_gamepads1; hashes in IDECK_CONTROL_EVIDENCE.json. This is API
enumeration, not Steam UI/button proof. Mac CUA reports locked; user drag/virtual
navigation/Steam menu regression question pending. No agent account switch or
new credential entry. Actual game-close/return and account-chooser UI still pending.

### Build46 Steam menu scan-code experiment

Base abf24db. User reports Build45 Steam menu still ineffective; no explicit
result for drag/virtual navigation. Latest private ACK is no-game (exit action),
so it cannot establish whether the earlier menu request dispatched. Exact shipped
Steam UI TranslateKey uses event.code and maps ctrl+Digit1 to STEAM_GUIDE. Pinned
Wine win32u/message.c passes KEYBDINPUT.wScan unchanged for virtual-key SendInput;
helper supplied zero. Hypothesis: CEF gets no usable Digit1 physical key code.
Minimal patch populates MapVirtualKeyW(VK, MAPVK_VK_TO_VSC) for fixed chord events,
including releases. No Steam/CEF binary, native compatibility or auth changes.
Full Xcode46, i386 Werror helper, deep strict signing and iDeck/launcher/keyboard
host regressions pass. New bundled PE hash in IDECK_CONTROL_EVIDENCE.json; private
build/sign/install artifacts in .madeira-install/ideck-build46. This is a single
input-format experiment, not proof of root cause or actual menu opening. Next:
physical on-device Steam menu click with corrected helper, then distinguish focus
or modifier routing if still ineffective. Account switching and game return remain
unverified; do not log out or force-close games for diagnostic convenience.

### Build47 disabled Steam controls: helper startup architecture

User reports Steam menu and change-account disabled in Build46. Private native
log proves helper started as i386 pid0068/tid006c then ended with c0000005 before
ready ACK. Fault is wow64.dll RVA1b724 writing0x480 with absent CPU reserved state;
this is helper compatibility-layer initialization, not failed Steam shortcut UI.
No sole cause of the underlying WoW64 initialization failure is claimed. Build45
had reached ready; its success does not establish reliable i386 helper startup.

Small discriminating change: compile our helper x86_64 and enforce that exact
machine in native shell resource validation, avoiding additional i386 startup.
Genuine Steam stays i386, existing native runtime/Valve/auth paths unchanged.
Prior scan-code correction retained but not yet proven by physical UI effects.
Xcode47, helper x64 machine inspection/Werror, strict deep signing and existing
iDeck/launcher/keyboard checks pass. Private artifacts ideck-build47; exact hashes
in IDECK_CONTROL_EVIDENCE.json. Next establish actual ready ACK, then physical
Steam-menu and account-chooser availability; do not automate account switching.

Build47 device outcome: installed/signed. First launch failed JIT pool allocation
before Wine; original PID21122 was absent on inventory, so no termination was
performed. Fresh explicit launch PID21130 actually produced `ready ready` ACK
(private ready2.txt; hash in control evidence). This verifies x64 helper startup
on this session, not all-session reliability or Steam menu UI success. User asked
to check enabled state/menu; account action intentionally not invoked by agent.

### Build48 account entry moves to iDeck launcher

User confirms Build47 Steam menu works, but account action has no visible effect.
User requests selecting/login via iDeck before entering Big Picture. Native Steam
credentials are not interchangeable with Dock tokens: preserve Valve-owned login.
Add launcher account action and pass the exact fixed steam://changeuser URI to
validated Steam exe on initial launch with Big Picture, avoiding old ShellExecute
registry dispatch. This is a new routing hypothesis; chooser success is unverified.
Remove old HUD account item and adjust controller indices. One-time migration
exposes launcher by disabling auto-start; subsequent toggle choice is preserved.
No account/config login-cache deletion or credential arguments. Main unchanged.

Full Xcode48, strict deep signing, final debug Mach-O label and production launch
policy tests pass, including account URI present only on explicit account launch
and absence of credential flags; existing iDeck/keyboard checks pass. Installed
and ordinary no-argument launch succeeds. Private artifacts ideck-build48. Agent
did not trigger logout/choose account. Physical chooser/login and subsequent
Big Picture account continuity remain pending user test; no claim of validation.

### Build49 initial Steam input focus discriminator

User clarifies controller/mouse unresponsive inside guest Steam login/account
window, not native launcher. Actual current helper reads xinput1/buttons0/hid1;
resting enumeration is not event delivery. Prior native log had pad=none, so no
physical controller presence is established. Additional question pending: direct
finger response and virtual vs physical controller. Mac CUA remains locked.

Hypothesis: initial visible Steam window is not foreground; helper previously
only focused on menu action. Minimal isolated helper change waits for first
visible Steam-owned window and focuses until one successful initial activation,
then stops activating (cannot continually steal focus from games). Writes only
startup focus/match booleans and sampled controller-state-change count. Own stale
diagnostic files removed on fresh session. No key/text/account/window-title logs.
No underlying runtime/FEX/Valve/auth changes. This is a discriminator, not a
confirmed input fix. Full Xcode49/x64 Werror/strict signing/final PE markers and
existing launcher/iDeck/keyboard regressions pass. Artifacts ideck-build49. Next
read actual foreground match and observed controller changes while comparing
physical touch/controller/mouse response; distinguish a frozen UI or unsupported
login gamepad navigation if foreground and events are proven. Counter polls at
500ms and may miss short presses; do not overinterpret zero count.

Actual Build49 installed and launched ordinary genuine Big Picture mode without
account-switch request. Fresh helper reports startup_focus1/foreground_matches1,
and resting xinput1/hid1/observed_changes0. Hashes in control evidence. Confirms
initial foreground acquisition, not previous lack of focus, working mouse or
controller UI. Waiting for physical touch/virtual-vs-physical clarification and
post-change response. Keep this session alive. No agent credential interaction.

### Build50 post-Steam-Guard stall: ordinary Steam login before Big Picture

User confirms Build49 input now responds and credentials can be entered. User
reports approving the official Steam mobile login request, but iDeck stalls.
Preserved native PID21346 session and private Steam logs before modifying code.
Steam login state stays WaitingForCredentials; no current Success/OK. webhelper
10:27:41 says it kills an unresponsive browser. CM WebSocket handshake completed,
then10:27:16 Try another CM/Failure was ignored because client was not waiting for
a logon response. These do not prove bad password, rejected Guard or a sole
network cause. Two early native auxiliary WoW64 faults and later Crashpad
vector-front-empty are not treated as the original login failure. No agent login.
Raw logs remain private; hashes and categorical findings in control evidence.

Single hypothesis: authenticating inside direct Big Picture may differ from the
previously verified ordinary desktop login path. Product launch/account setup now
opens genuine desktop Steam first; bounded observer starts at current login-log
EOF and waits for a new exact Success/OK. It ignores historical success, partial
lines and non-success states, handles rotation/truncation, and records no account
payload. Only after success plus helper readiness dispatch fixed Big Picture URI
to actual running Steam executable, with protocol fallback only when it cannot
find that process. No credential arguments/cache editing/FEX/Valve changes.
Explicit madeira-steam-login-desktop-experiment tests same existing login data
without invoking changeuser. Main unchanged. Full Xcode50/x64 Werror/deep signing,
final debug dylib/PE markers and existing gates pass; observer regression covers
stale success, split writes, log replacement and spoofed/non-success text.
Actual new authentication and Big Picture transition remain unverified; do not
claim compilation proves the hypothesis or cures the browser hang.

Build50 actual isolated install/explicit desktop launch succeeded PID21478.
Copied actual device batch confirms neither -bigpicture nor changeuser on this
controlled launch; helper ready/ready. Final helper/debug Mach-O hashes recorded.
User fresh-login/Guard completion test is pending. Preserve session and verify
actual successful-login marker plus real Big Picture view before any GO claim.

### Build51 post-login transition and current-process WoW PEB isolation

User reports Build50 login succeeds then Steam icon spins entering Big Picture.
Actual Steam10:41:53 Success/OK and categorical native success marker confirm
fresh authentication. Helper ack big-picture-requested only proves dispatch.
Captured native snapshot has no Mach unhandled/CEF-fatal marker; frontend has
missing-friend-cache warnings and an uncaught promise TypeError reading persona.
No identifiers published and no sole-cause attribution to that JS error.

Single discriminator: same Build50/client/prefix, fresh direct Big Picture start
without changing account. Identity-verified PID21478 stopped after collecting
logs; direct PID21564 launched but failed before UI in wow64.dll RVA1b724, write
0x480. Exact shipped ARM64 PE disassembly identifies class26
NtQueryInformationProcess(ProcessWow64Information), load returned PEB32, then
store WOW64INFO at PEB32+0x480. This is a NULL returned PEB32, not proof of absent
CPU-reserved area. Correct the earlier Build46/47 description accordingly.

Source matches this failure: current-process query reads shared wow_peb, while
loader clears/reassigns it during sibling native startup. Minimal Build51 lab+
64bit-only correction resolves calling TEB->Peb through owner-bound WoW registry
and returns that owner's PEB+Wine page_size, or0 for native owners. Ordinary,
old-style and remote-handle query branches unchanged. No FEX/Valve/submodule or
assertion edits. ASan/UBSan production tests include two concurrent WoW owners,
native owner, foreign/null shared legacy values, missing TEB and gates. 37/37
native units/full Xcode51/final debug Mach-O marker/deep signing pass; launch,
login observer/keyboard/affinity/keyed-event regressions pass. Host sanitizer
checks rerun using system clang after LLVM-Mingw PATH lacked Darwin ASan runtime.

Ordinary launcher now uses direct Big Picture for the preserved Steam login;
desktop-login-first remains explicit account setup and diagnostic mode. Avoid
forcing every normal reopen through the already problematic live desktop-to-BPM
transition. This is not evidence that live transition is repaired. Private
artifacts ideck-transition50 and ideck-build51, hashes and exact limits in
IDECK_LOGIN_TRANSITION_EVIDENCE.json. Actual device query/startup/UI result pending.

Build51 actual install/direct launch PID21625 succeeded. Fresh Steam10:50:52
Success/OK verifies saved login survived restart without agent credentials.
Steam UI new BrowserReady10:50:55 follows gamepadui initialization; not proof
of rendered or interactive home. Native live log copy failed CoreDevice7000/
POSIX60 and produced an empty file; do not infer absence of faults or process
exit from it. Login/UI evidence hashes recorded. Keep session alive for physical
UI confirmation; next discriminate whether home/library renders and navigation
works before changing runtime again. No account re-login needed based on logs.
