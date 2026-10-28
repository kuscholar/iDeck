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
