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

## 2026-10-27 08:37–09:12 EDT: unlocked-device startup progression (local changes)

- Starting revision2d82b99b5ae4d71fa7f7d9c4b848658802b73621; origin and
  remote experiment head revalidated equal. All subsequent changes below are
  LOCAL/uncommitted. Tuesday daytime is outside the user's22:00–07:00 Git
  window. Production iDeck/Madeira and their containers remain untouched.
- User unlocked the actual iPhone. Same device/iOS27.0(24A435), official manifest
 1792618285. No account or credential entry in this experimental container.
- Control launch8: exec observer confirms path=NULL, result-1/errno14(EFAULT).
  Adding advertised executable link changes launch9 to a real steam_osx basename
  and result-1/errno1(EPERM). This proves the path defect separately from the
  subsequent denied native self-exec; no denial is intercepted as success.
- Exact binary's STEAM_APP_BUNDLE_PATH environment contract provides a simpler
  startup route: passing the actual installed `<app>/Mac` enters second-stage
  initialization directly, with unchanged executable instruction bytes. Observer2
  logs only fixed allowlisted switches, total/redacted counts, never arbitrary
  argument strings. No exec failure was suppressed. Native helper creation is
  still unresolved and must be tested separately.
- Launch11 reaches Steam's case-sensitive volume rejection for code/data roots.
  Replaced the reference's limited case matcher with an app-container-scoped
  pathname view: absolute/relative and openat paths, case-insensitive component
  matching, symlink containment, ambiguity refusal. A private fixture's eight
  actual-device operations ALL PASS in launch12: create, alias read/same inode,
  O_EXCL collision, openat, rename, stat and unlink. Physical volume properties
  unchanged. Case-collision scan of the supplied Steam tree found0 collisions.
- Launch13 enables reporting this emulated view only for a successful original
  NSURL resource query, experiment Info flag, completed eight-operation self-test
  and canonical app bundle/data scope. Other keys, failures and unready/outside
  paths keep the original result. This is NOT a complete case-insensitive POSIX
  filesystem (hardlinks, all *at APIs, concurrent rename/symlink races and Unicode
  normalization equivalence remain unproven). It must stay isolated/experimental.
  Steam now passes both checks but fails loading steamui because crashhandler's
  @loader_path/Frameworks/Breakpad.framework is absent under MacOS.
- Added only an internal `Mac/Contents/MacOS/Frameworks -> ../Frameworks` alias,
  with conflict checks/idempotence. Four synthetic layout tests PASS. Launch14
  then actually loads genuine steamui.dylib and SDL3.4.0, before SIGSEGV in
  CFStringCompare: generated CGDisplayModeCopyPixelEncoding returnsNULL. Actual
  ARM64 SDL returnsite0x10644c and its public Cocoa source agree on that contract.
  Read-only source reference:
  https://github.com/libsdl-org/SDL/blob/release-3.4.0/src/video/cocoa/SDL_cocoamodes.m
- Narrow pixel-encoding override returns a retained CFString SDR/ARGB8888 mode
  descriptor. ASan/UBSan1000-iteration copy/compare/release and null test PASS.
  Launch15 passes that site; next SIGSEGV is objc_retain from SDL's CF array
  insertion(returnsite0x105634). Reference mode token was a plain C struct.
- Replaced only mode Copy/CopyAll/Retain/Release with a genuine stable CF object
  and CF ownership. ASan/UBSan1000-iteration SDL-style CF array/retain/release,
  identity and invalid-display tests PASS. Launch16 passes display initialization,
  then SIGSEGV copying cursor pixels into NULL NSBitmapImageRep bitmapData;
  actual SDL returnsite0x10a620, not a CEF fault. Implementing a bounded RGBA8
  bitmap store next; no cursor rendering or full NSImage API is claimed.
- Every installed candidate was developer-signed and deep/strict verified.
  A separate optional bootstrap crashhandler has malformed zero-fill metadata;
  this warning is not the terminating fault in these later traces. Duplicate
  GURLHelper classes and numerous generated AppKit/CoreVideo/Carbon placeholders
  remain. No CEF/login/library/Steam Guard/Windows depot/gameplay success yet.

- Launch17's bounded RGBA8 storage passes the earlier NULL memmove site. It
  reaches VGUI/chromehtml initialization and records CEF child creation failure,
  then an unimplemented fontWithName:matrix: selector exception. Added only
  uniform/unrotated UIFont-backed handling; next launch18 SIGSEGV is in that
  matrix reader. Launch19 crash confirms the pointer contains ARM64 instruction
  bytes(0x910003fda9bf7bfd): the generated NSFontIdentityMatrix is incorrectly a
  FUNCTION, whereas the actual AppKit SDK declares `const CGFloat *` DATA.
  Corrected the exported data ABI. Final linked AppKit shim's symbol is typeD,
  with host sanitizer ABI test PASS. This latest correction is NOT device-tested.
- Launch18 and19 read-only observers confirm actual fork=-1/errno1(EPERM).
  Launch19 resolves both calls to exported CreateSimpleProcess returnsite
  libtier0_s+0xbe80. An independent explicit native self-posix_spawn probe in
  that SAME signed app returns1/EPERM, created=0. This is a verified constraint
  of this actual device/app sandbox/signing environment, not an inference from
  a blank window. No fake successful PID or denied-syscall workaround is used.
- Read-only exact tier0 analysis: CreateSimpleProcess invokes fork, child-side
  cwd/environment/exec, and exposes process activity/suspend/resume/terminate/
  exit methods backed by kill/waitid/waitpid. Native Chromium single-process
  does not itself provide these parent/Helper lifecycle contracts. Found a
  CSingleProcessPipe class string, but no verified client switch selecting an
  in-host CEF browser; do not confuse a string with a working launch mechanism.
- Installing the next font-data candidate failed CoreDevice4000/peer unreachable.
  One fresh device inventory confirms Kusch unavailable. No repeated install,
  launch, lock workaround or production-app action. Last actual run is launch19
  (crash recorded), not an assumed live/stale PID. Asked user to reconnect once.
- Prepared experimental CFBundleVersion2, with original developer entitlement
  scope, all three rebuilt shims signed and final deep/strict verification PASS.
  Read-only final markers confirm native-spawn observer, CEF-load discriminator,
  and corrected NSFontIdentityMatrix DATA export are linked. This Build2 is
  NOT installed. No install success inferred from local signing.
- Reproducible builder now reads pristine MIT source at c2562a3 via git-show,
  applies guarded source-level overrides and builds three dylibs in a disposable
  converted copy. Actual rebuild PASS. Unified local regression PASS: manifest3,
  staging4 and layout6 tests; semaphore concurrency under ASan/UBSan; encoding,
  CF-mode ownership, bitmap bounds/overflow/unsupported format and font DATA ABI
  tests under ASan/UBSan; all device-only new sources iOS Werror compile.
- Security gate remains: inspection found generated macOS AuthorizationCreate,
  AuthorizationExecuteWithPrivileges, SecKeychainFindGenericPassword and other
  legacy functions with NULL placeholders(also zero/success as OSStatus). No
  authentication attempted; audit/implement proper fail-closed typed contracts
  before asking a user to authenticate. Public reference forwarding wrappers
  also need availability checks. These stubs are not permission to skip checks.
- Next single discriminator after reconnection: install prepared isolated Build2
  preserving its container; launch ONLY IDeckCEFLoadProbe=1. Normal signed dyld
  must load the genuine converted CEF framework and resolve required exports.
  Probe exits before Steam main/CEF initialization; success would prove loading
  only. Then decide whether a minimal in-host Helper/IPC experiment is feasible.
  Do not implement a fake fork/getpid model. Authentication/UI, Windows depots,
  games/return and comparative performance remain unverified.
- Current recommendation: continue only the bounded in-process CEF feasibility
  test. Direct unmodified macOS native-child-process architecture is NO-GO in
  the tested configuration; the overall in-process architecture is UNDECIDED.
  Existing Windows Steam route remains the working route. No improved startup,
  stability, memory/CPU or game reliability result has been measured.


## 2026-10-27 09:15 EDT scheduled continuation

- Origin/branch/worktree checked: experiment/mac-arm-steam-ios at2d82b99;
  live remote experiment head remains2d82b99b5ae4d71fa7f7d9c4b848658802b73621.
  Preserved the preceding run's uncommitted source/diagnostics. No overlapping
  device experiment found. Current source snapshot and prepared Build2 shim
  hashes exactly match the recorded evidence; no reason to repeat passed tests.
- One fresh device inventory still reports Kusch unavailable. Existing reconnect
  request remains pending; no repeated install/launch or user notification.
  No on-device CEF result added. Prepared Build2 remains uninstalled.
- PhaseB next experiment remains the explicit load-only IDeckCEFLoadProbe, after
  actual reconnection. All locally verifiable build/ABI work for that test is
  complete; no new speculative runtime patch. Main and working app untouched.
- Local America/New_York Tuesday09:15 is outside the allowed Git window;
  nothing committed or pushed, and no wait automation created.

## 2026-10-27 13:13 EDT direct continuation: CEF constructor/VM discriminator

- User said continue. Revalidated origin, experiment branch and remote exact
  HEAD2d82b99b5ae4d71fa7f7d9c4b848658802b73621; preserved preceding uncommitted
  changes. Kusch now available and actually unlocked. Installed the previously
  prepared, deep/strict verified isolated Build2. No production app action.
- Actual launch20 ONLY IDeckCEFLoadProbe=1 reaches load=begin, then fails in the
  genuine ARM64 CEF library's global constructors, BEFORE dlopen returns or any
  cef_initialize call. Two real mmap requests for17179869184bytes(16GiB),
  PROT_NONE, MAP_ANON|MAP_PRIVATE, tag253 fd0xfd000000 return ENOMEM12. Native
  crash is EXC_BREAKPOINT at CEF RVA0x3b4dda0 with the same allocator chain.
  This is not the historical Windows libcef fault. The nearest exported Rust
  symbol printed by the stripped crash report is NOT a reliable function name.
  Exact read-only ARM64 disassembly confirms the16GiB constant and BRK fatal.
  No smaller substitute, fake mapping, mprotect change or instruction patch.
- Standard developer debugging discriminator: devicectl --start-stopped followed
  by Xcode's own `lldb device select` / `device process attach`. Initial batch
  attempt(launch21) raced the asynchronous attach and produced no valid CEF
  result. Interactive launch22 actually stopped at dyld_start under LLDB. Remote
  shared-cache reads were slow, an interrupt timed out, then normal detach
  completed. Do not interpret waiting or a running PID as progress/success.
- After the normal attach/detach, launch22 crash confirms CS_DEBUGGED was added
  (CS_DEBUGGED bit0x10000000 is added; other bits also change), yet the same
  CEF RVA0x3b4dda0 and allocator
  return chain recur. This is evidence that the DEBUGGED flag alone did not
  remove this fatal, NOT a claim of continuous attached CEF validation.
- Added an explicit IDeckNativeVMProbe=1 discriminator, no CEF or Steam main.
  Uses the genuine libc mmap/munmap, sequential PROT_NONE reservations, and
  TASK_VM_INFO range; no writes to reserved memory. Saves its own numeric result
  file under Documents/ideck-native-vm-<pid>.txt in the isolated container.
- Build3 is INVALID as probe evidence: a C compile error left old dylibs; the
  outer shell lacked fail-fast and re-signed/installed the old artifact. It was
  NOT launched as a VM test. Corrected the compile errors; subsequent command
  used set-eu, Werror compile, successful full shim rebuild, explicit final
  dylib VM-marker assertion, signature and deep/strict verification BEFORE
  install. This is why build/sign/install receipts alone are insufficient.
- Actual Build4 launch23 VM-only result: CS status query succeeds/debugged0;
  TASK_VM_INFO succeeds(count93), reported min0x102c54000 max0x7180000000.
  4KiB and1GiB reservations succeed and unmap;16GiB and32GiB return ENOMEM12.
  cleanup1/memory-written0, diagnostic exit0. Exit0 means the test completed,
  NOT that CEF or16GiB reservations worked. Do not infer a63GiB/512GiB range
  from older comments: use this actual iOS27 measurement. Large readonly/guard
  regions were present in launch20; this is not proof of physical RAM exhaustion.
- Existing lab profile has get-task-allow but no extended-virtual-addressing or
  increased-memory-limit keys. Apple publicly documents Extended Virtual
  Addressing as a larger address-space capability:
  https://developer.apple.com/documentation/bundleresources/entitlements/com.apple.developer.kernel.extended-virtual-addressing
  Its effectiveness here, Personal Team eligibility and a matching profile grant
  remain UNVERIFIED. Do not assume it is available, necessary/sufficient, or paid.
- Prepared ONLY a separate local capability-check project in private
  .madeira-install/mac-arm-steam-memory-capability. Entitlements request exactly
  the public extended-virtual-addressing Boolean for the same isolated lab ID.
  Corrected missing UIKit link; unsigned CODE_SIGNING_ALLOWED=NO build PASS.
  Placeholder app was NOT installed; no new memory entitlement granted.
- Automatic approval review REJECTED the proposed -allowProvisioningUpdates
  operation before execution: developer-account/provisioning permission scope
  change requires separate explicit user authorization. No GUI or indirect
  workaround. Requested authorization for this one isolated profile change;
  pending. Completing local unsigned preparation did not change account state.
- Next: ONLY if explicitly authorized, use normal Xcode provisioning to determine
  whether this public capability can be granted; inspect resulting profile and
  effective device map, then repeat VM-only/CEF-load discriminators one at a time.
  If no legitimate grant is available, record the specific signing gate and
  investigate source-supported alternatives; do not fabricate entitlement access.
  Native Helper fork/spawn EPERM remains a separate unresolved contract even if
  CEF loading advances. Interactive UI/authentication/Windows depots/game bridge
  and performance remain unvalidated. Working Windows iDeck remains untouched.
- Tuesday daytime: all progress stays uncommitted/unpushed under user Git policy.

## 2026-10-27 14:17 EDT scheduled continuation: local build integrity

- Revalidated origin/experiment branch and live remote head at2d82b99. Preserved
  all existing local work. No overlapping LLDB/device/build experiment found.
  Explicit authorization for the new provisioning capability remains pending;
  heartbeat/task continuation does not constitute that approval. Did not retry
  provisioning, use GUI/indirect routes, repeat the user question or device tests.
- Independent work addresses the demonstrated invalid Build3 pipeline defect:
  builder compiles every shim into a private staging directory, invalidates a
  previous success receipt before attempting compilation, and replaces final
  outputs only after ALL three compiles succeed. Completed build emits unsigned
  output SHA256/source fingerprints/pinned-reference receipt. No runtime/shim
  behavior changed in this run; existing signed/installed Build4 left intact.
- Discriminating regression: real compiler #error in first component preserves
  all final binaries and Info; #error in second component after successful first
  compile also preserves ALL finals. Both invalidate old receipt and clean temp
  output. Separate complete-success fixture reads generated SOURCE only and
  verifies three final ARM64 Mach-O files and exact receipt hashes. All3 PASS.
  Tests use synthetic disposable app layouts; no Valve executable, profile,
  account, device action or new claimed device milestone. This is compile-failure
  protection, not an all-files filesystem transaction on I/O failure.
- Actual private evidence: mac-arm-steam-official/build-staging-tests-final.log,
  hash in MAC_ARM_STEAM_EVIDENCE.json. Local modified-source hashes refreshed.
  Prior signed Build4 hashes verified unchanged. No need to repeat runtime tests
  for this host-only build change. Next substantive device experiment remains
  conditional on explicit public-capability provisioning authorization.
- Tuesday14:19 America/New_York is outside22:00–07:00; changes remain local,
  uncommitted/unpushed. No wait automation. Same pending approval kept quiet.

## 2026-10-27 14:44 EDT: authorized capability request, genuine membership gate

- User explicitly authorized the new public EVA capability ONLY for the isolated
  com.kuschqin.ideck.maclab.macprobe app. Prior automatic-review authorization
  gate is RESOLVED; do not ask for this permission again. Revalidated worktree,
  branch/origin/live remote2d82b99 and phone availability before acting.
- Authorized xcodebuild -allowProvisioningUpdates build fails No Accounts plus
  existing-profile-missing-capability. This CLI account-discovery failure is NOT
  evidence the user logged out. Initial CUA check found Mac locked; user then
  unlocked it. Used the actual existing Xcode GUI session and private capability
  project, selected Kusch via Product/Destination, Build only (no install/run).
- Actual GUI build14:46 fails with an explicit server/signing requirement:
  Personal development teams do not support Extended Virtual Addressing.
  Signing pane confirms this error; actual Team menu lists only None, the
  user's Personal Team, and Add an Account. No paid team available in that
  session. Did not add accounts, enter credentials, enroll/pay, fabricate an
  entitlement, modify profile contents or attempt installation with invalid
  signing. No new capability profile granted; Build4 remains the last installed
  lab build, working iDeck unaffected.
- Independent official documentation check: Apple's current Supported
  capabilities(iOS) table has EVA checkmarks for ADP and ADEP, and an empty
  Apple Developer/free-account column. Web text extraction loses the checkmark
  figures; fetched the official HTML and inspected exact row/column structure
  (`figure icon-checksolid alt=yes`) rather than inferring from blank text.
  https://developer.apple.com/help/account/reference/supported-capabilities-ios
  Account terminology is described at
  https://developer.apple.com/help/account/basics/about-your-developer-account
  This matches the actual Xcode refusal; no blanket account availability guessed.
- Smaller-pool alternative audit: re-fetched THREE official Chromium sources at
 126.0.6478.183 and SHA256-matched existing pinned comparison copies:
  partition_alloc_config.h, partition_alloc_constants.h, partition_address_space.cc.
  This is comparison source, NOT proof of Valve's exact private build options.
  DYNAMICALLY_SELECT_POOL_SIZE is guarded by IS_IOS; max pools are16GiB for the
  general non-iOS/non-Android/non-pointer-compression64bit configuration and8GiB
  for those special cases. iOS test-only reduced pools rely on compile-time iOS
  code. Actual Mac CEF disassembly independently uses immediate16GiB and the
  device reproduces its failure. Retagging LC_BUILD_VERSION does not recompile
  allocator branches; renaming a process to an iOS test suffix or random flags
  is not a justified solution. No such spoof/shrink/fake-map experiment added.
- A source-built compatible CEF with a genuine smaller allocator configuration
  would be a separate research route, requiring actual source/platform support,
  ABI/API-hash/Valve-extension compatibility, signed loading and device evidence.
  It is NOT implemented or claimed feasible here; blindly replacing Valve's
  framework with a generic CEF download is not an acceptable verified fix.
- Current matrix: minimal macOS AppKit/Metal/touch probe DEVICE PASS; genuine
  native Steam main + steamui/SDL startup DEVICE PARTIAL; CEF constructors
  reached but load fails/16GiB ENOMEM DEVICE FAIL; normal developer DEBUGGED
  flag does not remove same fatal; native fork/self-spawn EPERM DEVICE FAIL;
  interactive CEF/login/library/Windows depots/gameplay/return UNVERIFIED.
- Canonical EVA discriminator is blocked by the actual Personal Team limitation,
  not user authorization or Mac lock anymore. Asked whether user already has a
  Developer Program team available; no purchase or new-account action authorized
  or performed. With a legitimate eligible team, ONLY isolated profile request,
  inspect granted profile/effective VM, then VM-only and CEF-load tests in order.
  Even a successful EVA grant would not solve native Helper IPC/process identity.
- Recommendation: preserve the working Windows Steam implementation and keep
  native route isolated. The current official Mac CEF+Personal Team route is
  NO-GO at the measured address-space gate; no claim the overall source-built/
  eligible-team architecture is impossible or that EVA would be sufficient.
  No new successful device milestone or performance result in this run.
- Tuesday daytime: local changes still uncommitted/unpushed, no wait automation.
  Private authorized CLI log, observed GUI-error transcript, official table HTML
  and source verification hashes are recorded in MAC_ARM_STEAM_EVIDENCE.json.

## 2026-10-27 14:53 EDT: user selects route without the entitlement

- User explicitly has NO Developer Program team and requests alternatives
  without EVA. Stop requesting membership/unlock/provisioning for this gate.
  Existing isolation/legitimate signing constraints and full native Steam goal
  remain. Origin/branch/remote still2d82b99; all changes local under Git window.
- First source-route discriminator: identify actual CEF public ABI WITHOUT
  loading it (constructors already fail16GiB). Added static ARM64 Mach-O reader
  recognizing only audited literal-table version/hash getter instructions, with
  VA-to-file backing/bounds checks and strict40hex CEF identifiers. No code is
  executed, patched, compatibility hash overridden or authentication touched.
- Actual metadata: CEF126.0.0 commit-number3171, Chromium126.0.6478.183. Public
  cef_api_hash entry2 declares bbb75964a9f4095daf2926163a63cbf11af56565. Exact
  upstream chromiumembedded/cef commit lookup returns422/no commit; public
  GitHub commit search returns0. ValveSoftware/cef public path404. Search results
  do not prove absence from all possible sources. Valve wiki source page403;
  did not bypass it. ValveSoftware/steam-for-linux issue12226 is an open source
  request, not authoritative proof of source unavailability and not a test result.
- Fetched only~296KiB of selected public CEF6478 headers/loader/build/license
  source at pinned a5d51ba9db7ee74a523dc247bd09ec91ba4d7446, not a full Chromium
  tree. Both actual platform/universal API hashes differ from that header.
  Actual Helper contains the same platform-hash literal as the Steam framework.
  Seven shared Helper/framework symbols are absent from upstream loader:
  cef_generate_gpu_report, cef_is_gpu_compositing_disabled,
  cef_is_hardware_acceleration_enabled, cef_set_force_device_scale_factor,
  cef_set_minimum_font_size, cef_set_preferred_contrast,
  cef_set_reduced_motion_enabled. These are candidate custom extensions; no
  claim every symbol is mandatory or that all struct differences are known.
- Source-build conclusion: this pinned standard CEF is NOT a verified drop-in
  replacement. Matching Steam-custom headers/ABI/semantics or a fully validated
  compatible implementation remains a prerequisite. No API-hash spoof or blind
  generic-CEF substitution. Current full-build upstream guidance requires
 150–200GB; internal workspace has~5.8GiB free. No huge source download attempted
  before clearing ABI requirements; external build storage could be planned
  later, not treated as proof building is categorically impossible.
  https://github.com/chromiumembedded/cef/blob/master/docs/automated_build_setup.md
- Second independent discriminator: can a legitimate smaller aligned geometry
  fit in the current free-signed sandbox? Implemented own pool-layout arithmetic
  with checked overflow/containment, one-page leading guard, power-of-two align
  and mask boundaries. ASan/UBSan varying-address and invalid/overflow tests PASS;
  actual iOS Werror compilation PASS. This is NOT Chromium PartitionAlloc code.
- Built isolated Build5 with existing NON-EVA entitlements/profile. All3 pending
  shim compiles succeed; receipt output hashes and new header input fingerprint
  checked before signing, FINAL linked small-pool marker present; deep/strict
  signature verified. Kusch actually unlocked; install receipt success. No
  production install/account/game/save changes; no new privilege requested.
- Actual launch24 IDeckSmallPoolProbe=1: each of TWO simultaneous real PROT_NONE
  chunks reserves512MiB+16KiB, containing a256MiB-aligned256MiB subrange with
  >=16KiB preceding guard. Both reserve and plan succeed; disjoint1/masks1/
  cleanup1/memory-written0/cef-integrated0. App exits0 after diagnostic. No
  MAP_FIXED, mprotect, fake grant, retry loop or modifications to Valve/FEX/Wine.
  This proves ONLY capacity/geometry for those own mappings, not actual CEF/BRP
  allocator safety, committed memory, JS/Skia, browser initialization or login.
- The original16GiB CEF request is unchanged. Smaller constants require correct
  source-wide allocator/mask rebuild and Steam ABI compatibility. Current source
  blocker: no matching buildable Steam-custom CEF source located. Native Helper
  OS process denial and in-host IPC remain separately unresolved.
- New read-only ABI tool6 synthetic tests PASS: exact getters, unknown-code
  refusal, encoded/unbacked pointer refusal, malformed-hash refusal, command
  bounds and preservation of unrelated output/symlinks. Small-pool arithmetic
  sanitizer test PASS and device geometry PASS. No new runtime success beyond
  the explicitly named geometry milestone. ABI report is static evidence only.
- Next justified work: obtain/reconstruct a genuine compatible CEF source/API
  baseline before full small-pool browser build. If unavailable, record that
  source/ABI gate and assess alternative component splits with an explicit IPC
  contract; don't claim a Windows Helper is interchangeable with macOS Helper.
  Current assessment: GO for a controlled small-layout source prototype,
  NO-GO for direct stock-CEF replacement; end-to-end native Steam UNVERIFIED.
  Existing Windows Steam route remains the working product path.
- Private artifacts: cef-abi-comparison.json, cef6478-source-audit/, build/
  sign/install-small-pool5 logs and launch24-small-pool.log. Only hashes and
  redacted facts in Git. Tuesday15:04 is outside22:00–07:00; no commit/push.

## 2026-10-27 15:19–15:36 EDT: real Helper boundary; two optional API failures

- User requests continuation without EVA. Rechecked origin, experiment branch,
  remote and HEAD: all remain2d82b99b5ae4d71fa7f7d9c4b848658802b73621.
  All research changes below are UNCOMMITTED. Tuesday daytime is outside the
  explicit22:00–07:00 window; no commit/push or wait automation. No main,
  FEX/Wine/graphics sources, working apps/accounts/games/saves modified.
- Read-only research of MIT Millennium at
  d6a7822a43744b6290a0e059bdd032d9b9a2ec94: macOS tier0 proxy re-exports real
  tier0; its Helper bootstrap still relies on an actual native child. Linux
  CreateSimpleProcess hook is a useful boundary reference, NOT Mac ABI proof.
  No source copied, plugin injected, debugger port enabled or raw command
  logging adopted. Exact audited ARM64 disassembly independently establishes
  x0 command/argv, w1 flags, x2 environment, x3 working directory, w0 result;
  bits3/4 select argv, bit5 returns before command inspection.
- Hypothesis1: the failed optional GPU query and real Helper use the same
  CreateSimpleProcess boundary; observe arguments without changing behavior.
  Added own re-export proxy with fixed-name-only summaries; no values/path/
  account/token/environment payload output. Text hints are lexical, not a shell
  parser or executable command. Original arguments, incoming/outgoing errno and
  return values pass unchanged. Host ASan/UBSan privacy and forwarding tests
  PASS. Builder stages all metadata edits, validates10 consumers' __TEXT,__text
  hashes unchanged, preserves exact converted tier0 SHA and refuses an existing
  proxy. Original official source bundle remains read-only. Filesystem copying
  is not transactional: any failure must stop signing/install.
- Build6 final linked marker, unsigned receipt hashes, nested+deep/strict
  signing PASS; installed and actually launched on Kusch/iOS27.0(24A435).
  Actual Helper argv flags0xa,25arguments includes language/cache/log paths,
  SteamPID/ID/universe, UI mode, launcher and feature settings (VALUES REDACTED).
  No --single-process switch observed in this call. Both launch attempts return0,
  errno1, with native fork EPERM at tier0+0xbe80. Thus no Helper/CEF was started
  by these calls. Later abort: UICTFont maximumAdvancement missing selector.
- Hypothesis2: provide the real horizontal glyph advance metric for the observed
  named UIFont rather than returning a dummy NSSize. Own CoreText implementation
  enumerates actual glyph advances, checks bounds and finite values. Host glyph
  containment/font-size scaling/NULL contracts PASS; actual iOS compile PASS.
  Scope excludes arbitrary variable-font axes/transforms/full AppKit semantics.
  Build7 all3 shims rebuilt; final marker/receipt/deep signing/install PASS.
  Device trace now passes the previous selector failure. New crash is SIGSEGV,
  KERN_INVALID_ADDRESS0x0: dispatch_set_context <- IOKit
  IONotificationPortSetDispatchQueue+104 <- steamclient+0x98b6b8.
  Private actual .ips shows x0=0 and x1 symbol gDummyPort. The pinned MIT
  reference IORegisterForSystemPower returns a fake nonzero session and port;
  Steam checks session and then passes fake port to the real IOKit dispatcher.
  This is source+device-backed evidence for that crash, not a CEF root cause.
- Hypothesis3: correctly decline unsupported macOS root-domain power registration
  so Steam skips dispatch setup. Apple installed SDK IOPMLib.h documents
  IO_OBJECT_NULL on failure; exact client disassembly branches past dispatch
  on zero session. Rebuilt isolated IOKit shim with IORegisterForSystemPower
  returning zero and clearing port/notifier. Real IOKit/SystemConfiguration
  exports remain re-exported. No dummy port, fake callback, private capability,
  power-service request or forced-success result. Host ASan/UBSan failure/null
  output/no-callback tests PASS; iOS Werror compile PASS.
- Build8 final power marker+absence of dummy-port symbol, unsigned receipt,
  deep/strict signing/install PASS. Actual launch27 prints unsupported-registration
  marker. No previous power-port crash during25s console sample. Observer
  command times out; NOT app death. Fresh process listing confirms exact lab
  app path/PID25917 still running. Device Hub screenshot directly observed black
  guest screen; shim fps=0/loops=0 after startup. No interactive Steam UI. Exact
  identity verified before terminating this bounded diagnostic run. No live
  process assumed afterward. The earlier font selector is absent from this trace.
- Static Helper imports include bootstrap/Mach port+message APIs, shm_open/unlink,
  mmap, socket and getpid. These identify contracts to investigate, not proof of
  execution or that replacing PID alone works. No single-process literal found
  in the inspected client/Helper files; absence is NOT proof no mode exists.
- Full local test-local.sh PASS: existing manifest/staging/layout/ABI, semaphore,
  display/bitmap/font-pointer/pool contracts plus new privacy/forwarding/glyph/
  power tests and actual iOS source compilation. Metadata parser5 synthetic
  tests PASS. Private raw launch/crash/sign/install/source artifacts and hashes
  listed in MAC_ARM_STEAM_EVIDENCE.json; no Valve/signing/device payload in Git.
- Current closest milestone: native Steam main+UI libraries can progress past
  these two shim crashes and remain alive in a bounded sample, but black screen
  remains. Native child-process EPERM and stock CEF16GiB ENOMEM remain independent
  measured gates. No native CEF/login/library/download/game/return/performance
  success. Preserve Windows Steam as working product path. Next prerequisite:
  compatible Steam-custom CEF source/API for a real small-pool source rebuild,
  plus explicit tested Helper IPC/identity ownership before any in-host model.
  Do NOT substitute a mismatched generic CEF, spoof API hash, shrink an mmap
  return, suppress assertions or pretend native spawn succeeded.

## 2026-10-27 15:37–15:47 EDT: VM placement discriminator and Helper entry gate

- User requests continued implementation. Verified experiment branch/origin/remote
  and HEAD still2d82b99. Existing working-tree changes preserved; production
  main not edited. All new changes remain local, uncommitted and unpushed under
  the weekday22:00–07:00 rule. Device check: Kusch unlocked/iOS27.0(24A435).
- Hypothesis: the earlier POSIX16GiB failure might be specific to mmap placement,
  rather than the task's nominal full min/max address span. Read Apple XNU at
  f6217f891ac0bb64f3d375211650a4c1ff8ca1ea: vm_map.c distinguishes default/data/
  large-file ranges and inserts inaccessible occupied holes; kern_mman.c assigns
  range policy. This public source is comparison evidence, NOT the exact running
  iOS kernel. Never remove or repurpose existing inaccessible regions.
  https://github.com/apple-oss-distributions/xnu/blob/f6217f891ac0bb64f3d375211650a4c1ff8ca1ea/osfmk/vm/vm_map.c
- Implemented native-vm-range-probe.c, explicit IDeckNativeVMRangeProbe=1,
  diagnostic exits before Steam main. First compilation correctly rejected
  mach/mach_vm.h as unsupported on this iOS SDK; corrected final code uses only
  SDK-declared vm_map/vm_region_64/vm_deallocate with compile-time64-bit ABI
  assertions. No manual private MIG declarations. Actual iOS Werror compile PASS.
- Read-only region scan treats mapped regions as occupied, including PROT_NONE;
  inventory is not an atomic map snapshot and does not prove the exact purpose
  of every region. Reservations use normal VM_FLAGS_ANYWHERE, max/current
  protection NONE. No FIXED/OVERWRITE, custom address-range flags, entitlements,
  mprotect, fake mmap result, byte writes or CEF integration. Every successful
  mapping is released before next test; cleanup failure stops further tests.
- Build9 all3 pending shims compile; unsigned receipt hashes/final range marker,
  ordinary NON-EVA profile and deep strict signing verified. Actually installed
  and ran launch28 on Kusch. Inventory137 regions; mapped474750828544 bytes,
  no-access mapped413396074496 bytes; largest observed unmapped gap6442450944
  bytes(6GiB), nominal task span483109666816 bytes. vm_map1GiB succeeds and
  releases;8GiB and16GiB return3(KERN_NO_SPACE). mmap8GiB returns ENOMEM12.
  cleanup1, memory-written0, cef-integrated0, actual diagnostic exit0.
- Conclusion: switching to the normal SDK VM path did NOT solve large-pool
  allocation in this measured lab layout. The nominal task max is not a promise
  of that much allocatable contiguous space. This is NOT a universal capacity
  statement for all apps/devices/entitlements. No guessing that task max alone
  permits16GiB, no kernel/security bypass, no retries of unchanged large mappings.
  Source-wide genuinely smaller pools remain the justified research route.
- Pinned Chromium126 source has compile-time IS_IOS dynamic pool support; simply
  retagging the existing Mac Mach-O does not compile this code in. Matching
  Steam-custom API/struct semantics remain required. Targeted authenticated
  GitHub public code searches: cef_generate_gpu_report3 indexed hits and
  cef_set_reduced_motion_enabled2, all unrelated binary-analysis reports, not
  implementation source; C++ generate_gpu_report search0. No samples downloaded
  or executed. Search incompleteness means this is not proof source is absent.
- Independently inspected unchanged Helper filetype2(MH_EXECUTE), LC_MAIN file
  offset847956 and direct CEF load dependency. No exported reusable helper-main
  contract is established. Added helper-load-probe.m to test normal in-process
  dlopen of this unchanged Helper, with all dlerror text redacted and fixed
  failure-category-only logging. No entry call, conversion, PID/IPC simulation,
  argv/environment mutation or CEF patch. Unexpected load is diagnostic, not UI
  success. Explicit IDeckNativeHelperLoadProbe=1 excludes other probes.
- Build10 compiled, final linked helper-load marker/unsigned inputs verified,
  signed and deep/strict signature passes. Installation command timed out60s;
  fresh successful installed-app query STILL reports Build9. No install receipt
  success, no Build10 runtime launch, no repeated install or old-binary probe.
  Loader acceptance/rejection remains UNVERIFIED; do not infer it from filetype.
  Exact prepared unsigned input receipt and signed binary hashes saved privately.
- test-local.sh PASS after both additions, including existing sanitizer contracts
  and actual iOS probe compilation. Real staging regression PASS: first and
  second compiler failures preserve final files/Info and invalidate receipt;
  synthetic full success verifies all3 output hashes. No public IPA/new release.
- Next: on fresh device availability recheck installed version/pending state;
  if already10 do not reinstall, otherwise install prepared10 once, then run
  only the Helper-load probe. It may establish the loader prerequisite but cannot itself
  solve native process lifecycle or CEF capacity. Native interactive UI still
  requires compatible source-built small pools AND a real Helper IPC/identity
  design; unchanged stock CEF/native fork remains NO-GO in this measured free-
  signed route. Working Windows Steam remains separate. Full native login,
  library, Windows depots, gameplay/return and comparative performance UNVERIFIED.

## 2026-10-28 00:24 EDT: installed10 reconciliation and observer contract regression

- Periodic run verifies experiment/mac-arm-steam-ios, origin kuscholar/iDeck and
  remote/HEAD2d82b99b5ae4d71fa7f7d9c4b848658802b73621. Worktree untouched by
  another experiment. Primary checkout is NOW experiment/steam64-hybrid at
 47535fe (other work); did not change its branch, files, accounts or install.
- Fresh successful app query now reports isolated macprobe Build10. Corrects the
  earlier timeout's still9 observation: installation eventually completed.
  DO NOT reinstall10 merely because the old install command timed out. Fresh
  lock query shows passcodeRequired=true. No launch/install attempt, unlock
  bypass or repeated unchanged-gate request. Helper-load runtime remains
  UNVERIFIED. Prepared original Build10 already contains its linked marker.
- Independent review found older exec/fork/spawn observers could pass errno
  changed by symbol lookup/logging into the original function; their output
  errno was preserved already. Added incoming errno restoration and fixed
  executable/module-name classification so unknown basenames are redacted.
  Original path/argv/environment/attributes/result are unchanged. No new flags,
  fake PID, auth behavior, mappings or native child-process implementation.
- Discriminating host test mocks exact dlsym/dladdr and the four original calls;
  asserts argument identity, incoming/outgoing errno, return values, unchanged
  failed-spawn pid and missing-resolver semantics. Captured output excludes
  synthetic private basename/path/password/env values. ASan/UBSan PASS; no
  actual host exec/fork/spawn is performed. Full test-local.sh and real compiler
  failure/success staging regressions PASS. Actual iOS Werror compile PASS.
- These latest observer edits are SOURCE/HOST verified only: installed Build10
  predates them. Do not claim new code was linked or device-tested. CEF16GiB,
  native process EPERM and interactive UI gates remain unchanged. Evidence and
  exact source hashes recorded; no proprietary/account/signing/raw logs in Git.
- At00:24 America/New_York, commit/push window is open; reviewed scoped research
  sources/docs/tests may now be published to the experiment branch only. Check
  time separately immediately before each operation. No merge into main.
- Next on actual native unlock: launch ALREADY installed10 once with only
  IDeckNativeHelperLoadProbe=1 and current app URL, collect categorical result.
  Do not mistake constructor exit or CEF load for an interactive Steam window.

## 2026-10-28 05:34 EDT: unchanged device gate; source-location and matrix review

- Verified origin/branch/worktree, clean research HEAD and current remote all
 147c7a84ed3c6422236f80ffc3908bc1933db295. One fresh native lock query still
  shows passcodeRequired=true. No install/launch, stale PID action, lock bypass
  or repeated notification. Installed10 confirmation from prior run remains the
  latest version evidence; do not repeat the old installation-timeout diagnosis.
- Independent source-location check reads five official bundled legal/license
  notice files, including ThirdPartyLegalNotices-Chromium.html. No matching
  Steam-custom buildable CEF source location found among the inspected links.
  This is not exhaustive global evidence and does not establish redistribution
  permission. No third-party samples or executables fetched/run. Private report
  records source-file hashes; no Valve notice contents copied into Git.
- Added MAC_ARM_STEAM_COMPATIBILITY.md to consolidate the requested compatibility,
  limitations and current continue/no-go assessment with per-milestone evidence.
  Distinguishes geometry from actual CEF, host-only observer hardening from
  installed10, process survival from rendering, and working Windows product from
  this native experiment. No unsupported auth/game/performance claims.
- Runtime code and installed app unchanged; no reason to rerun identical host
  tests for this documentation-only update. JSON parses, evidence hashes and
  document links checked. Current source parent147c7a8; device/iOS last actual
  verified27.0(24A435), not guessed from user's older report.
- Next still requires native unlock for the already installed10 loader probe.
  Keep source-built compatible smaller CEF and Helper IPC/lifecycle research
  separate; no new successful native Steam milestone in this run. Check local
  time before each scoped commit/push; no main merge or waiting automation.

## 2026-10-28 10:37 EDT: actual Helper loader test and probe-path correction

- Verified origin/experiment branch/worktree/remote atfbdb6eb2014072fc7d97730242e7326766752fac.
  Phone natively unlocked; fresh installed-app query confirms10 and process list
  has no active lab session. No overlapping debugger/build. Working apps untouched.
- Ran installed10 with ONLY IDeckNativeHelperLoadProbe=1. It reports loaded0,
  rejects-main-executable0. This is an UNKNOWN failure, not MH_EXECUTE rejection.
  Source review identifies a diagnostic defect: pinned AppKit_RuntimeHooks.m
  redirects NSBundle.bundlePath to the Mac root; probe appends another Mac
  component. No target preflight and no raw error captured, so do not attribute
  its unknown failure to the real Helper's filetype or claim runtime load success.
  Console says exit0 despite a source path selecting _exit3; preserve that
  discrepancy rather than infer probe success from transport exit status.
- Minimal correction: derive root via _NSGetExecutablePath resolved directly in
  real libSystem, bounded helper-path function rejects logical redirected paths,
  and open/read preflight verifies exact ARM64 MH_EXECUTE header before dlopen.
  No raw paths/error text or account payload logged. Explicit diagnostic-result
  marker distinguishes result from transport exit. Own path ASan/UBSan test PASS
  including exactly-one-Mac, redirected-path rejection and capacity/NULL checks.
- Rebuilt all3 isolated shims (includes earlier observer errno hardening); final
  preflight marker/unsigned input hashes verified; standard profile/deep strict
  signing PASS. Actual isolated Build11 installation receipt success. Launch30
  ONLY Helper-load switch: native-path=verified, preflight=arm64-MH_EXECUTE,
  loaded0/rejects-main-executable1/missing-image1/entry-called0/diagnostic-result0.
  Error categories can overlap within dyld path searches. Strong evidence this
  preflighted Helper did not load via normal dlopen, NOT proof every relinked or
  source-based in-process architecture is impossible. No Helper entry called.
- Full local contract suite and actual iOS Werror compilation PASS. Real staging
  tests PASS: first/second compiler failure preserves all final outputs/Info;
  synthetic full success verifies3 pending outputs/receipt hashes. Signed
  Build11 binary fingerprints and all raw logs retained privately; redacted
  evidence index and compatibility matrix corrected. Earlier pending-unlock/
  Build10 source-only statements are historical, superseded by this section.
- No UI, authentication, CEF initialization, depots, games or session-return
  milestone. Stock CEF constructor16GiB capacity gate remains independent from
  this loader result. Any future loadable Helper adaptation needs isolated
  copy/relink/metadata checks preserving instruction bytes and real IPC/lifecycle
  semantics; a successful header edit would not solve CEF or process identity.
  Avoid repeating unchanged native-spawn/stock-CEF failures.
- New source/docs remain uncommitted/unpushed: weekday10:37 is outside the user's
 22:00–07:00 window. No waiting automation or main changes. Next work should
  address a justified loadable Helper design and compatible source-wide smaller
  CEF, without fake process success, ABI-hash spoofing or assertion suppression.

## 2026-10-28 15:43–15:49 EDT: loadable-bundle design proven with own fixture

- Verified research branch/origin/remote atfbdb6eb; local morning probe changes
  preserved. One fresh lock check shows native unlock. No main/FEX/Wine/DXMT
  edits, account entry, privilege requests or other working-app installation.
- Hypothesis: after normal dlopen rejects actual unchanged Helper on iPhone,
  an instruction-preserving executable-to-bundle layout can at least work for
  an own minimal Mac ARM64 fixture under normal iOS development signing.
  This is a loader design discriminator, NOT a replacement/mock Steam helper/UI.
- Added own C fixture with unique marker, static constructor counter and explicit
  getter; main increments a separate counter. Compile genuine macOS ARM64
  executable, transform ONLY own fixture metadata, retarget platform with Xcode
  vtool, re-sign normally. No CPU instructions changed or kernel/signing bypass.
  Strict synthetic-only tool requires exact hash+own marker, bounds-checks load
  commands/sections, refuses existing output or sidecar, and keeps binaries out
  of source repo. It must NEVER be applied to Steam/CEF/third-party binaries.
- Initial own transformation removed PAGEZERO; host dyld rejected it because
  chained-fixup segment count/ordinals no longer matched. Corrected metadata
  keeps the PAGEZERO segment slot but with zero vmsize, removes LC_MAIN and
  LC_LOAD_DYLINKER, changes type to MH_BUNDLE and clears PIE. All post-command
  payload/instruction bytes unchanged. This is specific tested fixture geometry,
  not a universal executable conversion tool or a tested real Helper fix.
- Host result is nuanced: current macOS dyld loads original own executable too;
  do NOT infer iOS behavior from it. Corrected normally signed own bundle loads
  on host, getter verifies constructor1/main0. Six tests cover payload/ordinal
  preservation, wrong hash/marker, malformed bounds, sidecar preservation and
  actual signed host loading. All PASS; complete local contracts/iOS Werror PASS.
- Isolated Build12 compiles updated shims and includes two own Mac ARM64 fixture
  copies (executable and bundle), vtool platform-retargeted to iOS. Text hashes
  verified unchanged before signing. Final diagnostic marker, input receipt,
  nested fixture signatures and deep/strict app signing PASS. Actual install
  receipt success; launch31 only IDeckSyntheticHelperProbe=1.
- Actual iPhone result: executable loaded0; bundle loaded1/fixture-verified1;
  main-called0; diagnostic-result0, steam-entry0, cef0, process-emulation0.
  Constructor count1/main count0 is checked by getter==100. Diagnostic exits0.
  This establishes a real loadable-own-bundle milestone through standard signing,
  not actual Helper hosting, native CEF/login/library/gameplay or IPC correctness.
  No Valve binary was converted to a bundle or replaced in this run.
- Next real Helper adaptation would need its OWN exact-version isolated-copy
  metadata/relink audit: preserve instructions and chained-fixup segment indices,
  handle actual loader-relative dependencies and normal signatures. Do not reuse
  synthetic-only tool on Valve. CEF16GiB/source ABI and actual process/IPC/lifecycle
  remain independent gates even if a Helper bundle loads. Do not fabricate PIDs,
  skip assertions/authentication or claim a signed build proves runtime behavior.
- Evidence/private fixture reports and hashes added to the index. Latest lab is
  Build12, diagnostic completed; no assumed live process. All new work remains
  uncommitted/unpushed outside weekday22:00–07:00. No waiting automation.

## 2026-10-29 06:58 EDT: source regression and scoped publication audit

- Revalidated origin/experiment branch/worktree and remote atfbdb6eb. Preserved
  prior Build11/12 source/evidence changes. One native lock check shows locked;
  no repeated install/launch, stale PID action, lock bypass or notification.
- Reviewed new synthetic-only transformer, path resolver, fixtures and diagnostic
  sources. Re-ran full local contract suite and six real synthetic metadata/
  signed host-loader tests: PASS. No new on-device result; Build12 own-bundle
  milestone is unchanged and does not establish genuine Helper/CEF success.
- Publish only scoped text sources/tests/redacted docs if each immediate local
  time check remains inside22:00–07:00. Do not rush or bypass the cutoff; leave
  changes local if the window closes. No main merge or waiting automation.
- Next: exact-version read-only real Helper metadata/dependency/fixup audit;
  synthetic-only transformer remains prohibited for Valve binaries. Original
  CEF capacity, compatible source ABI and real IPC/lifecycle gates still apply.

### Post-publication read-only Helper layout follow-up

- Published prior reviewed sources/docs atb6212bdae6d64aaac5e6dc6cb59916e739fc81b1;
  commit06:58:55 and separate push06:58:55 America/New_York checks both passed.
  Remote equality verified; no force-push/main change.
- Actual unchanged Helper metadata audit:5 segments, LC_DYLD_INFO_ONLY (NOT the
  synthetic fixture's LC_DYLD_CHAINED_FIXUPS), encrypted load-command flag0.
  Never infer arbitrary conversion support merely from that flag or own tests.
  A future design must preserve rebase/bind segment indices as well.
- Found a concrete layout requirement: direct CEF dependency is
  @executable_path/../Frameworks/Chromium Embedded Framework.framework/Chromium
  Embedded Framework. Resolving this single candidate relative to the root iOS
  host executable finds no file; Helper originally expects its own executable
  directory. This static check is not a full dyld search or proof of the exact
  first fatal. Do not attribute all earlier error categories to MH_EXECUTE alone.
- No proprietary bytes modified, no Helper entry or new device test. Exact audit
  hash indexed privately. Next exact-version isolated-copy design must address
  both loadable metadata and real CEF dependency layout; fixing these still
  leaves measured stock CEF capacity and process/IPC gates unresolved.

## 2026-10-29 09:35 EDT: user requests actual connected iPad

- User explicitly changes immediate test target to local physical iPad. Preserve
  full native Steam goal, branch isolation and existing working iDeck. Verified
  experiment branch/origin/remote atb6212bd; existing local evidence changes kept.
- Actual discovery excludes simulators: physical iPad Pro11-inch, productiPad8,1,
  iPadOS26.7.1/build23H30; developer mode enabled, trusted/paired, native unlock
  and DDI available. Private device identifiers/serial remain outside Git.
- Prepared isolated Build12 exact bundle com.kuschqin.ideck.maclab.macprobe
  supports iPad family2/minimum17. Existing standard profile already covers
  the iPad, expiresNov3. No profile request/new capability/account login needed.
  Deep strict signature and linked VM-range/own-bundle markers verified; signed
  fingerprint report retained privately. Native probes need no FEX JIT step.
- Physical iPad already has3developer apps: HomePad, HomeViewPad, iDeck97.
  No assumption that a slot was free; attempted only independent lab install.
  First60s command times out; fresh lab-app query empty. Checked actual transport:
  localNetwork, prepared app607MB. Changed timeout to240s with detailed error
  capture, not an unchanged blind retry. System then explicitly rejects fourth
  free-profile app: MIInstallerErrorDomain13 / IXUserPresentableErrorDomain14,
  max installed free-development-profile applications. Generic integrity text
  is not the root diagnosis and is not proof valid final signature failed.
- No working app uninstalled/overwritten, no auth/game/save copy, credential
  automation, simulator substitution or device lock bypass. Asked user to back
  up/remove one unused HomePad/HomeViewPad and notify; preserve working iDeck.
  Experimental app NOT installed, and no iPad runtime success claimed.
- Next after slot is available: recheck iPad availability and existing lab state;
  install signed isolated12, run separate IDeckNativeVMRangeProbe and
  IDeckSyntheticHelperProbe bounded sessions, collect real output. These own
  diagnostics precede any genuine Steam/CEF comparison. iPhone results do not
  prove this iPad/OS behavior. No repeated quota-failing installs meanwhile.
- Evidence matrix and private hashes updated; no runtime source changes or reason
  to repeat host tests. Weekday daytime: no commit/push/wait automation.

## 2026-10-29 11:59 EDT: user removed HomePad; device service unavailable

- User reports HomePad uninstalled. Preserve this as user report until actual
  app inventory verifies slot; do not repeat the quota request or delete others.
  Research branch/origin/remote remainb6212bd with existing local docs preserved.
- Actual CoreDevice app query fails4016: trusted remote connectivity/services/
  power assertions unavailable. Refresh device list marks physical iPad
  unavailable. Asked for USB connection/native unlock/keep awake and trust prompt
  if shown. No device install, app replacement, service restart or lock bypass.
- Checked alternate supported Xcode discovery once: xcdevice reports available
  network iPad26.7.1, but subsequent CoreDevice app query times out15s. Record the
  disagreement; discovery availability does not prove usable install/debugging
  services. No further identical unavailable-device retries or install claims.
- Independent work: added run-native-lab-probe.py to execute exactly one explicit
  diagnostic in an already installed audited12 lab. Requires physical device,
  native unlock, exact isolated bundle/version/current URL, absence of existing
  lab session, and new private .madeira-install artifact folder. No install,
  signing, JIT, credential, unlock or process-termination operations. Working
  iDeck or another build cannot silently substitute. Exact diagnostic markers
  are required; console exit0 alone is not runtime success.
- Eight runner tests PASS: wrong app/version/URL refusal, missing diagnostic
  markers, inventory/cleanup and verified fixture requirements. Full local
  contracts/iOS compilation PASS. Read-only replay recognizes prior PHONE9/11/12
  artifact markers; explicitly not new iPad device evidence. No installed lab
  binary change from the new host-side runner. No reason to rerun phone tests.
- Next after USB/native access works: verify free slot and installed lab state,
  install isolated12, then use the runner for separate vm-range and own-bundle
  probes. Both must produce fresh actual iPad logs before making runtime claims.
  All new source/docs remain local outside weekday22:00–07:00 commit window.

## 2026-10-29 12:06 EDT: unchanged iPad connection; scheduled continuity corrected

- Revalidated experiment branch/origin/remote atb6212bd; local user-work preserved.
  One new iPad state query still fails CoreDevice4016 trusted-connectivity/power
  assertion. No install/launch, unlock attempt, service restart, repeated prompt
  or new device result. The user's pending USB/native access step is unchanged.
- Updated the EXISTING305minute heartbeat prompt to respect the latest physical
  iPad target, HomePad-removal report, existing isolated12 and runner, no simulator
  substitution, no stale quota/phone-success claim and quiet unavailable gate.
  Preserved schedule/name/thread/status and full original mission/time constraints;
  no duplicate task, new wait automation or change to notification preferences.
- No runtime edits or repeated tests for this state-only update. JSON/diff checks
  pass. Daytime source/evidence remain uncommitted/unpushed. Next actual iPad
  installation/testing still awaits usable trusted native device services.

## 2026-10-29 13:05–13:22 EDT: real iPad tests and exact Helper candidate

- User confirms connected/native-unlocked iPad. Branch/origin/remote revalidated
  atb6212bd; local work preserved. Fresh physical iPad inventory confirms HomePad
  removed, leaving HomeViewPad and working iDeck97. Existing standard profile/
  signed12 preflight passes. Actual isolated12 install receipt succeeds; no
  existing app overwritten, credential/cache/game/save transfer or new capability.
- New runner actual iPad VM-range report: iPad8,1/iPadOS26.7.1,127 regions,
  mapped6511230976bytes, no-access mapped5390336bytes, largest observed gap
 5771362304bytes, task span14313553920bytes. vm_map1GiB success+cleanup;
 8/16GiB return3 KERN_NO_SPACE; mmap8GiB errno12. Cleanup1/memory-written0/
  cef-integrated0; this is a real device report, not prior phone replay.
- Separate own-bundle run: executable loaded0; bundle loaded1/fixture-verified1,
  constructor1/main0/Steam-entry0/CEF0/process-emulation0. Separate unchanged
  real Helper run verifies native ARM64 MH_EXECUTE target then loaded0 with
  executable1/missing-image1 categories. Neither is genuine interactive UI.
- Actual direct native CEF load-only run: two16GiB mmap PROT_NONE failures,
  errno12, followed by SIGTRAP before dlopen returns. Copied actual .ips confirms
  EXC_BREAKPOINT at Chromium Embedded Framework+0x3b4dda0, during dyld initializers,
  same RVA as phone. Do not interpret nearest symbolicated Rust names as a causal
  function identity. No cef_initialize/login called. One crash-list request was
  initially NOT executed because automatic approval review could not complete
  due usage limit; later fresh ordinaryUsageAllowed status and normal review
  succeeded. No approval or sandbox bypass was used.
- Next single hypothesis: exact Helper loader metadata plus dependency layout
  can progress beyond the unchanged-executable refusal, independently of CEF's
  capacity. Added a SEPARATE exact-version preparer, not the synthetic-only tool.
  Original signed converted Helper SHA76374b69... is required; thin ARM64, fixed
 5segments/LC_DYLD_INFO_ONLY, entry, encryption and section/stream bounds checked.
  Preserve segment ordinals; zero PAGEZERO size; MH_BUNDLE, remove LC_MAIN and
  LC_LOAD_DYLINKER/clearPIE. No instruction/bind/rebase payload modifications.
- Candidate lives Mac/Contents/MacOS/IDeckNativeHelperLoad.bundle, beside real
  dependencies. CEF import becomes @loader_path/../Frameworks/Chromium Embedded
  Framework.framework/Chromium Embedded Framework, verified to resolve INSIDE
  app. Original nested Helper app remains untouched. An earlier staged candidate
  inside that Helper app was discarded after checking its own output hash;
  it was never deployed, avoiding unnecessary re-signing of original Helper.
- Five synthetic metadata tests PASS: exact payload/ordinal preservation, default
  production-hash refusal for synthetic input, malformed bounds, changed segment
  contract and unbacked bind stream. Complete local ASan/UBSan/iOS Werror and
  real compiler failure/success staging regressions PASS. No signature bypass;
  only ordinary existing developer signing. Final original Helper full SHA and
  candidate text SHA verified after signing as well as before signing.
- Isolated Build13 compiled, receipt/final marker checked, candidate+shims signed,
  deep/strict app signature PASS; actual iPad install receipt success. Explicit
  IDeckNativeHelperBundleProbe=1 only: verified ARM64 MH_BUNDLE preflight and
  instructions-unchanged marker, then actual CEF constructors request16GiB,
  fail ENOMEM and SIGTRAP. New .ips again CEF+0x3b4dda0. dlopen does NOT return,
  no Helper entry called. This progresses loader validation/dependencies into
  CEF initialization constructors but is NOT a completed Helper/CEF load or UI.
- First independent iPad native-process session: legitimate self-posix_spawn
  returns1(EPERM), created0. Existing diagnostic then continues genuine Steam
  main; tier0 fork attempts return-1/errno1 at+0xbe80. Console observer25s timeout
  is NOT process death; fresh exact installed app path/PID identity verified,
  then only bounded lab process terminated. No auth or UI-success claim.
- Updated runner supports only audited12/13 for existing unchanged probe
  contracts, refuses11/14/ordinary iDeck. Nine host tests PASS; native13 candidate
  was launched explicitly with exact install receipt, not an unreviewed runner
  fallback. Prepared source fingerprints and all private install/launch/crash/
  signed-output hashes indexed. Working apps/data remain intact.
- Core end-to-end blockers on this iPad now artifact-backed: stock CEF fixed16GiB
  constructor reservation and actual native process EPERM. Metadata alone does
  not solve either. Need compatible source-built truly smaller allocator pools
  and real IPC/lifecycle integration. No fake grants/PIDs, MAP_FIXED fallback,
  mprotect retries, assertion suppression, ABI hash spoof, FEX or Valve-instruction
  edits. Native UI/auth/library/depots/games/return and speed comparison incomplete.
- Latest installed native lab13; diagnostic process ended; no assumed live PID.
  New source/docs uncommitted/unpushed outside weekday22:00–07:00. No wait task.
- Existing305minute heartbeat continuity now records actual iPad13 install/tests,
  resolved signing-slot/connectivity gates and both measured blockers. Schedule,
  notification settings, original mission and Git window preserved. Do not
  replay obsolete install12/quota/unlock instructions over the current lab.


### 2026-10-29 13:44–13:55 EDT; continuity finalized17:16 — actual Chromium126 allocator on iPad14

- Parent/remote remain b6212bdae6d64aaac5e6dc6cb59916e739fc81b1 on
  experiment/mac-arm-steam-ios, origin kuscholar/iDeck; remote freshly checked.
  All prior uncommitted work preserved; no concurrent builder/device tool at
  final check. No commit/push outside weekday22:00–07:00. Working iDeck97 and
  primary checkout/data untouched. Fresh physical iPad8,1 /26.7.1(23H30) wired,
  paired and unlocked; old isolated13 exact app-path identity checked before
  terminating its one session. No authentication or credential operations.
- Observed failure remains stock CEF constructor16GiB ENOMEM/fatal, plus native
  child EPERM. Prior own geometry alone cannot establish allocator correctness.
  Hypothesis: real Chromium126 iOS small-pool path can initialize ordinary+BRP
  pools and perform correct allocations within the measured no-EVA VA capacity.
- Inspected actual126 external_builds.md/BUILD.gn/config and source. The web search
  surfaced an older Linux-only standalone GN recipe; the pinned126 tree does
  NOT have that gn/ folder. Do not claim that older build recipe supports iOS.
  Verified362 blobs (~3MB), subtree3e6d40abe3803b5f785a0adbd1030740cf1e8071;
  two actual upstream build headers SHA-pinned. No full Chromium download/GN
  installation, no upstream source edits. New direct-clang harness compiles62
  real units; explicit generated standalone flags documented, not Valve CEF's
  full config. Chromium BSD LICENSE/AUTHORS retained in rebuilt app.
- Minimal new patch is an isolated UIKit executable and reproducible builder.
  PartitionAllocRunner suffix selects actual upstream IsIOSTestProcess256MiB
  pools; no instruction patch, runtime spoof or fake map. BRP+slow checks,
  DCHECK+expensive DCHECK stay enabled. No EVA/JIT/new entitlement needed.
  Initial own probe used private pool-size accessors and failed compilation;
  corrected to public GetPoolInfo/mask/bases, never weaken upstream access/checks.
- Build14 final linked marker/system-only libraries/iOS17 platform checked,
  standard existing profile covers iPad; deep strict signing PASS. Actual install
  receipt success. Console proves pool268435456/disjoint1, allocations398/frees398,
  workers4/failures0/pools-uninitialized1/cef-integrated0. Actual requests1byte–2MiB
  in normal+BRP pools, content and simultaneous requested-range isolation,
  non-LIFO frees and concurrent workers. BRP raw_ptr lifetime semantics NOT tested.
- Console25s transport timeout is not app death. Subsequent installed14 app and
  exact executable process observed; completed test UI remains. Do not act on
  recorded historical PID without identity revalidation. Current isolated lab
  is standalone14, NOT Steam13. Original converted Steam13 remains on host.
- Full host/sanitizer/iOS/staging test-local suite PASS. Source trust tests reject
  tampered receipt/source/build-header and symlink; temporary-path root initially
  needed canonicalization, fixed and all tests PASS. Final builder independently
  rebuilds unsigned app successfully after guard/license-only changes; actual
  signed/device binary and exact receipt hashes retained separately, not conflated.
- Evidence paths/SHA256, exact source fingerprints/config and signed binary hash
  are in MAC_ARM_STEAM_EVIDENCE.json ipadPartitionAllocSourceProbe20261029;
  private raw partitionalloc14-* and partitionalloc-probe14* outside Git.
- Conclusion: real small-pool allocator is now on-device verified, stronger than
  geometry-only. It is iOS-compiled standalone PA, not stock macOS CEF or Steam.
  No full allocator feature/stability/performance/CEF/browser success claim.
  Next gate: reproducibly compatible CEF source/custom API, consistent allocator
  build across consumers, then actual browser+Helper IPC/lifecycle. No hash spoof,
  assertion suppression, smaller fake mapping, private entitlement or FEX edit.


### 2026-10-29 23:34 EDT — user requests currently wired iPad Air preflight

- Existing branch/HEAD/origin and all uncommitted work inspected and preserved.
- New physical candidate is iPad13,1; existing iPad8,1 remains separately paired.
  New candidate has no readable OS version/UDID/name and pairingState unsupported;
  Xcode does not expose it as an available development target. Official single
  CoreDevice pair attempt fails1014 with only RestorableDeviceRef representation.
  USB product string iPad/id4779 observed; recovery/DFU/old OS is NOT established.
- No install, launch, signing/profile change, reboot, restore, erase or working-app
  action. Cannot verify profile coverage/free-app slots until normal pairing.
  User asked to enter normal home screen, unlock/trust and report exact iPadOS.
  This is a device-access gate, not proof the hardware cannot run the probe or
  that genuine native Steam will work. Do not substitute old iPad/simulator.
- Private evidence index:
  - .madeira-install/ipad-air-preflight-20261029-2334/ideck-current-wired-devices.json SHA256 8f7f1c934d2f35712d4571f584d22b7c4907e288f048772a7171f6e31dcb304b
  - .madeira-install/ipad-air-preflight-20261029-2334/ideck-xcdevice-current.json SHA256 23de84e579411701aaf461bd415a20fcefbb1c8db616bfcde93f9404ffc7f792
  - .madeira-install/ipad-air-preflight-20261029-2334/ideck-air-details.log SHA256 2fd6d4916b986cbf1a66d29f4435f25044553cefe2b046d842f4b10cba47a19e
  - .madeira-install/ipad-air-preflight-20261029-2334/ideck-air-pair-result.json SHA256 6f1efe5b7e9a0e9fff1d67246eaaa3896115a33a054628fa39c4b54f1ea2a805
  - .madeira-install/ipad-air-preflight-20261029-2334/ideck-air-usb-ioreg.txt SHA256 7f3e60e6cba4e29e69d8857844d8c59aa0d255cf646e01aa21d8c01a8d3a6995


### 2026-10-30 03:24 EDT — research snapshot review and target continuity

- Branch/origin/remote revalidated at b6212bd; no overlapping build/tool.
- Latest user target is newly wired iPad Air candidate iPad13,1, superseding
  automatic preference for the old Pro. One read-only availability check still
  shows pairing unsupported and OS unavailable. No repeated pair/install/unlock
  request; no old-device substitution. Existing lab14 success is on iPad8,1 only.
- Independently reviewed scoped source and redacted evidence; current full
  test-local host/sanitizer/iOS/staging suite and real-source tamper tests PASS.
  Private log .madeira-install/native-lab-reviewed-20261030.log. No new native
  Steam/CEF runtime milestone. Compatible CEF source/API and native IPC remain
  open; do not repeat proven stock failures or declare hardware unsuitable.
- Fresh Air inventory private .madeira-install/mac-arm-heartbeat-20261030-0323/
  ideck-air-heartbeat-20261030.json SHA256 9318cd3096a1fc6be8f091dda5b450e9022f43c86469ae42de1487800a5f82c8.
- Preparing signed-off research snapshot only on experiment/mac-arm-steam-ios;
  time checked separately immediately before commit and push. No main/submodule
  change, Valve/runtime/signing payload, private device identity or raw log staged.


### 2026-10-30 08:33 EDT — unchanged Air access gate, quiet heartbeat

- HEAD/remote ad53b4083147539528c9e5c07cdc2d2641138884, correct fork/branch,
  clean checkout at entry, no overlapping builder/device tools. One fresh read-only
  Air inventory: iPad13,1 pairing unsupported, OS still unavailable. No user reply
  to prior unlock/trust/version request. No repeat pairing/install, alternate-device
  substitution, reboot or working-app change. No new runtime result.
- Small-pool allocator14 remains device-verified on old iPad8,1 only. Reviewed
  existing exact CEF ABI inventory/source-gate and do not weaken mismatched API
  checks or repeat stock memory/process failures. Next actionable experiment
  still requires normal Air development access and/or reproducibly compatible
  CEF source/API; no new compatible source or browser result established.
- Private current inventory .madeira-install/mac-arm-heartbeat-20261030-0832/
  device-inventory.json SHA256 b4fa23c8755815a0a0a75d11af5376387cfb22c9146700d9181096db8a4322da.
- Outside weekday Git window; this continuity note stays local, no commit/push.
  No repeated notification for unchanged gate; original305-minute task retained.


### 2026-10-30 17:16–17:19 EDT — Air trusted, Finder OS confirmed; developer pairing required

- User reports unlocked, trusted and iPadOS27.2. Actual Finder General page
  confirms iPad Air4/27.2, proving normal trust/device communication; no recovery
  inference. Finder was backing up; left backup/settings untouched.
- CoreDevice still only exposes unsupported/restorable representation and Xcode
  developer target list omits Air. Opened actual Device Hub official File > Pair
  Nearby Device: window explicitly requires Privacy & Security > Developer Mode.
  Left waiting; user asked to enable/confirm on device or report pairing prompt
  if already on. No agent security-setting change, restart, credential automation.
- Distinct physical USB identity normalized against existing lab profile (remove
  UDID formatting hyphens) is not covered; existing profile expires2026-11-03.
  Need ordinary automatic provisioning for new target after development pairing;
  no EVA/new capability. Existing signed14 standalone probe deep strict PASS.
- No Air app installed/started, no simulator/old-device substitution. Existing
  working apps/data preserved; no commit/push outside22:00–07:00.
- Private report .madeira-install/ipad-air-trusted-preflight-20261030/report.json
  SHA256 7354ceb382b9435bfbfe0993349505afa9b8e0f3e95fbb612835c6783e20755f.


### 2026-10-30 17:22–17:27 EDT — Air paired, ordinary signing/install PASS; native trust pending

- User completed official Device Hub pairing. Fresh CoreDevice now paired,
  hardware iPad13,1/actual iPadOS27.2 build24B119, developerMode enabled, unlocked.
  Earlier unsupported representation/unlock gate superseded. No target substitution.
- Existing lab profile did not include new Air. One ordinary CLI provisioning
  build returns No Accounts/device not included. Did NOT infer GUI logout or ask
  credentials. Created disposable AirLab project with no Memory.entitlements/EVA;
  opened actual Xcode session, selected exact Air via typed target-filter and
  built. New ordinary lab profile covers Air, expires2026-11-06; certificate
  fingerprint matches existing signing identity. No new capability/EVA requested.
- Deep verified prepared standalone14 source/binary receipt and current probe SHA;
  copied to private new ipad-air-partitionalloc14 and re-signed with new profile.
  Deep strict and application/team/get-task/device matching checks PASS, no EVA.
  Actual install succeeds in isolated bundle; working apps/data unchanged.
- First launch is refused CoreDevice10002/FBS Security citing invalid signature,
  inadequate entitlements OR profile not explicitly trusted. All local signing/
  profile/identity checks pass; native developer-app trust is the next concrete
  gate, not yet sole-root-cause proof. User asked Settings > General > VPN & Device
  Management > Developer App trust, then open iDeck PA Lab. No automated security
  confirmation or credentials, no repeated launch before response. No Air runtime
  result, actual CEF, UI or Steam success claim.
- Private artifacts hashes in ipadAirPairedInstall20261030 evidence section;
  standard provisioning project/build log remains private. Do not publish raw
  profiles/device IDs or pairing code. Source/log edits stay uncommitted outside
  weekday22:00–07:00; next collect actual probe console only after native trust.


### 2026-10-30 17:46–17:50 EDT — authorized trust, UIKit scene fix, actual Air15 PASS

- User explicitly authorized Trust/confirm/test at action time. Device Hub
  correct physical Air Developer App page showed only iDeck PA Lab; clicked Trust
  then Allow and visually confirmed trusted state. No credential entry or other
  device/profile security changes. Fresh lock/proc state and branch/remote checked.
- Real trusted14 launch now starts, then SIGTRAP before allocator markers. Copied
  actual dedicated .ips: EXC_BREAKPOINT, UIKitCore top symbol
  ___UIApplicationEvaluateRuntimeIssueForNoSceneLifecycleAdoption_block_invoke.
  This demonstrates original Security launch refusal was resolved; the next
  fault is independent UIKit lifecycle compatibility, not an allocator failure.
- Hypothesis/discriminator: provide required real UIScene window lifecycle in
  own harness and rerun unchanged62 Chromium units/config on same Air. Implemented
  UIWindowSceneDelegate, app configuration callback, matching manifest, own-window
  creation and scene-connected marker. Process once gate avoids repeated global
  allocator teardown; status retained on reconnect (reconnect itself NOT tested).
  No Apple check suppression, upstream allocator/FEX/Valve edit or SDK downgrade.
- Build15 passes actual iOS ARM64 compile/link and verified-source/tamper tests.
  Final scene symbol/log marker+manifest checked, ordinary existing Air profile
  sign/deep-strict PASS. Same isolated bundle upgraded, no working app/data change.
- Actual Air15 install+console+Device Hub UI verified: scene1, two268435456byte
  disjoint pools, allocations398/frees398/workers4/failures0/pools-uninitialized1,
  cef-integrated0. Visible Allocator test PASS. Observer25s timeout is not death;
  subsequent actual version15 and exact installed executable still alive checked.
- Private ipad-air-partitionalloc14/launch-trusted.ips and
  ipad-air-partitionalloc15/{launch.log,result.json,signed-receipt.json,...};
  redacted facts/hashes/source fingerprints in ipadAirSourceAllocator15_20261030
  evidence section. Source parent ad53b40 plus local patch; no commit/push outside
  weekday22:00–07:00. Existing old-Pro results remain historical, not Air proof.
- PhaseA allocator gate on requested Air now actually passes; native Steam UI
  mission remains incomplete. Need compatible CEF source/custom API/small-pool
  build and real native Helper IPC; own UIKit scene patch has NOT yet been applied
  to the AppKit compatibility shim. Do not assume this probe passes Steam through
  its stock16GiB constructor/process gates or proves performance/game support.


### 2026-10-30 17:51 onward — genuine native Steam on requested Air, two distinct shim faults

- Correct branch/origin/remote ad53b40 and local changes preserved; actual
  Air developer access revalidated. Pinned AppKit source already implements
  ShimSceneDelegate and app manifest; no redundant standalone-scene patch.
- Native16 uses preserved converted13 copied privately, build number/signature
  updated only, normal Air profile. Final shims/Helper/scene markers and internal
  symlinks verified. Only completed15 probe identity-verified/ended; source15
  backup remains on host. Working iDeck/apps/accounts never overwritten.
- Actual Air16 VM probe completes/cleans:130 regions, largest observed gap6GiB,
  vm_map1GiB succeeds,8/16GiB KERN_NO_SPACE and mmap8GiB ENOMEM. Inventory is not
  atomic; large mapped/no-access/task-span values do not prove usable backing.
- Actual native16 main loads steamui and reaches UIKit foreground/active callbacks,
  remains black/fps0. Self-spawn result1/created0; tier0 fork-1/EPERM1. Optional
  crashhandler preload misses CoreServices dependency and duplicate GURLHelper
  warning observed; neither established as sole root cause. No UI/login success.
- Important attribution correction: SIGTERM did NOT prove process exit. A later
  launch with CEF env reused original2549 (same procLaunch). No CEF begin marker;
  its .ips is stack-guard KERN_PROTECTION_FAILURE on main, repeated vgui2+3f554
  and shim makeMainWindow. Do not label it CEF failure. Read-only actual VGUI
  disassembly identifies VGUI_NSWindow super order-front call followed by main
  request. Source base makeMainWindow incorrectly dispatches order-front again.
- Hypothesis1/minimal patch: own window-main.m implements focus transition with
  state committed before delegate/observer notifications, no order-front dispatch.
  Only exact pinned generated source method is replaced; upstream checkout and
  Valve instructions untouched. Host reproduction exercises VGUI call direction,
  delegate/observer reentry and transitions under ASan/UBSan; all PASS. Final17
  linked own function, source hashes and deep signing checked before install.
- Fresh17 explicit CEF PID2574 really prints load=begin; two16GiB mmap ENOMEM,
  SIGTRAP, actual .ips CEF+0x3b4dda0. Nearest Rust symbol is not causal attribution.
  No cef_initialize/browser entry. This is the actual Air CEF discriminator.
- Normal17 new2578 progresses to a different failure around121s: missing custom
  NSEvent factory returns nil; NSApplication postEvent inserts it into array
  and raises NSInvalidArgumentException. Exact exception backtrace copied. Not
  a clean150s regression PASS and not proof all main-window behavior is fixed.
- Device Hub Home/app-icon interaction was near/after17 crash; another17 process
  appeared. Do NOT claim same-process scene reconnect success.18 install guard
  caught active lab and refused; fresh exact app-path/PID matched, killed only
  this empty experimental session and verified absence before installation.
- Hypothesis2/minimal patch: other-event.h real custom event factory, types13..16,
  position/modifiers/time/windowNumber, short subtype, NSInteger data1/2 stored.
  Removed wrong pointer-return subtype stub. Invalid event types still raise;
  nil array insertion checks remain, no payload logging. Public Apple API contract
  linked in README. Shared actual factory host fixture tests signed16/64bit
  boundaries, all supported types, real queue insertion and invalid exception.
- Host test initially omitted CoreGraphics link; staged iOS compile exposed
  ambiguous generic-id setters. Corrected link and typed NSEvent accesses; failed
  builds never signed/installed. Final full host/sanitizer/iOS suite, first/second
  compiler-failure preservation and successful3-shim staging checks all PASS.
  Final18 method/marker+focus symbol/input hashes/deep strict signature and
  unchanged original Helper checked.18 installed with same standard profile.
- Build18 extended normal launch result recorded in the following continuation;
  no current genuine login/library/depots/game/return claim. Root source/API/IPC
  gates remain; no FEX/Wine/DXMT or baseline modifications.

### 2026-10-30 19:24–19:27 EDT — Build18 bounded result and later identity limitation

- Recovered completed private observer: actual18 starts18:08:19, reaches the new
  custom-event marker at the old failure point and continues until150s observer
  timeout. No prior nil-event exception in that trace. This supports the specific
  event-contract correction; it does not prove full UI or long-term stability.
- All sampled frame rates remain0. Steam checks/downloads its own update despite
  the fixed startup switches, reaching178283/289112KB by observation end. Download
  completion and post-update contents are NOT verified. Do not silently compare
  later sessions against the originally staged payload. No browser/login proof.
- Fresh19:24 process inventory identifies the same installed18 app with a
  DIFFERENT PID from the bounded run. Original process survival and the reason
  for that change are not established. Device Hub currently shows Home. A single
  later crash-list collection times out initializing CoreDevice; this is not
  crash evidence. No restart/install/termination of the later unknown session.
- Exact remote research branch still ad53b4083147539528c9e5c07cdc2d2641138884,
  verified read-only; scoped changes stay local under weekday Git restriction.
  Private native16..18, signed receipts, host regression/staging logs and source
  fingerprints indexed under ipadAirNative16to18_20261030. Raw data stays private.
- Next device action must first reconcile lab identity and any updater state.
  Further broad AppKit polishing cannot resolve the measured CEF16GiB or native
  process/IPC gates: pursue a compatible source/API CEF with source-wide pool
  layout and real Helper lifecycle. No generic CEF drop-in/hash spoof or binary
  mask patches. Keep working Windows Steam route intact; native route remains
  incomplete, with no login/library/Windows depot/game/return/performance success.

### 2026-10-30 — required custom CEF loader APIs, static discriminator

- Same isolated branch/origin/remote ad53b40 verified read-only; existing local
  edits preserved. No new app install/launch or action on the later unknown18
  session. This experiment is source/host evidence, not a device milestone.
- Hypothesis: the seven custom symbols might be optional; if so a public source
  baseline could potentially progress without reconstructing them. New own
  audit-mac-cef-loader.py reads the genuine official universal Helper ARM64 slice,
  resolves its actual dlsym import stub and recognizes a narrow lookup/store/
  null-check/return-zero shape. All seven have unique required lookups, distinct
  pointer slots and the same resolver/failure epilogue. Missing any returns0 in
  this observed initialization path. This rules out treating them as optional
  for that path, not every possible future architecture.
- Actual original official Helper SHA2568047352bdbd37800dc3ff4d82920c0c9a285c4d578b2b57c796346c467b00f90;
  ARM64 slice dcaea7d1540ad45bae6137ae09fdd572ee93a0a522d8c03878fae07ec2162c37.
  Different from the retargeted/signed installed18 file; do not conflate them.
  Actual audit report/hash and source fingerprints in cefRequiredLoaderAPIs20261030.
- Fourteen synthetic non-executed tests pass: real shape, inverse conditional,
  wrong/matching slots, changed argument/import/return, absent/ambiguous names,
  section bounds, fat bounds/duplicate architecture and import-table separation.
  Existing6 ABI tests pass. Python cache initially hit sandbox's protected cache;
  compile succeeds with PYTHONPYCACHEPREFIX in temporary directory. No runtime
  exception/auth/signing suppression or Valve instruction dump committed.
- Fresh public searches again do not locate matching custom126 source. Official
  upstream remains a different API baseline. Valve issue12226 is still an open
  source request (not proof source is globally unavailable); wiki returns403,
  not bypassed. Public CEF build instructions do not establish Steam ABI support.
- Next: compatible source must implement these extensions with correct semantics
  and all layouts/callback ownership, then build consistently with smaller pools.
  Function-name stubs/hash spoofing would defeat the test. Workspace currently
  has only~3.4GiB free; no huge Chromium download is justified before ABI baseline
  exists. Native Helper IPC remains separate; no new native UI/login/game result.
- Work stays uncommitted/unpushed outside authorized Git hours; source-only audit
  does not justify rebuilding identical installed18 or rerunning unchanged fatal.

### 2026-10-30 19:59 EDT — full public CEF source baseline, hash semantics and exact gate

- User requests continuing until actual success. Goal remains incomplete; no
  substitution with Windows UI or another device, no hash/check/sandbox bypass.
  Branch/origin/remote ad53b40 and local work preserved. One current requested-Air
  process query times out initializing CoreDeviceService; no new launch/install
  or action on the later unknown18 session. Both macOS-on-iOS reference HEADs
  remain pinned c2562a3/CyPort65e2e57; no new existing solution from these refs.
- Acquired full public CEF repository at a5d51ba9db7ee74a523dc247bd09ec91ba4d7446:
  ~2.98MB archive/~15.97MB regular files, NOT full Chromium. Safe regular-only
  extraction, previous8 pinned files match exactly, archive/source hashes saved.
  BSD notices retained privately, no vendored/Valve source or binaries in Git.
- Real upstream cef_api_hash.py regenerates the exact previously observed
  upstream mac e585e190387e31a71267207b66d175e213991470 and universal ed1dfa5f...
  fingerprints. Control changes ONE cef_initialize parameter name only, leaves
  its Clang C function type identical, yet changes mac/universal fingerprints.
  Therefore hash mismatch alone is not exhaustive proof of different ABI layouts;
  also cannot infer all required source edits from7 exported names. Exact private
  argument names/other declarations remain unknown. No guessed implementation
  or generated Valve-matching hash was used.
- Final baseline/control C header AST compiles both succeed, after filling real
  missing build inputs: explicit default mac client cef_config.h and actual
  Chromium126.0.6478.183 net_error_list.h. Initial missing-input compiles were NOT
  successes. These are host header checks, not Valve GN or complete CEF builds.
- Read-only actual official ARM64 Helper has four cef_api_hash(0)/strcmp checks
  against3bf3a90aebd22f3098ae1f2040d618be71553754, with mismatch check-failure
  paths; two correspond to ExecuteProcess/Initialize wrapper sites. Did not patch
  or execute these paths; current actual CEF constructor fails earlier on device.
- Own audit-cef-source-surface.py runs only two reviewed SHA-pinned public hash
  modules copied into a disposable directory, parses the SAME upstream declaration
  objects, rejects symlinks/oversized headers/unreviewed Python and writes a NEW
  report only. Actual full public126 fails mac+universal checks and lacks all7
  required declarations (expected exit2). Passing surface checks would still not
  prove layouts/callback ownership/functional semantics; no no-op stubs allowed.
- Source gate9 tests, existing loader14/ABI6 and full test-local host/sanitizer/iOS
  compile suite pass. Exact code, archive, AST and raw report fingerprints indexed
  under cefFullPublicSourceBaseline20261030. No new device/UI/auth/depot/game result.
- Existing authenticated GitHub code index also searched: exact actual platform
  hash0 hits and custom API constrained toC++0 hits. Broad names find unrelated
  reports, not usable source; no payloads fetched. This is bounded search evidence,
  not proof no source exists globally. No upstream Issue/PR/message sent.
- Specific remaining prerequisites: matching custom source/headers/semantics,
  then consistent small-pool CEF build and actual native Helper IPC. Available
  workspace~3.4GiB is inadequate for a full Chromium tree, but no large download
  is justified before API source gate is resolved. Do not claim success or rerun
  identical stock fatal tests to fill a run. Leave current local work uncommitted
  and unpushed under weekday Git restriction.

### 2026-10-30 23:38 EDT — actual Air19 update/config experiment and Mac CEF control

- Recovered actual18/19 continuation, not a new baseline/main change. Origin/
  experiment remote remain ad53b40. CLI/CoreDevice timeouts were execution-context
  dependent: authorized official queries outside restricted sandbox succeed on
  the unlocked physical Air while Device Hub reported Mac locked. The previous
  Mac-unlock request became nonblocking; no unlock bypass/credentials performed.
- Built19 in a private copy of18 with two new steam.cfg files containing only
  BootStrapperInhibitUpdateOnLaunch=enable, based on actual Bridgeplay source
 8e18aa8. No reference code copied. This is ONLY an unauthenticated version-pin
  hypothesis, not a product security-update policy or established fix.
- Added own opt-in IDeckNativePinProbe=1 observer around existing open/fopen: logs
  fixed basename-category/success/error only, preserves errno, caps32 records.
  Host ASan/UBSan privacy/gating/limit tests and actual iOS Werror compile pass.
  Full test-local and real staging compiler-failure/success regressions pass.
  All3 new final shim markers/input hashes verified; signed with existing exact
  Air profile identity and deep-strict signature. Root instructions, official
  Helper full hash and CEF unchanged. Initially prepared config-only19 signing
  receipt archived; only FINAL observed19 receipt eligible for installed test.
- Fresh preflight confirmed18 app path/PID then ended ONLY that isolated empty
  research session and verified absence. Actual19 installed; current installation
  URL used for STEAM_APP_BUNDLE_PATH, only pin-observer diagnostic enabled.
- Actual180s trace: two successful steam.cfg fopen markers, real native fork
  EPERM and invalid CEF process handle, all fps0. At~122s still background manifest
  check. Actual manifest version1792618285, installed version0 and pending0,
  then Download complete marker. No prior nil-event exception during this trace;
  no interactive browser/login/library result. Key does NOT establish suppressed
  background updates. A basename-only successful open does not identify source
  config path or establish the parser honored that value. Do not claim pin fixed.
- Later fresh process inventory identifies same installed19 path but different
  PID; no cause inferred. Current crash list exposes only3 older16/17 reports;
  no new19 report found, which is not proof of no crash/relaunch. No stale PID
  termination. Package inventory has24 cached update objects with signed manifest,
  no installed marker in that directory. Private bootstrap log also proves18
  completed289112KB cache download at18:11:21 after its observer ended. No cached
  code installation proved; did NOT fabricate an .installed marker/checksum.
- Independent host control: same official CEF SHA4bee8be5... initially fails
  codesign verify because unsigned. Private framework copy receives ordinary
  Mac ad-hoc signature; ARM64 text hashes across Mach-O files stay identical,
  original source unchanged. Own Mac C load-only test now dlopens successfully,
  reads real126.0.0/Chromium126.0.6478.183 and platform3bf3a90a.../universal908f7378...
  identifiers. No cef_initialize, Steam main, browser, login or auth invoked.
  This controls file/host loading; does not solve measured Air16GiB capacity.
- Redacted evidence ipadAirNative19PinAndMacControl20261030 indexes private
  installed/signed receipts, console/cache/bootstrap/host logs and exact source
  hashes. Actual remaining gates unchanged: validated custom CEF source/ABI plus
  source-wide small pools, then real Helper IPC/lifecycle. Generic hash spoof,
  no-op exports, fake mmap/PIDs and private entitlements remain excluded.
- Full task remains incomplete. No native Steam auth/library/depot/game/return
  or performance improvement claim. Working Windows app/data preserved. Current
 23:xx NY Git window permits scoped reviewed source-only checkpoint; verify time
  again immediately before commit and push, do not merge into main.

- Final bounded cleanup: fresh installed19 app identifier/version/path and exact
  current lab process revalidated, terminated ONLY this unauthenticated native
  experiment, verified no matching process.19 remains installed with its data;
  working apps untouched. Final full host/sanitizer/iOS/staging and Mac control
  Werror compile pass again before checkpoint. No native completion claim.

### 2026-10-31 00:16 EDT — Air debug control and real Mac-target compact allocator20/21

- User requests immediate continuation. Verified experiment branch/origin/remote
  f3fcb40, other worktrees unchanged. Actual Air still27.2(24B119). No waiting for
  schedule and no overlapping device experiments. Explicit probes only, no auth.
- New debugger discriminator: fresh signed19 start-stopped and real LLDB attach.
  Default remote symbol reading warns no matching on-disk shared cache and halt/
  detach time out. Exact probe identity revalidated before cleanup. Its later
  .ips proves CEF trap at+3b4dda0 with CS_DEBUGGED; initial sparse console was not
  proof constructors never ran. A separate minimal-module/no-preloaded-symbol
  session obtains a real dyld stop and detaches successfully. Same process then
  logs CEF begin, two16GiB ENOMEM, SIGTRAP. Actual .ips confirms CS_DEBUGGED and
  exactCEF+3b4dda0. This is attach/detach, not continuous-attached CEF validation.
  No grant/protection/code/signature bypass; normal debug still fails on Air.
- Implemented the next source-rebuild component: actual macOS ARM64-targeted
  Chromium126 PartitionAlloc, then metadata-only retarget to iOS and load from
  own UIKit app. Unlike earlier iOS Runner probe, allocator TUs compile with
  IS_MAC1/IS_IOS0 and explicit compile-time shared compact definition. All62
  pinned units + own entry share patched headers/flags; original362 source blobs
  remain byte-verified and untouched. Only3 files change in a disposable copy.
- Initial actual Mac link exposes missing real Security.framework for upstream
  SecTask queries; linked it and verified public iOS SDK exports. No dummy
  signing-status implementation, new entitlement, MAP_JIT grant or JIT test.
  Host Mac real allocator398 alloc/free/4workers/0failures passes. Instructions
  before/after vtool+framework path retarget and after signing match.
- Actual Air standalone20 install/run passes: dlopen1/entry1, compiled-mac1,
  two256MiB independent pools, disjoint1,398alloc/free,4workers,0failures,cleaned1.
  Source changes are isolated, no Valve payload.20 uses initial resultABI1;
  final source evolves toABI2/72bytes for glued telemetry, distinguish receipts.
- Glued pool source experiment initially fails REAL link: CorePoolsSize inline
  calls RegularPoolSize whose definition is in another TU. Fixed shared header
  selectors inline under explicit compact-Mac opt-in; excluded duplicate .cc
  selectors for that opt-in only. Dynamic masks/checks preserved; no arithmetic
  instruction patches. Public CorePoolsSize, adjacent base and core-mask interval
  tests now link and run. Non-opted iOS selection unchanged.
- Current default20d and glued21c Mac host builds both pass. Own source snapshots
  saved before compile; change-during-build refusal and receipt fingerprints.
  Null result, wrong capacity and repeated-entry contracts pass in Mac control.
  Seven own synthetic patch/metadata tests and full host/sanitizer/iOS suite pass.
- FINAL21 compiled symbols, Mac target static asserts,IOS metadata, instruction
  hashes, existing profile and deep signature verified before installation.
  Ended only exact completed20 probe; same isolated ID upgraded, container kept.
  Actual Air21 console: build21/load1/entry1/pass1, glued1,398alloc/free,4workers,
 0failures,two256MiB pools,disjoint1,cleaned1. After35s observer timeout, fresh
  actual21 installation and exact completed-probe process confirmed alive.
  No screenshot was captured; device logs/install/process artifacts are evidence.
- This is a useful source-side allocator component, NOT Steam/browser integration.
  Do not preload it into stock CEF with fixed inline masks. Still need matched
  custom CEF source/headers/semantics, all-consumer rebuild, browser/V8 allocation
  validation and real Helper IPC/lifecycle. Threadcache/raw_ptr lifetime/malloc
  replacement/pointer compression/StarScan/MTE/V8JIT untested here. No native
  auth/library/depot/game/return/performance-success claim. Working iDeck intact.
- Evidence macCompiledCompactAllocator20261031 and ipadAirDebugCEFControl20261031
  holds hashes/source fingerprints; raw logs/binaries/profiles stay private.
  New scale-interface public reference supplies a Linux caller signature only,
  not a CEF implementation or matching headers; no code copied or executed.
- Prepared CEF_SOURCE_REQUEST_DRAFT.md for existing Valve issue12226. Requested
  explicit authorization before any upstream message; nothing sent. Continue
  local verified work while pending. Do not treat elapsed time as approval.

### 2026-10-31 00:20 EDT — authorized matching-source request published

- User explicitly approved the exact prepared technical request to existing
  ValveSoftware/steam-for-linux issue12226. First published verified source
  checkpoint bfb0b8bde61336d2d75b7a331ab44664701920b7; both commit00:19:37 and
  push00:19:51 EDT individually checked within allowed weekend window.
- Correct issue open, no comments before send. GitHub connector write403 is an
  integration permission limit, not a user-account denial. Existing authorized
  gh session separately confirmed kuscholar, official API sent exact approved
  JSON body once; independent connector read confirms same author/body/ID.
- Published2026-10-31T04:20:50Z:
  https://github.com/ValveSoftware/steam-for-linux/issues/12226#issuecomment-6538931459
  Body receipt/hash recorded in cefSourceRequestPublished20261031. No raw device
  data, account/signing payload, new issue/PR/email or additional message.
- Delivery is not maintainer acceptance, a source release, or working Steam.
  No response/source access inferred. Keep full native mission incomplete,
  current isolated21 component evidence separate from the actual CEF/UI gates.

### 2026-10-31 08:01 EDT — actual compact-Mac raw_ptr BRP lifecycle, Air22

- User requested immediate continuation. Branch/origin/worktree/remote02697f3
  verified clean before edits; other worktrees preserved. Valve issue12226 still
  only contains the authorized request; no response or additional message.
- Hypothesis: compact dynamic masks preserve genuine raw_ptr BRP metadata and
  deferred-free semantics, beyond earlier bare allocation tests. Added explicit
  --raw-ptr-brp to own builder, two unmodified upstream pointer units (64total),
  USE_RAW_PTR_BACKUP_REF_IMPL1 shared by all consumers, and own lifetime tests.
  Same3 private BSD pool-source edits; no Valve/FEX/Wine/DXMT/product changes.
- Cases1/128/4096/2MiB test real copy/move/interior references, original metadata
  alive-state transition, count1 quarantine after allocator free, no retained-slot
  reuse, and count/bytes0 after final release. Fifth case moves final reference
  to worker and releases there. No freed payload dereference or metadata access
  after final release; no unsynchronized mutation of the same wrapper.
- Real Mac-target glued host PASS:407 allocations/frees,4workers,5lifetimes,
  0failures. Same source default no-raw-pointer independent host PASS398/0cases;
  independent BRP host PASS407/5cases. ABI3/80bytes distinguishes these new
  receipts from historical21 ABI2/72bytes. Existing7 builder fixtures and full
  host/sanitizer/iOS/staging suite PASS. Actual allocator not sanitizer-built.
- Fresh user-selected Air physical access/unlocked confirmed. Ordinary existing
  profile/identity and module text hash/deep signing verified. Identity-checked
  completed21 upgraded ONLY in isolated lab to22; working apps/auth/games intact.
- Actual Air22 console load1/entry1/pass1, two256MiB glued/disjoint pools,
  407alloc/free,4workers,5BRPlifetimes,0failures,cleanup1. Observer35s timeout is
  not process death: fresh installed22 and exact completed-probe path alive.
  No screenshot; source/signed/install/log/process receipts private and hashed
  in macCompactRawPtrLifetimes20261031.
- Bounded lifetime test, not full raw_ptr/race/reporting semantics; standalone
  dangling-report callbacks remain untested. Threadcache/malloc replacement/
  pointer compression/StarScan/MTE/V8JIT/browser allocations untested. No CEF or
  Steam integration/UI/auth/library/depot/game/return/performance success.
- Next substantive integration still needs matched custom CEF source/semantics,
  consistent full-consumer rebuild, then actual browser and native Helper IPC.
  Do not inject this into stock fixed-mask CEF or repeat its unchanged fatal.
