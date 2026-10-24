# Native Steam Big Picture on iOS via Madeira

User-authorized research task, 2026-10-22. This is a task specification, not a
claim that any milestone has been achieved. Record progress separately.

## Objective

Investigate, implement, and validate a proof of concept that runs Valve's genuine
Windows Steam Big Picture UI locally on a non-jailbroken iPhone using Madeira.
Do not recreate Steam's UI in SwiftUI, stream Steam from a PC, emulate DRM, or
bypass authentication. Target: iPhone 15 Pro Max, Apple A17 Pro; iOS with JIT
through Madeira's existing debugging workflow.

## Sources and mandatory first reading

Primary upstream: https://github.com/willfaust/Madeira
Working fork: https://github.com/kuscholar/Madeira
Historical CEF research: https://github.com/deezhizyu/madeira

Read README.md, docs/BUILDING.md, docs/MADEIRA_DOCK.md,
docs/STEAM_SIGNIN.md, and the historical fork's STEAM_CEF_HANDOFF.md and
ARCHITECTURE_ANALYSIS.md first. Pin source revisions and distinguish historical
observations from verified current behavior. Do not assume historical fixes are
present in the current main branch.

## Phase 0: repository audit (mandatory gate)

1. Inspect the current repository and all submodules.
2. Record exact commit hashes, build dependencies and missing resources.
3. Identify Wine process creation, wineserver integration, the FEX JIT entry,
   Steam launch, Metal composition and session lifecycle.
4. Determine whether historical CEF implementation can be reconstructed from
   published commits.
5. Identify where current Madeira Dock deliberately avoids steamwebhelper.exe.
6. Produce docs/BIG_PICTURE_ARCHITECTURE.md.

Do not modify runtime code until this audit is complete.

## Phase 1: restore real Steam CEF startup

Implement a separate feature-flagged experimental Steam UI launch mode.
Preserve existing Madeira Dock. Launch Valve's real client; allow
steamwebhelper.exe and libcef.dll to initialize; preserve genuine Steam
authentication and licensing. Log pseudo-process creation/termination, CEF
initialization, BrowserReady events, window creation and rendering. Never log
secrets, refresh tokens or passwords.

First milestone: an interactive real Steam login window, before Big Picture.

## Phase 2: diagnose compatibility, one hypothesis per experiment

### A. libcef.dll+0x41258FB crash

Distinguish KERN_MEMORY_ERROR from protection failures. Trace relevant Mach VM
mappings and backing objects; inspect section/shared-memory lifetime. No blind
retry or mprotect workaround.

### B. Chromium/Skia rendering

Reproduce historical tile displacement if still present. Capture framebuffer
checksums and source/destination buffer comparisons. Compare software raster and
GPU paths. Build an isolated x86-64 PE test when possible. Determine whether FEX
translation is responsible rather than assuming it.

### C. Steam CM failures

Separate TCP, TLS, WebSocket and authentication failures. Inspect Steam's own
logs while redacting private information. Never bypass Steam Guard or DRM.

For every fix document: observed failure, hypothesis, discriminating test,
evidence, minimal patch and regression results.

## Phase 3: genuine Big Picture

Only once CEF is reliable, add a genuine Steam Big Picture feature flag;
investigate -bigpicture; display the actual Steam UI via Madeira's existing
display pipeline. Test Bluetooth controller input, navigation, library loading,
scrolling and account persistence. Neither SwiftUI nor WKWebView may substitute
for the actual UI. Wired Backbone success is not Bluetooth validation.

## Phase 4: game launch and return

Start an installed game from Big Picture and return to Steam. Preserve Valve's
legitimate license checks and Madeira's existing game runtime.

## Engineering constraints

- No jailbreak or assumed private entitlements.
- No unrelated changes to the primary gaming path.
- Preserve GPL and all component licensing obligations and contribution rules.
- Prefer isolated tests to device-only debugging.
- A successful build does not prove a fix is linked into the final Mach-O.
- Never invent test results. Device validation requires actual device logs or
  test artifacts; label user-reported results separately.
- Never merge unfinished experiments into the working baseline.
- If compilation/device access is unavailable, finish verifiable local work and
  explicitly distinguish verified findings from hypotheses and blocked checks.
- Prioritize whether genuine Steam UI is technically achievable over polishing.

## Deliverables

1. docs/BIG_PICTURE_ARCHITECTURE.md
2. docs/CEF_COMPATIBILITY_MATRIX.md
3. Feature-flagged Steam UI launcher
4. Reproducible build instructions
5. Minimal diagnostic test programs
6. docs/BIG_PICTURE_POC_RESULTS.md
7. Evidence-backed final GO / NO-GO assessment

## Recurring execution and baseline preservation

Continue every 5 hours 5 minutes in the Codex thread scheduled by the user.
The verified local gaming baseline is Build 8; its fixes are described in
LOCAL_IPHONE_REPAIR.md. Keep main as the working baseline. Use an isolated
worktree and experiment/steam-big-picture (or a documented topic branch) for
research and experimental commits. Before a run, inspect branch/remote/worktree
state and prior results; resume rather than restarting completed work. Do not
reset other changes, force push, overwrite saves, uninstall the working app or
publish credentials, signed provisioning assets, Steam/Valve binaries or games.
Commit and push reviewed, tested research progress only to the fork's experiment
branch; do not send upstream PRs or messages. If device access requires user JIT
or unlocking, record the specific gate and continue independent local work.
Each run should leave reproducible commands, evidence paths/hashes, its current
phase and the next discriminating experiment in BIG_PICTURE_POC_RESULTS.md.
