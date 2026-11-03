# Steam UI performance investigation — Build 139

This investigation is separate from the unresolved repeated-game-launch image
pool problem. A smooth game does not establish that the Steam browser uses the
same rendering backend. No speedup or hardware-accelerated browser is yet proven.

## Verified baseline

The captured physical Kusch Build137 session explicitly starts Steam with
`-cef-disable-gpu`. Its webhelper receives both `--disable-gpu` and
`--disable-gpu-compositing`. Native process diagnostics report V8 `JITLESS`.
The persisted Steam64 profile reports one guest CPU. That setting is not host
single-core affinity. The native Metal display compositor is not proof that CEF
rasterization/compositing uses the GPU.

The same baseline contains 492 thread-sampler lines and 75 RIP-profiler lines.
The sampler implementation suspends threads during periodic bursts. Its existing
`MADEIRA_LEAN_DIAG=1` mode avoids those bursts and guest RIP sampling. These counts
establish active diagnostics, not the amount of performance lost. The phone also
reported serious thermal state; comparisons need comparable temperature.

## Minimal patch

The genuine Steam launcher unconditionally assigned `MADEIRA_JITLESS=1` just
before Wine startup, defeating an existing native V8-JIT opt-out. Build139 honors
an explicit setting while preserving compatibility default `1`. Exact `0`
selects JIT; process environment takes precedence over scoped Steam64 and general
configuration. The scoped setting is exported before Foundation environment
snapshots. Legacy and explicit diagnostic selection remain isolated.

A separate default-off `steam64.gpu-acceleration=1` option removes only the
launcher GPU-disabling flag, and only for the owned full64 source-CEF layout.
This requests automatic hardware selection; it does not force or prove a working
hardware backend. Existing sandbox compatibility flags and Valve authentication
are unchanged. No game, Valve, FEX, Wine-submodule or reservation-guard edit is
part of this performance patch.

## One-variable experiments

1. **V8 JIT only:** `steam64.env.MADEIRA_JITLESS=0`; software GPU policy and guest
   CPU count unchanged. First agent launch did not enter Wine: LocalDevVPN was
   disconnected and native JIT enablement failed. User retry reports black screen
   or startup failure. Fresh15:02 webhelper records browser initialization without
   `--js-flags=--jitless`, but no observed BrowserReady or usable home. The live
   native-log copy timed out, so no exact fatal/sole-cause claim is made. A normal
   exit request was accepted after identity/game-state checks, but the same PID
   remained present: receipt acceptance is not process death. Original
   config was restored and subsequently read back byte-for-byte, despite the
   initial upload timeout. Do not recommend JIT mode as a successful fix.
2. **GPU automatic selection only:** restore V8 compatibility, retain CPU count
   and diagnostics, and opt in using `steam64.gpu-acceleration=1`. Require fresh
   backend evidence and visible navigation. The first staging attempt correctly
   refused its idle gate because the original V8 test still existed; no GPU
   configuration was uploaded or GPU test launched. Absence of a disabling switch,
   BrowserReady, a GPU-process name or native Metal presents alone is insufficient.
3. **Sampling overhead:** separately test the existing `MADEIRA_LEAN_DIAG=1`
   option with the same renderer/JS policy. Confirm the native lean marker and
   absence of suspend bursts. Do not combine with a CPU-count change.
4. Change guest CPU count only after thread/allocation budgets and comparable UI
   measurements justify it. No “all cores” affinity claim follows from this key.

Compare the same homepage and library scrolling without launching games, after
startup settles and with comparable thermal state. Record UI observations
separately from CPU time, footprint and display-present cadence. Never infer a
browser speedup from a successful Xcode build or an animated compositor alone.

## Validation and rollback

Focused production launcher tests, early-environment ASan/UBSan checks and debug
privacy regressions pass. Full unsigned Xcode139, linked final markers, unchanged
private FEX/helper overlay hashes and deep-strict signing pass. Version139 was
installed/read back on Kusch. This does not validate its performance experiments.

The original private configuration and exact readback are retained outside Git.
Rollback restores that file, preserving `steam-runtime=steam64`, both account
prefixes, games and saves. No logout or cache deletion is required. Raw device
logs and signed/runtime binaries remain private. See
`STEAM_UI_PERFORMANCE_EVIDENCE.json` for redacted evidence and limitations.

V8's [official JIT-less explanation](https://v8.dev/blog/jitless) describes why
interpreter-only JavaScript can cost performance; its desktop benchmarks are not
iDeck measurements or a prediction of a particular speedup here.

The forced-end fallback was rejected by automatic approval due possible active
user state. No SIGKILL was sent. Await normal physical app-switcher closure and
fresh absence verification before staging another experiment.

## Follow-up: user game/return report and Build140

After the user closes the old test, PID68543 is absent and a different69333 is
present. Preserve the new session. Config readback still matches the original.
The GPU-only next-start setting is then staged/read back without restarting the
new process. Activation reuses69333. The captured batch still disables GPU:
this is not an effective GPU test. User reports Steam opens but is slow and the
native Exit game action stays pending while Hot Roads runs.

Device Hub is actually opened and visually shows Hot Roads Game Mode, virtual
controls and the native menu. A selected-prefix command file contains an exit
UUID, but its reply remains `ready ready`. Existing return-status fields have no
freshness nonce and do not prove this request completed. Mouse clicks and one
standard balanced Alt-F4 do not establish game closure. No process kill or
account action is performed. File/process requests time out, and a read-only
debugger process listing cannot connect; no attach or stack snapshot is claimed.
One screen-service error recovers; later the Mac locks and guards refuse input.
The proposed Stop Screen Sharing action is not executed through that lock.

Independent source inspection finds the compositor also walks every thread's
stack every20s, regardless of the server's lean flag. Build140 defaults genuine
Steam sessions to existing lean diagnostics after configuration export, respects
an explicit override, and gates this additional periodic walker in the same
exact session. Ordinary gaming paths and bounded actual-main-thread-stall dumps
are preserved. It changes no GPU, JS, CPU, allocator, protection or exit policy.

Production-header ASan/UBSan cases and existing lean/launcher/privacy checks pass.
Full Xcode140, final linked markers, unchanged private runtime overlays and
deep-strict signing pass. The app is prepared privately but is NOT installed;
no measured speedup or exit repair is claimed. First recover diagnostics and
verify no active game, resolve the staged next-start GPU configuration without
overwriting user changes, then install/test lean-only before another GPU-only
comparison. The exit helper's blocking point still needs current evidence.

## Build141/142 device follow-up

The staged GPU change was rolled back with byte-exact device readback before
these tests. GPU remains forced software; V8 remains interpreted and guest CPU
count remains one. Neither test establishes a browser hardware backend.

Build141 was installed, but its first cold start failed before Wine: a native
mapping occupied the required executable window, and the allocator correctly
rejected overlapping alternatives. This is a startup-layout failure, not CEF
performance evidence or proof that hidden-log pausing caused a regression.
Build141 also uses the existing hidden-log pause API while genuine Steam runs;
a host behavioral test confirms 20,000 hidden lines remain in the raw file
without being parsed, and future lines resume normally when the log is shown.

Build142 was compiled, signed, installed and read back. Its cold start obtained
JIT pools and entered Wine, and the new helper recreated its fixed build marker.
The user reports “Steamwebhelper is not responding”; the stable native log
independently records that exact guest window. Fresh webhelper/CEF records stop
in browser initialization, before observed BrowserReady or a new login success.
The captured log has no observed INT3/system_error/STATUS_NO_MEMORY signature;
that does not identify the blocking operation or establish a sole cause.
CEF timestamps in this file are UTC, whereas webhelper timestamps are local EST.

The existing LEAN switch changes virtual-memory monitoring/replay cadence in
addition to suspending fewer threads. It is therefore a broader experiment than
pure sampler removal. After confirming the failed process had ended, the same
installed142 was launched with only `steam64.env.MADEIRA_LEAN_DIAG = 0` appended
to a fresh configuration backup and verified by exact device readback. The new
ordinary launch opened only the configured developer shell and did not enable
JIT or start Wine; its login timeout is not an A/B outcome. The shell was
identity-verified and normally closed before using the established explicit
Steam64 Big Picture test argument. That session is the diagnostic A/B, not a
validated fix. Preserve explicit
rollback and obtain fresh browser/login evidence before a GPU-only comparison.

The exit-control stall has separate binary/stack evidence; see
[control stall evidence](STEAM_CONTROL_SPAWN_STALL_EVIDENCE.json). Build142's
menu no longer starts another Steam client when an existing Big Picture window
cannot be focused. Host tests and final helper sealing pass; actual in-game
exit and resumed navigation are still unverified. No new game was agent-launched
in these UI-only tests.

## Pure sampling refinement — Build143

The actual explicit142/LEAN0 test records fresh login Success at18:03:01 and a
new Big Picture window at18:02:51 local time. The helper marker also matches the
new existing-window menu implementation. Actual navigation is awaiting user
confirmation. This single successful login versus a failed LEAN1 startup is a
useful discriminator, not proof of causality: process placement also differs.
The ineffective ordinary developer-shell attempt is excluded.

The source now defaults only `MADEIRA_STEAM_UI_SAMPLING=0` in exact genuine Steam
sessions after config export. The same production policy gates server periodic
thread-sample/RIP/wprof bursts and the compositor's periodic stack walker.
An explicit `1` opts into sampling. Existing explicit broad LEAN configuration
continues to work independently; the pure default never writes LEAN or the VM
sweep setting. Raw error capture, actual-stall evidence, sync-census and ordinary
paths remain. No GPU/JS/CPU, allocation, replay, guard, authentication, FEX or
Valve change is part of this refinement.

Production-header ASan/UBSan tests exercise100 session/override/LEAN cases and
verify VM/JS/CPU environment preservation. Existing broad LEAN behavior and
launcher/early-selection/menu/focus/return regressions pass. Device validation
is still required. Do not install over the active142 test before reviewing its
real UI result; a successful build or login is not a measured speedup.

## Installed Build143 evidence

On the next resume, no iDeck process is present; the ended142/LEAN0 session log
was preserved (SHA256
`db4ab3ac989de032119d2900ca04605a76fab92c8624d945080beb81d1709402`).
Its process absence and lack of a clear fatal in that capture do not establish
normal closure or exclude a crash. The fresh official gameprocess log contains
no new game launch in that session.

Build143 main/helper profiles cover physical Kusch and remain valid through
November6; deep-strict signing passes. Installation succeeds and device app
metadata reads back143. Configuration readback is byte-identical before/after
upgrade. An initial CLI launch invocation is rejected for argument ordering
before app launch; corrected explicit automatic-JIT launch is the actual test.
Fresh Steam Success is recorded at20:01:06 local and a BPM window at20:00:46.
Official webhelper still explicitly disables GPU. V8/CPU/GPU settings are fixed.

A single menu command receives a matching UUID `menu-requested` reply. This
establishes a responsive helper control loop for that request, not visible
navigation, successful game exit or measured UI speedup. Current raw native-log
transfer returns CoreDevice7000/POSIX60; the runtime sampling marker has not been
retrieved. No process suspension, game launch, restart or further config change
is made while awaiting the user's143 menu/library observation. Mac lock guards
refuse Device Hub capture; no lock bypass. Next test only GPU automatic selection
once real navigation is established, retaining the same interpreted JS, CPU and
pure-sampling/VM policies. Keep the current session until the observation arrives.

User subsequently confirms143 menu is visible and browsing is more fluid. Keep
this as the verified user-observed baseline; do not turn it into a measured
speedup or a GPU claim. Game exit and repeated loops are still separate gates.

## Build143 GPU-only cold test and rollback

Only `steam64.gpu-acceleration=1` is appended to a fresh baseline backup and
verified by exact device readback. Same installed143, interpreted JS, CPU1, pure
sampling and VM policy. Actual new batch removes `-cef-disable-gpu`; fresh
webhelper no longer receives `--disable-gpu`/`--disable-gpu-compositing`. Native
marker confirms hardware-auto request. New login and BPM window are recorded.
This finally exercises the requested policy rather than prospective staging.

The official log records a Hot Roads launch20:16:19. The agent does not launch
it. A bounded native snapshot refuses before any pause because a game is
observed. A later normal-exit test also refuses before sending its request:
the original native PID is absent. No stale-PID attach, suspend, resume, close
or terminate is sent. Session-end cause remains unknown; user was asked whether
they manually closed the app. A later20:38 developer-shell startup log belongs
to another app open and must not be confused with the GPU test.

The preserved rotated GPU-session log contains a guest breakpoint at
`0x70e1ac48e2`; its actual loader base `0x70de590000` identifies libcef RVA
`0x35348e2`. The failed check/caller is not identified; later native lines exist.
This is not proof that GPU acceleration caused the breakpoint or app exit.
Footprint reaches about4GiB. A D3D11 warning is present but not attributed to
CEF instead of the running game. Hardware CEF rendering and performance remain
unverified. No assertion/protection/allocator workaround is applied.

The candidate is restored to the user-confirmed good software baseline after
fresh exact comparison, with byte-exact rollback readback. GPU automatic
selection is not promoted as a default. Preserve menu/diagnostic performance
improvements and all account/game data. Future GPU work needs a CEF-owned
renderer/backend discriminator and actual comparable UI observations, separated
from game activity, plus investigation of the observed breakpoint and resource
pressure. No new release or general stability claim follows.
