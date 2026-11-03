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

## iDeck Ratatan follow-up, 2026-10-26, Builds 61/62

Standalone iDeck source baseline 4ad061b; primary Madeira and historical research
checkout untouched. User confirms downloading/installing Ratatan now works,
but startup stalls. Artifact-backed baseline shows FEX host-band exhaustion
and failed thread initialization; worker count reduction alone in Build 61
still fails. Build 62 changes the existing checked spill-window order only in
isolated Steam sessions. All 37 native units, full Xcode build, final linked
marker, signature and in-place install verified. Device session saved login
succeeds but Steam waits at ShowInterstitials before game launch. Mac locked;
user UI response pending. Preserve that session, do not call this a completed
runtime fix. Exact evidence, hashes, regressions, opt-out, and next acceptance
criteria: `IDECK_RATATAN_STARTUP.md`. No FEX/Valve binary changes or new release.

### Ratatan white window, Build 63

Build 62 fresh device trace places guest spill outside FEX's band and proceeds
past Unity graphics initialization, but fails the later steamclient64.dll
executable copy with STATUS_NO_MEMORY; game logs SteamAPI_Init failure and
shutdown. User screenshot shows decorated white window. Build 63 defaults the
existing image-headroom budget to 192 MiB for isolated Steam sessions (ordinary
48 MiB and explicit overrides preserved) and applies Ratatan-only borderless
current-desktop Unity args unless the user supplies fullscreen settings.
37 native units/full compile, linked marker, strict signing/install pass; actual
native trace confirms 192 MiB policy. Steam waits at ShowInterstitials, so game
execution/visual validation is pending user response, not a claimed success.
Detailed evidence, hypotheses, opt-out and limits: IDECK_RATATAN_STARTUP.md.

### Build 64: Ratatan main menu, remaining display/input defects

User screenshot now confirms actual Ratatan main menu. Native window first
covers 1424x656 then changes to {72,0,1352,656}; saved Unity mode is windowed(3).
Virtual XInput accepts touches, but game selects Windows.Gaming.Input and Steam
launch lacked the library profile's WGI host-pad enable. Build 64 supplies WGI
and foreground defaults only on genuine Steam launch (explicit cfg overrides
win), and backs up five display DWORDs before setting Ratatan fullscreen/current
resolution via registry API. Source/binary game files and saves untouched.
Host backup/failure/override tests, x64 Werror helper, full Xcode, final marker,
strict signature and install pass. Actual helper confirms preferences applied
and backup complete. Final full-screen appearance/WGI enumeration/in-game touch
controls remain pending user test; preserve running session. Exact hashes,
rollback/opt-out and limits in IDECK_RATATAN_STARTUP.md.

### Re-signing / JIT shortcut repair, local Build 65 (uncommitted)

Tester reports Shortcuts destination-output error and approximately one minute
waiting. Verified old scheme inference disagrees with actual registered scheme
after bundle rename, and suffix gate disables a marked iDeck product. Read
registered schemes and retain product marker across re-signing; preserve ordinary
Madeira isolation. Correct signed shortcut outputs to explicit text while native
VPN stays in Store Content; stop offering outdated cloud import. Host regression
and signed archive checks pass. Full custom-ID unsigned Build 65 and actual final
metadata/helper/payload checks pass. No affected-tester/device validation claimed;
Build 64 phone session not replaced. Workaround, exact reproduction, hashes and
limits: IDECK_JIT_RESIGN.md. User prohibits commit/push outside weekdays22:00–08:00
or weekends; current daytime changes remain uncommitted/unpushed. No automation
was created. AGENTS.md and an explicit-request memory note preserve the rule.

### Local Build 66: initial CM TLS failure handling

Reporter iOS27.2/0.1.3, LeiShen+Karing supplies old Connection failed/TLS text and
Dock offline result52. Exact native WebSocket ping wrapper discards error codes;
initial connect failure leaked transport and did not penalize CM selection.
Add bounded distinct-CM failover for recoverable transport failures, cleanup,
safe domain/code errors and stale-task callback guard. Trust errors/cancellation
fail closed, normal TLS unchanged, no entitlement bypass. Production-loop/
actual-selection scripted tests and existing Cloud save regression tests pass;
full custom-ID unsigned Build66 and linked marker checks pass. No accelerator
or affected-device runtime validation; phone64 untouched. Full evidence and
remaining discriminator in IDECK_ACCELERATOR_TLS.md. Work remains uncommitted/
unpushed per user time restriction, no new automation.

## Steam logout/recovery follow-up (local Build 67)

- User: Steam crashed during account switching; next launch failed Steam/browser
  prerequisite. Device enumeration worked; executable copy failed CoreDevice4000,
  connection reset54. No crash/root-file evidence; logout cause remains unknown.
- Confirmed code defect: failed prerequisite offered preparation, but existing
  client import returned early on an existing incomplete/incompatible directory.
- Added per-file categorical diagnostics and an explicit launcher recovery action,
  compatible bundled/user-imported source selection, active-session refusal,
  public-file backups, post-write validation, failure rollback, and mandatory
  fresh app process after successful repair. No account/game/save deletion.
- Production host steam-ui and iDeck policy checks pass. See
  IDECK_STEAM_RECOVERY.md. No on-device success claimed. Current source baseline
  remains 0ec1eb7 with earlier JIT/CM fixes preserved locally; no commit/push.
- Full unsigned iOS Build67 succeeded; actual Info.plist version67 and linked
  Madeira.debug.dylib repair-action/error markers verified. git diff --check
  passes. Not signed/installed; affected device repair remains unverified.
- Local time Monday2026-10-26 17:06EDT is outside the allowed Git window;
  changes remain uncommitted/unpushed. Next: retrieve affected client headers
  and logout crash log on restored device connection, then install/test recovery
  with real compatible client resources and re-test Valve account switching.
- Follow-up device evidence: copied current Steam32BundleLab/steam.exe and
  Documents/Steam32OfficialRepair/steam.exe successfully. Current installed
  client PE machine is AMD64 0x8664; retained repair source is i386 0x014c.
  Confirms incompatible client architecture explains readiness failure, but
  does not establish logout crash causal chain. Build67 rebuilt for existing
  com.kuschqin.madeira.steamui, signed/deep-verified, and installed successfully
  without uninstall. Private artifacts: .madeira-install/ideck-repair67.


## v0.1.3-alpha.3 packaging

Build67 compiled from code revision c90a16c; a documentation-only follow-up records
packaging evidence. User confirmed Steam recovery restored use after installation.
1245-file public IPA audit passed with no excluded-payload findings; packaged
main/StikJIT/converter section hashes match build products (49/36/14 sections).
103-input portable relink and ten host regression scripts/six release-tool tests
passed. Source, dependency pins, LGPL patches and relink materials accompany IPA.
No affected-accelerator TLS fix, exhaustive game regression or resolved logout
crash claimed. User Demo.gif excluded from this release commit/source archive.

## Issue1 local Build68 — iPad WoW capacity failure

- Reporter trace: guest-window-reserve c0000017, only639MiB free VA, cannot
  reserve4GiB plus8GiB margin. Not a local device reproduction; mapping owners
  and the underlying cause of the limited free VA remain unmeasured here.
- Confirmed defect: no capacity prerequisite or visible child-boot error; the
  Wine desktop and main running flag can survive a failed Steam child.
- Patch: read-only actual-map/free-hole snapshot, seventh capacity prerequisite,
  direct/automatic launch check, bounded current-log child-failure observation
  independent of suppressed UI tail, native alert, one shared client-directory
  selector and no implicit import replacing a valid fallback selection.
- Host production tests passed: startup/capacity boundary/639MiB/margins/overflow,
  partial writes/busy logs/rotation/negative events; Steam policy/ASan diagnostic
  checks and prerequisite/lifecycle regressions. Full unsigned iOS Build68
  succeeded; actual Info68 and linked failure/capacity markers verified.
- Private build log/evidence: .madeira-install/ideck-issue1-build68.log and
  ideck-issue1-build68-evidence.json. No installation, affected-iPad or new
  entitlement/current64-bit-Steam runtime validation. No allocator guard removed,
  FEX/Valve edits, automatic logout, credential or issue-comment submission.
- docs/IDECK_IPAD_ADDRESS_SPACE.md records scope, Valve's retirement notice,
  incomplete legacy-client acquisition and the next mapping-census experiment.
  This fixes silent failure/reporting and prevents knowingly impossible launches;
  it is not a capacity expansion or claim the affected iPad can now run Steam.
- Weekday daytime: local changes remain uncommitted/unpushed per user rule.


## Current64-bit migration — Builds69/70

User replaced target with current64-bit Steam; implemented explicit isolated
wine-steam64 arguments, preserved ordinary wine baseline/auth/games. Latest
Valve HTTPS win64 manifest1792618285 verified; all four core client/CEF images
AMD64. Signed/installed69, actual JIT/main Steam/updater execution; official
update completed, cef.win64 launched and hit libcef RVA6923404 after real pool
capacity failures. No login/BrowserReady/Big Picture success. See IDECK_STEAM64.

Attempted clean relaunch DID NOT create a new PID; same25625/log retained.
SIGTERM intercepted, SIGKILL timed out; do not claim fresh reproduction. Need
verified process exit before next trial. Normal unsigned70 compilation passes.
Host launch/isolation/checklist policies pass. Existing CUA/CLI signing method
reviewed; account GUI already logged in, manual certificate/profile resign works.
Independent GUI device probe explicitly reports Personal Team does not support
Extended Virtual Addressing. No repeated login/purchase requests. User requested
remembering verified signing method; small authorized memory note added.
Raw artifacts private steam64-current; no Git commit/push during daytime.


User physically closed app; old process absence confirmed. Genuine clean PID25956
post-update launch repeats CEF allocation failure and fatal libcef+6923404.
It excludes updater retention as sufficient explanation. Two16GiB PA ranges,
16GiB FEX arena and8GiB cage hold leave no third16GiB slot in the current high
64GiB band. Private clean-evidence.json pins bases/callers/hashes. No root fix,
login or Big Picture success claimed. Need disjoint alternative arena/pool
layout or supported reduction; no assertion suppression or overlapping grants.


Build71 disjoint compact layout compiled37native units/fulliOS, exact final
marker/signing verified. Real phone FEX4GiB reserve succeeded and consumer wired;
third16GiBPA pool succeeds for first time. Fourth16GiBguard pool fails,32GiB
fallback/fatal remains. Four pools64GiB plus FEX4/cage8/furniture cannot fit the
current64GiBhighband. Not a login/BPM fix. Private layout71-evidence.json pins
hashes; no FEX edits, fakegrants or check suppression. Windows Chromium126 does
not include the iOS dynamic-pool-size path. Further progress needs additional
real VA or compatible source-built smaller-pool browser; do not blindly retry
or promise allocator movement alone can fit it. No day-timecommit/push.


Build72 installed and early-constructor native probe completed. Same62requests,
8successes54failures; no extra16GiB aligned region found beforemain. Full source
CEF6478 reference inspected against actual AMD64webhelper77imports:8names absent
from upstream headers, so stock rebuilt CEF not a proven compatible replacement.
Current64Steam remains uncompleted; additional-real-VA or matching Valve ABI
source/build needed. Current personal-team extendedVA request unsupported;
internaldisk5.6GiB vs officialCEF150–200GB. No fakeAPI/hash, check suppression,
proprietary patch or purchased service. Failed compact layout made explicitly
opt-in in source; source follow-up needs compilation. All raw artifacts private.


## 2026-10-27 continuation — actual AMD64 main / official i386 CEF workaround

Source base e3d845e plus uncommitted isolated experiments. Primary Madeira and
ordinary iDeck wine prefix remain preserved. Builds73/74 restore ordinary VA
geometry for hybrid i386 execution; compact64 layout is explicitly opt-in.
The direct-child redirect is triple-gated session1, DIRECT_CEF32=1 and exact
wine-steam64 prefix; only the exact official64webhelper path is redirected to
the official i386 sibling, preserving arguments and the original caller's
actual childPID. All37native units and full Xcode74 compile; final linked
diagnostic marker and strict development signing verified. No FEX/Valve edits.

Observed failure: current October AMD64 main + frozen i386 helper initializes
CEF but no real browser window. Discriminator: audit their embedded public
HTML IPC schema, then compare a historical official AMD64 snapshot.169 vs162
messages, changed CMsgBrowserCreate field numbering; not a packet-level proof
of sole cause. Jan22 AMD64 client1769025840 and Jan29 i386 CEF1769731672 have169
identical schemas, both CEF126. Steam's own HTTPS updater installed the matched
older snapshot; device steam.exe read-back SHA matches officialAMD64 package.
This is a pinned old-client compatibility experiment, not latest64CEF success.

Actual Build74 visible genuine login; user credentials/Guard only. Steam-owned
log17:10:04 Success/OK confirms authentication. User cancelled Steam Service
Error, then spinner. Native loader identifies steamclient64 and i386 libcef.
Post-auth exact fault is Wine i386 atlthunk.dll RVA1310, atomic increment to
pool+1004. Guest4KiB code and mutable metadata share host16KiB protection page.
Not a KERN_MEMORY_ERROR; journal reports PROTECTION_FAILURE currentprot5.
Code-buffer guard warnings predate successful login, so no exhaustion claim.

Build75 synthetic probe tests64 direct ATL callbacks/free plus64 USER-window
destroy callbacks/free. First attempt failed BEFORE Wine at JIT placement; a
fresh session runs originalDLL and PASSES128, while reproducing two identical
metadata protection/undecoded-atomic faults. Thus those native faults may be
recovered and MUST NOT be claimed the sole spinner cause.

Minimal LGPL Wine overlay pads thunk code to16KiB, keeps mutable fields in the
next native page, preserves original copyright/export ABI and default4KiB
source behavior. Build76 is a disposable repackage of full Xcode75 with only
version and i386 DLL overlay changed; strictsign/install passed. SAME probe
PASSES128; data offset4104→16392, shared-native-page1→0, both protection faults
and undecoded atomic stores disappear. Both runs retain unrelated type6 native
teardown trap. No assertion/protection suppression, retry workaround or FEX
patch. Overlay does not auto-apply in Xcode; reproducible private overlay
instructions in tests/steam-ui/README.

Fresh Build76 direct-bigpicture restart retains saved auth: actual17:40:14
Success/OK, BrowserReady, SP BPM window. DeviceHub visually shows Welcome to
Big Picture over actual game tiles at17:41. This establishes visible genuine
authenticated BPM with AMD64main/i386CEF. NOT fullAMD64CEF, interactive
navigation, game launch or affected-iPad repair. Missing-persona JS errors
remain but did not prevent this visiblehome. First UI took about90seconds.
Existing fixed Steam Menu command acknowledged, but remote DeviceHub mouse
click/keyboard delivery is not established; requested physical A/navigation
verification without restarting the active session.

Evidence: docs/IDECK_STEAM64_EVIDENCE.json contains redacted SHA256/versions and
A/B boundaries; private .madeira-install/steam64-current contains manifests,
matched64-device-steam.exe, native74-after-auth-bpm.txt, auth74-steamui_login.txt,
atl75/76-results.txt, native75/76-atl.txt, native76-bpm.txt, logs76-stable, and
full build/sign/install/launch journals. No raw account logs or Valve payloads
are in Git. Regression: production Swift launch/probe-isolation tests (including
ATL missing/wrong-architecture/wrongprefix/flag/ordinaryapp gates), native
ASan/UBSan categorical events, iDeck readiness tests passed; final PE counter
offset4004 and original/patched SHA checked.

Next: preserve this live saved-login session, pass welcome with physical input,
verify library navigation, then installed-game execution/return. Keep the
latest-AMD64CEF capacity limitation separate. Full64target remains incomplete
until these gates, and hybrid alone still requires a viable32bit VA window.
No commit/push during Tuesday daytime per the user's global time rule.


Build77 continuation: user reports virtualA ineffective on76. New bounded
hit/touch counters and triple-gated fixedEnter/Right/Escape test helper compile
with full Xcode77 and x64Werror. Actual gate ASan/UBSan and linked MachO/PE
markers verified; signing/install succeeded. Fixed Enter actually dismisses
welcome; next screenshot shows unobscured home. Fixed Right visibly changes
selected game tile. Therefore interactive keyboard navigation in real BPM
with AMD64main/i386CEF is confirmed. Remote mouse/control-delivery and native
virtual-pad response remain distinct. Actual native touch records active1,
accepting1, four40–80ms press/release pairs.500ms helper counter0 cannot exclude
these short edges; asked one3second held-A discriminator. Preserve live session;
no credential/game/cache mutation. New source and private A/B artifacts remain
uncommitted/unpushed during Tuesday daytime.


Held-A completed: native active/accepting1,4second hold; helper XInput sampled
change counter0→2, no game activation. SDL logs independently identify Xbox360
controller and genericHID. This locates remaining input response after Windows
API delivery, not missing iOS detection. Build78 adds post-merge bits and finite
left/up/down directions (same triple gate), fullcompile/sign/install and markers
pass. Only runtime policy change under test is documented SDL background events1;
saved-auth actualhome displayed again. No controller-success claim yet.


Build78 reported freeze captured a SECOND actual failure: native fault
address180c, x18zero, instructionb9980e48, registered ownTEB7931520000,
PEB7900310000, exact wow64.dll callerRVA1c854. Disk PE disassembly shows
ldrsw x8,[x18,#180c]; then add x8,x18,x8; then store Win32 data. Wine defines
signed WowTebOffset at180c. Native x18-zero decoder lacked unsigned-immediate
LDRSW, while other load variants existed. Minimal experiment fills only this
own-registered-TEB field under exact Steam64/session/encoding/offset gates; it
uses existing state restore (including realx18) and PC+4, preserves sign
extension and every other register. No global/sibling TEB borrowed, no FEX or
Valve patch. Recorded native journal proves the defect, not sole cause of all
UI stalls. Host observed-instruction/refusal/sign tests ASan/UBSan pass.

Full37native units and fullXcode80 compile; final debugdylib marker verified,
strictsign/install passed. First native build adapter lacked generated headers
and failed2units; corrected adapter READS primary Wine generated headers only,
then37/0 passes. No primary source/output modified. Old79 helper-only signed
trial was prepared but NOT installed. Build80 launches saved prefix with SDL
background0 and optional menu-key fallback0, isolating native fix. Need fresh
UI/navigation and actual marker/fault evidence before device-success claim.


Build80 final afternoon evidence: actual246second snapshot exercises new native
TEB signed-load marker with no original UNHANDLED in that bounded run. Hot
Roads official appmanifest StateFlags4/build7695775/221125214bytes confirms
installation. Play inputs did NOT produce a gameprocess entry; no game-running
claim.22:47 EDT continuation confirms old app absent, starts supported Steam
-applaunch1819280 on same saved prefix. JIT confirmed, first36second snapshot
not yet game success. Experimental changes isolated to new local branch
experiment/steam64-hybrid; main e3d845e remains baseline, no compiled/Valve/auth
payloads staged. Recheck time before separate commit/push operations.


Fresh80 supported-applaunch discriminates UI dispatch: actual22:51:11 Steam
log tracks app1819280 hr.exe, DeviceHub visually shows Unity screen-resolution
configuration window over BPM. Steam-controlled real game process confirmed;
main-menu/gameplay/return not validated. Preparing81 fixed Enter for only
foreground/unambiguous visible steamapps/common game window under the existing
lab triple gate. Never focus/account-type text. Also reviewed redirect early
denials now release the three new path buffers.37native units/host input gates
pass; full81 build follows. No primary source/runtime resources modified.


Build81 installed/signed/fullcompiled; actual hr.exe AMD64 Machine8664 and
private SHA pinned in evidence. Genuine Steam again reaches Unity graphics/
input configuration.23:00 game-confirm command fails before delivery with
CoreDevice4000 disconnect; no game-key ACK, no gameplay/return/crash proof.
One reconnect/unlock handoff pending. Preserve prefix/account/game; don't
reinstall, relogin or repeatedly launch while disconnected. Fresh device/app/
visible-dialog check precedes any next command. Reviewed source-only research
0c4b01e pushed to experiment/steam64-hybrid inside verified allowed time window;
no main merge/release/Valve payload. User Demo.gif left untouched/untracked.


User now confirms Hot Roads ran successfully. Its actual PE was already
verified8664, and Steam main/steamclient64 genuine AMD64. Core Steam64-main
→ game64 execution PoC now succeeds by USER REPORT, supplementing prior
artifact-backed launch/configuration evidence. No new gameplay artifact,
duration/controller/game-return proof. Still historical pinned AMD64main plus
official i386CEF; not full64CEF/current-client or iPad-capacity resolution.


## Full AMD64 CEF continuation after user-confirmed game run

User requests continued full64CEF work. At research ca698ef, fresh source and
Build71 trace audit isolates two16GiB pools each in chrome_elf and libcef of
the same guest PEB. Official upstream CEF126 stock chrome_elf also requests
two16GiB pools, so stock swapping is not the fix. Prepared separate pinned
source-only chrome_elf1GiB-pool experiment, exact-header/two-constant tests
pass, load/VA/15-export probe compiles AMD64 Werror. Windows build and device
tests pending. No runtime/binary/FEX/auth change; live Build81 download left
untouched. Source/evidence: experiments/cef64, IDECK_CEF64_SOURCE_EVIDENCE.json.
Next discriminate actual source-built DLL reserve sizes on Windows, then
isolated iOS load and genuine64CEF startup; no login/UI success assumed.

Build82 adds an explicit isolated source-component probe, full Xcode/final
linked marker/deep signing pass; NOT installed while source DLL build pending.
Production Swift missing-input/symlink/prefix/flag and no-Steam command checks
pass, existing hybrid/input/TEB/readiness checks pass. Windows attempts1/2
stopped at missing build-time Rust inputs, then selected supported C++-only
GN configuration; attempt3 currently in progress. These are build-system
results, not DLL/CEF/device success. Source artifact packaging retains notices
and refuses to publish a component before its Windows load/VA test passes.


Actual Build83 phone discriminator PASSES: all six disjoint full-sized native
NONE/NONE fixed-no-overwrite regions, total0xe40020000 (57GiB+128KiB), held
simultaneously; every requested base exact, every cleanup0. Includes full8GiB
V8 cage,15GiB arena capacity, both16GiB CEF pools and both1GiB source-ELF pools
with real BRP guards. This proves before-main simultaneous CAPACITY only;
no guest ownership, commits, FEX consumption or CEF/login/rendering claim.
User data retained; old idle PID2744 ignored TERM, actual SIGKILL exit verified
before in-place83 install and explicit native-only diagnostic launch. No JIT
or Steam needed for this test. Numeric artifact hash/slots in source evidence.

Build84 ACTUAL backing discriminator passes: same six full-sized reservations
held concurrently with maxRW,12own data pages at region edges become RW and
pass zero/write/read checks; BRP guards untouched; all cleanup0. Only these
12pages committed, not57GiB of physical RAM. Before-main timing and no JIT/
Steam remain explicit. This validates capacity plus bounded backing, not
executable permissions, guest ownership transfer, FEX or interactive64CEF.

Windows source attempt5 reached bounded100-input discovery, before compiling:
unreferenced Sandbox tests and NaCl process_type pulled renderer/Mojo graph.
New metadata retains exact upstream required target bodies only, with checked
source hashes, original compiler/security flags, and unsafe-developer=false.
Native83/84 capacity/backing are independent actual device passes; they do not
prove this source component builds or links into an actual Steam helper.

Windows attempts8/9 now compile actual C++ (193 then231 of1661edges),
not merely GN. Missing pinned googletest include and upstream rc_win binary
are distinct build-input failures; resolver and hash-verified official RC
hook address them. No DLL or CEF success. Own AMD64 reserve/commit/query/free
contract PE compiles Werror; it has no Valve or network dependencies. Build85
installed in-place, launch refused due native phone lock; no runtime adoption
result. Existing auth/games preserved. Await unlock while continuing Windows
component work.

Build85 native/Wine ownership transfer is now built, linked, deep-signed and
installed. Exact dual-gated native holds feed checked one-time Wine views and
the existing FEX arena publication path.37native units/fullXcode pass; host
ASan/UBSan actual boot rollback/16thread claim race and actual Wine adoption
bounds/alignment/live-view/duplicate/create-failure rollback pass. Production
Swift own-contract no-Valve mode passes prefix/flag checks. Actual launch
REFUSED CoreDevice10002/FBS Locked: no Windows contract or FEX/CEF pass.
User unlock request pending; no repeated launches/installs. Signed final
debug dylib hash and limitations in IDECK_CEF64_SOURCE_EVIDENCE.json. Claims
are single-use/native lifetime; not a finished restart-safe broker or general
fixed-hint Windows semantics proof. Next run own Windows contract before
source-DLL load, then genuine matched64CEF. Preserve hybrid/auth/games.

Windows source-control milestone PASSES in run40632409115 (245d910): actual
AMD64 DLL build and actual Windows loader/VirtualQuery tests find15exports
and two1GiB private pools with no new16GiB reservation. DLL SHA256
7dee97bd5ea0a363a68304b71ea4f8d9cbdac0647f716db59639f79f51989cab.
Public source/notices retained, downloaded artifact hash reverified. This is
NOT genuine Steam64CEF or device success and DLL is not staged into Steam.

Further source audit isolates a compatibility gate: ordinary Chromium uses
ChromeCrashReporterClient, while exact matching published CEF uses its own
configuration/handler/optional-argument contract. No observed device fault
of this DLL yet, no causal claim. New CEF-aware variant applies complete
hash-pinned crashpad_1995.patch at CEF a5d51ba9... (requires same Chromium
tag); ten-file pristine apply and exact retained production GN targets pass
host tests. Real Git ancestry generates CEF version. Next Windows browser+
renderer DLL load/payload/VA gate, then isolated iPhone ownership/component
load. Build85 unlock gate unchanged; no repeated launch or credential action.

Run40633251602 control repeats actual Windows success and adds payload-size80,
version-match1, mode-size192. Re-downloaded DLL has identical SHA256 to run10.
CEF-aware run40634322760 passes clone/full published patch/version generation;
test fixture then fails because outside checkout it inherits Windows global
auto-CRLF. Actual checkout was explicitly false and correctly patched. Host
A/B reproduces358CRLF/wronghash vs0CRLF/exact9ea7d127...; force false per
fixture command, keep strict source hashes. Windows CEF-aware compilation and
device ownership/CEF/UI still pending; no stock DLL staged into Steam.

CEF-aware run40634577387 passes source/patch checks but GN reaches bounded100
inputs: shared chrome/common header metadata also resolves unused Chrome/UI/
PDF libraries. Keep exact original Chrome/media/UI buildflag target bodies
and their production options; hashes/host comparisons pass, no flags disabled.

Separate static layout check: old512MiB CodeRange service targets exactly
[0x7180000000,0x71c0000000), wholly inside new ELF BRP. Build86 skips only
that old service in owned mode, leaving normal checked Wine placement/V8
reach checks.37native/fullXcode/deep signing pass. Final signed Mach-O
NtAllocateVirtualMemory has8 owned-layout queries vs7 in85; branch included,
NOT proof it works on device.86 prepared, NOT installed over pending85.
One read-only lock check after source builds still passcodeRequired=true;
no repeated launch/install, no credential action. Actual V8 reach and full
CEF/UI remain gates. Main baselines unchanged; user's Demo.gif untouched.

CEF-aware run40636094452 now passes GN and performs1680-edge C++ compilation,
advancing to final81edges. Exact failure is missing generated V8 buildflags
from content_switches.h, not a CEF runtime fault. Retain hash-checked original
generator/options and add explicit CEF static-library dependency; do not stub
the header. Host source/target checks pass. Full research recipe added in
CEF64_BUILDING.md with explicit control-vs-CEF and local-vs-device boundaries.
Static official ELF install-mode constant atRVA106260 has size192/index0/
Chromium, matching observed control; payload-size80/version also matched.
These static/public prefix fields are not a complete Valve ABI/device pass.

2026-10-28 continuation, tested base be8151a plus local fixed renderer selector:
CEF-aware Windows run40638006082 PASSES both browser and renderer component
load/payload/export/allocation tests. AMD64 DLL SHA256
673584661cd0044b186e40286b3d57a099b45002d3fc50f334ae1d3d14bc7621.
Full published CEF crash integration retained; no crash assertions suppressed.

After physical unlock, actual Kusch Build85 OWNERSHIP test PASSES all five
exact reserve/query regions, ten committed edge-page zero/write/read checks,
duplicate refusal error8 and all five releases; result0/exit0. Native snapshot
confirms real held-region adoption, not overlapping soft grants. FEX initializes
with EmulatorData0=0x7402001140 inside the exact published15GiB arena. This is
actual bounded consumer evidence, not full-range physical/executable capacity.
Private owned85-results.txt SHA32de351c... and native85-owned.txt SHA29cc66ba...
have full hashes/paths in IDECK_CEF64_SOURCE_EVIDENCE.json.

The same source DLL PASSES actual iPhone component initialization in browser
mode85 and renderer mode87: payload80/version-match1/mode192, all15exports,
two1GiB pools, exit0. Both native snapshots record real slot0/1 adoption.
Renderer selection is a fixed explicit diagnostic environment/argument;
mixed ownership+renderer is refused. Host production Swift checks, full87
Xcode and deep-strict signing pass. Build87 includes native86's isolated old
V8-service skip; no actual V8 code reach or full Steam UI claim. Generic PE
footer cannot establish platform provenance; external CoreDevice/native
artifacts establish these particular phone component runs, not full CEF.

Next single hypothesis: the validated source component and real disjoint
backing permit genuine matched AMD64 Steam/helper/libcef initialization.
All81 original CEF-folder files copied from device and matched January22
official snapshot before replacing ONLY source chrome_elf in isolated
wine-steam64. Original main/helper/libcef unchanged; full original CEF folder
privately preserved for rollback, no auth/cache transfer. Recognized client
update-on-launch setting added to keep the matched experiment stable; no
checksum/auth/Guard/license check disabled, actual setting effect unverified.

Full desktop Steam87 trial uses explicit steam64 argument, source-layout1,
direct-CEF32=0 and strict-reservations1. Latest attempt was REFUSED by native
device lock; no app process launched, and Mac Device Hub is locked too.
Requested opening iDeck and keeping foreground; no repeated locked launch or
install. On unlock, run the already-installed app once, verify actual64helper/
libcef/ownership logs and visible UI before BPM/game tests. Preserve login,
games and saves. Main baselines untouched. Local changes remain uncommitted:
fresh Wednesday10:59EDT check is outside user's commit/push window. No new
automation or timed wait is created. Full64CEF remains NO-GO for release
until actual interactive and stability gates pass; research continues.

Later12:05EDT retry: idle launcher was already running, so initial CoreDevice
activation reused its old argument/environment state. Fresh idle-only restart
actually enables the explicit experiment and paired JIT. Native logs confirm
AMD64 official helper/libcef startup, but NOT source component execution:
Steam's own bootstrap log12:06:02 reports a previously pending update and
installs it, changing updater Jan21 to Oct21 by12:06:17. Post-run support DLL
SHA6358830f96f36efa7516b3277cf69c1f132f97d4d93c365ccf061a7cf11e1e39
differs from the staged/read-back source DLL. Actual module size is original
0x166000 rather than source0x1a9000; no1GiB slot0/1 adoption, first16GiB
regular/BRP adopted then further16GiB refused. Generic libcef RVA6923404 fatal
and browser respawn follow. This invalidates the source-component experiment;
it is not evidence that the source DLL failed. Snapshot/bootstrap hashes are
recorded in the source evidence. Failed session identity-checked and stopped.

Build88 isolates the discriminator: production launcher uses recognized
-nobootstrapperupdate/-skipinitialbootstrap only for active native owned mode,
AMD64 and wine-steam64. Ordinary AMD64 launch unchanged. This avoids applying
a queued updater before testing matched resources; no checksum assertion,
authentication, Steam Guard or license check suppressed. The attempted
update-on-launch configuration alone did NOT stop the already-pending update.
Production Swift ordinary-prefix/x86 refusal and flag tests pass, fullXcode88
passes, final signed dylib contains new policy symbols, deep-strict signing
and isolated in-place installation pass. User data retained.

To undo the observed public-file update, complete Jan22 official manifest
packages fetched from Valve HTTPS and individually size/SHA256 checked:
6229public files/782645366bytes. Source support DLL is the sole component
overlay. Restore targets only explicit public top-level entries; config,
userdata, steamapps, logs, caches, package and save paths are excluded. No
credential/cache transfer. Runtime is stopped during restoration. Next repeat
the actual fresh full64 startup, first require source1GiB adoption and unchanged
helper/libcef hashes before interpreting further failures. Full64UI remains
unverified; do not reuse prior hybrid gameplay as proof. No commit/push during
weekday daytime.

Build88 public-only restore completed. Actual device read-back of main,
steamclient64, official helper/libcef and source ELF all SHA256-match the
prepared snapshot/overlay. No account/game/save/cache directory was copied
or removed.12:14EDT fresh activation timed out while Device Hub visibly
displayed Face ID/passcode lock; subsequent fresh CoreDevice process list
reports zero Madeira processes, so no88 runtime result. Physical unlock
requested once for this new gate; no lock bypass or repeated launch. Next
test can use installed88 immediately, with no further restore/build needed.

2026-10-28 13:01EDT actual88 full64 startup: paired JIT passes; the source ELF
really loads (image1a9000), and the same helper adopts source1GiB regular/BRP,
official16GiB regular/BRP, then the8GiB cage. These are real backed views,
not UI success. Subsequent crashpad admission/child1GiB refusal and a V8
ExternalEntityTable subspace OOM block the UI. An independent safety failure
is visible: a generic4GiB retry succeeds at7600000000 INSIDE the published
FEX7400000000..77c0000000 reservation. No soft grant is needed for this bug:
the fixed-map path ignored FEX-only ownership. Failed88 session stopped.

Build89 adds a narrow owned-mode pre-map guard for generic fixed>=1GiB
requests overlapping FEX. Explicit arena-constrained requests remain eligible;
small legacy/ordinary paths unchanged. Actual own Windows probe PASSES the
same5region/10edge/release tests plus generic4GiB refusal error487; native DENY
marker confirms this precise path. Host bounds/overflow/ownership fixtures,
37native units/fullXcode/final linked marker/deep signing pass. First89 install
timeout left88; one retry after fresh responsive inventory actually installed89.

Separate explicit MADEIRA_CEF64_NO_BREAKPAD=1 passes Steam's recognized
-cef-disable-breakpad in owned mode only. Actual89 bounded full trace has no
crashpad admission (present in88), retains real primary source/official pools,
and denies attempted4GiB FEX intrusions. V8's4GiB/8GiB retries still fail.
Existing inherited single-process/jitless/feature-splice compatibility policy
was already active; no new assertion or BRP source check removed. This does
not establish all inherited flags as suitable for release. Failed89 was
identity-checked, paused during preparation to stop respawns, then killed and
absence-verified BEFORE90 installation; no suspended test left behind.

New single hypothesis in90: allocate V8's observed4GiB and512MiB requests
from their OWN real reservations by reducing only opt-in FEX capacity15->8GiB.
The89 named-region high-water ends7578010000, below7600000000; this is NOT
live/complete accounting or future game capacity proof. Exact pinned public
V8 source was inspected, including cppgc caged-heap and external-entity table
reservation paths. No FEX or Valve executable changed. All eight intervals
are disjoint,54.5GiB+128KiB total. Default old six-region mode remains.
Auxiliary leases accept no hint, unmappable high ASLR hints or exact owned
base; an in-range foreign fixed address is not redirected into another hold.

Host original6/split8 all-slot/edge/rollback, native16-thread claims, actual
Wine auxiliary adoption/bounds/duplicate failure, Swift fixed split command,
Werror AMD64 PE,37native/fullXcode90/final markers/deep signing pass.
Actual Kusch90 native split-backing test PASSES: all8regions held together,
16data-edge zero/write/read checks, untouched BRP guards,8successful cleanups,
result0. It commits only those own pages, not54.5GiB physical RAM. Native
test was stopped by verified identity; next actual own7region Windows
contract launched in a fresh source-layout1/split-layout1 JIT session. Full90
CEF/UI/game/stability and8GiB long-run FEX capacity remain unverified.

90 actual Windows split contract PASSES: all7exact reserve/query regions,
14edge commit/zero/write/read checks,7releases; extra4GiB7600000000 and
512MiB7700000000 present; generic FEX intrusion refused487, duplicate8,
exit0. Full hashes/private paths in source evidence. No CEF/UI claim.

Native snapshot of that completed test then failed during suspend with remote
XPC invalidation; finally SIGCONT was attempted but timed out too. A single
fresh process/availability check returns CoreDevice4016, no assertable service/
trusted-connectivity/power states. Do NOT call this a crash, successful resume,
or native-marker pass. Own-probe process may be suspended. Full90 Steam
dependency chain stopped; launch90-fullcef-split.json was NOT created.
User asked to reconnect/unlock. First revalidate launch90-owned-split.json's
actual process identity/state (historical6432, never target blindly); resume
or stop that exact completed test, then launch already-installed90 full Steam
with source/split/no-breakpad1, directCEF32=0 and strict1. No reinstallation,
repeated ownership test or credentials needed. Failed89's intentional pause
was resolved by verified termination before90 install; it is not this gate.

15:32EDT reconnect: fresh process list confirms completed probe and all Madeira
processes absent; possible-suspension gate reconciled. Full90 actually launched
and enabled JIT. Same real helper adopts all7guest holds including4GiB and
512MiB. No UI pass:512MiB returned7700000000 is freed immediately, while the
initial hint70e0000000 is near the builtins. Exact pinned V8 code-range source
contains preferred-region containment/release logic; this supplies a concrete
placement contract rather than a generic capacity hypothesis.

The next child exposes another experimental routing bug: after reserving and
freeing7fff0000 at7760000000, it reserves aligned1GiB at7780000000. Size-only
lease selection routes it into already-used slot0 and refuses, though the real
fixed address should go through normal overlap-checked mapping. An endless
over-reserve/free/aligned-reserve loop follows. The partial log copy contains
over180000cycles. Launched process later absent; exact termination cause is
NOT established. CoreDevice copy timed out but its service retained the local
destination and continued transferring; the private prefix reached3.09GB.
Preserved via verified gzip round-trip hash, not published. First-failure
bounded excerpt/hash is in source evidence; this is not a complete exit log.

Build91 preserves old6/8 layouts and adds explicit NEAR_CODE1 on top of
SOURCE_LAYOUT1/SPLIT_LAYOUT1: separate512MiB code hold7140000000 and512MiB
placeholder-table hold7700000000,9real disjoint holds total. Reserve-only code
and placeholder table requests select distinct leases. Valid in-range fixed
addresses outside a lease fall through unchanged to normal checked mapping;
no fake overlap grants or assertion suppression. Own regression reproduces
the actual2GiB-over-reserve/free/1GiB-aligned transaction plus8guest holds.
Table probe currently covers placeholder reserve/query/free, not full split/
replace semantics. Host geometry/rollback/race/actual adoption/foreign-fixed
output preservation/Swift gates pass ASan/UBSan;37native/fullXcode91 pass.
Final near-code markers and deep-strict signing verified.

Disposable91 signing copy initially failed ENOSPC. Removed only that failed
copy; verified gzip preserves the task's partial raw log, then unlinked raw
copy. CoreDeviceService retains a deleted descriptor; do not kill a shared
system service to reclaim it. APFS cloned signing copy succeeded. No unrelated
data or game/save files removed. Build91 installation in progress; next native
near-backing, own8region Windows contract, then short bounded real full64
trial. No91device/CEF/UI claim yet; no daytime commit/push.


## 2026-10-28 Build92/93 actual failures and standalone Crashpad candidate

Phase: full AMD64 CEF compatibility; interactive full64 Big Picture is still
unverified. Base remains experiment/steam64-hybrid
be8151a7bf5773b1013f275161b7db6149284bcc plus local uncommitted experiments.
Standalone iDeck main e3d845edd4cf46a247baea6d2cc398d7ba71812d and original
Madeira main ee9fd2f4c21229dfce31a25c211d44df267336d8 remain unchanged.
No FEX source or Valve executable was edited. Prior user-confirmed hybrid
Hot Roads gameplay is not full64 CEF validation.

Observed failure: actual92 with Crashpad enabled adopts the parent's real
source1GiB/official16GiB pools; the crash child obtains one real1GiB region
but fails its second support pool. The earlier indefinite aligned-child
reservation loop is gone. Actual93 adds separate role-selected real1GiB
regular/BRP pools. Native11hold/22edge/cleanup and own Windows parent8region
plus separate child2pool tests PASS. Genuine Steam's crash child also adopts
those two independent pools, with a distinct PEB, then attempts another16GiB
libcef pool.16/32GiB attempts fail. Parent subsequently reports broken pipe,
crash-server failed and self-termination. This does not prove a successful
Crashpad handshake, V8 code-range acceptance, BrowserReady or UI.

Build92's corrected512MiB code candidate is at70a0000000, inside the actual
70xx module's4GiB reach segment. Native9holds/18data edges and own Windows
8region/14data edges/placeholder/over-reserve-free-aligned-re-reserve tests
PASS, but the genuine trial fails earlier in crash startup. A real backing
test is not proof that V8 accepts this code range.

Reporting policy: automatic approval review rejected a proposed launch that
disabled Crashpad. No bypass was used. Actual92 retried with reporting enabled;
93 removes that optional source switch. Earlier89/90 reporter-disabled results
are historical only. New instructions require reporting to remain enabled.
All failure/assertion checks are retained. The failed bounded93 session was
freshly matched by exact PID/executable, killed, and absence verified. There
is no intentionally suspended test left. Accounts/games/saves are preserved.

Evidence: private steam64-current/native93-fullcef-bounded.txt1481508bytes,
SHA256 a9f8e60af0f40dc1b1d9a1e2665e00ec9a02e49c282cfaa03f5d6ceea7247e17.
Exact92/93 native/own-test hashes and cleanup receipt are recorded in
IDECK_CEF64_SOURCE_EVIDENCE.json. Raw logs remain outside Git. The incomplete
3.09GB historical90 copy is retained as a verified gzip/receipt, not claimed
as a complete process-exit log; no shared CoreDevice service was stopped.

Next single hypothesis: CEF's documented ExternalHandler can start genuine
standalone Crashpad without another complete libcef/PartitionAlloc instance.
Pinned Crashpad1174aa4fc3196f478b5b4b77fc970d1cb85cb7cf comes from matching
Chromium126 README.chromium, not an inferred nested Git HEAD. The preparer
applies the complete eight-file public CEF crashpad_tp_1995.patch at
CEF a5d51ba9db7ee74a523dc247bd09ec91ba4d7446, SHA256
 e1474ca60831144a5c096e8dcd3f8e0a36307b55ceb1ab63fe45883dcd396d85.
The standalone graph uses pinned mini_chromium, not full Chromium //base.
CEF upload filtering/backoff/settings-v2/options/retention remain included.
Only build/include paths, one missing string parser and the entry convention
are adapted. CEF always passes --type=crashpad-handler; the entry removes at
most that one exact role before real HandlerMain, retaining IPC/reporting/
database/monitor arguments and rejecting duplicate/different roles.

Locally verified: complete-patch/source reverse-hash checks, byte-preserving
config candidate generation, malformed/conflicting config refusal, and actual
CEF crash-key filter/role/parser tests under ASan/UBSan PASS. Mac compiles
and links the actual handler plus own smoke program. Its standalone dependency
graph has no full Chromium base/PartitionAlloc. Mac smoke explicitly exits77
instead of claiming Windows IPC. Mac-only modern deployment/visible SDK
warnings do not change Windows flags or runtime checks. The candidate has
NOT been staged into the phone. Windows linking/real registration/minidump,
iPhone registration/minidump, genuine full64 UI and game regression remain
required. This is candidate preparation, not an installed Build94 result.

Reproduction and rollback: experiments/cef64/crashpad/README.md. New workflow
cef64-crashpad.yml requires actual AMD64 build plus real own-process IPC and
MDMP generation before producing an artifact; it excludes raw dumps and Valve
inputs. After Windows success, repeat the own contract on Kusch, then change
only the backed-up isolated CEF crash_reporter.cfg ExternalHandler entry and
require actual child/module/handshake evidence before evaluating UI.

Publication gate: on Wednesday16:15EDT the configured22:00–08:00 workday
commit/push window was closed. The user explicitly declined a one-time
exception and asked to preserve that window. Nothing was committed/pushed;
no automation was created to wait. Finish local verifiable checks now; the
new Windows workflow can run after an authorized-window experimental push.
Do not merge/release this unfinished work or claim a final GO.


Independent follow-up before the publication gate: a fresh second pinned
checkout reproduced preparation and all source/config/actual CEF filter/role
ASan/UBSan checks. Windows-target C++ syntax checks for the actual smoke,
entry, HandlerMain and CEF upload policy pass with llvm-mingw; this does not
prove MSVC linking or Windows IPC. The existing layout/ownership/transfer/
role/fixed-guard/launcher host regressions also pass. Read-only CoreDevice
copy of the actual isolated CEF crash_reporter.cfg succeeds378bytes. The
private candidate adds one ExternalHandler line only; removing that line
reproduces the original bytes exactly, retaining the reporting URL, rate
policy and crash keys. It has NOT been staged on the phone. Original and
candidate hashes are in the JSON evidence record, raw configs remain private.


## 2026-10-28 local-only continuation: no source publication prerequisite

The user correctly asked to continue local testing. The prior GitHub-worker
route was optional, not a technical requirement. No commit, push or workflow
dispatch occurred. Mac LLVM-MinGW generated the real AMD64 Crashpad handler
and own smoke; a second fresh-copy214edge build reproduced the process.
GNU adaptations preserve actual TLS callbacks, exact upstream assembly via
llvm-ml/one C++ name alias, CPADinfo, unwind metadata, and public dump layout
sizes. Missing SDK types come from matching public Crashpad, not a stub.
Final PE imports exclude libcef/chrome_elf and dynamic C++ runtime DLLs.

Actual Build94 own iPhone test passes TLS thread destruction, real Crashpad
registration and real minidump creation. Privately retrieved16774888byte MDMP
validates header/version, all stream ranges and system/misc/thread/exception/
module streams. Native wrapper exit1 after child exit0 is recorded separately;
no clean full exit0 claim. Own native session ended with exact identity check.
Real Steam94 still failed: it rewrote ExternalHandler candidate back to the
byte-identical378byte stock cfg before starting the old embedded handler.
No new standalone process was loaded. This is a configuration integration
gate, not failure of the already-tested real standalone handler. Failed94
session was killed and absence verified before the95 upgrade.

Build95 adds an isolated dual-gated config-write discriminator/rollback.
The own C tool records exact original attributes, requires the one fixed
ExternalHandler line, sets read-only and verifies real OPEN_EXISTING write
refusal without writing/truncating. Any guard failure aborts Steam. It retains
all report URL/key/rate policy bytes. No VM-protection workaround, assertion
suppression, Valve/FEX code change or credential operation. Restore runs on
normal return and on a later flag-off Steam64 launch; explicit config-restore
component mode restores attributes without Steam/dump test. Actual-source
failure-injection/rollback host ASan/UBSan, x64Werror, Swift launcher gates,
fullXcode95/final debug markers/deep signing/install pass.

Actual first95 trial never starts Wine: JIT896MB shrinks720MB, first placement
crosses protected Windows executable band and remaining placements hit guest
space. Existing guard refuses and deliberately exits10seconds later. This is
not CEF crashing. A delayed CPU report references PID8051 at15:32..15:34,
action=none; it is unrelated to launch95 PID8879 and cannot explain that exit.
The original madeira.cfg was privately backed up before the supported pool384
experiment.95b safely allocates384MB above the held executable window, but
cannot load CEF's0xd3ca000 (~212MB) image after main image usage~334MB.
No existing pool/window/overlap guard was relaxed. Measured safe runs include
630MB above and619MB below, motivating608MB as a next bounded budget, not a
proven fix or sustained capacity claim. No external-handler UI success yet.

Historical95b cleanup gate (resolved below):95b was paused after a bounded30second trace. CoreDevice
subsequently loses trusted connectivity, and Device Hub explicitly displays
Currently Unavailable. Fresh exact identity query fails, so no stale PID was
resumed/killed. It MAY remain paused. Temporary pool384 config remains and
CEF read-only marker outcome is uncollected. Preserve private identity record
paused95b-fullcef.json, madeira95-before-pool.cfg, and original CEF config
crashpad94-device-original.cfg. On physical reconnect/unlock, FIRST revalidate
and end/resume only that exact installed lab identity, restore original global
config plus recorded CEF attributes with MADEIRA_CEF64_CONFIG_RESTORE=1,
and restore original CEF config bytes if ending. Then test608MB if appropriate.
The user was asked once to reconnect; no repeated lock prompt or automation.
All exact artifacts/hashes are in IDECK_CEF64_SOURCE_EVIDENCE.json. No merge,
release, full64 UI/game success or final GO is claimed.


### Reconnection and95c: cleanup verified, new bounded trial awaiting evidence

After the user's physical reconnect, exact old95b identity is absent. The
isolated restore diagnostic actually reports original CEF attributes restored
and exit0; that Native session is ended and absence verified. Original global
and CEF config bytes are restored and read back exactly. Private receipt
cleanup95-reconnect-complete.json and config95-restored-results.txt prove this
cleanup, superseding the old95b pending gate above.

Separate95c changes only the supported isolated JIT budget to608MiB and
re-stages the same reviewed reporting-preserving ExternalHandler candidate.
Both actual files are read back and matched, with no overlapping lab session.
Launch succeeds. The30second identity query fails before any suspend, a fresh
query times out, and device overview/Device Hub show connecting. No native
snapshot was collected.95c was NOT intentionally suspended; process existence,
pool placement, CEF startup, real handler use and UI remain unknown. Never
interpret this observer/connection failure as a Steam crash or successful run.

Next: revalidate this exact trial identity on reconnect, collect bounded native
evidence, end/resume explicitly, then restore original global config plus CEF
attributes/bytes before ending experimentation. Temporary608 budget and candidate
remain staged; private backups and exact identity/artifact hashes are in
IDECK_CEF64_SOURCE_EVIDENCE.json. No account/game/save changes. No repeated
launches, credential operations, disabled reporting or relaxed mapping guards.

Fresh actual-source config guard failure/rollback ASan/UBSan, pinned real CEF
filter/parser/source-integrity tests and launcher gates pass locally. These
do not substitute for the missing full64 device/UI result. Changes remain
uncommitted/unpushed under the user's time-window rule; publication is not
a prerequisite for these local builds or actual-device tests.

User's subsequent report: phone remains in iDeck on a blue guest desktop with
a Steam - Error dialog. Exact body pending. This rules out claiming the phone
rebooted from the Mac connection loss; it does not establish the underlying
Steam/CEF failure. Latest Device Hub explicitly Currently Unavailable with
connection timeout. Preserve the error/session; collect its exact text and
reconnect data link before any new launch or causal patch.


## 2026-10-28 dedicated full64 branch, image-pool discriminator

At the user's request all tracked uncommitted changes and nonignored untracked
files were byte-preserved while creating experiment/steam64-cef64 from
be8151a7bf5773b1013f275161b7db6149284bcc. No commit or push was made.
Main, the old hybrid branch tip, other worktrees, user Demo.gif and all pinned
submodules remain untouched. Future experimental workflows now target this
new branch. Private branch-cef64-move-receipt.json records the exact snapshot.

Recovered95c evidence supersedes the observer/connection-only gate above:
the config discriminator PASSes, the candidate is retained byte-identically,
and actual CEF adopts both genuine16GiB PA pools. The requested external
Crashpad then fails image allocation: SizeOfImage0x17fa000 (~24MiB) exceeds
the largest free0x810000 range in the effective560MiB main image pool. Later
GLES/steamclient64 DLL loads fail STATUS_NO_MEMORY. No file-corruption claim
or reinstall is justified. Failed Native identity was ended and absence
verified; actual fresh restore96 proves recorded attributes restored/exit0
before restoring original CEF bytes and proceeding.

Minimal own packaging patch: retain original private symbol-bearing PEs and
create separate runtime/ copies with GNU DWARF removed. All mapped non-debug
section bytes, RVAs, sizes and flags plus executable/security headers are
checked unchanged; real TLS callback, unwind data, CPADinfo and imports are
verified. Handler image0x17fa000 ->0x151000; smoke0x6a5000 ->0xe7000.
Same-input stripping reproduces exactly. Separate source builds may have
different build IDs; no cross-build bit-identity claim. Actual artifact/code
corruption discriminator and pinned CEF source/filter ASan/UBSan PASS.

The installed app is STILL Build95: trial96 changes only own reporter files,
not Valve binaries/FEX/native runtime. Fresh phone own test PASSes TLS thread
exit, real registration and real local minidump generation. Retrieved MDMP
validates header, stream bounds and system/thread/exception/module streams.
Native clean exit0 is not claimed. In the full30s trace, the compact actual
handler now loads, but steamclient64's0x18bc000 request still exceeds the
largest free0x80000 range and0xc80000 main virgin space of the608MiB pool;
region C has0x18ff0000 unused. Full64 BrowserReady/UI/handshake remain unproven.

Next single-variable trial97 uses the EXISTING default-off pure-x64
MADEIRA_X64_IMAGE_NOCOPY=1 policy to avoid redundant image-pool copies while
retaining native ARM64EC/hybrid copies. The signed final Build95 dylib contains
this path; its production host gates/rounded-section/negative cases PASS.
The old generic skip-copy failure warning predates this marked-view policy;
neither the warning nor host tests prove the new device outcome. Require
actual mapping/pool/first-fault/UI evidence before accepting it. All original
address ownership, executable-window, reporting and assertion guards remain.
No FEX edits, assumed extra entitlement, blind protection retry or GO claim.

### 2026-10-29 simultaneous V8 tables, isolated Builds96/97

Trial97's existing pure-AMD64 image-data mapping removes the observed image-pool
exhaustion in its bounded trace, but does not produce a usable Steam window.
Fresh CEF UTC1029/023528 reports ExternalEntityTable subspace allocation OOM.
The BrowserReady message is for SPSharedJSContext, not proof of visible login.
The apparent bigres-free message includes MEM_PRESERVE_PLACEHOLDER; it is not
evidence that a complete live table reservation has been released.

Own Windows probe98 reproduces the missing second simultaneous512MiB table:
first-table split/replace/remaining ownership pass, second reservation fails8.
Explicit experimental MULTI_TABLES adds a separate real native hold; Build96's
12-hold/24-edge native test passes, and the identical PE changes to a distinct
second table with overall result0. Full CEF then adopts both but fails a third
table with the same V8 OOM. No live lease is recycled or granted twice.

Pinned public V8 revision556665385d5cdc2a0793b977d373da88091a7208 initializes
multiple external/cpp-heap/shared pointer tables. It is architecture evidence,
not a claim that Valve's source is byte-identical. Own99 reproduces a third
table failure on96 while retaining the first two. Build97 adds one disjoint
512MiB hold at71e0000000..7200000000 only in the optional table mode. Bounds,
alignment, fixed-address meaning, live views, atomic one-use ownership and
create-view rollback remain checked. Original6/8/9/11 modes are unchanged.

Current host native-ownership/rollback/concurrency/view-transfer tests pass;
37 native units, complete Xcode97, actual final linked markers and deep strict
signature pass. Actual phone97 holds13 simultaneous regions and passes26
edge backing operations. The same own PE now reserves all three distinct
tables and preserves split/replace semantics. Its overall result is NOT PASS:
the child reports a nonzero exit1245438208, yielding result86; cmd's outer
exit1234608384 is also anomalous. The copied child file says result0, but
freshness and CRT/server exit-status behavior need a separate discriminator.
Do not describe table-specific success as a clean child-process regression.

Before the next full97 run, another user-authorized32-bit task installed public
Build99. A fresh launch log identifies99 and only prerequisites; its old CEF
file is not new full64 evidence. That own launched instance was identified and
ended, original configs restored, and the verified experimental97 reinstalled.
The signed public99 rollback app is retained. Never attribute99 behavior to97
or overwrite the other task's source. This branch remains experiment/steam64-cef64,
with all work uncommitted/unpushed and auth/games/saves preserved.

Next: bounded full97 CEF64 run with independently retained tables; require fresh
native module/ownership evidence and actual visible interaction before success.
Then isolate the own child exit-status anomaly. Private artifacts and hashes
are listed in IDECK_CEF64_SOURCE_EVIDENCE.json; raw logs/binaries stay private.

### Full97b rendered login, Build100 public-network discriminator

After reinstating the expected97 build, the actual native header/identity and
59 pure-AMD64 image-data markers agree. Full CEF adopts all three separate
512MiB tables; fresh CEF UTC1029/051003..051012 has no prior table OOM.
Login popup131073 is created, BrowserReady logged, and Device Hub visibly shows
Valve's animated Logging in UI. This is stronger than shared-context readiness,
but not an authenticated library or Big Picture pass. New login states are
WaitingForNetwork then WaitingForServerResponse. CM log schedules directory
lookup at01:10:11 and stops there. Native threads remain active/footprint~2.7GiB;
activity does not prove forward progress. Exact trial was ended and fresh
cleanup97b restored original attributes and both config readbacks.

Isolated100 adds a fixed, feature-gated AMD64 network/child-exit diagnostic,
mutually exclusive with other component tests. Public requests have bounded
time/body size, normal certificate checks, no account/Guard calls and no response
payload/address logging. Parent verifies a fresh tagged child result alongside
actual wait/GetExitCodeProcess; CRT return7 and direct ExitProcess7 are separate.
Production launcher prefix/flag/mixed-mode/symlink tests, PE Werror compile,
full Xcode100/final linked markers/deep strict signing/install pass. Host Swift
cache permission/alias failures were resolved using a distinct canonical
workspace cache, with actual tests passing afterward.

Same-byte phone PE tests with existing image-data1 and0 in separate native
lifetimes both pass tagged child exit7, HTTP, neutral HTTPS, Steam server time
and versioned CM directory200 within48..317ms. An unversioned alternative
returns404/92bytes, so overall diagnostic result1/probe-exit1 is retained.
IMPORTANT: the categorical Steam log can omit the version; its displayed path
is NOT an observed wire URI.404 is not proof that Steam sent an invalid URL.
No basic TLS, credentials or global mapping root cause is established. Small
standalone successes also do not prove full concurrent Steam networking.

Next single-variable101 restores existing client/support copies/aliases and
saves only the large pure-AMD64 libcef image copy, under an extra explicit
LIBCEF_DATA_ONLY1 plus actual held-layout/session gates. Existing pure-image
eligibility and all VM/reporting/assertion rules remain unchanged. Actual-source
selector/gate/malformed-name ASan/UBSan and existing image-data regressions pass.
Require full final-link/device comparison before attributing the login stall.
No FEX/Valve edits, credential automation, main merge, release or GO claim.

###101 actual authenticated success, then separate FEX arena failure

The libcef-only comparison actually marks only the large libcef image as host
data and retains client/support copies. Fresh directory lookup completes, real
CM WebSocket connects and logged-on response arrives01:26:01; Steam's login
state records Success/OK01:26:07 with saved auth and no agent credential action.
This differs from97b, but a single A/B cannot establish the sole mapping cause.
No visible authenticated desktop/library/BPM/game proof is claimed.

The Native identity subsequently disappears. Retrieved static native trace
explains why: at~68.5seconds the existing8GiB FEX band7400000000..75ffffffff
cannot allocate0x1800 bytes aligned8. ml798 errors repeat, an unrecoverable host
fault is repeatedly misdelivered, and ml465 terminates the app. Footprint~3525MiB
does not make this a generic physical-memory/Jetsam claim. Earlier table/pool
OOM is absent. Raw records are private; hashes are in the evidence JSON.

102 prepares one explicit layout alternative: after all13-region flags, move
ONLY hold3 to6000000000..7000000000,64GiB entirely below guest furniture.
Other12 holds remain byte-identical in geometry. Existing versioned Native
publication passes the exact range to the unchanged emulator. No blind overwrite,
soft grant, FEX edit, extra entitlement or automatic fallback is introduced.
Actual production host boot/claim races/all-slot rollback and wide13/26 backing
fixtures, view/owner-bounds regressions pass ASan/UBSan; full Xcode102 and final
wide/table/libcef/network markers/deep signing pass. Prepared signed102 is NOT
installed and has NO actual-device wide capacity/FEX/Steam result.

Current physical gate: phone Locked10002 rejects the cleanup101 diagnostic;
Mac CUA is locked too. One unlock request is pending; no repeated launches,
installs or lock bypass.101 is already absent and no test is intentionally
paused. Original global config is restored and read back byte-equal via paired
file service. CEF candidate bytes/read-only attribute marker still require
fresh actual CONFIG_RESTORE and original CEF-byte readback after native unlock.
Do that FIRST, reconciling any new user session; then install102, require real
wide-backing13/26 capacity and actual published/consumed64GiB range before
bounded full CEF/login/BPM/game testing. Do not mistake prepared102 for installed
101, repeat the old signing/account gate, or lose public99 rollback resources.

All new source remains uncommitted on experiment/steam64-cef64, HEADbe8151a7;
no push, main merge, release or full64 GO claim.

###102 rejected low arena;103 standalone layout prepared

User physically unlocked. Actual installed101 cleanup102-before-upgrade restores
original CEF attributes and both original byte readbacks.102 installs, but its
real simultaneous wide-backing test fails at slot3:6000000000+1000000000,
Mach kr3. First3 own holds are released; result1. No full102 Steam launch.
The subsequent existing early VM inventory completes despite launch observer
timeout:8 successes/54 failures, all own successful mappings cleaned, fresh
process query no lab app. It reports actual PROT_NONE mapping1000000000+6000000000
(the documented system/GPU64..448GiB carveout), and lower16GiB sample requests
are already occupied by system/malloc/shared mappings. Never unmap/overwrite
these. Four high-band16GiB sample positions succeed individually, not together.

101's actual FEX census confirms fragmentation/capacity pressure:920 views,
covered1e3254000, free1cdac000, overlap0,406 holes, maxgap7fe000 and aligned
maxgap410000 cannot serve16MiB/aligned16MiB. This explains the later small
rpmalloc failure without pretending a6KiB application allocation needs8GiB RAM.

103 repacks only the usable high band. Native full101 never adopted legacy
embedded-report support9/10 after real standalone reporting. A new separately
identified11-hold geometry moves Oilpan to740..750, FEX to750..77ffff
(12GiB minus64KiB), first table to714..716, retaining other tables71c/71e.
Actual16GiB CEF pools/guards,8GiB cage, source-component pools and near-code
hold remain real and disjoint.9/10 now mean tables only in this new Native
metadata mode; legacy paths remain unchanged. SOURCE/SPLIT/NEAR/CRASH/MULTI
plus STANDALONE_LAYOUT1 and EXTERNAL_CRASHPAD1 are required; conflicting wide
layout or missing reporting fails before mapping. Bounds/alignment/live views,
exact fixed identities, atomic single claims and create failure rollback remain.

Production11/22 geometry/all-slot failure/cleanup, Native claim race/gates,
legacy and new role/bank/fixed-address ASan/UBSan pass;37 final native units
and full Xcode103 pass. Actual signed debug SHA9a43560a33ffd0fce64c55cbc543f5ee1a8a485e1575b5859647b69ebb403ab0
contains new geometry/gate markers and metadata symbol; deep strict signature
passes. Current own Windows PE compiles Werror and explicitly separates the
absent legacy-child test from real standalone reporting.

103 is NOT installed. The install preparation fails at its fresh process query
before install; a following capacity attempt fails during file copy before
launch. Fresh inventory reports paired but trusted tunnel unavailable/DDI=false
and CoreDevice4016. Device Hub also reports screen sharing unavailable while
phone microphone/camera active; do not stop those user activities automatically.
One physical reconnect request is pending; no service restart, repeated install,
stale-PID signal, credential action or intentional suspended session. Latest
actual installed lab102 has not protected CEF config; original cleanup102 was
verified before these native-only probes.

Resume EXISTING signed103 after connection, verifying current app identity/version
and no other task session. Require actual11/22 Native capacity, current own
Windows compact ownership, genuine standalone IPC/TLS-exit/MDMP, then full saved
Steam login/BPM/library/controller/game/return over the earlier failure interval.
Native numerical published/consumed range outranks an old generic16GB plan
label. Private RESUME103.md contains the precise sequence. All artifacts/hashes
are in IDECK_CEF64_SOURCE_EVIDENCE.json. No full64 GO, commit, push or release.

###103 actual wireless install, capacity and authenticated desktop

2026-10-29: user restored Device Hub access; the paired wireless CoreDevice path
also recovered. No evidence that Tailscale caused it. Signed103 installed in the
existing isolated bundle, preserving auth/games. Native11 simultaneous holds,22
backed boundaries and11 cleanup operations PASS. First own Windows attempt never
started: JIT failed while existing LocalDevVPN was disconnected. After directly
restoring that existing VPN, fresh owned103-vpn C result0 verifies8 exact
reservations/commit-zero-write-read/placeholder/refusals/free and distinct extra
tables. Its cmd exit1235017984 is still wrong; do not call it a clean process pass.

Genuine standalone reporter103-vpn passes TLS-thread exit, IPC registration and
real local synthetic MDMP. The16775576-byte MDMP has bounded streams3/4/6/7 and
SHA89c73e16c1206a4fef718cd4bc12a2b2601c7473f7d92d2d03284d26d78f47d3.
Own smoke only; network upload disabled only for that synthetic test, not CEF.
No clean wrapper exit within the bounded observation; exact test identity ended,
original global config byte-readback restored between tests.

Full103 genuine AMD64 Steam/CEF adopts compact layout; fresh LogOnResponseOK
12:07:44 and SteamSuccessOK12:07:52 prove saved auth without credential action.
Actual desktop chrome appears, content black. The+156.54s native snapshot has no
ml798/unrecoverable/FATAL and8716MiB FEX used/3571MiB free; largest gap3112896KiB.
This crosses101's~68.5s failure interval without the same exhaustion, but is not
working UI proof. Real BrowserReady/JS stores initialize. Fixed Steam Big Picture
URI ACK succeeds, but no visible BPM; Steam restarts webhelper12:09:40 and
replacement helpers cannot reuse single-lifetime claims. Never silently overlap
or recycle their leases. Observe-timeout/host-alive is not a browser pass.

Next sameBuild103 comparison is fresh direct Big Picture startup after exact
cleanup/restoration; no second patch before the UI/render failure is distinguished.
SourceHEADbe8151a7 plus scoped dirty research, no FEX/Valve edits, credentials,
commit/push/main merge/release or full64 GO. Artifact hashes are in source evidence.

###104: x64 ROOT-store lifetime defect reproduced and isolated fix validated

Direct103 BPM remains on login spinner/WaitingForServerResponse after current
CM-directory query. At+178.14s FEX has5603MiB free, no ml798/FATAL. This differs
from101 exhaustion. No browser/home success. Exact session/config guard cleanup
restores original attrs and both config byte readbacks.

Own concurrent WinHTTP/CryptoAPI discriminator then reproduces a concrete bug:
parent opens ROOT before child launch, has125certs and4HTTPS200 responses; two
children each have5certs and fail4requests with12157. Existing x64 enum_root_certs
removes/frees each master-list cert; that Unix list is shared by all pseudo
processes. WoW64 already has a separate non-destructive reader. Never conflate
this own API path with Steam's actual network stack or claim its sole root cause.

104 adds only an explicit ROOT_STORE1/SteamUISession1/actual standalone-layout
gated x64 reader: immutable master list, private thread/PEB cursor, retry without
advance, end/reset; no timeout/eviction/process-cap or certificate/trust change.
Existing ordinary/WoW64 code retained for A/B. Actual-source host ASan/UBSan
checks64simultaneous readers/resize/end/owner/gates/bytes.37nativeunits and full
Xcode104 pass, final debug ROOT_STORE marker verified and deep strict signed
app actually installed. Signed debug SHA
f66ac6e46b13463419fd45ab1668bcbaadb8bb36ad4a8b2d7e55ee7b985ecc21.

Same own PE104 with flag1: all3processes125roots, all12HTTPS200, child exit7
fresh-nonce receipts, parent result0 and cmd exit0. No credentials/response
payload/TLS exceptions. Next same-build opt-out plus full genuine Steam/CEF
Big Picture regression; no boot/game GO yet. Source still uncommitted; main,
FEX, Valve and submodules unchanged. Private hashes in source evidence JSON.

###105: full64 home displayed, later fourth table fails

104 full login succeeds12:27:55 then real CEF INT3 at RVA59efb95. Exact loader
base and unchanged disk CEF hash establish the RVA. Its code matches Chromium's
delay-load failure handler (including bthprops exception/error1455 branch), not
a refcount check. The old brp-contain label is misleading. Unknown module/import
remains unresolved; do not suppress the hook or pretend this is table exhaustion.
Original104 config guard attrs and both byte readbacks restored.

105 adds read-only, exact CEF126 header/timestamp/SizeOfImage/code/prolog/
DelayLoadInfo gates, only public DLL/import names and numeric error; no stack
payload logging or context/memory/exception-policy changes. Actual-source
ASan/UBSan refusal/overflow/name/ordinal tests,37nativeunits/fullXcode/link
markers/deep signing and actual install pass. No matching fault105 captured.

Actual105 genuine AMD64 Steam plus AMD64 CEF displays Big Picture home with
real recent-game art, including Hot Roads. Device Hub screenshot evidence in
this chat; no claim of responsiveness. Remote virtual Right/keyboard/menu tests
do not prove navigation: later helper says steam-window-unavailable, and tree
has no visible Steam window. Steam's fresh12:39:11 CEF log reports V8 OOM
ExternalEntityTable::InitializeTable; Native shows3real table claims then a
fourth512MiB request refused. At+291.89s the host remains alive with5196MiB
FEX free and no ml798. Visible home is cached after browser death, not success.
This separates the remaining table-capacity defect from the ROOT reproducer
(closed) and the separate104 delay-import failure (unresolved).

106 prepares an explicit FOUR_TABLES1 alternative after standalone/reporting
gates. Keep all old pools/table identities; FEX becomes11GiB750..77c, add one
real aligned table77c..77e. No lease reuse, silent overlap, suppression or FEX
edit. Need actual12holds/24backed edges, four-table Windows ownership, full
Steam/live navigation/game/return before claiming usefulness. Smaller FEX may
limit games and a fifth isolate remains a capacity question. Scoped host
production geometry/rollback/claim races/adoption/fixed-identity tests pass;
Native37 and final full build in progress. Source remains uncommitted.

###107 continuous lifetime trace rules out unsafe lease recycling

106 full actually adopts all4tables then fifth512MiB allocation fails12:54:59.
Added read-only observer107 to record type/status/remaining-view per table free
under virtual_mutex; no claims/protection/exceptions changed. Own Windows
contract shows preserved/coalesced placeholders remain1, complete releases0,
confirming observer discrimination. Full107 runs continuously without any
suspend snapshot; savedloginSuccess13:04:23, realhome and Steam menu physically
open after fixed command. Subsequent Library navigation is ineffective and
CEF13:06:50fifthtable OOM. Actual14table free events all8002/8001 andremaining1,
ZERO complete8000/remaining0. No safe recycle evidence; never unclaim them.
Host remainsalive with~1.5GiBFEXfree after CEFdies, not usableUI/controllerproof.
Exact107ended, originalattrs/bothconfigreadbacks verifiedrestored.

108 prepares a new opt-in SIX_TABLES1, requiring FOUR_TABLES1 and actual
standalone/reporting gates: two additional512MiB realalignedholds706..708 and
708..70a in earlier observed free guestband before Wineheap placement. Keep
11GiBFEX; this trades genericguestspace, may hurt gamecapacity. No overlap,
softgrant, table-reuse or FEX/Valve change. Host14/28geometry/bootallslotfailure
rollback/claimraces and actualadoption6bank/fixedidentity/bounds/seventhrefusal
passASan/UBSan. Native37/fullXcode108 pass; actualphonecapacity and6tableWindows
gates precede fullSteam. Not finalarchitecture or full64GO. Uncommitted, no push.

###108 native six-table capacity passes; generic guest space fails early

Actual10814simultaneousholds/28backededges/14cleanup PASS. OwnWindows6distinct
512MiBtable leases/placeholder/refusal/free Cresult0; same cmd1235017984 issue
retained. Full108 fails before V8cage/table adoption: ordinary0xa0000..0x100000
heap/stack/image requests cannot map in guestfurniture, CrBrowserMain is in
CEF's OOM/report wait path. Only source/CEFpool0/1/4/5 adopted. Thus the Native
capacity result did not predict full client capacity; six-table guestband
tradeoff is not a solution. Exact app ended, attrs/bothconfigreadbacks restored.

109 adds read-only bounded Mach submap backing classification for the low
RO/system ranges; no deallocate/protection/entitlement or trust changes. Also
identified existing documented MADEIRA_SMALL_STACK_EXES per-program option:
Steam's non-Chromium threads currently pay the universal8MiB stack floor.
Next same layout test can select steam.exe ONLY for2MiBminimum, still honoring
explicit larger requests and leaving steamwebhelper/game/native stacks alone.
This is not a new default or evidence that Chromium can use small stacks.
Host config comments warn not to list Chromium; preserve that boundary.


### 109: the Steam-only small-stack option does not fix guest-space starvation

Build109 actually selects the existing2MiB minimum for steam.exe: twelve
stack-floor records confirm it. Chromium and game stack floors remain8MiB.
It still fails before V8 table/cage adoption, with69ordinary allocation scan
failures and only source/CEF pools0/1/4/5 adopted. The six-table guest-band
layout is therefore rejected. The exact session was terminated, and the
original reporter attributes and both configuration files were restored with
exact byte readbacks.

### 110: tables in the FEX tail reach home, but a seventh live table is needed

Hypothesis:108/109 reserved tables in the generic image/heap/stack band;
moving only those two tables into the old FEX tail avoids that conflict.
`MADEIRA_CEF64_TABLES_FROM_ARENA=1` requires the existing six-table,
standalone and external-reporting gates. It publishes FEX750..778 (10GiB),
with distinct tables778..77a and77a..77c; the old fourth table77c..77e is
unchanged. No FEX source, Valve binary, assertion or lease-recycling change.

Actual-source ASan/UBSan geometry, all-slot failure/rollback,16-thread claim
races and Wine adoption tests pass. Native37units, full Xcode110, linked
Mach-O markers, deep signing and installation pass. On Kusch,14simultaneous
holds/28backed boundaries/14cleanups and the own Windows6table contract pass.
The own C result is0; cmd still reports1235017984, so clean process exit is
not established.

Saved login succeeds at13:34:46. Device Hub shows genuine Big Picture home
and its menu. At+247seconds all six tables are adopted, FEX has3295MiBfree,
and there are no Native allocation scan failures/refusals/ml798 in that
snapshot. At13:42:59, however, a seventh512MiB table is refused and CEF logs
ExternalEntityTable OOM. Later menu requests report no Steam window while
the old frame remains visible. Navigation/game/return success is not claimed.
The initial run was continuous; one later serial Native snapshot briefly
suspended and then resumed the exact app. Its final failure and configuration
restoration are retained separately.

Diagnostic correction: Build109 descended a returned Mach submap at its base,
which can classify the wrong low-address leaf.110 resets to the original
requested address at every depth and reports leaf containment. Host tests cover
success, gaps, errors and the eight-level bound. Prior109low-leaf observations
are invalid; no system/GPU mapping was unmapped or reprotected. The expanded
lease observer's4096record budget was mostly consumed by DECOMMIT, which retains
reservations.111filters to RELEASE, including preserve/coalesce, without
changing claims or memory behavior.

### 111: actual virtual-controller navigation; eighth-table OOM

Hypothesis:110 had2727MiBFEXfree at failure, so another distinct512MiBtable
can be exchanged for arena capacity. ExplicitSEVENTH_TABLE1 requires all prior
arena-tail gates. FEX becomes750..776 (9.5GiB); table14 is776..778, with the
other table identities unchanged. Geometry, ownership, rollback and refusal
host tests pass; Native37/fullXcode111/Mach-O/sign/install pass. Actual Native
15holds/30backed edges/15cleanups and the own Windows7table contract pass.
The C result is0, but the same cmd exit discrepancy remains.

Saved login succeeds13:50:14. Device Hub shows the virtual D-pad moving the
selection to Hot Roads, then virtual A opening its genuine Steam detail page.
The own input-status file records6state changes. These are actual UI responses,
not merely command acknowledgements. Play does not start a new game process.
CEF then logs an eighth512MiB ExternalEntityTable OOM at13:52:07. All22observed
release operations are preserve/coalesce with a remaining view; zero complete
releases were observed. FEX last has2176MiBfree; later19generic scan failures
and a missing Steam window follow. No full64game, Bluetooth, return or
long-term GO assessment is supported.

The exact111session was verified and ended. The subsequent restore attempt
failed at its first process query: CoreDevice tunnel unavailable and DDIservices
false; Device Hub also reports CurrentlyUnavailable. **Original reporter
attributes/configuration restoration is pending**, and must precede any new
installation or ordinary launch. No paused app is intentionally left behind.
The user was asked to restore the existing wireless connection; no credential,
lock or network-security bypass was attempted.

### 112: eighth-table experiment prepared locally, not device validated

ExplicitEIGHTH_TABLE1 requires the seven-table arena-tail gates. FEX becomes
750..774 (9GiB); a new distinct table15 covers774..776. The generic guest band
and earlier table identities remain unchanged. Actual-source host tests cover
all sixteen holds, failure/rollback, concurrent claims and eight-table Wine
adoption/refusal. Native37units and fullXcode112 pass; linked markers and deep
strict signing are verified. The prepared app is private and **not installed**.
There is no Native16/32/16, Windows8table, Steam, game or return device result.

Next: restore111's original attributes/configuration after connectivity returns;
verify exact installed identity and no old experiment; install112; run Native
16/32/16 and own Windows8table gates; then repeat real navigation/game/return.
A finite table layout is a capacity experiment, not an unlimited long-term
architecture. If demand or FEX game headroom exceeds it, investigate a genuinely
ABI-compatible source-built CEF with smaller compiled pools/tables or a supported
larger address space. Never reduce backing under unchanged Valve masks, overlap
FEX, recycle preserved placeholders or suppress allocation failures.

Source remains on experiment/steam64-cef64 atbe8151a with local changes. No
commit/push outside the user's time window; main, FEX and Valve binaries remain
unchanged. Raw artifacts stay private; hashes and exact limits are recorded in
IDECK_CEF64_SOURCE_EVIDENCE.json.


### 112 actual device follow-up: ninth-table failure reproduced

Wireless device availability recovered on2026-10-29. A newly running instance
of the old lab bundle was identified before recovery; the previous stale PID
was not reused. The original111 reporter attributes and both configurations
were restored with exact readbacks before installing112. Actual112 native
16holds/32backed edges/16cleanups and own Windows8table contract pass. The C
result is0; outer cmd still returns1235017984, so clean process exit is unresolved.
Saved login succeeds at17:54:03EDT. Device Hub shows real Big Picture home and
virtual D-pad changing the selection to Hot Roads. A detail/game transition is
not established. CEF logs another ExternalEntityTable subspace OOM at
21:55:13.962UTC. All eight table slots8..15 were adopted before a ninth request
was refused. All25observed RELEASE operations retain a view; zero complete
releases. Last FEX sample is7099MiBused/2116MiBfree. The exact failed session
was ended; original reporter attributes and both configurations were restored.

A fresh112 pre-Wine VM probe uses110's corrected submap descent. It confirms
the64..448GiB interval is still a tagged31 protected system mapping; no change
to it is attempted. The4GiB target is in a protected mapping up to64GiB, not
an available free interval. This corrects the unusable109low-leaf inference.

### 113: compact source-pool layout, one discriminating change

Observed112 failure: nine simultaneous512MiBtable requests exceed eight holds.
Hypothesis: rearranging the already source-built1GiB regular/BRP pools can
recover one512MiB aligned interval without reducing FEX or the generic guest
band. ExplicitMADEIRA_CEF64_COMPACT_SOURCE_POOLS1 requires every eight-table
standalone/reporting gate. It moves only source regular slot0 to714..718,
source BRP slot1 to70ffff0000..714 (guard before710), and first table slot8 to
718..71a; new table slot16 is71a..71c. All compiled pool sizes, pool alignment,
BRP guard,9GiBFEX, official CEF pools and other table identities are preserved.
The guard occupies a new64KiB native interval; native no-overwrite is mandatory.

Actual-source ASan/UBSan geometry/all17slot failure/rollback/backingedges,
claim races, flag dependencies and9table Wine adoption/fixed identity/tenth
refusal pass. Native37/fullXcode113/finalMachOmarkers/deepstrictsign pass.
Actual iPhone installation and native17holds/34backededges/17cleanup pass.
Own Windows9table and genuine Steam/UI/game/return tests are still pending at
this record. No FEX source, Valve binary, compiled mask, assertion or live-lease
recycling is changed. This is a finite capacity experiment, not a long-term GO.


113 actual follow-up: own Windows9distinct tables pass with C result0, while
outercmd1235017984 remains unresolved. The full client adopts the moved source
regular/BRP pools and the first3table identities correctly. Saved login succeeds
18:35:35EDT and real Big Picture home is visible. Input status records4changes,
but navigation does not complete and fixed menu reports steam-window-unavailable.
The bounded serial snapshot is resumed with a verified SIGCONT receipt.
Unlike112, this failure has no new ExternalEntityTable log or owned-table refusal:
only3table slots were adopted. Native logs identify STATUS_NO_MEMORY while
creating the1MiB CHPE emulator stack, at148native threads, followed by a CEF
renderer report path at verified libcef+0x6923349. Generic1MiB allocation scan
fails twice in that snapshot. This is a distinct observed thread-allocation
failure, not evidence that the nine-table capacity is sufficient.14observed
RELEASE operations all retain a view. The exact failed session was ended and
original attributes/global/CEF bytes restored.

Next single-variable test uses the SAME113binary and existing opt-in
`MADEIRA_THREAD_STACK_SPILL=1`. Source review shows kernel/emulator stacks pass
a4GiB lower bound, which previously prevented the existing advisory furniture
ceiling fallback. That flag permits a kernel-selected real mapping after the
scan fails, preserving explicit caller upper limits. It changes no stack size,
assertion, reservation identity or FEX source. Require actual spill placement
records, absence of the specific thread-create failure, then real navigation
and game/return evidence. This A/B is pending at this record.

113 same-binary spill A/B actual result: saved login18:40:30EDT; Native logs
show16logged kernel-selected real1MiBstack placements (e.g.121ef0000) and zero specific
thread-create failures, without changing guest8MiBstack floors. Actual Device
Hub virtual D-pad selects Hot Roads; A opens its detail page and requests Play.
Steam18:41:52 tracks app1819280/PID824/hr.exe. Native maps/runs AMD64 hr.exe,
but no interactive game window is observed. Steam's i386 bin/x86launcher.exe
fails its4GiBWoWwindow+default8GiBheadroom policy (595MiBfree at that sample).
The diagnostic game-focus command reports no-game. At22:45:04.789UTC, CEF needs
a tenth512MiBtable and logs ExternalEntityTable subspace OOM; all9holds were
adopted. This does not establish game launch/return or long-term GO. Two bounded
serial snapshots at different stages both resumed the same exact session;
after failure it was ended and original attributes/config bytes restored.

Long-term ABI check: exact official CEF hash45927f... has cef_api_hash RVA278f90.
Read-only PE disassembly and ASCII data identify platform
8e4d334971e43b4e56c93030410b02d735d99c8b and universal
1c1ddb9d9359dea0869d53800924279a716e3deb, both different from the supplied
public126reference. Its returned commit is8482cf107230fa5599d2ad5a783f77ef30d71f73;
the corresponding publicCEF GitHub URL returned404 on this check, not proof
that no matching source exists elsewhere.8of76matched helper static CEFimports
are absent from the reference header function-name census. Stock CEF cannot
simply be claimed as an ABI-compatible replacement. No hash is spoofed, export
stubbed, Valve binary patched or runtime check suppressed. Private ABI inventory
retains exact hashes and the8public names. The reference snapshot lacks Git
metadata; header hashes identify the actual inspected bytes.

Next discriminator: Steam's own per-game Overlay toggle for Hot Roads, to test
whether the i386 auxiliary launch and extra table demand depend on optional
Overlay. A fresh same113spill session is started for that reversible UI test.
No overlay setting has yet been changed at this record.

113 Overlay discriminator: using Steam's actual game Properties, the initially
ON Hot Roads Overlay switch was visibly turned OFF. Play still spawns i386
x86launcher.exe, whose guest-window reservation fails. Steam tracks new
hr.exe PID860 at18:53:08 and reports exit0xc0000135 at18:53:12. This is a
DLL_NOT_FOUND result, not proof that the x86launcher refusal caused game exit.
CEF also exhausts a tenth table at22:53:42.246UTC. Disabling Overlay is rejected
as a workaround. The exact failed session was ended; original reporter/global/
CEF configuration restored. CEF could not reopen Properties for UI rollback,
so after confirming no lab process, the exact app1819280 OverlayAppEnable0
field was returned to prior1 in its private localconfig. A structured KeyValues
walk verified the app/key identity; exactly one byte changed, all account data
and other bytes stayed identical, and actual device readback matches.

114 discriminator: retain113geometry and spill option, add an exact lab opt-in
MADEIRA_STEAM_UI_MODULE_ERRORS1. WineProcessBridge chooses only-all,err+module
under session1; all trace/relay/process/file payload channels remain disabled,
even if verbose1 is also set. Ordinary policy is unchanged. Actual extracted
bridge policy passes32ASan/UBSan combinations; launcher regressions and full
Xcode114 pass, finaldebugdylib markers and deep signing verified. This is a
minimal diagnostic patch, not a game fix. The next test must name the missing
DLL/import from a fresh actual Hot Roads launch; do not infer it from exit code
alone or bypass legitimate Steam dependencies.

114 actual: installed into the same isolated bundle; saved login18:59:42EDT,
real home/details and virtual A Play. New hr.exe/PID844 is tracked19:01:38,
then exits19:01:46 with2110081575 (0x7dc54a27). The module-error snapshot shows
a probe for Managed/mscorlib.dll.dll returning c0000135, not an identified fatal
import. Do not install a speculative replacement based on that probe or the
prior exit code. The direct fatal evidence is instead FEXAlloc refusing0x280000,
repeated8MiB+8KiB and16MiB allocation failures inside the9GiBFEXband, and many
arm64ec_thread_init c0000017 errors. Last sampled headroom891MiB precedes later
fragmentation; the failing scan's largest gap is8MiB. No interactive game window.
The bounded snapshot resumed correctly; exact app ended and original configs/
attributes restored. The diagnostic is useful but not a causal runtime fix.

Next same114binary variable: existing MADEIRA_CPU_COUNT=2. Pinned Wine's
init_cpu_info supports this already (no Wine/FEX edits): it changes the reported
Windows CPU count, not host scheduling or stack sizes. Hypothesis: fewer guest
workers reduce concurrent FEX reservations and V8isolate tables. Require actual
cpu-count override marker, counts/headroom, then full navigation/game/return.
Fresh launch114-cpu2-big-picture.json starts this test; result pending.

114 CPU2 actual: Native confirms reporting2processors(host6). Saved login
19:04:44EDT, real home/detail/Play. Game progresses to a visible Unity
"Failed to initialize graphics / InitializeEngineGraphics failed" dialog.
Direct logs identify d3d11.dll's native image-copy allocation0x480000 failing:
main pool was requested608MiB but safely shrank to560MiB; bump557MiB leaves
only3MiBvirgin, freelist largest512KiB. d3d11.dll returnsc0000017, rather than
being absent on disk. At this snapshot FEXlast7250used/1965freeMiB, with no
ml798 fatal. This is a different measured gate from defaultCPU FEX exhaustion.
No gameplay/return is claimed. The snapshot resumed; exact session ended and
original attrs/configs restored.

A704MiB-target config was prepared but NOTRUN: requested size is not actual
capacity, and the prior560MiBclamp must not be ignored. Source instead already
provides default-off MADEIRA_POOL_LOW_IMAGES1. It permits native image copies
up to16MiB in unused, already signed regionC, preserves4MiB for code, and uses
the same atomic cursor as FEXcode without reusing live buffers. Actual-source
small-image capacity/ownership/WoW64/concurrentcode-image and retired-code
reuse/grace/PC/poison/alias tests pass. Next same114CPU2binary trial enables
only this flag; require actual pool-low IMAGE record and successful d3d11load,
then game/menu/input/return. Fresh launch114-cpu2-lowimages-big-picture.json
is in progress. Do not report704MiB or graphics success from preparation alone.


Continuation after delayed user connection reply: at23:35EDT the exact
low-images trial PID is absent. Fresh identity guards reject both status and
fixed-key commands; no stale PID is signaled. Static native trace confirms CPU2
and ends19:25:44, with no game/d3d11/pool-low IMAGE record and no owned-table
refusal/ml798 in that retained run. Thus no graphics outcome is established;
process absence is not evidence of a crash or a successful test. Build114 remains
installed. Matching cached main/helper profiles expired00:19UTC/20:19EDT;
no valid matching renewal is present. Device CLI is connected, but CUA reports
Mac locked. One manual-Mac-unlock question is pending; no Xcode logout inference,
credential automation, signature modification or lock bypass is attempted.

The exact session is absent and static logs retained. Direct original global/
CEF byte recovery is tracked separately in cleanup114-lowimages-direct.json;
runtime original-attribute restoration is still PENDING because its diagnostic
needs a valid signed launch. Inspect that receipt; do not claim complete cleanup
from byte readbacks alone. Next after native Mac unlock: use official Xcode
provisioning renewal (the established manual re-sign route reuses granted
profiles, it cannot extend expired grants), preserve bundle/data and identical
binary where possible; run attribute restoration and confirm both original
bytes again. Then repeat the installed114CPU2+LOW_IMAGES experiment and require
actual d3d11pool copy, visible interactive game and return. No credential entry
or new Steam login should be needed for the saved prefix. Broader full64capacity,
32bithelperwindow, Bluetooth and stable game-return remain unverified.


### 115 user-requested build/install preparation

User requests the newest build on Kusch and will perform gameplay testing.
Full unsigned Xcode115 succeeds with the current experimental source. The
existing lab bundle ID is retained; final debugdylib markers for compact9table,
stack-spill, low-image fallback and module-error gating are verified. A disposable
unsigned115copy and source/binary receipt are private. No new runtime patch is
introduced in115. The prepared user-test launch uses the existing CPU2+stackspill+
LOW_IMAGES1 flags, with the previously tested113geometry; low-image graphics
and gameplay results remain unverified.

Fresh official provisioning-update attempt fails NoAccounts/missing matching
profiles; this does not establish GUI logout. Existing signing identity remains
available in login.keychain-db, but both lab profiles have expired. The only
valid device profile found is for a different app and cannot sign this bundle.
Manual re-signing cannot extend an expired Apple grant. Current Kusch network
pairing is connected. CUA reports Mac locked, and independent console metadata
confirms ScreenIsLocked=true onKuschMacMini-M6-New. One precise manual-unlock
request is pending; no account credential or lock bypass is attempted. Renew
matching profiles through official Xcode after access returns, manually sign115,
validate and install the same bundle preserving data. The profile-expired app
must then run the pending original-attribute diagnostic; original global/CEF
bytes are already verified restored. Start the prepared115experiment and leave
gameplay testing to the user.115is not signed/installed at this record.


115 follow-up, 2026-10-30: after user reported Mac unlock, fresh CUA and
active-user console metadata still report the actual M6-New session locked.
Kusch is available/paired; no lab app is running. One official Xcode retry
fails: main profile absent, renewed helper profile covers iPad only, not Kusch.
NoAccounts remains insufficient to claim GUI logout. The unsigned115copy and
its final debugdylib hash remain intact. No installation, renewed iPhone grant,
attribute-restoration run or runtime validation occurred; original data/config
byte recovery is preserved. Continue normal Xcode provisioning when this
active console is accessible, then sign/install/recover and handoff to user.


115 signing automation: added tools/refresh-development-signing.py and
docs/DEVELOPMENT_SIGNING.md. It validates exact main/helper bundle IDs, team,
device, certificate, expiry and debugging grant; if needed it requests renewal
through official Xcode once, signs a disposable copy, verifies deep strict
signatures, and optionally upgrades an idle existing app with version readback.
No app launch, scheduler, credentials, lock bypass or keychain changes. Synthetic
profile/isolation/active-app/refusal and read-only main-path tests pass. Actual
read-only cached-profile check exits2 (missing/invalid). Actual renewal, signing
and installation remain unverified; this does not fix or bypass current Xcode
account/session availability. No runtime patch or new gameplay result.


115 signing gate resolved, 2026-10-30: Xcode GUI is accessible and the existing
account/Personal Team is present; no user credential entry was requested.
Background xcodebuild still reports NoAccounts after GUI resource sync, so
this is not proof of account logout. Normal GUI automatic signing with the
exact existing main/helper IDs and Kusch selected generates both profiles,
valid through Nov6 and covering Kusch/original certificate. Temporary project
signing edits were backed up and restored byte-exact after closing the project.
The automation then signs the prepared115 resource-complete copy using cached
profiles. Deep strict signature, get-task-allow, exact IDs/device/expiry and
linked markers pass; signed debug Mach-O TEXT section bytes equal the verified
unsigned build (load-command signature metadata is excluded). No Extended VA
grant is assumed. No new runtime patch or gameplay claim.

Before installation, Kusch disconnected: configuration read attempts return
CoreDevice4016, and DeviceHub independently shows CurrentlyUnavailable. No
install/launch/attribute recovery occurred. One remote-reconnection request is
pending; do not repeat signing/account requests. Prepared signed115 is private.
After reconnection revalidate current app/process and original configuration
bytes, upgrade same bundle, run pending attribute restoration/readbacks, then
start prepared115 user-test flags and leave gameplay to the user.


115 actual installation/user handoff, 2026-10-30: after user restored remote
connection, fresh metadata confirms installed114 was idle and original global/
CEF bytes matched before upgrade. Same-bundle115 installation succeeds; actual
version readback confirms115. Fresh original-attribute recovery diagnostic passes
with exit0, then both original configuration readbacks match exactly. Thus the
previous pending attribute-cleanup gate is now resolved. No uninstall or auth/
game/save replacement occurred.

Prepared full64 compact9table/CPU2/stack-spill/low-image flags launch115. Exact
native identity remains live at bounded check. Current Steam log records fresh
saved-login Success/OK at12:56:05EDT after launch (timestamp checked against
launch-receipt write time). No agent credentials entered. Live native-log copy
is unavailable, which is not proof of no faults or process death. No suspend,
restart, controller actions or game launch is performed after handoff startup;
user explicitly requests to test gameplay. No visual Big Picture, graphics fix,
gameplay, Bluetooth, game-return or long-term capacity success is claimed.
Next: user reports current UI/game/input behavior; preserve live session and
revalidate identity before actions. All research stays local/uncommitted.


115 user follow-up: user reports a Steam service error popup. The current
dialog body/buttons are not independently captured. A read-only process query
fails CoreDevice4016 before log collection; this does not establish a crash or
current native-process identity. Preserve the session and do not issue stale
commands or invent a service root cause. The earlier service prompt offered
Install Service/Cancel and user cancellation allowed progress then; apply that
manual step only if the present dialog matches. Obtain exact text if different.


115 blue-screen investigation after user reconnection: both current native log
and previous rotated log are collected without pause/restart. Original controlled
full64 session uses wine-steam64/CPU2, saved login12:56:05, and retains a visible
Steam Service Error window in the captured window tree. No identified FEXAlloc
fatal/owned-table refusal appears in that trace; this does not prove no other
fault or identify why the native process later relaunched.

The current process is a different app instance, started13:06 with paired JIT
explicitly enabled13:08:09. It uses Documents/wine and C:\Steam32BundleLab, not
the isolated full64 prefix/profile. Source uses explicit launch arguments for
usesSteam64/runtimePrefix; the experimental profile is not retained on normal
reopening. This is an actual launch-path mismatch, not evidence that signing or
JIT failed. Repeated mprotect warnings in that different session are not a sole
causal diagnosis and do not justify a protection workaround.

Both traces are retained privately. After fresh current-identity validation,
only the stuck observed main was ended; full original attributes/config bytes
were recovered and verified. Existing115 is relaunched with unchanged controlled
full64 flags; fresh saved login13:19:46EDT is verified after launch. Current live
native-copy failure/0bytes leaves UI state unknown, not absent. No automatic
window/key action was sent. User screen-state question pending. No new runtime
patch, browser/game success or long-term GO. Ordinary reopening still selects
the legacy path; a persistent isolated launch profile remains unimplemented.


### 116: distinguish helper notice, game image backing and translator exhaustion

User confirms115Big Picture is visible. Screenshot shows Hot Roads detail page
with native32-bit-child reservation notice. Actual private native/gameprocess
logs distinguish two failures: x86launcher.exe is refused its4GiB guest window
(621MiB free versus required window plus headroom), while AMD64hr.exe DOES
launch. Its5.3MiB Mono DLL image copy fails STATUS_NO_MEMORY; the game creates
“Failed to load mono.” The generic dll-missing log label does not establish a
missing file. Preserve reservation guards and installed game/auth/saves.

The margin256/pool608trial is rejected as an isolated comparison: ASLR placed
main608below the executable window, so no regionC existed and FEX failed. Exact
failed session ended; original attributes/global/CEF bytes recovery PASS. A
separate own-PE test with existing pool560/margin256 gets realC336MiB and
original-attribute restore exit0. It does not establish game success.

116adds only an explicit lab-only installed-Hot-Roads diagnostic sending fixed
steam://run/1819280 through genuine running Steam, plus accurate “Steam runtime
notice” wording for failed32-bit children. No allocator/FEX/Valve/game patch.
Host gates/URI/file/failure tests ASan/UBSan and existing input/startup/readiness/
launcher checks pass. AMD64 helper cross-compile matches final bundled bytes.
Full Xcode116, final helper/debugdylib markers, deep strict signing, same-bundle
install and installed version readback pass. This is not game validation.

Actual116fresh saved login succeeds13:52:51EDT. Bounded serial native snapshot
and exact-identity SIGCONT confirm mainRX0x148000000/560MiB, regionC352MiB and
258MiB left for low images. After fixed Steam URI, Mono and D3D11 load; actual
Unity2017.4.21f1 log creates Direct3D11(level11.1) on Apple A17 Pro GPU. This
clears those specific initialization gates in this trial. Game exits after a
later translator allocation fails; no playable game/controller/return claim.

Failure-time live census: nine-GiB arena, free0x22e66000 bytes in463holes, no
overlap, largest gap8MiB, largest16MiB-aligned gap0x410000, request16MiB. This
is address fragmentation/capacity, not a claim of physical RAM exhaustion.
Associated earlier JetsamEvent lists Madeira but lacks a termination reason
for it, so it does not prove a jetsam kill. Native116remains alive at fresh
query; user reports an error dialog. Current serial snapshot/resume confirmed.

Single next discriminator: reuse installed116with previously native/Windows-
validated seven-table/9.5GiB geometry, retain pool560/margin256/CPU2/LOW_IMAGES.
Recover original attributes/config bytes and end exact prior lifetime before
launch; all recovery checks pass. Require actual realC and matching fresh
identity before the fixed game URI. This gives FEX512MiB more but fewer V8
tables; it is a finite tradeoff, not a long-term solution or GO. Exact evidence
paths/hashes and revision are in IDECK_CEF64_SOURCE_EVIDENCE.json. Local changes
remain uncommitted under the user's time-window instruction.


116seven-table/9.5GiB follow-up: actual startup retains main560/C352/margin258;
fresh saved login14:06:14EDT. Fixed game request starts PID744; exits14:07:13
c0000135. Bounded serial native snapshot/resume identifies earlier IMM32/DNSAPI/
IPHLPAPI executable-copy STATUS_NO_MEMORY, then propagated dependency failure
for UnityPlayer. Both main and regionC image budget are depleted. No FEXAlloc
fatal in this trace; no game success, and larger translator capacity alone is
insufficient. Exact session/config recovery passes before next comparison.
Next changes only existing main-pool target560to592MiB, retaining seven tables/
9.5GiB/margin256/CPU2/LOW_IMAGES. Require actual above-window main placement
and realC before game; requested pool is not capacity proof. No source/binary
patch in this comparison and no long-term GO.


116main592comparison: actual main592MiB/C336MiB/9.5GiB; fresh saved login
14:10:08EDT. Game PID748 starts14:11:08, Mono/D3D11load again, but complete
retained native trace records a16MiB allocation failure with0x2c358000free,
505holes/largest0x7fe000/no overlap, then FEXAlloc0x2800fatal. Fresh query
finds exact native instance absent; no stale suspend/signal occurs. No gameplay
success. Increasing finite capacity did not cure fragmentation.

117tests one placement hypothesis: triple-gated full64/source-layout FEX_PACK1
places small native translator requests top-down and>=16MiB bottom-up ONLY
for the exact whole owned arena and an unhinted placement. Preserve sizes,
alignment, protections, backing, owner/release rules and reservation guards.
Ordinary/foreign/narrow/invalid-gate paths retain original direction. No FEX
source, Valve or game binary patch. Actual policy plus Wine's actual gap search
under ASan/UBSan shows identical footprint but old layout strands gaps while
separated placement serves another aligned16MiB request. It is an isolated
geometry test, not a replay or device fix claim. Relevant owner/layout/census/
low-image/reclaim/retirement/fixed-guard regressions pass. All37nativeunits
compile after reusing the primary checkout's generated Wine headers read-only;
initial direct script lacked those headers, its archive was restored before
corrected private build. Xcode117in progress. Next require final Mach-O marker,
strict signing and actual device direction/layout/game results. No GO from host
tests. All changes remain local on experiment/steam64-cef64.


117actual first launch: signed marker and16real full-arena policy-direction
records prove the new branch ran. However ASLR reduces the actual above-window
hole to557MiB: request592shrinks to560in the lower562MiB hole, leaving noC.
Bounded snapshot/resume verified; game request is refused by experimental gate.
This cannot establish a packing fix or same-capacity comparison. Exact session
and temporary settings recovered. Next uses existing main544/margin192to fit
the measured hole and retain signed code/image capacity. Because geometry also
changes, any subsequent success is not sole proof of packing causality.


118pool-selection discriminator: the next117lifetime has above-window holes
285/276/297MiB versus611MiB below. Requested544again lands below; no realC.
No game is requested, so neither117launch establishes a game packing result.
Source confirms pair selection only runs when singleFit<requested and only
accepts A+B larger than the below-window single pool. It ignores capacity inC
that the below placement eliminates.

118adds KEEP_LOW_POOL1 triple-gated to the full64session/source-layout. It
permits the existing disjoint upper A/B selection even when the below single
fits. Existing A>=256MiB/B>=64MiB, requested budget, window exclusion, native
mapping/protection/fallback checks stay intact. No FEX/Valve/game edits. Actual
Swift gate and selection loop host test uses measured117holes and passes
ordinary/disabled/budget/bounds/minimum/window/single-above cases. Existing
pool-split/low/startup-budget regressions pass. Full Xcode118, final linked
KEEP_LOW plus native PACK markers and deep strict signing pass. Not yet
installed: interrupted prior-session recovery must complete first; fresh paired
tunnel is connected. Next same isolated bundle upgrade, existing pool704/mid1/
margin192with both opt-ins; actual A/B/M/C then fixed Steam game request.
Geometry also changes: do not claim packing-only causality or long-term GO.


118upgrade follow-up: repeated remote process-service calls interrupted prior
cleanup. A fresh successful query established availability; the private runner
now reuses a single fresh identity snapshot for absence/idle checks rather than
three redundant queries, preserving all identity guards and saving any error
privately. Original attributes/config readbacks then pass. Signed118upgrade
and actual version118readback pass. Controlled launch in progress with existing
saved full64prefix; no game/UI success claimed yet.


118actual startup: fresh Steam Success/OK14:31:22EDT; serial native snapshot
and exact SIGCONT verified. ThisASLRmapalreadyhas a larger upper hole: actual
main624MiB at0x148000000 plusC416MiB, with206MiB left for low images. No
FEXfatal in snapshot;16actual packing-direction records. KEEP_LOW override
is not exercised because the upper hole already wins; its device fallback
behavior remains unverified despite linked marker/host failed-geometry tests.
Only after these exact-lifetime gates, one fixed Steam game URI is requested.
Game outcome pending; preserve current session, no gameplay/long-termGO yet.


118first game result: Steam tracks Hot Roads PID764from14:32:56EDT. Complete
serial native snapshot/resume confirms Fatal error/Failed to load mono, with
mono.dll0x549000image reservation STATUS_NO_MEMORY. No FEXAlloc fatal or
signed-pool capacity refusal in captured trace; latest FEX sample7314MiBused,
2413MiBfree,1728MiBmaxgap. Mono initialization blocks the later workload, so
this does not prove packing solves the earlier game-stage exhaustion. The
Unity output-log copy fails because initialization has not created it.
Next changes ONLY current118pool704profile's low-image margin192to256, the
allowance under which Mono/D3D11loaded in116. Preserve packing/CPU/source/
table/strict guards, recover exact prior lifetime/settings, and verify actual
regionC capacity before fixed game request. Visual-state question remains
pending; latest artifact-backed failure supersedes assumed game progress.


118margin256first trial is invalid: JIT helper starts but attach times out90s;
Steam never starts. Startup snapshot occurred before confirmed JIT/Steam and
may interfere; no causal claim. No game was requested. Recorded old helper
is already absent on fresh identity check; no unrelated helper signaled.
Original exact native instance/settings recovery and fresh own-PE JIT restore
pass. Next uses unique clean launch receipt and an explicit fresh-SteamSuccess
after-launch/same-identity ready receipt before startup snapshot; do not reuse
historical login lines or suspend while the JIT helper is enabling.


118clean margin256 startup: fresh-SteamSuccess/same-identity readiness gate
passes before snapshot. Actual native A624+B80=704MiB usable,23MiB native
gap excluded; C224MiB for total928MiB. C's local remainder is4MiB, but the
separate untouched lower363MiB run satisfies configured256MiB margin (actual
log explicitly says held by lower run); do not confuse C remainder with total
low-image allowance. All signed regions are disjoint, below0x180000000, and
C ends below the executable window. Native packing branch runs, no FEXfatal
in startup snapshot, exact SIGCONT verified. Smaller C is supported by existing
fallbacks; trial gate now checks actual combined capacity and separate retained
low run rather than assuming every C must be>=320MiB. Production minimum,
4MiB code reserve, ownership/protection/overlap guards remain unchanged.
ASLR changes geometry too, so no packing-only causality claim. One fixed game
request follows; outcome pending. Keep current exact session for user test.


118clean margin256game observation: Steam starts/tracks PID792at14:48:10EDT.
Fresh native trace loads UnityPlayer/Mono/D3D11; actual new Unity output
initializes2017.4.21f1/Direct3D11.0level11.1 onAppleA17Pro. Complete5891730byte
serial snapshot and exact SIGCONT are verified. No FEXAlloc fatal, Mono
error or signed-pool refusal appears in this capture. This is initialization
progress, not a responsive menu/gameplay claim.

A16MiB native constrained allocation still fails at peak:9.5GiB arena with
0x299d000freevirtualbytes/481holes/maxalignedgap0x3c0000/no overlap. Later
headroom recovers to809MiBfree/128MiBmaxgap; no captured FEXAlloc fatal. Do
not equate this recoverable/uncategorized allocation failure with process
death, or claim total capacity solved. Geometry and signed capacity differ
from prior trials, so no packing-only causal success. Current session remains
open/resumed; UI/controller response question pending. No further game input
or restart before a fresh result. If unusable, prepare the existing CPU-count1
versus2 single-parameter test to reduce worker/thread heap demand. Bluetooth,
game-return, stable long browsing and universal compatibility remain unverified.
No long-term GO. Source remains local/uncommitted under NYtime-window rule.


118handoff: final fresh exact native identity check passes; latest Steam
gameprocess log still tracks PID792without recorded exit. Process status is
not visual/interactive proof. Current session is resumed and left open; UI
question pending. CPU1 discriminator runner is prepared privately only and
has NOT run. Await current screen/controller result before interrupting this
test. Verified signing/install/host checks remain separate from game outcome.


### 118dialog follow-up: actual UI distinguished, CPU1 comparison

User reports an error dialog. Existing authorized macOS screen-capture and
input permissions plus Device Hub Kusch window provide direct physical-phone
view without a lock/credential/permission bypass. Actual screenshot is the
native Steam runtime notice for guest-window-reserve c0000017; not Mono/
Steam Service Error. One known-OK click dismisses it. Actual Steam Game Info
click changes Big Picture pane: genuine authenticated UI responds. Resume
click does not bring game forward. Existing gated game-confirm reports
no-game, meaning no visible installed-game window found (not all hidden
windows disproven). No arbitrary keyboard input is sent by that negative path.

Current exact native identity/Steam game PID792still tracked. Complete38MB
serial native snapshot and exact SIGCONT pass. No FEXAlloc fatal/Mono error/
signed-pool refusal in that capture; peak16MiB allocation refusal remains,
later headroom836MiBfree. Native alert is not evidence of app/game death.
Single next test uses existing CPU_COUNT1 instead2 to reduce CPU-sized worker/
thread heap demand; no FEX/source patch or new build. Source accepts1..<64;
existing mask1affinity conversion ASan/UBSan passes. Exact previous session/
settings recovery precedes fresh CPU1startup. Require fresh Steam login and
actual code/image regions, then one fixed Steam game launch; no success claim
from startup. All screenshots/raw logs remain private; hashes only published.


CPU1gate: exact previous native session/original attributes/config readbacks
recovery PASS. CPU1config files staged and read back exactly; same installed
signed118, no rebuild or account/profile change. iOS refuses the launch with
CoreDevice10002/FBS Locked. Thus CPU1has NOT executed and no device result
exists for it. One manual Kusch-unlock request pending; no lock bypass,
repeated launches/installs or credential action. Experimental config remains
staged in the isolated lab; baseline/working app untouched. Resume by verifying
these bytes and launching only after native unlock; do not overwrite successful
old launch receipts or treat error JSON as a process receipt.


Final read-only lock-state confirms passcodeRequired=true and
unlockedSinceBoot=true. No repeated launch/install/unlock attempt. CPU1
launch-only retry is prepared, not run; it retains the staged readbacks, exact
idle guard and unique receipt without redundant uploads. Native app globally
disables its idle timer while open; long staging after recovery stops the app
can leave Home exposed long enough to auto-lock. Avoid that delay on resume.
Current previous game/native session has been ended by verified recovery; do
not reuse its PID. Manual phone-unlock question pending. No new code build or
credential action is required. No runtime fix/long-term success claim.


### 119: actual Unity graphics failure is DLL address placement

After user unlock, existing118CPU1launch records fresh Success/OK17:07:46.
Actual retained native trace confirms reporting1processor(host6), Mono loads,
and Steam tracks user-driven HotRoads launch17:08:21. Screenshot explicitly
shows Failed to initialize player / graphics / InitializeEngineGraphics failed.
Unity log says d3d11failed-load80029c4a; native names actual d3d11.dll size
0x477000and STATUS_NO_MEMORY on two searches constrained below7100000000.
This is mapping failure of a present DLL, not evidence DirectX needs reinstall.
No FEXAlloc fatal/signed-pool refusal in captured run. Fresh process query
sees no app instance; process absence does not itself name a termination cause.

Code review: map_image_view inserts the furniture ceiling as a hard image
bound. Generic stack/kernel allocations may spill, and actual CPU areas
already use the separate7160000000region. New IMAGE_SPILL1opt-in attempts one
ordinary mapper call only AFTER original image placement fails NO_MEMORY,
for a dynamically relocated64-bitDLL<=64MiB in an installed Steam-game owner.
The non-compact source slots must match; all17native reservations are checked
for overlap with exact gap7160000000..717fff0000. Existing kernel/Wine view
collision checks, mapping protections, relocations, signed copy and owner
release rules retained. No explicit caller bounds are widened; CEF/Steam/
ordinary/WoW32/nonrelocatable/compact/foreign/overflow/unknown extra holds
refuse. Failure propagates original NO_MEMORY. No FEX/Valve/game modification.

Production policy/native-integration ASan/UBSan passes, including all17lease
conflicts, owner/path/flags/machine/bounds/error checks. Existing owner/transfer/
fixedguard/FEXpack/poolplan/low-image/nocopy regressions pass. All37native
units compile with prior generated primary headers read-only. FullXcode119
in progress; no installation or device fix claim. Next final linked marker/
strict sign, exact current lifecycle/config recovery, samebundle119upgrade,
CPU1profile plus ONLY new flag, fresh readiness/capacity then fixed game URI.
Actual fallback log, DLL load and physical UI/gameplay are separate gates.


119build/sign: fullXcodePASS, actual final signed debugdylib IMAGE_SPILL
flag/action markers and deep strict signature PASS using existing matching
profiles; no Xcode account/login operation. Previous config/attrs recovery
passes. A newly opened118session is JIT-enabled/pre-Steam; idle guard refuses
upgrade. Exact main22206/own helper22207identified; main termination remains
held while its debugger attached. Stop only that exact helper to allow pending
termination; do not overwrite/install into an active session or infer a game
crash. No game/user data changed, and no fallback runtime success claimed yet.


119actual upgrade: fresh query eventually confirms old app/helper both absent.
Idle/restore/signature guards pass; samebundle119install and actualversion
readback pass. Controlled full64CPU1profile plus IMAGE_SPILL1launch accepted.
No uninstall/login/cache/game/save replacement. Fresh Steam readiness and
game fallback outcome pending; never claim fix from accepted launch/build.


119diagnostic correction: after startup snapshot, native log stayed byte-identical
and helperACKremained ready; the requested game had not executed. Accepted
SIGCONT/resume receipts alone do NOT prove continued execution. CoreDevice
resume's own JSON also recordsSIGCONT; the initial explanation that it was a
different task-resume operation was premature and is retracted. Foregrounding
with --activate returns exact SAME nativePID22298/executable and the original
pending game request then acknowledges. No duplicate game command or runtime
profile replacement. Need actual post-snapshot log/ACK progress on future
experiments; prior118actualDLLfailure evidence remains valid.

Immediately after actual gameACK, native/process/Unity collection times out.
No fallback/DLL/game outcome established. Preserve current session and inspect
connectivity once; timeout is not crash/death/fix evidence. Raw artifacts/hashes
recorded privately. Current119long-term/runtime success remains unverified.


119external gate: current list-devices confirms paired but tunnel unavailable.
One remote-reconnection/current-screen question pending; do not reinstall,
restart, reauthenticate or target stale PIDs. Keep current119app/session/data.
Phone-side IMAGE_SPILL/D3D11/game success remains unverified. Independent
minimal experiments/cef64/d3d11-probe.c dynamically loads d3d11then calls
D3D11CreateDevice, emitting categorical Win32/HRESULT/feature-level results
to a fixed file. AMD64Werror/PE/runtime-load checks pass locally; no device
copy/run/render/input claim.

Future private bounded snapshots now request foreground of the same existing
instance afterSIGCONT, verify unchangedPID/executable, and require later
log/ACK advancement for runtime claims. Refused foreground (including lock)
is not a resume success; no lock bypass. The operational change is separate
from the119DLLmapping patch. Raw logs/screens/PEs stay outside Git.


119reconnection: user restored the remote channel. Fresh process listing shows
no lab/helper instance; do not signal oldPID22298 or infer its termination cause.
Saved isolated HotRoads output has advanced to Direct3D11level11.1 / Apple A17Pro
GPU / Begin MonoManager ReloadAssembly, and Steam records game launch17:26:11.
This passes the prior graphics-init failure point, but is not gameplay proof.
Native log has since rotated through later ordinary119starts18:15/20:19;
20:19uses Documents/wine Steam32BundleLab, not the controlled full64profile.
Thus no original119fallback-address line or native exit cause is recoverable
from those files. Preserve all copies privately with hashes. Repeat the SAME
installed119profile under a unique receipt, fresh login/layout gates and one
fixed game URI; no rebuild/reinstall/authentication. Mac window capture refuses
known lock; CLI diagnostics continue without bypass. No Git outside time window.


### 119game DLL fallback verified; post-game CEF capacity failure

Repeat actual119full64CPU1starts with signed713MiB/C352/native-margin266MiB,
fresh saved login and exact native identity. Unlike first119ASLRgeometry, B
placement succeeds. Actual native trace shows d3d11.dll originalc0000017 then
IMAGE_SPILLsuccess0x717d4a0000, signed code copy0x16b5a7000 and module load.
Unity reaches D3D11level11.1/A17ProGPU, Mono reload, input/touch and scene load.
User subsequently confirms game entered; supplied screenshot is32-bit child
guest-window warning, distinct from prior Unity graphics-init error. Keep
reservation guards; do not claim every32-bit child can start.

Steam tracks hr.exe20:28:35 and normal exit0 at20:30:01. Helper's old
returned-to-steam ACK means URI sent, not UI restored. User reports return
freeze. Same nativePID alive; CEF at20:30:36EDT explicitly reports eighth
512MiBExternalEntityTable subspaceOOM. Native seventhslot14adopted, partial
release retained, next512MiBrequest refused. Fixed menu request then reports
steam-window-unavailable. No assertion suppression/unsafe lease recycling.

### 120: prefer existing Big Picture on game return

Observed existing exit helper always spawns Steam with BigPictureURI. Hypothesis:
restoring an already-open verified BigPicture window can avoid extra client/UI
allocation. It is not yet proven that this is the sole cause of tableOOM.
Minimal helper change restores/focuses an exact-title window validated by
existing Steam process/visibility check. Focus denial does not spawn. Absent
window permits one fixedURI, and ACK now distinguishes focus vs request without
claiming responsiveness. Native/VA/CEF/FEX/game files unchanged. Production
policy ASan/UBSan, fixedgame/input and Swift launcher host checks PASS. Xcode120
in progress; not signed/installed/device-tested. Next same profile/game/exit,
no new capacity option; require actual input/navigation and no duplicate client
spawn before any success claim. Main/submodules untouched, no Git outside window.

120build/sign: fullXcodePASS, bundled helper Werror, actual new return PE
markers and retained IMAGE_SPILL final debug dylib verified; deep strict signing
PASS with cached matching profiles. Current119game exit0 permits ending exact
frozen session. Original config/attributes restore PASS/readbacks; idle upgrade
guard PASS, installation in progress. No device return-success claim.

120actual installed/signature/versionPASS, fresh saved-login20:37:35. Actual
ASLRlayout signedspan715/C304/margin266 differs from119C352: original C352
comparison gate failed. Recorded separate capacity variant; no native guard
changed. One game request20:39:13 accepted, guest760 exits1715561600 at20:39:17.
Native D3D11maps, but FEX16MiB reservation fails with free0x2139000 and largest
alignedgap0x1a0000 across1177Wineviews; later FEXAlloc0x2000fatal. No120return
test reached. Do not attribute FEX failure solely to C304; no false game-success
claim or stale Unity-output reuse. Exact-session/config recovery in progress.
One clean same-build repeat will require original C352code-budget gate before
game; no repeated layout tuning or extra capacity feature.


120clean repeat: C352/span722/margin258 meets prior budget gate but ASLR differs.
UnityD3D11/A17GPU, Mono0.698s/input and owned game window confirmed; Steam guest752
starts20:43:16 and exits0 at20:44:38. New ACKsteam-focus-pending: existingBPM found
but not focused. Retained trace has no Steam spawn after exit, no new owned-table
refusal/FEXAllocfatal; CEF has no new tableOOM after prior11920:30:36. This is
progress against redundant launch, not responsive return proof. Later23:30native
instance absent; cause unknown, preserved logs before any restart. DeviceHub
nowunlocked but selectedanotheriPad; capturedonlydevicepicker/sidebar, selected
Kusch, then confirmed phone currentlyshowsCodex (not a live Steam screen).

###121: distinguish responsive-window focus denial from a browser hang

Wine server queue.c can reject older caller input via STATUS_ACCESS_DENIED;
actual120Win32error not captured. New return-only helper performs bounded500ms
WM_NULL probe, queued activation check and numeric diagnostic file. Only after
ERROR_ACCESS_DENIED, responsive verified target and Steam/game foreground owner
may it temporarily join input queues and retry once, immediately detach. No
foreground-lock settings, unrelated window or credentials touched. Hung/existing
window never spawns Steam. Actual foreground match required, not API acceptance.
Production policyASan/UBSan and return/game/input regressionsPASS. FullXcode121
inprogress; device resultpending. No FEX/Valve/nativeVA changes or GO claim.

121actual upgrade/versionPASS; fresh saved login and actualKusch screenshot
genuineBPMhome/Steam menu after fixedshortcut. Actualspan722/C336/margin258,
CPU1/seven-table9.5GiB unchanged. Native before game request adopts seventh
table14 then refuses next512MiB; later SteamURI ACK only creates IPC client,
gameprocess has no new game, owned-window command no-game. CopiedUnity0.698s
output belongs previous120 (stale), never count it as121success. No121return
test reached. Actual extra-menu sequence exceeds finite table capacity before
game; no sole cause claim for menu implementation. Exact recovery inprogress;
one same-build directgame sequence with no initialmenu/back, matching earlier
119/120success sequence. No new capacity flags or unsafe reuse.

121direct-game repeat: savedloginPASS but actualA544/C288/margin260, B lands
0x11eee0000 instead of computedupper0x16b4ec000 and is released. Original
capacity gate refuses game. No121game/return claim. Existing B code DOES
plug lowerholes; failed plug status absent, so do not call missing plugs
the root cause. New exact-session config recovery inprogress.

###122: exact owned second pool, isolated discriminator

Inspected actual madeira-jit.js: CMD1 can prepare non-null owned address without
first-fit _M allocation. ExplicitEXACT_POOL_B1+SESSION1+SOURCE_LAYOUT1 now
claims only measured B interval with vm_allocateflags0(NOoverwrite), checks
exact owned result, prepares it through existing debugger, then observes full
RX/non-Wcoverage. Failure releases only own range, no retries/foreign free/
protection changes. Original span/hole/alias checks retained. Host actualSwift
policy+platformmocksPASS gates/collisions/rollback/fullRX/partial/gap/RWX/
overflow and pair-selection regression. FullXcode122pending; no device claim.
This removes a first-fit dependency if verified, not V8capacity or TXM proof.

122protocol refinement before signing: matching private ScriptRunner source
shows debugger blessing writes one byte/page and does not set current RX.
The new owned range therefore has one checked initial RX transition AFTER
blessing, then complete RX/non-Wreadback; failure releases only own new range.
No faulting CEF pages or protections are changed, no retry. Host rejection
test includes refused initial protection; passes. Earlier unsigned122not
signed/installed, final source rebuilt separately; do not confuse MachO hashes.

122actual: exact-B owned range does NOT pass completeRX gate, released without
retry. Individual failing subcheck not logged, no kernel-only attribution.
RemainingA624/C352/margin266 permits separate directgame trial; savedloginPASS.
Request ACK read staysready, so no duplicate request; actual Steam guest752
23:53:55 and fresh UnityMono0.912s/D3D11A17GPU/input/touch establish real launch.
Later FEX16MiB allocation fails:1153views,totalfree0x41e1000,largest0xdc0000,
zero overlap. NativeFEX IREmitter::ResetWorkingList RVAfe770 writes0x800010
withx8=0x800000 and terminates after2000identicalredeliveries. This is NOT a
new successful return, CEFtable or missing-DirectX diagnosis. See
docs/CEF64_IR_ALLOCATION_FAILURE.md for exact symbols/source and local repro.

Local ASan/UBSan read-only diagnostic compiles unchanged pinned dual allocator
classes; NULL16MiB backing becomesList0x800000 and nodefield0x800010, without
performing invalidwrite. Real bundlePE faultinstruction matchesdevice; linked
prefixfile hash readback refused, so no independentdeviceSHAclaim. FEX source
remains clean. This reproduces unchecked allocation failure, not all growth
or a leak. Earlier121directSteamlog later showsgame23:42:30exit1; initiator
unknown, agent had issuednogameaftercapacitygate. Correct prior whole-session
no-game wording accordingly. Current122temporaryconfig/attribute recovery
inprogress; don't target stale native PID. No long-termGO.

122recovery finalPASS: original reporter attributes restored by fresh own PE
exit0, original global/CEFbytes readback exact, exact sessions absent. No
accounts/games/saves changed. Added read-only local IR failure reproducer and
standalone evidence doc. Source-level FEX experiment requires resolving earlier
no-FEX-edit/CONTRIBUTING restriction; explicit user scope question pending.
No FEX source modified; no success or finalGO claim.


### 2026-10-31: authorized private FEX IR experiment / Build 123

The user explicitly authorized independent local FEX IR-buffer and failure
handling experiments, with no upstream submission. This supersedes the prior
pending scope question for this private test only. Original FEX and Wine
submodules and the working mainline remain unchanged. The detached private
FEX copy is pinned to f59cab95659e8add0c88f0c76ec1cf483c536dbf with all remotes
removed; no modified FEX source/binary is published here. iDeck diagnostic
revision is 6cd461182e6586f15b70278b433b3766e656025d plus the existing local
experimental runtime changes.

Observed failure: Build 122 exhausted contiguous 16 MiB IR backing and then
wrote through NULL-derived List=0x800000. Hypothesis: reducing each paired IR
buffer to 4 MiB can reduce address demand without that invalid write, provided
translation size is also bounded. The private experiment requires three exact
startup gates, limits MAXINST to 256, and adds release-mode NULL/overflow/bounds
rejection before IR node access. Rejection currently aborts deliberately; it
is not graceful recovery or a proof of sufficient capacity. Ordinary defaults
remain 8 MiB per half. The rejected exact-secondary-pool flag is disabled.

Actual host ASan/UBSan tests passed gates, capacity, exact boundaries, startup
cache and controlled NULL/overflow rejection. The private ARM64EC DLL compiled
and contains the intended markers. Build 123 overlays this PE onto complete
native Build 122 and changes bundle versions; it is not a fresh full Xcode
123 build. Deep-strict signing and same-bundle physical Kusch upgrade/version
verification passed with existing valid profiles.

Discriminator: an own AMD64 test ran four waves of four threads on Kusch, all
16 thread exits were zero, all outputs matched an independent Python 64-bit
integer oracle, and the own test plus enclosing batch exited zero. The actual
native log confirms MAXINST=256 and FEXMem_OpDispatcher size=0x400000. This
proves the intended experiment executes, not Steam/game compatibility. An
initial live native-log copy failed CoreDevice7000/POSIX60; after stopping only
the completed diagnostic identity the stable log was collected. The own probe
was restored with exact byte readback, followed by successful original reporter
attribute/config restoration. Auth/games/saves were preserved.

Private evidence: ../.madeira-install/steam64-current/ir123-stress-evidence.json
(result SHA256 b91687db67ae2fc9a9c30ab24232ef8516e6a1cdc246e29770e2c6700bd2a2c3;
native SHA256 123b38b11132b5268701ef5ec0bd5e3a2e0a2d77c31924141f2ec05cc85289f2).
Next: full saved-login Steam, game launch, normal game exit and responsive
return under the same private IR mode. No new gameplay/return or long-term GO
claim follows from the standalone test.


123 full lifecycle result: saved login Success00:24:49 EDT, tracked game
start00:25:46, fresh UnityD3D11level11.1/A17Pro/Mono0.915/input/touch. Verified
game-window Enter ACK; normal exit0 recorded00:27:19. Post-exit native snapshot
has89 logged4MiBOpDispatcher allocations and no IR reject/FEX allocation
fatal/exception-redelivery termination. This count is not a live allocation
census. Actual JIT A544+B160=704MiB, C304MiB;723MiB reported pool size is the
address span INCLUDING an excluded19MiBgap, not signed capacity. ASLR budgets
differ from122, so the successful lifecycle does not establish IR-size change
as the sole cause.

Return discriminator: bounded WM_NULL passes (responsive1), foreground fails
with error5, foregroundWinPID32. Startup trace identifies PID32 as system
explorer. No new Steam client is spawned. This is a measured activation
failure, not proof CEF is dead. Build124's own helper permits the one existing
access-denied handoff only when the foreground is GetShellWindow or
GetDesktopWindow AND exact system explorer; arbitrary explorer windows and
non-system paths remain excluded. Immediate detach/actual foreground checks
remain. Host ASan/UBSan positive and exclusion tests plus game-return/game-URI
and launcher regressions pass. An initial Swift test needed its module cache
redirected to private temporary storage; rerun passed.

124 is another PE-only overlay on native122, retaining identical private FEX
PE. Deep signing/install/version passed. First124 saved login passed, but
actualA592/noB/C240/margin268 was below the established game-test budget.
No game request was issued in that run; original temporary settings restored
before one controlled same-build repeat. Focus correction is not yet
device-validated. No long-termGO or production release of private FEX changes.


124 controlled repeat met capacity A560+B144=704MiB (span716 includes12MiB
excluded gap), C304/margin264. Fresh saved login00:32:52, game74000:33:37,
fresh UnityD3D11/A17/Mono1.200/input+touch and helper Enter ACK. Normal game
exit0 at00:34:43. No IR rejection/original FEX allocation fatal/redelivery in
post-return native snapshot. Own helper copied from actual prefix hashes
exactly to compiled124PE (9731e66fdf98d6d50df59ad22da841898de623704333b2b9a90a15d54fbdcdb9).
Return remains responsive1/error5, foregroundPID32, shell0/desktop0, attached0.
Thus124 registered-handle extension did NOT solve real focus. Do not mark it
validated from host tests. Read-only pinned Wine explorer code creates named
steamui with built-in class32769 but deliberately only registers ShellWindow
for Default desktop. Next125 is a separate exact system-explorer + class32769
discriminator, with numeric foreground class atom diagnostics and all previous
bounds/exclusions. Host ASan/UBSan tests pass; no device125 result yet.


125 signed/installed as own-helper-only overlay with identical private FEX
PE and native122. Fresh saved login passed. Native startup measured A592+B112
=704MiB, C272, margin268, span719 with15MiB excluded gap. A bounded game test
was allowed with executable total976MiB, equal to119/122 totals but repartitioned
from C352/AB624. This is a new capacity test, not proof partitions are generally
equivalent. Native bounds/owned reservations were unchanged. First124 low
budget total832 remained refused. Current125 game logs fresh Mono1.226s,
D3D11/A17/input+touch; helper game Enter ACK; normal-exit discriminator pending.


125 return still responsive1/error5, foregroundPID32, shell0/desktop0 and
actual class atom49188, NOT the hypothesized built-in32769. Thus the named
desktop/class workaround is falsified for this foreground window; do not
present it as a fix. Third game reached fresh graphics/input+touch and normal
close; post-return snapshot retained privately. Next126 identifies the actual
canonical system-explorer owner instead of restricting arbitrary class atoms.
It retains explicit-return-only, verified responsive Steam target, error5-only
queue join and immediate detach, and excludes non-system explorer paths and
unrelated processes. Adds numeric system-owner/attempt/error diagnostic and
a gated fixed return-focus diagnostic that refuses any active game and never
starts another client. Host ownership/exclusion/failure/paired-detach
ASan/UBSan and existing return/game-URI regressions pass; actual device pending.
No FEX changes after the private123 module. Mac screen access still guarded
refused due lock; no screenshot or visual-return claim.


126 actual first return passes the bounded discriminator. Fresh saved
Success00:44:51, A624+B80=704/C352/margin266/span714; game740 starts00:45:35
and exits0 at00:46:41 after fresh D3D11/A17/Mono1.208/input+touch. Return
status responsive1, initial focus_error5, foregroundPID32, system_explorer1,
attach_attempted1/attached1/detached1/attach_error0/focused1; ACK
steam-window-focused. The class-constrained hypotheses were wrong for the
observed dynamic shell-owned window; canonical system-image ownership plus
the already explicit return request permits the bounded queue handoff.
Post-return right-arrow ACK diagnostic-key-sent followed by fixed no-spawn
WM_NULL/foreground probe ACK steam-window-focused. A post-return snapshot
contains no original IR rejection/FEX allocation fatal/redelivery termination.

This is real window-response/actual foreground evidence, not physical visual
confirmation of browser scrolling or gameplay. Mac remains locked and screen
capture correctly refused. Current same native task retained; second HotRoads
cycle requested to test reuse/return without restarting Steam. No finalGO.


126 same-process second cycle refutes long-term completion. Game1024 starts
00:48:17, fresh Mono1.133/D3D11/input+touch; close stays game-close-pending
and no second exit0 is recorded. Native snapshot8.29MB shows a NEW16MiB
aligned allocation failure despite the4MiBIR mode:1235views, free0x93e6000,
max aligned gap0xd90000, zero overlaps,475reservedRW16MiBviews. New Steam/game
threads04a8/04ac/04b0/04b4 fail arm64ec_thread_init c0000017. Original IR
NULL write/IR rejection absent, but capacity is NOT solved. Old fatal-string
checks alone missed this propagated failure; include STATUS_NO_MEMORY/thread
initialization failures in future validation. First successful bounded Steam
focus result remains valid, not a second-cycle pass.

Private pinned rpmalloc uses16MiB aligned spans and16MiB large pages. This
matches the dominant geometry but does not alone prove every view or exact
failed callsite. Next private allocator discriminator will use8MiB spans/pages
with maximum pooled block4MiB and a correspondingly shortened size-class
table (8MiB minus header cannot hold an8MiB pooled block). Larger requests
keep the existing huge-allocation path; no live-memory release, guard removal
or unconstrained allocation fallback. Call-return/SEH stack geometry unchanged.
Actual allocator host tests and own device probe required before full Steam.
Cleanup126-before-span127 restored original attrs/config and ended exact
test task. No native session left paused. No FEX source/binary publication.


127 private allocator span discriminator compiled and linked. Actual PE has
span8+IR2 markers and the oldspan16 marker is absent; C-module getter is
verified at ProcessInit. FEX DLL SHA256
eb7db5cfd8c57b81c09c59fd025bc97581ce02146e3dcf4b9677ce8f3d61940d.
Native122 and own helper126 unchanged;127 is a PE overlay, not a full Xcode
rebuild. Actual modified rpmalloc POSIX host test passes every pooled class,
4MiB->huge reallocation/content preservation,4MiB+1/8MiB/10MiB huge blocks,
alignment,12 worker retirements and cross-thread free with ASan/UBSan. Only
legacy unconditional Win32 log sinks and the disabled allocation-watch hook
are adapted by this host harness. This is NOT the Wine/iOS mapping path.

Existing exact cached profiles/deep-strict signing pass. Idle guard's current
Kusch process query failed, so the actual install was NOT attempted; the own
device probe also refused its absent127 installation receipt before changing
anything. Build127 is NOT installed or device-tested. Build126 prior test
recovery is complete (original attrs/config readback and exact sessions
absent); no new probe/config mutation or paused native process is pending.
Next: restore current device access, install only127, then own thread/oracle
probe + actual span8/IR2 markers before any full Steam two-cycle test.


### 2026-10-31 07:55 EDT: propagated-failure validation while device unavailable

Fresh availability check still shows Kusch paired/tunnel disconnected/DDI
servicesfalse. Public Mac session state is locked; no capture/control or lock
bypass attempted. No repeat install, launch, profile renewal or auth action.
Build127 remains signed/prepared, NOT installed/device-tested; original
probe/config/attrs remain restored from126. Mainline and original FEX untouched.

Closed a local validation gap: tools/analyze-steam-ui-pools.py now recognizes
propagated arm64ec_thread_init failures, unavailable thread-state, private IR
rejects and actual constrained-arena failure censuses/scans as well as the old
FEXAlloc fatal. Its optional --fail-on-fex-allocation-error exits2 when such
evidence exists; no-matched-failure NEVER means runtimePASS. Only whitelisted
numerics/categories/line numbers are added, with bounded samples and explicit
repeat-count/ownership/lifetime limits. Existing interval inventory stays
available. Host CLI/redaction/negative-status/unrelated-range/bounds tests pass.

Actual saved artifacts:122 failure detected through census even with no
FEXAlloc fatal;126 first-return snapshot has no matched allocation failure;
126 second-cycle detects4 thread-initc0000017 failures and20 failed FEX-range
scans. These are repeated observations, not20 distinct allocations. Strict CLI
exits2 for this known-failing bundle. Private JSON hashes summarized in the
standalone evidence document. No new phone result, memory-footprint fix orGO
claim. Next still: restore device connection, finish guarded127 installation
BEFORE staging own probe, validate actual span8/IR2 modes + thread/oracle/exit
results, then repeated game/return in one Steam lifetime.


### 2026-10-31 connected: Build127 actual mode and seven-table limit

Kusch process service recovers on demand despite stale disconnected discovery.
Deep signature/idle/original-restoration guards and actual version127 upgrade
pass. Own AMD64 probe16threads passes independent Python integer oracle, C0
and enclosing batch0. Actual native getter confirms rpmalloc8MiB and IR4MiB
MAXINST256; original own probe restored byte-exact. No FEX allocation/thread
failures matched in probe. Original attrs/config recovery completes.

Seven-table full Steam fresh saved login08:21:33 EDT; actualA560+B144=704MiB,
C320, margin258, span722 includes18MiB excluded gap. Game760 starts08:22:57,
fresh Mono1.078/D3D11A17/input+touch and real swapchain presents; exits0 at
08:23:21. User explicitly confirms manual exit (method unspecified). This
is not an agent-requested close or invented visual gameplay validation.
First-exit native snapshot has no FEX allocation/thread failure matches.
Phone control return-status shows responsive1/attached1/detached1/focused1;
agent return-focus diagnostic never obtains its own nonce ACK (a phone-UI
nonce remains), so no agent-command completion claim. Fresh same-PID
activation does not resolve that. A live existing hard-link log copy succeeds
without suspension and shows advancing08:33:52 output, refuting a stopped
native-task assumption. Exact helper-block cause remains unproven.

Separate genuine CEF failure:08:26:22.596 EDT (CEF12:26:22.596UTC) reports
ExternalEntityTable::InitializeTable(subspace allocation) OOM. Native bank7
adopts slot14 then refuses another512MiB claim. No second game starts. The
FEX no-failure checker is not a whole-CEF/Steam success gate; this independent
table shortage must also be checked. Preserve raw span127-seven-ended-native,
span127-seven-final-cef/gameprocess privately. Current game-log check confirms
no active tracked game before ending only the exact failed task; original
attrs/config restored. No accounts/games/saves deleted.

Next discriminator uses EXISTING noncompact eight-table geometry, unchanged
127FEX/native/helper binaries: FEX9GiB[7500000000,7740000000), new512MiB table
7740000000, all other intervals retain identity, including716 game-DLL spill
gap. Actual native16simultaneous disjoint holds/32boundary checks/16cleanup
pass. Current own Windows contractC0 verifies8distinct table claims,14core
boundary checks, split/replace/preserve, duplicate/generic refusals and frees.
Actual published numeric range and private8MiB getter verified; outer shell
exit line absent during bounded observation, so no clean-process-exit claim.
A too-specific expected label assertion was corrected using the real numeric
range, with no runtime change/retry. Original own PE restored byte-exact;
strict FEX failure checker matches none; original attrs/config restore done.

One unexpected new idle lab task32697 appears between probes, fresh log1173B
contains no Wine start; origin unknown (user open or helper return URL), not
attributed to user. Exact identified idle task alone ended before continuing.
No overlapping Wine experiments. Existing layout/ownership/game-image-spill
host ASan/UBSan regressions pass. New eight-table full Steam session launched;
no eight-table UI/game/return success claimed until its own fresh evidence.
Mac screen remains locked; no screen capture/lock bypass or credentials.
Private FEX source/binary remains unpublished.


### 2026-10-31 — eight-table game return fails; noncompact ninth-table discriminator

Fresh complete Build127 Steam process logs confirm Hot Roads guest756 launched
08:54:57 EDT and exited0 at08:55:25. CEF then reports V8
`ExternalEntityTable::InitializeTable (subspace allocation)` OOM at08:55:32.179.
All eight separate512MiB native-backed tables had been adopted; the next request
was refused. Observed partial placeholder frees still leave live Wine views.
Do not recycle these claims. The earlier inference from incomplete startup
collection that this preceded any game is corrected by the complete lifecycle.
The user reports a working game despite the runtime notice and an unresponsive
Steam UI after manual exit. Window-message responsiveness is insufficient UI proof.

The separately logged x86launcher guest-window failure explains the runtime
notice; it does not establish that the64bit game failed. Keep its4GiB guard.

Build128 adds only an explicit noncompact ninth-table layout option, moving
another512MiB from the published FEX tail into a separate owned table. FEX is now
8.5GiB in this option. Source pool placement and the measured game-DLL spill gap
remain unchanged. Compact and tail-nine together fail before any reservation.
Existing native bank/adoption logic already handles slot16; no assertion,
protection, Valve binary or FEX source change is made for128. The previously
user-authorized private span8/IR4 FEX DLL and helper126 are unchanged.

Host layout/ownership/concurrency/failure rollback, all17 game-image exclusions,
launcher and return-focus checks pass. Full Xcode128, exact final Mach-O markers,
deep-strict signing and isolated same-bundle upgrade pass. The actual native
probe held17 disjoint regions, checked34 boundary pages and cleaned17 mappings.
Real CEF/game/return validation is still pending; finite extra capacity alone is
not the long-term solution. Evidence and private artifact hashes:
`docs/CEF64_V8_TABLE_CAPACITY_EVIDENCE.json`. Published source HEAD8c4794d plus
local runtime changes; no original FEX/Wine submodule or working app modified.


### 2026-10-31 — ninth table insufficient; Build129 twelve-table headroom test

Actual Build128 saved login09:10:43 EDT, Hot Roads guest77209:11:43 to09:12:09
exit0, CEF ExternalEntityTable OOM09:12:15.133. All nine tables were adopted;
tenth512MiB request refused. The user independently reports the same working
game/manual quit/Steam freeze. No full release with remaining-view0 is observed;
partial frees do not authorize recycling. FEX analyzer has no matched failure,
which does not exonerate every allocation path. Actual signed A624+B0+C352MiB,
margin262MiB: requested pool704 was not an obtained704 allocation. Live master
log transfer failed; an existing game-session hard link provided the native
log without suspending or restarting the app.

Build129 tests twelve distinct native-backed tables by exchanging another1.5GiB
of the native FEX tail. FEX7GiB and the source/game-image geometry remain disjoint.
All20 native leases are now checked by game image spill and release observation;
a future unmeasured hold20 still refuses image spill. A new actual-geometry
adopter test found the new770 fixed hint aliasing an old layout address. Actual
current held bases now take priority, preserving fixed-address meaning.

Host ASan/UBSan geometry/backing/rollback, native owner/concurrency, all-slot
12-table adoption/fixed hints/failed-create rollback/retained claims, prior
adoption, all20 image exclusions, observer and launcher/return tests pass.
All37 native units and final full Xcode129 pass. Actual final Mach-O markers,
changed native archive/object hashes, unchanged private127 FEX/helper126,
deep-strict signing and isolated upgrade are recorded privately. On Kusch,
20 simultaneous native holds/40 edge checks/20 cleanup pass; own AMD64 Windows
12-table contract C0 and outer batch0 pass. Original own PE and temporary
attributes/configs restored byte-exact before real Steam.

Real Steam/CEF64 launched once and fresh saved login succeeded. A user question
is pending about one game/exit/navigation cycle; preserve this session. Extra
finite capacity is a discriminator, not a sustainable lifetime fix or final GO.
No new FEX/Valve/Wine-submodule changes; no private binaries or raw logs published.


Build129 first real cycle: saved login09:23:44 EDT; Hot Roads guest74809:24:51
through09:25:13 exit0. The user confirms game exit and continued Steam/Library
navigation. Live native sample has6/12 table claims, no table refusal; current
CEF log has no new fatal/OOM. Strict FEX analyzer finds no matched failure.
Actual signed A576+B128+C336MiB, margin258MiB. JIT span724 includes a20MiB gap;
it is not724MiB signed capacity. No process suspend was used for these reads.

One second-cycle remote URI was staged with exact readback, but the ACK nonce
was stale and no new game appeared in the sampled lifecycle. This is not proof
of Steam freezing. The pending request was cleared byte-exact; do not duplicate
it. The user is testing the second cycle manually in the same native lifetime.
The helper/remote command-path issue remains separately unresolved; sampled
helper thread was in NtDelayExecution, not proven dead. Do not claim full return
stability from one user-confirmed successful cycle.


### 2026-10-31 — Build129 second launch fails in decoder; private130 discriminator

User second-cycle report: entire app crashed. Exact129 native identity is absent;
second Hot Roads guest1016 starts09:31:35, with no normal exit observed. Native
census: FEX7GiB,1311views, free0x2768f000, max aligned gap0x7f0000, no overlaps,
8MiB request fails. A12288byte ThreadState allocation fails and ThreadInit reports
c0000017. A subsequent native NULL write resolves unambiguously to the exact
private FEX PE's `Decoder::DecodeInstructionImpl+0x38` (RVA21558, stp q0,q0,[x8]).
It repeats2000times before the native task ends. CEF has no new OOM in this copy.
Thus twelve tables improved the first return but exposed FEX capacity; not GO.

Original decoder uses65536 entries at128bytes each (8MiB), independently of the
already forced256 instruction default. Existing claim API supports resizing.
User-authorized PRIVATE130 requests only effective instructions up to the old
64K hard ceiling, retains explicit larger requests via that API, and rejects
NULL/undersized/out-of-bounds buffers before writing. Four exact runtime gates;
ordinary/default mode and original FEX submodules remain unchanged. RPM geometry,
CallRet/SEH, native129 and helper126 are unchanged. No private FEX code/binary is
published. Positive original allocation-size census is not sole attribution of
all573 large views to the decoder or rpmalloc.

Private host ASan/UBSan actual pre-write prefix/capacity/gates/cache/canaries and
controlled negative tests pass (not whole decoder semantics/Windows resize).
ARM64EC24step build passes; exact marker/hash/CHPE metadata checks pass. Its raw
PE machine AMD64 matches validated127; LLVM identifies ARM64EC CHPE version1.
Deep-strict signing/isolated130 upgrade passes. On Kusch, own16worker arithmetic
and thread test C0/batch0 match independent Python64 oracle; actual decoder
reports256entries/32768requested/backing-metadata bytes. This is not a kernel
reservation/residency measurement. Original own probe and configs are restored
before full Steam. Real repeated game-return validation remains outstanding.


### 2026-10-31 — decoder130 effective; residual allocator/CallRet capacity; private131

Retained actual130 logs show first Hot Roads74009:48:47 to09:49:09 exit0;
second99609:49:25 to09:49:38 exits0xd0594a27, not normal. New decoder request32768
is confirmed throughout actual Steam processes, with no decoder rejection or
repeat original null write. Residual CallRet0x802000 reservation fails in7GiB
arena:1394views/free0x2910e000/maxalignedgap0x7f0000,590 reserved8MiB views and
152CallRetguarded views. ThreadInit twice returnsc0000017; another FEX malloc
0x140000 fatals. CEF has no new OOM. Native continues logging until09:50:11;
its absence at10:22 does not independently identify why the native task ended.

Private131 changes only RPM geometry8->4MiB span+largepage, keeps medium4MiB,
pooledlimit2MiB/12largeclasses, existing huge path. Original CallRet/SEH capacities,
guards and source/native layout remain unchanged. Host actual POSIX allocator
classes/huge/alignment/retirement/crossfree ASan/UBSan pass with production argument
validation off and internal allocator assertions on. Initial attempted public
argument validation exposes preexisting undefined constants; not a runtime
failure/fix or a passed test. CMake regeneration needed established local toolchain
PATH for the archiver; actual ARM64EC link passes. Original FEX/Wine unchanged.

Deep sign and isolated131 upgrade pass. Actual own16worker arithmetic/thread
stress C0/batch0 match independent oracle, actual4MiB getter/decoder32768 confirmed,
original own PE and temporary configs restored. Actual full Steam saved login
10:27:31 and genuine Big Picture home captured on Kusch; not game success.
First actual signed A560+B0+C304MiB, margin263, below976MiB earlier game-test gate;
B misplaced and released by guard. No game was requested. One documented same
build clean repeat is prepared to reduce this observed ASLR budget confound;
no unsafe pool claim/protection retry/guard reduction. No long-term GO.


Build131 same-build repeat obtained signedA464+B240+C352MiB, margin266;
1056MiB actual code capacity, JIT span723 includes19MiB hole. Saved login10:30:06.
Fresh game78410:31:21..10:31:45 exit0, phone shows actual game/menu and iDeck
exit confirmation. Agent's single fixed URI returned `steam-open-failed`; phone
input also occurred, so do not assign every start/exit to the agent. Secondgame
1068 starts10:31:57, exitsc0000135 at10:32:01: UnityPlayer.dll import returns
c000007b. CEF13th table then refused/all12adopted and V8 OOM10:32:18.863. Stable
native has no matched FEX malloc/thread-init failure; this alone is not runtime
success. Some game-DLL spill maps succeed, so do not blame missing files.

After confirming no active game, exact lab task ended and temporary attributes/
configs restored. Existing image-mapper rejection markers do not explain this
second-load error. Build132 adds bounded numeric-only create-section/image-info
query diagnostics, exact session+SECTION_TRACE1 gates. Original create/query
operations/results remain unchanged; no extra request/file/header read, auth or
object-name logging. This is a discriminator, not a compatibility fix. Keep
private131 FEX policies and12table geometry unchanged for this comparison.


### 2026-10-31 — Actual132 second game; Steam content error; bounded133 lease channel

Runtime base be8151a plus preserved local experimental changes; source HEAD
d6a02be236ab4bf447c71ad827ac4ec40e842363. Primary main worktree and original
Wine/FEX submodules remain unchanged. Full133 retains private131 FEX and126
helper byte-exact; no new private FEX edit, Valve binary edit, assertion bypass,
lease reuse or overlapping reservation.

Actual132 own image-lifetime test: three sequential children,12maps/AMD64 header
checks/frees, all child0/batch0. Original own PE/configs restored before Steam.
Same native lifetime: first Hot Roads78810:49:53..10:54:08exit0. Second1084
starts10:58:28; actual configuration/Unity/menu captured. After visible Steam
return, Search opens Steam's content-error page. Second exit code/current CEF
failure cause NOT collected; do not claim stable navigation or an app crash.
Agent ended the exact task after screenshot; process absence verified.

CoreDevice file reads and writes time out, including after the user's reconnect;
official passcodeRequired=false and unlocked home screen captured. A partial
native copy is exactly10,000,000bytes, ends10:56:27/mid-line, before secondgame.
It shows nine table claims to one browser owner and preserved-view frees, but
proves nothing about later failures. A bounded serial suspend/copy/resume kept
the SAME task and later Search input visibly advanced UI; copy itself failed.
Temporary post132 configuration restore stopped at its FIRST upload timeout;
restoration/attributes are UNVERIFIED. No restore diagnostic/newSteam launch
was performed. Verify/restore this gate before installing or running133.

Independent source check at Chromium2e81dea shows single-process reuse check
precedes renderer-count limit; adding a process-limit switch alone lacks a new
discriminator. Existing Valve libcef custom-export constraint remains.

Prepared133 adds only bounded numeric lease evidence, exact session/trace/file
gates +standalone layout/isolated prefix. Exclusive per-native-lifetime file,
512KiB/4096record bound; no auth/path/payload logging, no overwrite/final symlink,
replacement/truncation/append refusal, errno preserved, no VM operation retry or
result change. Production writer ASan/UBSan actual-filesystem/concurrency/negative
tests and original adopter/observer regression tests PASS. All37 native units,
full Xcode133, final Mach-O markers, byte-exact private overlays and cached-profile
deep-strict signing PASS.133 NOT INSTALLED or device-run. Current blocker is the
file-service channel, not an Xcode account/login issue. See
CEF64_LEASE_DIAGNOSTICS.md and CEF64_V8_TABLE_CAPACITY_EVIDENCE.json for hashes,
commands, boundaries and next discriminator. NO-GO for claiming stable full64.


### 2026-10-31 — user selects connected physical iPad Air4

Fresh device evidence identifies Yilenda’s iPad, iPad13,1/A14, iPadOS27.2,
unlocked; only connected physical iPad, not the unavailable older Pro or a
simulator. Preserve completed separate MacAllocator22 app/data. Its own allocator
result does not establish Madeira Windows/Wine/FEX/Steam capacity on this iPad.
No SteamUI bundle currently installed, and no iPhone auth/cache/game/save data
was copied. Exact SteamUI main/helper profiles do not cover the iPad.

A disposable copy of the existing normal signing project retains the exact lab
bundle identifiers; only its previously ungranted ExtendedVA request is omitted.
No capability is forged or assumed. One official automatic-signing CLI attempt
fails No Accounts / selected iPad not in profile; GUI logout is NOT inferred.
The established remedy is the already-authorized Xcode GUI provisioning flow,
but a fresh UI guard reports this Mac locked. User asked once to unlock Mac,
not to sign into Apple ID/Steam. No lock bypass, app replacement or device test
claimed. Build133 remains prepared, not installed. Next first install requires
exact iPad profiles; first device discriminator is the native20region bounded
backing/cleanup probe before any JIT/Steam/authentication attempt.

The official Device Hub Show in Finder action exposes a CoreDevice DeviceFS
mount. Initial iPhone container listing/stat succeeds, but subsequent bounded
copy returns EINVAL. This does not recover the ended132 log or complete pending
iPhone configuration restoration. Preserve that separate gate during iPad work.


### 2026-10-31 — actual Air133/134 install and6GiB high-band capacity

User Mac unlock allowed normal GUI signing: exact private Signing64 project
selected physical Yilenda Air4, normal GUI Build produced main/helper profiles
covering the iPad, correct team/certificate/debug permission/expiry; Memory+
granted in profile, EVA absent. No AppleID re-login. Full133 actually first
installed, version read back; unrelated MacAllocator22 preserved. All native
experiments exclude Steam/JIT/autostart; no auth/cache/game/save transfer.

Actual20region/59.5GiB capacity test: slot0oneGiB succeeds; slot1guard-prefixed
source pool at717fff0000+40010000 returns KERN_INVALID_ADDRESS1, not a recorded
OOM. Own slot0 cleanup0; no backing-edge checks reached. Existing broad inventory
finds64..448GiB protected maxprot0 native range, high64KiB map succeeds but
16GiB fails. No overwrite or kernel-region workaround.

Added standalone134 bounds discriminator: exact explicit argument+flag,32point
samples/32prefix reservations, NONE maximum/current protection/no-touch, exact
own cleanup, stop on unexpected address/cleanup error; normal runtime unchanged.
Actual production-host ASan/UBSan safety tests and original backing/launcher
checks pass (Swift cache sandbox denial required normal-permission rerun).
All37native/fullXcode134/final linked markers/unchanged private FEX131+helper126/
deep signing pass. Exact completed diagnostic ended, only isolated lab upgraded
to134 and real version read back. Actual sampling:64calls,48successful mappings,
all cleaned0; continuous6GiB from7000000000 succeeds,6.25GiB and64KiB at7180000000
fail invalid-address. Probe result0 is measurement completion, NOT layout or
Steam success. This is virtual capacity evidence, not physical RAM/backing.

Mac auto-relocked. Previous -d/-i awake assertion did not prevent screen-lock;
prepared unlocked-only -u temporary assertion for next unlock. Private normal
EVA signing request prepared but GUI build NOT sent, so Apple acceptance or
rejection remains unknown. User asked once more to unlock/keep desktop open.
No lock bypass, forged entitlement or assumed paid-account outcome.

Headless LLDB attempt on fresh exact start-stopped own probe failed to obtain
a target; no valid debugger-enabled A/B result. Sentinel unchanged pre-attach;
exact new task ended and verified, no deliberately stopped process left behind.
No claim debugging is ineffective. Full64 layout under current Memory-only
launch remains NO-GO; not proof of impossibility with genuine EVA grant. See
IPAD_CEF64_CAPACITY.md/JSON for hashes and next gate. iPhone original132 temporary
configuration cleanup is still pending its separate file-service issue.

Local HEAD advanced tocb3b835 via unrelated README-only human commit; preserved.
Remote experiment remainedd6a02be on fresh read; no commit/push/merge performed
by this run, and no private FEX/Valve/signing/log payload published.


### 2026-10-31 23:05..23:11UTC — unlock-state mismatch; no EVA build

User reports Mac unlocked. Immediate native host check still reports
KuschMacMini-M6-New locked=true/frontmostloginwindow. A bounded180second
one-shot waits only for native user unlock and dispatches no UI while locked;
it ends23:11:06UTC with timeout_without_native_unlock. No GUI build, awake
assertion or EVA request is performed in this continuation. No new device
install/runtime result and no Apple acceptance/rejection inferred. Host-name/
desktop clarification is pending; avoid repeated generic unlock requests.

Installed Xcode.sdef confirms official background workspace-build/result API.
A narrowly guarded exact workspace/scheme/physical-iPad helper passes syntax
compilation only. Existing Apple-event permission check with prompting disabled
returns-1744; no event or consent prompt is sent and no OS permission changed.
Actual profile pair remains valid/Memory+true/EVAabsent. This is a normal OS
authorization gate, not an automatic tool-approval rejection or GUI-account
logout finding. No background monitor/recurring automation remains.

### 2026-11-01 — resume Kusch game/return stability after storage migration

User explicitly selects Kusch iPhone for direct operation and full-cycle testing.
Verified migration completion and mounted easystore UUID before new writes;
active project/artifacts remain on the external volume through compatible paths.
Experimental HEAD cb3b835 and all prior local changes are preserved; no merge,
release, commit or push performed. The later normal GUI EVA request did actually
fail: official Xcode build log BEBA4BE7-20C2-4BB4-8769-D116C57CC12E explicitly
rejects Extended Virtual Addressing for the current Personal Team. This
supersedes the preceding request-not-sent record, and is distinct from Kusch's
game-return problem. No account re-login or ungranted entitlement assumed.

Initial fresh CoreDevice list shows Kusch disconnected; native Mac check shows
loginwindow/locked and no Device Hub phone window. User requested once to
restore the existing remote connection, without opening Steam or signing in.
The unverified post132 config/attribute restoration remains the first device
gate before install/launch. Do not treat an unavailable file service as a
successful cleanup or a game crash.

Independent preparation: cached phone-signed Build133 includes the separate
MADEIRA_CEF64_LEASE_FILE marker, correct isolated bundle, Kusch device coverage,
get-task-allow and main profile expiry2026-11-06T16:46:27UTC; deep-strict signature
verification passes. This is artifact readiness, not a new device installation.
Private FEX and Valve payloads remain outside Git.

Added read-only tools/analyze-cef64-leases.py. Hypothesis for the next device
trial is that correlated small-file observations can distinguish retained
placeholders/still-live views from unsuccessful adoption and actual observed
teardown through two game cycles. It changes no runtime allocator or guards.
Four host tests cover failed-adopt false success, preserved/failed/remaining
frees, truncation/budget bounds and malformed/mixed records. Production writer
and free-observer ASan/UBSan regressions pass. No actual lease-file device
analysis, full-cycle success or causal fix is claimed.

Next: after fresh connection/identity verification, restore and read back
original post132 config/attributes, install the prepared isolated diagnostic
only while idle, verify actual installed version and unchanged private runtime,
then run genuine saved-login Big Picture. Collect matching numeric lease file,
game exit logs and real UI response at startup/first game/return/navigation/
second game/second return. Preserve account/games/saves. Never infer a successful
cycle from helper ACKs, process existence or compilation alone.

Follow-up in the same run: actual Kusch App/process/lock queries succeed;
installed132, unlocked and initially idle. Actual small configuration/native-log
copies also succeed, so the former file-service gate is recovered for these
operations. Started only the original-attribute restore diagnostic. Its result
remains the fresh pending sentinel: native log explicitly reports no VPN
interface, unreachable local debug loopback and Built-in StikJIT connection
timeout. No Wine/Steam/game launch is observed; restoration is not complete.
The initial temporary restore configuration upload succeeded, so retain the
restoration/readback gate before installation.

Normally opened the existing App Store LocalDevVPN on Kusch. No tunnel-provider
process observed afterward; normal foreground launch alone does not prove a
connection. User asked once to tap Connect in that already-open VPN app; no
credentials, configuration replacement or device-lock bypass. Exact owned
restore/helper/VPN identities and artifact hashes are private in
cycle135-preparation-evidence.json. Keep the current VPN foreground and await
the connection action; no blind Steam restart or claimed cycle result.

### 2026-11-01 — Kusch two game exits; x86launcher capacity and nonmodal notice

User connected LocalDevVPN; actual TunnelProv observed. Ended only the old
failed restore request after identity verification. New restore succeeds;
original CEF attributes and both original configs read-back match. Installed
Build133/read-back verified; private FEX131/helper126 unchanged. Fresh genuine
saved Steam login verified for native56773. Actual new bounded lease snapshots
39/54records retrieve successfully despite live native-log copy failure.

User manually tested. Steam gameprocess records guest744 and1068 both exiting0
in one native lifetime. Screenshot/user report show a blocking runtime notice
despite successful gameplay. Fresh game tracking verifies no active game before
agent intentionally ends only that Steam session for upgrade/log capture.
Stable7,120,224-byte native copy now succeeds. Both matching i386 failures follow
Valve bin/x86launcher.exe spawns;1172/928MiB free VA, below the actual4GiB window,
not merely its8GiB margin. AMD64 Hot Roads starts separately. No matched FEX
allocation-failure category in this captured log; later slot19 V8 refusal is
observed, with no proof of interactive navigation stability. Final small-file
copy fails when remote connection later drops; don't infer complete coverage.

Build135 minimal UI change: observed child-window failure now records a
nonmodal runtimeNotice in iDeck options/diagnostics. It no longer sets the global
startupFailure alert. True preflight errors and normal session error paths are
retained. Native allocator, headroom, ownership, Valve binaries and private FEX
are unchanged. Existing capacity/observer plus presentation-contract tests PASS;
fullXcode135/final Mach-O marker/private-overlay hashes/deep signing PASS.
Configs/attributes again restored/read-back before upgrade. Installation receipt
reports success; subsequent actual-version readback times out on the dropped
wireless connection. NO actual135 UI/regression or underlying-capacity fix claim.

User requested restoring current remote connection once; no Steam restart or
credential action requested. Source cb3 plus preserved local changes; no
commit/push/release. See STEAM_CHILD_WINDOW_NOTICE.md and private
build135-nonmodal-evidence.json/cycle135-first-exit-evidence.json for precise
boundaries. Next resume: version readback FIRST, same-profile135 launch and popup
regression, then genuine two-cycle UI/lease/failure correlation. Counterpart
x64launcher resource strings alone do not establish a safe replacement contract.

### 2026-11-01 — Build135 actual two-cycle milestone; third launch unresolved

Fresh reconnection reads actual installed135. Same isolated Kusch prefix keeps
auth/games/saves; genuine saved login succeeds. User confirms blocking runtime
notice absent and two normal game entries/exits. Gameprocess log records exits0
at22:14:10/22:14:47 EST. Third starts22:15:05, exitsc0000135 at22:15:08. Original
UnityPlayer.dll section creation/query succeed AMD64; image mapping fails
c0000017:22.023MiB request versus19.973MiB largest gap/195views. File corruption
or missing file is not established by the outer loader status.

Separately current CEF reports ExternalEntityTable::InitializeTable OOM at
22:15:20. Same-browser table bank claimed all12slots; next512MiB adoption refused.
74records/no partial tail/no budget exhaustion do not imply full-runtime coverage
or prove a leak. Placeholder-preserving frees are not permission to recycle.
One bounded native suspend/copy/SIGCONT snapshot followed the game failure and
preceded CEF OOM; scheduling effects are not excluded. Next use small files
without pausing. Preserve current live session for evidence.

Checkpoint retains experimental source/tests/docs, excludes Demo.gif and all
private runtime/auth/signing/raw artifacts, does not merge main or make a release.
Build135 fullXcode/final marker/deep signing and two exit records are distinct
from user UI evidence.29 existing host fixtures pass; pinned-header source rerun
and new section-trace ASan/UBSan test pass (31 distinct valid checks). CEF glue
fixture requires a proper pinned Chromium Git checkout; no pass claimed.
Publication review fixes failed-NtCreateSection output-handle diagnostic read;
that host-tested line was added AFTER135 and is not device-validated. All37
native units compile successfully after the follow-up; the generated archive
was not installed over the live test.

Next: attribute image views at automatic child exit; compare no-game CEF
navigation/table lifetime before changing layout or reuse. Do not weaken guards
or claim either failure is the sole cause of the whole session freeze.
See CEF64_BUILD135_MILESTONE.md and CEF64_BUILD135_EVIDENCE.json for evidence
hashes, private-FEX reproduction limits and exact boundaries.

### 2026-11-01 — user-authorized main merge and Build136 release regression

User explicitly requested merging the experiment into main, retesting and only
publishing a release if successful. Main merge9ffacca was conflict-free/pushed;
prior source-only isolation instruction is superseded for this merge, not a
claim of stability or permission to distribute private FEX. FullXcode136,12
merged core host regressions/final linked marker/deep signing pass; actual
Kusch install/readback136 and fresh genuine saved login pass.

First game23:04:46..23:06:38 EST exits0 and helper reports Steam focus. Second
23:08:00..23:08:03 exitsc0000135. Original section/query succeed AMD64 but JIT
copy allocation wants22.047MiB, largest15.031MiB despite81.844MiB total free.
Actual main span560MiB/C304MiB differs from requested704 and prior135 geometry.
Initial private harness wrongly captured candidate-hole566 as C size; corrected
actual-field/latest-session parser rejects geometry and its focused host checks
pass. No equivalent-geometry or merge-caused regression claim is made.

No third launch after failure. Bounded lease61records:13adopts including6tables,
no refusal through snapshot; no complete-coverage or current CEF OOM claim.
Failed session ended after game exit, pending control cleared, original attrs
and both configs restored/read-back. Auth/games/saves preserved. Installed136
retained; test ended. NO-GO for new release; existing alpha4 unchanged.
Exact private FEX corresponding-source/relink permission scope is another gate.
See release/BUILD136_RESULTS.md and release/BUILD136_EVIDENCE.json.

### 2026-11-01 — Build137 persisted ordinary entry and own-TEB adapter

Current user normal136 log confirmed prefixwine/Steam32BundleLab, unlike prior
explicit Steam64/wine-steam64 test. No changeuser in either batch; no agent
account action. Legacy browser196 suffers exact native LDRSW/x18zero read0x180c
AV, then threads end and browser784 starts. Existing adapter gate excluded wine;
host ASan/UBSan reproduces differing predicates. No current game start recorded.

User authorizes fix/build for own manual testing. Local fix/steam-runtime-entry
fromc969 adds persisted steam-runtime selection, early scoped steam64.env.*
config before reservations, normal launcher label and no silent account-prefix
fallback; legacy diagnostics remain isolated. Tight own-TEB signed-load adapter
now covers both supported Steam prefixes; no FEX/Valve code or guard changes.
Host launcher/selection/ownership/failure/TEB tests,37nativeunits/full137/final
linked markers/deep signing pass. Kusch install/actual137/config readbacks pass.

Normal no-argument app-open accepted;110s wait has no fresh SteamSuccess and
native file contains app initialization only, no Wine start. Do not mistake
previous batch/historical auth for a fresh pass. Preserve current auto-start
preference and hand installed137 to user for launcher/check/JIT/Steam/account/
game testing. No game launch or separate legacy-browser device test performed.
Both auth/game/save trees and original config backups preserved. No release;
135/136 repeated-cycle capacity/lifetime problems remain. See
IDECK_RUNTIME_ENTRY.md and IDECK_RUNTIME_ENTRY_EVIDENCE.json.

### 2026-11-02 — Build137 user ordinary launch and repeated-game failure

User first game succeeds and returns; later Play does not enter game but Steam
remains responsive (user report). Actual137/current native identity verified,
read-only no-pause copies succeed.11:14:11 normal launcher selects wine-steam64.
Hot Roads11:15:18..11:15:42 exits0; next11:15:54..57 and11:16:15..18 exitc0000135.
Original UnityPlayer executable pool-copy request0x160c000 failsc0000017; section
create/query succeed AMD64. Largest free0x15dc000, total0x55e4000/112entries.
Main requested704 becomes592MiB, C336/margin268. No input-loss/missing-file
claim; old CEF OOM lines are not attributed to this run.

First game owner reclaims60ranges/0x5af4000,55tombstones; exact Unity block fate
unproven. Source already has adjacent clean-block coalescing and best-fit.
Next trace large-image interval/owner/reuse/max-protection history and fix only
the demonstrated contract, preserving grace/ownership/exec guards. No code or
device configuration changes in this collection; keep user's current Steam
alive. New evidence appended to IDECK_RUNTIME_ENTRY_EVIDENCE.json. No release.

### 2026-11-02 — Build138 isolated Unity pool-copy demand discriminator

User requests continued repair/testing. Current137 evidence establishes large
Unity copy refusal; existing best-fit/coalescing cannot infer lost block fate.
Investigated existing pure-x64 data-image route already enabled only for libcef
in this profile. Minimal explicit Unity-only extension retains all client and
support aliases and outer AMD64/nonhybrid/nonbuiltin/nonresource/nonWoW guards.
No FEX implementation, Valve/game binary, reservation guard or assertion changes.

Separate owned24MiB DLL/driver compiles Werror AMD64 with real static TLS. It
tests32calls/callbacks plus worker TLS in2rounds across3children, including
explicit unload and loaded-at-child-exit. Device execution is required before
claiming image execution or gameplay success. Production policy ASan/UBSan
and runtime/spill/layout regressions pass,37nativeunits/fullXcode138 pass.
Signing preparation is independent; no installation or game action performed.

Fresh Kusch process query times out15s. One availability check confirms paired
but disconnected tunnel/noDDI. User asked once to restore existing connection
and preserve current Steam; no repeated install/launch or account prompt.
Private existing runtime unchanged. Next: revalidate current identity/no game,
restore config attributes safely, install signed138, back up/stage owned probe,
run fresh own execution discriminator, verify results/actual no-copy route and
restore probe byte-exact before enabling Unity flag for user game cycles. No
release or proven-fix claim. See experiments/cef64/IMAGE_EXECUTION.md and
CEF64_UNITY_DATA_EXPERIMENT.json.

### 2026-11-02 — Build139 Steam UI performance, unsuccessful V8-only trial

User reports slow Steam UI while games are smooth; UI performance becomes the
current priority. Physical baseline confirms -cef-disable-gpu / webhelper
--disable-gpu-compositing, interpreted V8 and one reported guest CPU. Guest CPU
count is not host single-core affinity. Thread-suspending diagnostic bursts and
serious thermal state are also observed, with no quantified causal cost.

Actual launcher bug unconditionally resets MADEIRA_JITLESS=1. Minimal patch honors
explicit V8 configuration with compatibility default1 and early scoped export;
separate default-off GPU-auto opt-in removes the disabling flag only in owned
full64 source layout. No game/FEX/Valve/submodule edits or guard relaxation.
Host launcher/early-environment ASan/UBSan/debug privacy checks and full139,
final linked markers/unchanged private overlays/deep signing pass. Installed139
version read back on Kusch. Unity no-copy/probe flags remain off throughout.

V8-only candidate readback matches; GPU remains disabled, guestCPU1 retained.
First start cannot enable native JIT because VPN is disconnected; no Wine launch
or fresh login. User retry reports black/start failure. Fresh15:02 webhelper
initializes without jitless switch, but BrowserReady/usable home not observed.
Live/stable native-copy attempts time out: no exact fatal or sole-cause claim.
Original compatible config restored; byte-exact readback confirmed after upload
timeout. Same agent-launched PID68543 remains despite accepted SIGTERM, so no
death claim. GPU-only staging safely refuses idle gate; no GPU upload/launch.
Automatic approval rejects forced SIGKILL due possible active user state;
no workaround attempted. User asked once to close iDeck through app switcher.

Next: verify absence, then test GPU-auto alone with restored V8 compatibility and
unchanged CPU/diagnostics; require actual backend evidence and real navigation.
Separately test existing lean diagnostics to avoid suspend bursts. Keep both
prefixes/auth/games/saves, no automatic game launch, no speedup/release claim.
No commit/push outside user window. See STEAM_UI_PERFORMANCE.md and its evidence
JSON for exact private artifact hashes, rollback and observed limitations.

Follow-up: user closes old test; exact68543 absent, new69333 retained. Original
config readback matches. GPU-auto request staged/read back for next Steam start;
activation reuses69333, captured batch still disables GPU. User reports usable
but slow Steam and Hot Roads, pending native Exit game, diagnostic notice. No
effective GPU backend/performance pass. Device Hub actual visual capture succeeds;
native menu later absent after keyboard interaction, but mouse/standard AltF4
do not establish game closure. Selected-prefix exit UUID has only ready/ready
reply; old return-status fields lack nonce, not current success evidence. No
game kill, account action, debugger attach or precise helper root-cause claim.

Current CoreDevice file/process calls time out; debugger device query cannot
connect. One preview error recovers. Mac later truly locks; guard refuses UI
input and does NOT stop screen sharing. Unlock requested once. Current all-app
identity/fault capture unavailable; preserve current session. Safe GPU rollback
requires compare/readback; if unavailable, last verified GPU1 remains prospective
next-start staging, not a verified setting for the active browser.

Independent Build140 removes confirmed diagnostic overhead by default only for
exact genuine Steam sessions after config export. Existing lean switch disables
server suspend bursts/RIP profiling; additional unconditional compositor20s stack
walker now honors that policy. Explicit diagnostic override, ordinary games,
error capture and bounded actual-main-stall dump remain. No GPU/JS/CPU/allocator/
guard/FEX/Valve/submodule or exit-policy changes in this follow-up. Production
header ASan/UBSan/isolation/override, existing lean/launcher/privacy tests pass;
fullXcode140/final markers/unchanged private overlay/deep signing pass. Prepared
but NOT installed; no device speedup/game-return/root-fix claim. Next recover
current logs and safe idle state, reconcile staged GPU config, test lean-only,
then GPU with fixed JS/CPU/diagnostic policy. No commit/push/release.


### 2026-11-02 — Build142 startup regression discriminator

Revision c969c9a plus preserved local runtime-entry/performance/control changes.
GPU staging was rolled back/read back exactly. Build141 fails guarded native
executable-window placement before Wine. Build142 installs/readbacks correctly,
allocates JIT pools, starts Wine and recreates the new helper marker, but user
and stable native guest-window logs confirm webhelper not responding. Fresh
browser initialization is recorded; no fresh login/BrowserReady observed. Native
4471134-byte ended-session log SHA256
`db09d27d5f4ddb5ad1c31cb709bf18f380515ba34ad426f9f4600f8771fd4ae1`.
Private artifacts: steam64-current/steam-ui-performance-20261102T144517.
No secret/raw device logs are published.

Hypothesis/test: existing LEAN mode changes VM maintenance/replay as well as
sampling; relaunch the same142 with only scoped LEAN_DIAG=0, original settings
preserved and exact config readback required. Failed-session identity verified
absent first. This A/B is running; not a root-cause/fix claim. Hidden-log pause
and existing-window-only menu tests/full142/signing pass. Device navigation,
GPU acceleration, in-game exit and repeated loops remain unverified. No FEX,
Valve, authentication or guard changes. No commit/push outside the user's window.


Build142 A/B update: initial ordinary launch only opened the configured developer
shell (no JIT/Wine); excluded. Identity-verified shell normally closed; explicit
Steam64/BPM entry then records fresh Success18:03:01 and new BPM window18:02:51,
plus exact new helper marker. Visible navigation pending. Single cold-start A/B
cannot establish LEAN causality because placement may differ. Current142 session
preserved, no game launched. Scoped LEAN0 config backup/readback retained.

Smallest follow-up: pure Steam-only sampling switch defaults0; server sampler
and compositor stack gate share production policy, leaving broad LEAN and VM
maintenance untouched.100 ASan/UBSan policy cases, old lean compatibility, early
selection, launcher/menu/focus/return pass. Build143 native37/fullXcode/final
sealing are checked separately; no device claim or release from these checks.
Next: obtain visible142 navigation, test pure sampling without VM changes, then
one GPU-only comparison and genuine menu/exit regression. Keep account data and
live test. No commit/push outside allowed hours.

Build143 final verification: native37, fullXcode, exact native/server and bridge
markers in final signed debug dylib, unchanged FEX131 and new helper marker,
deep-strict signing PASS. Candidate prepared privately; NOT installed. Current
142/LEAN0 successful-login session remains for user navigation confirmation.


### 2026-11-02 — Build143 installed and fixed menu serviced

Preserved ended142/LEAN0 native log SHA256
`db4ab3ac989de032119d2900ca04605a76fab92c8624d945080beb81d1709402`;
exact absence on resume, end reason unknown. Main/helper valid profiles and deep
signature rechecked. Installed143, version readback143, exact config unchanged.
Corrected explicit launch (initial CLI parse error did not launch app) yields
fresh Steam Success20:01:06 and new BPM window20:00:46. Same helper accepts one
fixed menu command and returns matching UUID menu-requested. No fresh gameplay,
visual menu/navigation, in-game exit or speedup claim. Raw native transfer fails
CoreDevice7000/POSIX60, not proof of absent runtime faults/policy. Mac locked;
Device Hub guard refuses capture. Current live143 session preserved for pending
user UI question. No pause/kill, account action, GPU change or automatic game.
Private artifacts steam64-current; redacted hashes in performance/control JSON.
Next require actual menu/library observation, then GPU-only comparison with fixed
V8/CPU/pure-sampling/VM settings; retain rollback. No commit/push outside window.


Build143 user validation: user explicitly confirms the Steam menu is visible and
homepage/library browsing is more fluid. This is user-observed improvement,
separate from the artifact-backed matching menu ACK/fresh login/window creation;
no quantitative speedup, hardware browser GPU, game-exit or loop-stability pass.
Next GPU-only experiment retains143, interpreted JS, CPU1 and pure sampling/VM
policy; back up fresh config and confirm no new game before normal cold restart.

Fresh official143 gameprocess follow-up supersedes earlier not-yet-tested
status: three Hot Roads1819280 launches20:02:15/20:02:48/20:03:58, exits20:02:32/
20:03:47/20:04:25, all exit code0 and removed from running list. Agent did not
launch these. User subsequently confirms menu visible and browsing improved.
This is bounded repeated-process-cycle evidence, not long-term stability or
proof of native Exit game action. Preserve this baseline before GPU-only test.


### 2026-11-02 — effective GPU-only experiment, baseline restored

Same143 with one appended GPU-auto key; exact candidate/readback. Actual batch
and fresh webhelper omit GPU-disable flags; native hardware-auto/JITless marker,
fresh login and new BPM window recorded. User/gameprocess activity starts Hot
Roads20:16:19; agent does not launch it. Snapshot refuses before pause when game
observed. Later normal-exit request refuses on absent original PID; no stale
signal/attach/exit/terminate. End reason unknown, user closure question pending.
Rotated native snapshot preserved; loader-confirmed libcef breakpoint RVA
0x35348e2, failed check unknown, later native lines continue. Footprint~4GiB.
D3D11 warning alone is not CEF renderer evidence; no hardware/performance pass.
Subsequent20:38 developer-shell log is another startup, not GPU test evidence.
Exact candidate safely rolled back/read back to user-confirmed143 baseline.
No assertions, guards, FEX/Valve/auth modifications. No GPU default/release GO.
Evidence hashes and limits in STEAM_UI_PERFORMANCE_EVIDENCE.json. Next investigate
CEF-owned hardware backend/failed-check with controlled idle UI, preserve genuine
menu responsiveness and confirmed three game-process cycles; require further
stability validation. No automated game launch or forced closure.

Final state of this continuation: exact software-baseline config rollback
verified; same installed143 explicitly relaunched after fresh idle/unlock check,
new Steam Success 2026-11-02T23:21:30 and exact process identity verified.
No forced kill, debugger attach, pause or agent game launch in these failed
gates. Keep baseline active; manual-closure answer and long-term stability
remain pending. GPU not promoted, no release claim.


Latest user correction for Build143: three game enter/exit cycles work, but
Steam freezes after the THIRD return. This supersedes any complete-loop/stability
impression from exit-code0 and early menu observations. User explicitly requests
an experimental checkpoint release with that known issue; not a stable GO.
