# Native macOS ARM Steam on iOS — experiment log

## 2026-10-26: isolated baseline and first build

- Baseline: iDeck `369cbc88d77370433894ee6b31c92eaac2f05091`, experiment branch `experiment/mac-arm-steam-ios`. Main workspace was at `0ec1eb7` with uncommitted changes; those changes are not included in this worktree and remain untouched. Experiment is based on the newer fetched origin/main. Submodules are not initialized here: FEX f59cab9, DXMT 128b297, madeira-dock 72558e4, Wine 9129e96. No submodule change.
- Device: iPhone 15 Pro Max (iPhone16,2), iOS 27.0 build 24A435, Developer Mode enabled; Xcode 27.0 (27A266a). Existing iDeck Build67 and Madeira Build8 are installed and must not be replaced. Device was connected at inspection; no on-device macOS probe has run.
- Current baseline source: `SteamUIExperiment.Plan` starts Windows Steam in Wine; `WineProcessBridge.m` starts the Wine process thread; `process_ios.c` maps Windows process creation to pthread-based pseudo-processes and injects Chromium `--single-process`. These interfaces do not implement native macOS `posix_spawn` or prove a native Steam helper can run in-process. Existing SteamOwnedLibrary/SwiftSteam install and Wine launch flows are candidates for later integration, not yet a tested native Steam bridge. Baseline operating Windows Big Picture is established separately; no paired measurements were performed in this experiment.
- Reference source revisions inspected: macos-on-ios-public `c2562a333d4de4c08da4ceb4a4f1485bddb84e04`, CyPort `65e2e57a95263f60516f567e274780d8ebd97072`, ullage `e09e8dddfc2a5d996d18aa21e6f7370b55aa3cbb`, ullage-patches `d2a5b75ed247f410cda746ca2cfe205e26f4f1ec`, NotProton `c4e7409914f412901747773728e7a1ff07836c23`, Bridgeplay `8e18aa819a98c2b288c1cf3af7395b45e2277f04`. Source checkouts were obtained outside this repository; further source and licensing review remains necessary before reuse. macos-on-ios is MIT and describes iOS retagging and UIKit shims with user development signing; its own documented working examples are not Steam. NotProton explicitly targets Steam and CrossOver on macOS. Ullage describes a macOS Steam/Wine bridge and platform-selection approaches. These reports do not establish iOS support or Steamworks success here.
- Hypothesis: the public minimal AppKit/Metal probe can build with the locally installed SDK and serve as the first device test.
- Test: clean reference `probe/build.sh mac shim` with macOS/iOS SDK 27.0. macOS ARM64 binary compiled, but shim link failed on missing GCController and GCMouse symbols. The source invokes GameController but its probe link command does not link the framework.
- Discriminating test and minimal change: link `-framework GameController` in a disposable copy of the reference build script; macOS probe and iOS AppKit/Cocoa shims then build successfully. Reproduction: `scripts/experiments/build-mac-probe.sh <clean-macos-on-ios-public-checkout> <absolute-output-dir>`. The script applies the one-line adjustment to a disposable copy; it does not modify the reference or device. It pins the reference revision. The source remains MIT licensed, and is not vendored.
- Artifacts: `/private/tmp/ideck-repro-macprobe/`; macOS Mach-O SHA256 `519d12d0568486acf532de50fcbeb3597d094cee4c9520a2ea7f7d9ff04009cf`, AppKit shim SHA256 `1a46a8c8c2c3f84c103b681bb4a89730f498bd709d02b423ec25e1a5ea39ad42`. These are local unsigned builds, not iOS execution or proof of Steam support.
- Gate: reference conversion requires an exact development provisioning profile for a new isolated app identifier. Existing local profiles checked cover other installed apps, not the new identifier. The reference profile generator also needs `xcodegen`, which is not installed. Do not reuse the existing iDeck identifier or delete another app. Next: use a supported Xcode automatic-signing workflow to create an isolated profile, verify free-signing slot availability, retag/sign the probe, install without replacing anything and observe actual launch/rendering. If signing or a free app slot prevents installation, record the exact error and continue independent source analysis. Never assume a signed probe demonstrates Steam.
- Milestones: native probe on device **not tested**; native Steam **not started**; interactive UI, authentication, Windows depot, game execution and return **not tested**. No performance comparison or GO claim is supported.

## 2026-10-26: retagging and isolated signing attempt

- Baseline commit: `1df9924`; target remains iPhone 15 Pro Max / iOS 27.0. Current device listing showed paired/available; no install or app termination performed.
- Test: retag the compiled ARM64 macOS probe with `vtool` and redirect AppKit/Cocoa to the locally built shims and the versioned system-framework paths to their iOS form. `vtool` reports platform IOS, minimum17.0, SDK27.0; `otool` shows shim rpaths and no macOS-versioned AppKit/Cocoa dependency. Reproducible script now includes this static test. Retagged private artifact SHA256 `928e54d1db726e7feaec6fcfd1744767f20597d5891d2a97bd03996ecfc7be36`. This does not demonstrate dynamic loading, signature acceptance or rendering.
- Signing attempt: a minimal independent Xcode project requested automatic iOS development signing for `com.kuschqin.ideck.maclab.macprobe` with team D7KZKWD692. Xcode build failed with `No Accounts` and `No profiles ... were found`. No new profile or device installation resulted. User asked to sign into Xcode Accounts; do not repeat unchanged signing attempt until login state changes. Private build log: `/private/tmp/ideck-profile-probe/build.log` (do not publish raw profile/signing material). Existing working bundle IDs were not reused.
- Source investigation: NotProton's `dylib/hooks/hook_spawn.c` filters environment then calls original posix_spawn; it still expects actual child processes and is not an iOS pseudo-process implementation. Ullage's `docs/platform-selection.md` reports a macOS experiment in which a platform override did not select the Windows depot and uses a global Windows platform setting; its result is not an iOS validation and may affect other app installs. SwiftSteam/SteamOwnedLibrary already implements owned-depot downloads and can be evaluated as a separate fallback. Do not conflate its account state with Steam's native client.
- Next: after Xcode login, repeat only the isolated profile-generation step, verify actual app slot availability, then sign/install/launch the probe and capture the first result. Continue independent process/IPC research meanwhile. Steam login, library, game execution and return remain untested.

## 2026-10-26: signing retry after user reported login

- User reported that they had logged in and authorized use of that session.
  Retried the same isolated Xcode automatic-signing project for
  `com.kuschqin.ideck.maclab.macprobe`; Xcode again reported `No Accounts` and
  no matching development profile. This is the actual command result, not a
  conclusion about which account or application the user signed into.
- Requested Xcode UI inspection; computer control reported the Mac locked and
  could not unlock it. Asked the user to unlock so the account and selected
  developer team can be inspected. No credential entry, lock bypass, install,
  or mutation of an existing app was attempted. Log stays private at
  `/private/tmp/ideck-profile-probe/build-after-login.log`.
- Additional reference-source evidence: NotProton explicitly preserves its
  dylib insertion for `steam_osx` and `Steam Helper`, while calling original
  exec/spawn APIs. Ullage includes an exec-based helper. Neither establishes
  an in-process Steam helper on iOS. The probe's `main.m` exercises AppKit
  application/window setup, Metal device creation and mouse/touch handling;
  these are targets to validate on device, not observed device results.
- Next: after native Mac unlock, inspect Xcode Accounts and developer team via
  UI; use only a supported authorized signing flow. Retry profile generation
  only when account availability changes, then verify exact profile, device,
  free slot and probe signature before installing isolated app.

## 2026-10-27: comparison with prior successful installs

- User reported Xcode login available in other sessions and Mac unlocked.
  Reviewed the prior iDeck Build67 deployment: it explicitly reused an existing
  development identity and the two exact iDeck app/helper profiles, then signed
  and installed with the same bundle ID. That does not demonstrate issuance of
  a profile for this new, isolated experiment. The OrionTV workflow likewise
  uses the login keychain and a matching existing app profile; those identities
  must not be reassigned to this probe or its container.
- Automatic provisioning for the probe previously returned No Accounts and no
  profile; current CLI runs as `kuschqin` in an Aqua session using
  `/Applications/Xcode.app`. The computer-control surface still reported the
  Mac locked, despite the user's report. Treat that as a tool observation, not
  proof the physical desktop is locked. Xcode account/team UI has not been
  observed, and no account or keychain changes were attempted.
- Next: obtain access to Xcode Accounts in the logged-in interactive session,
  or use an Apple-issued development profile explicitly matching the isolated
  probe ID. Preserve the installed apps and do not substitute their IDs.

## 2026-10-27: physical device graphics probe

- User supplied the account/team; Xcode GUI visibly showed the Personal Team.
  Previous CLI `No Accounts` did not mean the GUI account was absent. Opened
  the isolated `ProfileProbe` project in Xcode, selected Kusch and built. Its
  temporary source lacked a UIKit link and failed to link, but the GUI did
  provision a matching iOS development profile for the separate probe bundle,
  with get-task-allow and the target device. No credentials were recorded.
- Signed the public reference probe and shims with that profile and existing
  development identity. Default keychain selection failed `errSecInternalComponent`;
  explicitly selecting the existing login keychain succeeded and `codesign
  --verify --deep --strict` passed. The installed bundle is separate from iDeck
  and Madeira. It carries iOS LC_BUILD_VERSION min17 SDK27.1; no entitlement
  beyond the basic development identity and get-task-allow was requested.
- Actual physical device test, iPhone 15 Pro Max iOS27.0 (24A435): independent
  probe install and launch succeeded. Console captured `PROBE main`, UIKit shim
  foreground and `applicationDidFinishLaunching`, macOS-compiled metallib
  loaded, `PROBE pipeline OK` and scene active. Captured device screenshot
  shows the expected colored triangle; render and native entry are observed.
  Console observer timed out after 25 seconds; a fresh device process list
  still showed the probe process, so observer timeout is not process exit.
  Private screenshot SHA256 `fe9035ec233db87b47b826a2beb2eb10e635aa8d0d9029aa5673b3cdcd0e4e8b`;
  private console log SHA256 `5889f7bca48f20e38abcfdc711528868a97801a4c10552e3433ef2cfd78085bb`.
- Touch interaction has not yet been evidenced; user was asked to tap the
  triangle. This proves only the minimal probe, not Steam, authentication,
  CEF, helper process creation, game installation, or performance. Next: verify
  touch via device log or framebuffer change; then obtain and inventory Valve's
  official macOS client privately and identify actual architectures/dependencies.
- Follow-up real-device touch test: relaunched the same isolated probe under a
  fresh bounded console observer. After the user tapped, actual console output
  recorded `PROBE mouseDown` and changing hue, confirming UIKit touch reached
  the macOS-compiled AppKit callback. Private raw log SHA256
  `b06f258fa94ceb7e8143b665351e1aee8025adf040efd3a33b7c886e8787c698`.
  This supersedes the prior touch-unverified status. The observer may end while
  the app remains active; no Steam functionality is implied.
- Retrieved Valve's official macOS installer link from
  https://store.steampowered.com/about/ into private experimental storage.
  The downloaded DMG SHA256 is
  `e1abfbaaa7be3e0f48a0e0d4c313233e05861b1d26af32830ddc838be88f2691`.
  Its read-only mounted `Steam.app/Contents/MacOS/steam_osx` is **x86_64 only**,
  SHA256 `4d59bc0779fceaf1ee0c50ed564a7301424c6b5f73b958fc80afc8812c5b03cd`,
  bundle version 6.0. The image was detached after inspection. This is the
  distributed bootstrapper, not proof about a fully updated or beta client;
  do not call it an ARM64 Steam client. No Valve binary is committed.
- Next discriminator: locate a legitimate fully updated native ARM64 macOS
  Steam installation or official beta package and inspect all main/helper
  architectures without using or changing an existing user account. Treat
  missing ARM64 as an unresolved acquisition gate, not a proven absence. If
  copying, use a private isolated source and preserve existing Steam state.

## 2026-10-27: official ARM64 client acquisition and startup failures

- Source baseline `2c5d466`. Origin/experiment branch checked before work; no
  uncommitted work existed in this worktree. Working iDeck/main is untouched.
- Retrieved the official HTTPS `steam_client_osx` update manifest, version
  **1792618285**, and all23 default packages, verifying each size and SHA256
  against that manifest. This is HTTPS provenance plus integrity, not an
  independent verification of Valve's kvsign signature. Fetching does not
  require login. New fetch/staging scripts reproduce acquisition outside Git.
- Main `steam_osx`, `steamclient.dylib`, Steam Helper and CEF all contain ARM64
  and x86_64. The earlier Intel-only DMG bootstrapper is not representative of
  the updated client. Main SHA256 `57bf5908b17144687f3b64434dd4f59df291981a57e48276e5f4964b87ca33b7`,
  client dylib `b9d62be2ac64b77dc77e1d19eefcf3880df99495c7db85b30623095310b6a6bd`,
  Helper `8047352bdbd37800dc3ff4d82920c0c9a285c4d578b2b57c796346c467b00f90`,
  CEF `4bee8be5d09633bf5d875228357b0e9aa10b06c15dd405821927dfe2d832862b`.
- Staged a credential-free bundle from the official packages. Seven legacy or
  optional Intel-only binaries were excluded from conversion, listed in
  experiments/mac-arm-steam/README.md; no claim those functions work. The
  remaining56 Mach-O files were thinned/retagged with public MIT converter
  c2562a3. Generated shims contain many placeholders (340 AppKit symbols plus
  others), not complete API implementations. No authentication was attempted;
  security/authentication placeholders require audit before account testing.
- Conversion first stopped at AppleDouble metadata during signing. Removed
  only that metadata from the converted copy; fixed the moved steam.sh link
  and three helper dylib links, explicitly selected login keychain, signed
  nested code/bundles and verified deeply/strictly. The independent probe app
  was upgraded to the Steam experiment; working iDeck67 and Madeira8 remained.

### Experiment 1: exact first device fault

- iPhone15ProMax/iOS27.0: install and launch succeeded; official ARM64 code
  entered its startup. Process terminated SIGSYS12. Crash report identifies
  `libsystem_kernel.dylib semget`, with return into steam_osx RVA0x231730.
  An earlier optional crashhandler preload error about thread_bss file offset
  is also present; it is not the terminating frame and remains unresolved.
- Hypothesis: iOS disallows the required SystemV semaphore syscall. A diagnostic
  override logs only count/flags, returns ENOSYS and does not fabricate success.
  Device shows count1 flags0x7b6/0x780, synchronization assertions, then a second
  SIGSYS at semop. These are actual IPC failures, not CEF initialization.

### Experiments 2–4: real process-local semaphore subset

- Implemented bounded keyed semaphore objects using pthread mutex/condition,
  atomic batches, NOWAIT, zero/decrement waits, SETVAL/GETVAL and removal wakeup.
  First device run reaches beyond semget/semop SIGSYS and reveals SEM_UNDO0x1000
  requests, initially rejected. Added single-host-process SEM_UNDO semantics:
  thread exit does not undo; at host process exit the entire local registry
  vanishes. No cross-process, fork or pseudo-process lifetime behavior claimed.
  Unknown flags/commands remain explicit errors. Limitations in component README.
- ASan/UBSan production-code host tests passed atomic failure/no partial update,
  blocked waiter release, removal EIDRM, stale IDs,128slot exhaustion/reuse,
  unsupported flags and thread exit without process undo. iOS Werror compile
  passed. Linked dylib exports semget/semctl/semop, deep signature verified.
- Device regression: no SEM_UNDO unsupported errors and no semaphore SIGSYS in
  that run; next terminating error is an ObjectiveC missing
  `+[NSFont labelFontOfSize:]`. This is startup progress, not usable Steam.
- Corrected a test command detail: a `--` placed AFTER bundle ID had been passed
  into Steam argv. Correct devicectl invocation puts it BEFORE bundle ID. The
  corrected argv was captured; no claim this alone caused the runtime advance.

### Experiments 5–7: font call and native re-exec

- Added only the observed missing NSFont class method through UIFont's public
  system font; preserves an existing implementation. Linked marker and actual
  device constructor log `labelFontOfSize bridge=1` confirm inclusion.
- Device then progressed through updater setup (several generated AppKit control
  methods still placeholders), changed into its cache Steam.AppBundle path and
  exited255 with `exec failed: Bad address`. No login/CEF window observed.
- Single-hypothesis launch with the native client's recognized inhibitbootstrap
  option still attempted the same transition, then exit0. Exit0 is NOT success.
  Cached MacOS directory actually contains only public/package directories,
  without steam_osx; correct cached-client layout is not established.
- Added a read-only execv interceptor that forwards the call unchanged and logs
  only executable basename and result/errno. It has been built, deeply signed
  and installed. Launch7 was refused CoreDevice10002/FBS Locked; no execv trace
  yet. Asked user to unlock once; do not repeatedly relaunch while still locked.
- Next: after unlock launch the installed diagnostic once with corrected argv,
  distinguish null/missing executable path from sandbox re-exec restrictions.
  No instruction bytes, FEX/Wine/DXMT, licensing or authentication checks were
  modified. Optional crashhandler zero-fill metadata and native Helper process
  architecture/IPC remain subsequent concerns. CEF/login not reached.

### Reproduction and status

- `experiments/mac-arm-steam/README.md` documents fetch/stage and local tests.
  All proprietary payloads and raw device logs remain in `.madeira-install`,
  outside the Git checkout; hashes in MAC_ARM_STEAM_EVIDENCE.json.
- Offline manifest and archive boundary tests (7 cases), real semaphore
  concurrency tests under ASan/UBSan, iOS compile and deep signature passed.
  New staging script reproduced source construction from verified packages.
- Reusable existing runtime interfaces: wineserver_start(prefix) then readiness,
  wine_process_start(prefix), wine_process_is_running and initial-process exit
  reports. ContentView owns JIT pool/session/environment and Metal display
  lifecycle. A future Steam Play bridge must validate executable/working-dir/
  AppID/arguments before this path; directly calling wine_process_start is not
  enough for coexistence/return. SwiftSteam's owned-depot downloader is separate
  from native Steam authentication/session. No such integration is implemented.
- Compatibility matrix: minimal macOS AppKit/Metal probe + touch PASS on device;
  ARM64 Steam main entry PASS; single-process semaphore subset PARTIAL; genuine
  CEF/login/library/Windows depot/gameplay/return/relaunch NOT VALIDATED. No
  performance comparison, stable IPA or final GO is justified at this stage.

## 2026-10-27 04:10 EDT scheduled continuation: path-contract discriminator

- Revalidated clean experiment worktree and origin at114635d; remote experiment
  head matched. One fresh lock-state query: passcodeRequired=true,
  unlockedSinceBoot=true. Did not repeat installs/launches or the existing
  unlock request. Current installed diagnostic remains the execv-observer build.
- Independent read-only examination of the exact official ARM64 main executable
  found one execv call site: it calls realpath$DARWIN_EXTSN, stores the returned
  pointer as argv[0], and passes that pointer directly as execv's path, without
  a NULL guard at that boundary (preferred addresses0x100029bf4–0x100029c00).
  A native host reproduction of execv(NULL, argv) returned-1/EFAULT without
  executing a process. This makes the earlier Bad address insufficient evidence
  of an iOS exec policy restriction. No private raw disassembly is committed.
- The actual reference shim `libSystem.m::_NSGetExecutablePath` advertises
  `<app>/Mac/Contents/MacOS/steam_osx`, while converter moves the main executable
  to `<app>/steam_osx`. The converted bundle lacked the advertised steam_osx
  path. Previous steam.sh/helper links were corrected, but this separate logical
  executable link was missing. This is a reproduced bundle/shim contract defect;
  it has not yet been confirmed as the path used in the device's re-exec call.
- Minimal candidate: add only the missing in-bundle logical executable symlink
  to the existing signed root executable, with strict path/parent/link guards.
  No instruction bytes, licensing/authentication or exec result are changed.
  New fix-mac-executable-layout.py is idempotent and refuses conflicting files
  or links; three offline fixture tests passed, including the missing-path
  reproduction and symlink conflict/escape rejection. Actual converted artifact
  now resolves the advertised path to the root executable. Re-signed candidate
  and deep strict signature verification pass; NOT installed/device-tested.
- Next after unlock: preserve the already installed exec observer if a control
  trace is desired, then deploy candidate and compare. The first changed device
  failure distinguishes this path-contract correction from the still-unproven
  iOS self-exec restriction. Do not treat the candidate or host test as CEF/UI
  success. Native Helper spawning and other missing APIs remain unresolved.
