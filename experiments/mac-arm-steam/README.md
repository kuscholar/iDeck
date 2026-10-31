# Native macOS Steam compatibility experiments

These files are isolated research components, not linked into ordinary iDeck.
No Valve binaries, games, account data, signing profiles or device logs belong
in this directory. See `docs/experiments/MAC_ARM_STEAM_IOS.md` for actual results.

- `sysv-semaphore-diagnostic.c`: first-failure probe returning ENOSYS instead of
  calling iOS's unavailable semget syscall. Never link alongside the real subset.
- `sysv-semaphore.c`: process-local, one-semaphore-per-set implementation using
  pthread synchronization. Supports keyed lookup/create/exclusive, atomic batches,
  decrement/zero waits and NOWAIT, SETVAL/GETVAL/GETPID/waiter counts and removal.
  Removed IDs are generation-checked and waiters wake with EIDRM. Capacity128,
  at most32 operations per batch, maximum value32767. No cross-process shared
  memory or permission/ownership model is supplied. SEM_UNDO applies to the
  single hosting OS process; all entries vanish with that process, and thread
  exit does not undo a decrement. This does not implement future pseudo-process
  teardown. Signals/cancellation and fork semantics are not a complete SysV ABI;
  cancellation is disabled while waiting. Unknown commands/flags return errors.
- `appkit-font.m`: supplies the observed missing NSFont label font class method
  through public UIFont. Does not replace an existing method implementation.
- `exec-diagnostic.c`: forwards execv to the system and preserves its result and
  errno. Logs executable basename and fixed allowlisted switches; unknown values
  are counted and redacted. Native fork/spawn observers preserve actual errors.

Local tests (macOS/Xcode):

```sh
python3 experiments/mac-arm-steam/test-manifest.py
python3 experiments/mac-arm-steam/test-staging.py
xcrun clang -Wall -Wextra -Werror -fsanitize=address,undefined -pthread \
  experiments/mac-arm-steam/sysv-semaphore.c \
  experiments/mac-arm-steam/test-sysv-semaphore.c -o /tmp/ideck-sem-test
/tmp/ideck-sem-test
```

Fetch package inputs into a private directory OUTSIDE this Git repository:

```sh
python3 scripts/experiments/fetch-mac-steam.py --output ../.madeira-install/mac-arm-steam-official \
  steam_osx bins_osx bins_client_osx webhelpers_osx webkit_osx appdmg_osx \
  resources_all resources_misc_all resources_hidpi_all public_all strings_en_all \
  strings_all steamui_websrc_all steamui_websrc_sounds_all steamui_websrc_movies_all \
  tenfoot_images_all bins_codecs_osx bins_misc_osx bins_hardware_osx \
  bins_hardware_all sdl3_osx breakpad_osx miles_osx
python3 scripts/experiments/stage-mac-steam.py \
  --packages ../.madeira-install/mac-arm-steam-official \
  --output ../.madeira-install/mac-arm-steam-new-source
```

Downloads come from Valve's HTTPS CDN and are checked against the versioned
manifest's size and SHA256. This checks package integrity, not Valve's separate
kvsign cryptographic signatures. The staging script rejects an existing output,
archive traversal and escaping symlinks. It does not install or execute Steam.

The public macos-on-ios converter c2562a3 was used privately for the current
experimental bundle, with an explicit login-keychain signing selection. Its
AppKit and other generated stubs are incomplete and cannot establish API
compatibility or correct security/authentication behavior. Do not enter Steam
credentials until those paths are audited and actual UI is working. No login
attempt has occurred in this experiment. Preserve its MIT notices for any
future vendored or distributed shim code; that source has not been vendored here.

Conversion input excludes these non-ARM64 legacy/optional files (not claimed to
be functionally unnecessary): `MacOS/libsteamwebrtc.dylib`, `libopenvr_api.dylib`,
`libsteam.dylib`, `libMilesX86.dylib`, `libMilesX64.dylib`,
`MacOS/bin/hardwareupdater/hardwareupdater.macos.x86_64`, and
`MacOS/resource/sourceinit_macos.dat`. Prefix each top-level dylib with `MacOS/`
when using the converter's `--exclude`. The current ARM64 source has56 included
Mach-O files, not a general claim that all Steam components are ported.

On the converted COPY only, AppleDouble metadata was removed, the moved
`steam.sh` link was pointed to the root executable, and three helper dylib links
were pointed to the actual Contents/MacOS libraries. Sign Mach-O files, nested
bundles and app in that order with your own matching profile. Neither this
private converted Steam bundle nor its IPA may be published in the source repo.
The only installed target is the dedicated experimental probe app ID. Never
reuse the production iDeck ID. Current deployment still exits before CEF.

The reference converter moves the main executable to the iOS bundle root while
its `_NSGetExecutablePath` shim advertises `Mac/Contents/MacOS/<executable>`.
After conversion, `fix-mac-executable-layout.py <experimental-copy.app>` adds the
missing internal symlink to the actual root executable, refusing conflicting
paths. Re-sign the app afterwards. Offline fixture tests:
`python3 experiments/mac-arm-steam/test-executable-layout.py`.
Device comparison confirms the link removes NULL/EFAULT; native self-exec then
returns EPERM. Supplying the client's own STEAM_APP_BUNDLE_PATH environment
contract enters second-stage startup without self-exec; it does not enable
native Helper creation. The internal Frameworks alias is also needed for
crashhandler's loader-relative dependency.


Current local contracts and next device test:

```sh
bash experiments/mac-arm-steam/test-local.sh
python3 scripts/experiments/build-mac-steam-overrides.py \
  --reference /path/to/macos-on-ios-public \
  --converted /private/disposable/converter-output
```

The builder reads the exact pinned MIT reference revision from Git, generates
patched copies in a temporary directory, and rebuilds ONLY the three shim
dylibs inside the matching isolated experimental bundle. It does not sign or
install. Re-sign each rebuilt dylib and the root app with the matching developer
profile/identity and verify `codesign --verify --deep --strict` before installing.
It does not modify the reference checkout or the ordinary iDeck build.

New contracts are intentionally narrow:

- `casefold-path.m`, `casefold-probe.m`, `volume-case-view.m`: component lookup
  within this app's canonical bundle/data roots, plus a capability-gated NSURL
  volume-property view. Eight real-device fixture operations passed. This does
  not implement every filesystem API, race, Unicode normalization or physical
  volume behavior. Keep the Info flag `IDeckCaseView` experimental.
- `display-pixel-encoding.m`, `display-mode-object.m`: the reference's single
  SDR display needs a retained encoding CFString and genuine CF mode object.
  SDL retains modes through CF arrays. Other display APIs remain incomplete.
- `bitmap-image-rep.m`: bounded, writable, zeroed RGBA8 CPU storage only;
  unsupported sizes/formats fail. No NSImage drawing or cursor rendering claim.
- `font-matrix-constant.m`: correct AppKit DATA pointer ABI for the identity
  matrix; generated function placeholders are wrong for this symbol. The font
  bridge accepts only ordinary uniform, unrotated matrices.
- `native-process-probe.c`: explicit `IDeckNativeProcessProbe=1` attempts normal
  signed self-spawn; actual phone result EPERM. No fake process handles.
- `cef-load-probe.m`: next experiment, `IDeckCEFLoadProbe=1`, loads the actual
  signed/retargeted CEF framework and checks four exports, then exits. **Not yet
  device-run.** It deliberately does not initialize CEF or claim browser/UI
  success. Do not combine multiple diagnostic flags in one session.

After an isolated install, obtain its CURRENT installation URL from devicectl's
receipt. Pass `STEAM_APP_BUNDLE_PATH=<current-installed-app>/Mac` via devicectl's
JSON environment option. Put `--` BEFORE the bundle identifier, then the fixed
client arguments `-nobootstrapperupdate -skipinitialbootstrap -noarchrestart`.
For the next discriminator also pass `IDeckCEFLoadProbe=1`. Never reuse old
installation UUID paths. Console observer timeout is not proof the app exited.

Actual current limit: genuine Steam main, steamui and SDL execute; native fork
and a separate normal self-posix_spawn test both return EPERM in this phone's
sandbox/signing configuration. The original Steam Helper handle is invalid.
An in-process host must preserve IPC/identity/exit contracts; a fake PID or
Chromium single-process switch alone cannot establish that. No working native
CEF/login/library or Windows-game bridge is demonstrated.

Authentication remains gated: the generated Security shim includes unsupported
legacy macOS Authorization/Keychain functions returning zero placeholders.
Their types/output/status contracts need a fail-closed audit before any user
credentials. This experiment has no account data and has not attempted login.
Do not suppress signing/trust/authentication failures to advance the UI.

Build4 adds `native-vm-probe.c` (`IDeckNativeVMProbe=1`) for actual task-map
inspection and genuine4KiB/1GiB/16GiB/32GiB PROT_NONE reservations, each immediately
unmapped. It writes only its own numeric report under the isolated container's
Documents/ideck-native-vm-<pid>.txt, then exits before CEF/Steam main. The actual
phone fails16/32GiB with ENOMEM; this is a completed diagnostic, not CEF success.

The load-only CEF probe was now device-run: its library constructors request16GiB
and fatal before dlopen returns. A normal LLDB attach/detach sets CS_DEBUGGED,
but the identical CEF fatal recurs. No completed load or UI result is claimed.
Public Extended Virtual Addressing was separately authorized for the isolated
app, but Xcode rejected it for the actual Personal Team. The user has no paid
team and selected research without this capability. Current builds use the
original standard development profile, without EVA.

Always make the outer build/sign/deploy command fail fast (`set -euo pipefail`),
and verify diagnostic markers in the FINAL rebuilt dylib before signing/install.
A failed compile can leave old output files behind. An installed, signed app with
a newer Info.plist build number does not prove the new source was linked.

The builder now compiles all three shims into a disposable staging directory
before replacing final dylibs. A compiler failure preserves all previous final
dylibs and Info.plist, removes any prior `ideck-shim-build.json` success receipt,
and cleans pending outputs. Filesystem replacement errors are not transactional;
any nonzero exit must still stop signing/install. On complete success, the
unsigned receipt records pinned reference revision, source/generated-input
fingerprints and SHA256 for all three outputs. Verify it BEFORE signing (signing
changes whole-file hashes), then record signed hashes and verify linked markers.
The installed historical Build4 predates this receipt; do not fabricate one for it.

Real-compiler failure injection and optional full-success synthetic fixture:

```sh
python3 experiments/mac-arm-steam/test-build-staging.py \
  /path/to/pinned/macos-on-ios-public /private/converted-output/shims
```

This reads only reference source and generated shim source files, builds into a
new temporary fake app layout, then removes it. It does not read Valve binaries,
signing assets, authenticate, install or modify the actual converted app.

Free-signing continuation (user has no Developer Program team):

- `native-small-pool-probe.c` + `pool-layout.c`: explicit
  `IDeckSmallPoolProbe=1` reserves TWO real, simultaneously owned chunks. Each
  contains a256MiB-aligned256MiB subrange with at least one actual guard page
  before it. All mappings stay PROT_NONE and are fully released. Actual Build5
  device result: geometry/disjoint/mask-boundaries/cleanup all1. This is NOT
  PartitionAlloc implementation, CEF integration, physical-memory allocation,
  rendering, authentication or gameplay validation. No returned CEF mapping is
  altered or faked. The stock CEF still requests16GiB and remains unchanged.
- `audit-mac-cef-abi.py`: statically parses the audited ARM64 CEF126 public
  version/API-hash getter shapes, rejecting unknown code, unbacked/encoded
  pointers and malformed hashes. It NEVER dlopens the library. Compares pinned
  upstream headers/loader with actual Steam framework and Helper exports.
  Existing non-report outputs and inputs are preserved. The public ABI hashes
  are compatibility identifiers, never authentication tokens.

```sh
python3 experiments/mac-arm-steam/test-cef-abi-audit.py
python3 scripts/experiments/audit-mac-cef-abi.py \
  --cef '/private/converted/Steam-iOS.app/Mac/Contents/Frameworks/Chromium Embedded Framework.framework/Chromium Embedded Framework' \
  --helper '/private/converted/Steam-iOS.app/Mac/Contents/Frameworks/Steam Helper.app/Contents/MacOS/Steam Helper' \
  --upstream /private/pinned-cef-source --output /private/cef-abi-report.json
```

Current comparison source is chromiumembedded/cef6478 at
`a5d51ba9db7ee74a523dc247bd09ec91ba4d7446`. It is ONE upstream comparison, not proof
of every historical release or of Valve's private build options. Actual Steam
metadata is CEF126.0.0/commit-number3171, Chromium126.0.6478.183. Both API hashes
mismatch this pinned upstream header;7 CEF symbols shared by the actual framework
and Helper are absent from upstream's generated loader. Their presence does not
prove every one is mandatory, and symbol/hash comparison alone cannot establish
full C struct ABI. Never spoof the API hash to substitute a generic binary.

A source-built small-pool framework would need compatible headers, semantics,
Valve extensions and preserved licensing, then actual source allocator tests and
signed device CEF initialization. No matching buildable Steam-custom source has
yet been located. Do not describe the geometry probe as a small-pool CEF fix.


Native Helper boundary observer (private converted copies only):

```sh
python3 scripts/experiments/build-mac-process-observer.py \
  --converted /private/converted-output
```

Requires the exact audited, converted ARM64 tier0 hash and isolated lab bundle.
It stages a re-export proxy and dependency metadata changes for its consumers,
checking `__TEXT,__text` hashes before replacing files. Compile/validation failures
preserve final files; filesystem replacement errors are not transactional.
Stop the entire pipeline on ANY nonzero exit. The unsigned receipt is invalid
after signing, so verify input/output hashes before signing every modified file
and nested bundle; verify deep/strict signatures before installation. A second
invocation refuses an existing proxy rather than overwriting an unknown build.
The official source bundle remains read-only. This is NOT a production feature.

Explicit `IDeckNativeProcessObserver=1` reports fixed known switch names and
counts only. Paths, account IDs, tokens, parameter values, environment contents
and unknown switches are never emitted by this observer. Text command hints
are lexical only; no shell parser/execution or reconstructed command is used.
Original arguments, incoming errno, result and outgoing errno are preserved.
The actual Build6 phone test observes Helper argv flags0xa and native fork EPERM;
there is no `--single-process` in that observed call. No fake process/PID/IPC
is supplied, and no success is reported for a denied launch. Steam's own raw
logs are private, regardless of observer redaction.

`font-advancement.m` calculates the actual horizontal maximum glyph advance for
a CoreText font; the UIFont adapter provides the missing AppKit selector for
the observed named-font request. It does not implement arbitrary variation
axes, transformed fonts or a complete AppKit font API. Host tests verify actual
glyph bounds and font-size scaling; see the research log for device results.

Optional native power registration correction:

```sh
python3 scripts/experiments/build-mac-power-shim.py \
  --converted /private/converted-output
```

The observed reference dummy port caused a real dispatch crash. This isolated
shim now returns the documented failure sentinel and clears output handles for
unsupported macOS root-domain power notification registration. It does not fake
power events or request private IOKit access; other real IOKit functions remain
re-exported. Validate unsigned receipt and marker before signing. Build8 actual
phone trace passes that previous crash for25s, but shows a black screen and zero
presents; process survival is NOT CEF/UI success. The native Helper fork denial
and CEF16GiB reservation failure remain unresolved.

Additional explicit diagnostics (never combine their environment switches):

- `IDeckNativeVMRangeProbe=1`: enumerate occupied VM regions, then make real
  no-access ANYWHERE reservations through the SDK's LP64 vm_map and POSIX mmap.
  No fixed overwrite/custom range/entitlement/protection change. Actual Build9:
  largest observed unmapped gap6GiB; vm_map1GiB succeeds,8/16GiB KERN_NO_SPACE;
  mmap8GiB ENOMEM; all cleanup verified and diagnostic exits0 before Steam main.
  Region scan is not atomic or a capacity guarantee for other apps/devices.
- `IDeckNativeHelperLoadProbe=1`: normal dlopen of unchanged MH_EXECUTE Helper,
  no entry call; error text redacted to a fixed executable-rejection category.
  Prepared Build10 is compiled/signed but install timed out; fresh installed
  version still9. This probe has NOT been run on device. Do not enable it in an
  older installed build and mistake ordinary Steam startup for a probe result.

The native exec/fork/spawn observer source also restores errno BEFORE forwarding
(the existing returned errno preservation remains), and redacts unknown program
and caller-module basenames. `test-exec-diagnostic.c` mocks resolvers and checks
all four calls without executing any host process. This source-only hardening
postdates installed Build10; it has not been linked/deployed or device-tested.
A fresh query later confirmed Build10 installed despite the old timeout; do not
reinstall it blindly. Its Helper-load probe still awaits a native phone unlock.

Current milestone and limitations: [evidence matrix](../../docs/experiments/MAC_ARM_STEAM_COMPATIBILITY.md).

Build11 loader-probe correction: derive the target from real libSystem's native
executable path, since NSBundle.bundlePath is intentionally redirected by the
AppKit shim. Reject redirected logical executable paths and verify the actual
ARM64 MH_EXECUTE file header before dlopen. Build10's unknown failure lacked
this preflight and is not a loader-type result. Actual Build11 phone test verifies
the target, then dlopen returns NULL with executable-rejection category1 and
missing-image category1 (substring categories may overlap); entry-called0. An
explicit diagnostic-result marker is authoritative for probe outcome; console
transport/app exit status alone is insufficient. No native Steam UI success.

Own loadable-bundle design discriminator:

```sh
python3 experiments/mac-arm-steam/test-synthetic-helper-bundle.py
```

Only iDeck-authored synthetic fixtures participate. The exact-hash/unique-marker
metadata tool is NOT a Steam converter. It preserves instruction bytes and
chained-fixup segment ordinals, refuses output conflicts, and requires normal
signing. Six host tests cover guard/payload/ordinal/loader contracts. Build12
actual iPhone `IDeckSyntheticHelperProbe=1` loads the signed metadata-adapted own
Mac ARM64 bundle and checks constructor1/main0; executable-form counterpart
fails to load. This probe calls no Steam entry, CEF or IPC and is not UI success.
The Mac host accepting the original executable is not evidence iOS accepts it.
Never apply the synthetic-only tool to Valve files; real Helper adaptation
requires a separate exact-version private-copy audit and unresolved CEF/IPC work.

Reproducible single-probe execution after isolated Build12 is installed:

```sh
python3 scripts/experiments/run-native-lab-probe.py \
  --device YOUR_PHYSICAL_DEVICE_IDENTIFIER --probe vm-range \
  --artifacts ../.madeira-install/NEW_PRIVATE_RUN_FOLDER
```

Use a different new private folder for `--probe synthetic-helper` or `helper-load`.
The runner refuses simulator targets, ordinary iDeck, unreviewed app versions,
locked devices and existing lab sessions; it never installs, signs, unlocks or
terminates anything. Result markers, not console transport exit, determine
whether the diagnostic completed. Raw device metadata/logs stay outside Git.
`test-native-probe-runner.py` covers8 marker/identity/version/URL contracts.
The initial iPad connection attempt failed before runtime; prior phone-artifact
replay is not iPad execution evidence.

Actual iPad results now exist: isolated12 VM-range/own-bundle/unchanged-Helper,
then isolated13 exact Helper candidate and native-process tests. See latest
research log/matrix; earlier connection/slot gates are historical. Runner now
accepts only reviewed12/13, with9 host tests; no simulator or product app fallback.

Exact real Helper private-copy loader discriminator (separate from own-fixture
converter):

```sh
python3 experiments/mac-arm-steam/test-native-helper-metadata.py
python3 scripts/experiments/prepare-native-steam-helper-bundle.py \
  --converted /private/converted-output
```

The second command requires the exact audited converted Helper hash and isolated
lab layout, refuses existing output/receipt, preserves original Helper and all
instruction/bind/rebase payloads, and corrects only loader metadata/CEF path in
its separate candidate. Verify unsigned receipt, normal signatures and final
instruction hash before install. Use only explicit
`IDeckNativeHelperBundleProbe=1` for its bounded load test; never combine probe
switches. Actual iPad13 reaches genuine CEF constructors then16GiB ENOMEM/SIGTRAP;
no dlopen completion, Helper entry, CEF browser, auth or UI success is claimed.
The source-only metadata fixture tests do not execute Valve code.

### Actual PartitionAlloc source probe (Build14/15)

This is a separate UIKit test app using the same **isolated lab** bundle ID;
it replaces only that lab binary, never working iDeck. It contains no Valve
files and does not start Steam. The private converted Steam13 app remains on
the host for a later justified experiment. Read current installed-app/process
state before switching experiments; the old native runner intentionally refuses14.

```sh
python3 scripts/experiments/build-partitionalloc-probe.py --fetch \
  --source ../.madeira-install/partitionalloc126 \
  --output ../.madeira-install/NEW_PA_BUILD_FOLDER
IDECK_PA126_SOURCE=../.madeira-install/partitionalloc126 \
  python3 experiments/mac-arm-steam/test-partitionalloc-builder.py
```

The fetch verifies the pinned362-file Chromium126.0.6478.183 subtree/receipt and
two build headers, about3MB, without a full Chromium/GN download. The build
checks every source hash and compiles62 actual upstream units; no upstream
instruction/source patch, fake pool grant or malloc interposition. Generated
flags explicitly enable BRP, slow checks, DCHECK and expensive DCHECK. Other
optional features (StarScan, MTE, thread cache, malloc replacement, pointer
compression) are outside this probe. This is a minimal direct-clang harness,
**not** Chromium's complete GN build or Valve CEF's build configuration.

The executable is deliberately named `PartitionAllocRunner`: the *unmodified*
upstream iOS `IsIOSTestProcess()` selector recognizes the `Runner` suffix and
chooses256MiB pools. This public upstream test path needs neither EVA nor JIT.
Retagging stock macOS CEF does not enable it; a compatible CEF source build
remains necessary. Never rename the stock Steam executable and claim that its
already compiled allocator has changed.

Output is UNSIGNED. Check `build-receipt.json`, linked markers, iOS platform and
system-only dependencies before normal development signing. Embed a currently
valid profile covering the lab bundle and target device, sign with the existing
standard lab entitlements, then `codesign --verify --deep --strict`. No new
capability/profile may be assumed. With the prior lab session identified and
ended, install only `PartitionAlloc.app`, then launch:

```sh
xcrun devicectl device install app --device YOUR_DEVICE_ID \
  /private/path/PartitionAlloc.app
xcrun devicectl device process launch --device YOUR_DEVICE_ID --console \
  --timeout 25 -- com.kuschqin.ideck.maclab.macprobe
```

Actual physical iPad14 console: pool-bytes268435456, disjoint1, allocations398,
frees398, workers4, failures0, pools-uninitialized1, cef-integrated0. Ordinary
and BRP roots test sizes1byte through2MiB, content preservation, live requested
interval separation and non-LIFO frees. This tests allocations *in* the BRP
pool, not the complete `raw_ptr` dangling-reference protocol. Explicit root/pool
test teardown is checked; no long-run leak/performance or full CEF claim.
The UI remains visible after completion; a console timeout is not process death.
Chromium BSD LICENSE and AUTHORS are included in the standalone build.

Build15 now uses a real `UIWindowSceneDelegate`, a matching scene manifest and
the application delegate's configuration callback. The old Build14 launched on
iPadOS26.7.1, but on the newly paired physical iPad Air4/iPadOS27.2 it trapped in
UIKit `UIApplicationEvaluateRuntimeIssueForNoSceneLifecycleAdoption` before any
allocator marker. Do not disable that check or change the upstream allocator.
See Apple's [scene lifecycle migration guide](https://developer.apple.com/documentation/uikit/transitioning-to-the-uikit-scene-based-life-cycle).
The scene creates its own window and a process-wide once gate prevents allocator
test teardown from being repeated when a scene reconnects. Completion status is
retained for a newly connected scene; multiwindow/scene reconnection behavior is
not independently device-tested. The builder produces15 using the same commands.

After user-authorized native developer trust, actual Air15 shows PASS and logs
`scene-connected=1`, two256MiB disjoint pools, allocations398/frees398, four workers,
zero failures, pool teardown1. Installed version and exact live executable were
independently checked after the25s console timeout. No JIT/EVA, Steam or CEF.
Developer trust and computer pairing are separate steps; never assume the latter
authorizes or completes a device security confirmation.

### Native Steam on Air, window-focus discriminator (Build16/17)

The pinned native AppKit shim already has `ShimSceneDelegate` and a matching
manifest; the standalone probe's scene fix must not be blindly copied into it.
Native16 on physical Air27.2 enters real scene callbacks and loads `steamui`,
but remains black; native self-spawn and Steam tier0 fork return EPERM. Its VM
probe reserves/releases1GiB but rejects8/16GiB (KERN_NO_SPACE); mapped/task-span
counts are not evidence of a large usable contiguous range.

A later16 crash exposed a separate real failure: main-thread stack-guard
KERN_PROTECTION_FAILURE with repeating VGUI `makeKeyAndOrderFront:` /
shim `makeMainWindow` calls. Read-only disassembly confirms the VGUI subclass
calls its super's order-front implementation and then requests main-window
focus; the shim incorrectly called the overridable order-front selector again.
The initial alleged CEF16 attempt reused that same PID after SIGTERM and had
**no** CEF begin marker. It is not a valid fresh CEF experiment. Always verify
the previous exact lab PID has exited before treating launch environment
variables as a new test condition.

Build17's own `window-main.m` changes main-window focus directly, updates state
before callbacks and emits transition notifications once, without calling
order-front. The exact pinned reference method is replaced only in a staged
generated private-copy build. `test-window-main.m` reproduces the Steam subclass
call direction, delegate/observer reentry and focus switches under ASan/UBSan.
This is a narrow correction, not full NSWindow focus/visibility emulation.
No upstream reference checkout, Valve instructions, FEX or product path changes.
Full compiler failure-injection/success staging checks also pass:

```sh
python3 experiments/mac-arm-steam/test-build-staging.py \
  /private/pinned-macos-on-ios-reference \
  ../.madeira-install/mac-arm-steam-converted/shims
```

The real17 `IDeckWindowMakeMain` symbol was checked in the final dylib before
normal signing/install. A genuinely new17 CEF load prints `load=begin`, fails
the stock16GiB reservation with ENOMEM and traps; this fix does not make a
source-built small allocator part of the precompiled Valve framework. No login
or Big Picture claim. Read the latest research log for bounded normal-launch
regression results and exact private evidence hashes before any further run.

The actual17 normal launch progressed to VGUI's event queue, then failed after
about121s: missing `otherEventWithType:...` resolved to the generic nil stub and
`postEvent:atStart:` raised on nil insertion. The copied exception stack identifies
that queue operation; this is distinct from the old focus stack-guard failure.
Build18 supplies the real custom-event factory and scalar storage: allowed event
types13..16, position, modifiers, timestamp, window number, signed16bit subtype
and signed64bit data fields. Invalid types still raise an exception; no queue
assertion/exception is suppressed and no arbitrary payload is logged. The
obsolete graphics context parameter remains unused, per Apple's
[factory contract](https://developer.apple.com/documentation/appkit/nsevent/otherevent%28with%3Alocation%3Amodifierflags%3Atimestamp%3Awindownumber%3Acontext%3Asubtype%3Adata1%3Adata2%3A%29?language=objc).
The same `other-event.h` implementation is compiled into the shim and the host
ABI fixture; tests cover signed boundary values, actual array insertion and
invalid-type exceptions. Early host link and generic-id selector ambiguity
errors were corrected by linking CoreGraphics and using typed NSEvent access;
failed builds were never installed. See current evidence for18 device status.

Do not assume `SIGTERM` ended the old Steam process: an attempted16 CEF launch
reused it, and later a Device Hub app-icon click started another17 after its
earlier crash. Installation preflight refused that active session. Only after
fresh exact app-path/PID identification, bounded lab termination and an explicit
empty-process check was18 installed. This does not authorize terminating a
working game or reusing historical PIDs.

Build18 on the physical Air executes the new event factory and continues through
the150s bounded observation without the prior nil-event exception. All sampled
frame rates remain0, and Steam starts an update download; no interactive browser
result. Later process identity differs, so neither same-process survival nor
scene reentry is established. Before any next launch, reconcile the current lab
and downloaded update state; retain original official source fingerprints.
Observer exit2/timeouts and CoreDevice collection failures are not app crashes.

### Static required-API audit (no client execution)

```sh
python3 experiments/mac-arm-steam/test-cef-loader-audit.py
python3 scripts/experiments/audit-mac-cef-loader.py \
  --helper '/private/official/Steam.app/Contents/Frameworks/Steam Helper.app/Contents/MacOS/Steam Helper' \
  --output /private/new-cef-loader-report.json
```

The tool selects one ARM64 slice, verifies its executable text mapping and the
actual dlsym import stub, and rejects unknown/ambiguous lookup control flow.
All seven observed custom APIs have required lookup/null-return checks in the
audited official Helper. The report contains names/hashes/addresses, never a
proprietary instruction dump. This does not run CEF, prove a browser works,
supply missing API semantics or authorize substituting a mismatched framework.

### Candidate source-surface gate

```sh
python3 experiments/mac-arm-steam/test-cef-source-surface.py
python3 scripts/experiments/audit-cef-source-surface.py \
  --source /private/pinned-cef-source \
  --binary-metadata /private/cef-abi-comparison.json \
  --output /private/new-source-surface-report.json
```

Use the captured genuine metadata from audit-mac-cef-abi.py. Exit2 means the
candidate fails the surface gate; exit0 only passes this preliminary gate,
not runtime/ABI/behavior validation. The public126 source actually exits2 with
both hashes mismatched and7 declarations absent. Only two reviewed upstream
hashing modules with exact SHA256 may execute, isolated from other candidate
Python files; header symlinks/budget overflow and existing output are refused.
The source and any generated hash header are never modified.

CEF's real fingerprint includes declaration text/parameter names. A disposable
identifier-only control changes the fingerprint while retaining the Clang C type.
Do not use a mismatch alone to claim proven layout incompatibility, guess all
custom edits from exported names, spoof a fingerprint or supply no-op APIs.
A full CEF extension checkout is only~16MB here; full Chromium is separate and
is not downloaded/built by this tool.

### Native19 configuration observation and Mac control

In a new private copy of18 (same isolated lab ID), build19 adds
`BootStrapperInhibitUpdateOnLaunch=enable` in root `steam.cfg` and
`Mac/Contents/MacOS/steam.cfg`. Rebuild three shims using the pinned builder,
check its fresh receipt and final IDeckObservePinConfig symbol/marker, sign each
shim then root with the matching existing Air profile; deep-strict verify.
Archive older success receipts when rebuilding. Never install while another
lab session is active; identify its current installed path, not a saved PID.

Launch fresh with only `IDeckNativePinProbe=1`, plus the normal current-install
STEAM_APP_BUNDLE_PATH and three fixed startup flags, for180s. The observer reports
only config basename-category/open result/error (max32) and preserves errno.
Actual19 reads config but still checks the background manifest: the proposed
pin is NOT validated. Do not copy this into product defaults; it also delays
Steam security updates. No account use in this lab.

Own `mac-cef-load-control.c` is optional Mac-only control: compile with
`xcrun clang -Wall -Wextra -Werror`, point it at a private official framework
copy with normal Mac development signature. It calls dlopen and public version/
hash getters only, never cef_initialize or Steam main. Actual host pass is not
iPad/CEF UI proof. Keep raw logs, profiles and all framework payload outside Git.

### Real macOS-target compact allocator, private standalone20/21

This experiment rebuilds the actual allocator as macOS ARM64, then metadata-
retargets its own MH_BUNDLE to iOS. It does not modify or link any Valve file.

```sh
# Prepare the verified362-file source using the earlier allocator fetch workflow.
python3 scripts/experiments/build-mac-compact-allocator.py \
  --source ../.madeira-install/partitionalloc126 \
  --output ../.madeira-install/NEW-mac-allocator-glued --glued
python3 experiments/mac-arm-steam/test-mac-compact-builder.py
```

Use a new private output. The builder verifies original source/header/license
hashes, copies the tree and changes only3 files under that private copy. These
generated Chromium edits retain original BSD notices and use the same BSD terms.
All62 Mac-target units and the entry point share IDECK_MAC_COMPACT_POOLS=1. This
selects real256MiB pools with source-wide dynamic masks; no process-name spoof or
smaller mapping returned for a larger request. The glued option also validates
adjacency, public CorePoolsSize and combined core-pool masks. A real cross-TU
link failure required defining compact selectors inline in the common header.

It first runs a separate Mac host process (including null/size/reentry guards),
then changes only platform metadata and public framework dependency paths.
__text SHA256 must remain identical. Own source snapshots and input-change
refusal keep the receipt tied to compiled sources. The generated app is UNSIGNED.
Sign its MacCompactAllocator.bundle first, then the UIKit app, with the matching
existing isolated profile; verify both deeply/strictly and final export/markers
before install. No EVA/JIT capability is requested. Reuse ONLY the isolated lab
bundle ID; check current process identity and finish prior test before upgrade.

Actual Air20 intermediateABI1 independent pools and finalAir21 ABI2 glued pools
pass load/entry/398alloc-free/4workers/0failures/disjoint/cleanup. Current source
usesABI2/72bytes; its default20 rebuild also passes on Mac. The two intermediate
source versions have separate receipts; final21 is the reproducible current
device configuration.35s console timeout is not app death: actual installed21
and its exact completed probe executable were subsequently observed alive.

This is not CEF or Steam integration. Thread cache, complete raw_ptr lifetime,
malloc replacement, pointer compression, StarScan/MTE, V8 sandbox/JIT and full
browser allocations remain untested. Do not preload this into the precompiled
CEF with mismatching inline masks. Matching custom source/API plus a complete
consumer rebuild and actual Helper IPC remain separate necessary steps.
