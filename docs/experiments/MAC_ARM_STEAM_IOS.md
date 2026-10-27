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
