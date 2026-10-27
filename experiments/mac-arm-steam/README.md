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
  errno. Logs only executable basename, not launch arguments or credentials.

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
