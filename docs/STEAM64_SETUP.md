# Steam64 setup in the launcher (unreleased)

Build144 adds an explicit **Install / Upgrade to Steam64** action. Installing an
IPA alone does not install Valve's proprietary client or change the selected
prefix. Existing users opt in; iDeck does not silently move an account into a new
prefix. The Build143/alpha.5 release did not contain this installer.

## User flow (Build145)

The launcher is a four-action waterfall. Only the current unfinished action has
a primary button; completed actions show checkmarks and are skipped automatically.
The check above it combines signing/address checks without counting them as user
tasks. Checks rerun when returning from Settings/VPN/JIT, and the launcher scrolls
to the next step after the complete scan.

1. **Install Steam → Install Steam64.** This same action downloads the complete
   matched Steam/browser files and prepares the local Windows runtime. There is
   no separate manual runtime step or legacy32 repair detour. Keep iDeck open;
   progress and cancellation are inside this card. If prompted, fully close and
   reopen iDeck before continuing: native reservations are acquired at app startup.
2. **Connect LocalDevVPN.** Open it, tap Connect and return to iDeck. An already
   reachable connection is checked off automatically.
3. **Pair this device → Pair in iDeck.** This starts the existing on-device pairing
   immediately, with its live instructions/PIN in this card. The iOS Settings
   pairing host is still named **Madeira**. Pairing normally only needs doing once.
   On iOS26, the one fallback action opens pairing-file import in JIT setup.
4. **Enable JIT.** Return to iDeck after activation, then choose **Launch Steam
   Big Picture** once all checks pass. JIT is needed again after fully closing
   the app. Steam sign-in and Steam Guard happen inside Valve's genuine UI.

New product installs default to built-in JIT so the direct in-app pairing flow is
consistent. Existing saved method choices and ordinary Madeira's automatic default
are preserved. Advanced JIT methods/file import are under **Advanced options**,
not duplicate primary buttons in the pairing step.

For damaged files, open **Advanced options → Verify / Repair Steam64** in a fresh
app session. **Return to previous environment** restores the prior selection and
controlled settings without deleting either prefix. Legacy32 manual repair remains
an explicit advanced action only for an existing legacy installation. Automatic
checks and native address guards remain mandatory despite the shorter interface.

Build144 fresh installation was reported complete by the user; this feedback
establishes the installer path, not Steam login/gameplay stability. Build145's
new UI is separately compiled/tested; see its device/validation evidence before
claiming a new end-to-end result.

The original `wine` prefix is untouched. `wine-steam64` is separate; login caches
are never copied. Existing games/saves are preserved in their original location,
not automatically migrated into the new Steam library. Do not delete the old
prefix to reclaim space before checking your game/save backups.

## Capacity and compatibility limits

This cannot manufacture virtual address space. The older 32-bit preflight needs
one 4GiB child window plus headroom; the source-compatible full64 profile instead
needs a particular, much larger set of disjoint address ranges. The launcher
requires the task map to reach `0x8000000000` (512GiB address boundary), then on
restart requires `madeira_cef64_hold_state() == 1`, proving the native constructor
actually reserved its ranges. The first test is necessary, not sufficient, and
neither is a RAM/storage requirement. No entitlement is assumed to be granted.
A user with a small address map may remain unsupported after selecting Steam64.
32-bit games/auxiliary programs can still need a 32-bit child window.

The matched snapshot is Steam manifest1769025840 (January22,2026), with CEF126
and the pinned source-built ELF/standalone Crashpad components already used in
the prior device experiment. It is **not the newest Steam/Chromium**. Bootstrap
updates are held by the existing matched-client launch policy. It retains
Valve's authentication, licensing and crash reporting; no Valve executable or
libcef is patched. Upgrading this snapshot requires a separate compatibility and
security review, not following a moving manifest. Build143's third-game-exit
freeze remains unresolved by this installer.

## Engineering and release packaging

- `Steam64Packages.json` contains public metadata only:18 immutable official
  Valve HTTPS packages and6,229 unique file hashes. The application pins the JSON,
  version, package set, sizes and SHA256. There is no claim of independent Valve
  manifest-signature verification.
- `Steam64ClientInstaller.swift` adapts the proven Build99 streaming installer.
  ZIP traversal/symlink/case collisions, CRC, size/bomb limits, architecture and
  complete file hashes are checked. Download redirects are limited to the exact
  Valve HTTPS host/path. Cache entries are rehashed before reuse.
- Stock official files are verified before the pinned open components/config are
  overlaid in a disposable stage. One durable rollback journal covers all files
  installed into the64-bit drive. Unknown/private files are not deleted. Disk
  failures and cancellation roll back before the commit point.
- Activation rechecks the full composed installation, writes a durable receipt,
  then atomically changes `madeira.cfg`. A previous config snapshot is private
  on-device data. Later unrelated user preferences survive rollback; conflicting
  edits to controlled keys cause a refusal rather than an overwrite.
- `tools/stage-steam64-compatibility.py` stages only three pinned **open-source**
  binaries (`chrome_elf.dll`, `crashpad_handler.exe`, `config_guard.exe`) and their
  provenance/notices into the ignored `app/Madeira/Steam64Compatibility` folder.
  The Xcode project bundles it and the public catalog. The setup also requires
  the exact previously released FEX131 `arm64ec-windows/xtajit64.dll`
  (SHA256 `a3365a0d47f02efab8b31f4ae178e742769bcb827fd87c41c5db49de25ee590c`);
  no new FEX source changes are made. Preserve the alpha.5 source overlay and
  translator while building this launcher. No Valve client/CEF tree,
  profile, credential, game or raw log is bundled.
- A public build must ship the exact corresponding Chromium/CEF, Crashpad,
  mini_chromium/zlib and iDeck source/rebuild material and all applicable notices,
  in addition to the existing source/relink/license/checksum release assets.
  Merely adding the source URL or the three binaries is insufficient. The ELF
  artifact's full notice tree is retained. Existing component licenses apply;
  the Madeira exception grants no exception for third-party work.

Stage the verified support payload (use matching artifacts/toolchain; source files
are not replaced by this command):

```sh
python3 tools/stage-steam64-compatibility.py \
  --elf-artifact /path/to/ideck-elf-artifact \
  --crashpad-binaries /path/to/iDeckCEF64Crashpad \
  --crashpad-source /path/to/crashpad-standalone-source \
  --toolchain /path/to/llvm-mingw-20260421-ucrt-macos-universal \
  --output app/Madeira/Steam64Compatibility
```

Reproducible host checks:

```sh
python3 tests/host/check-ideck-waterfall.py
python3 tests/host/check-steam64-install.py
python3 tests/host/check-steam64-setup.py
# Optional private official packages and staged open components:
python3 tests/host/check-steam64-setup.py --real /path/to/jan22-package-cache app/Madeira/Steam64Compatibility
python3 tests/host/check-ideck.py
python3 tests/host/check-ideck-runtime-selection.py
python3 tests/host/check-steam-ui-keyboard.py
```

The tests compile the actual Swift extractor/transaction/profile logic. Synthetic
fixtures exercise rollback, malicious archives, private data and interruption.
The optional real test verifies/extracts the18 packages, checks the complete
stock client, composes the open components, and activates/restores a disposable
configuration. It starts no Steam/Wine process and does not establish device
installation, login, UI or repeated-game stability. Build145 is not published;
fresh-device download/login, repair/rollback UI and repeated game cycles remain
physical-device release gates.
