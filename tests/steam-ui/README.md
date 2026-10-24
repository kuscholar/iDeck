# Isolated Steam UI diagnostics

No Steam/Valve binaries, account data or game content are distributed here.

## Host checks

From the repository root (Python 3, Swift and a host C compiler):

```sh
python3 tests/host/check-steam-ui.py
python3 tests/host/check-dock-contract.py
python3 tests/host/check-frontend.py
```

The first compiles the production Swift launch policy with synthetic PE
headers and the production C child-event function under ASan/UBSan. It checks
flag-off, app isolation, missing/mismatched client architecture, symlink refusal,
bounded desktop size, a fixed credential-free command and categorical log
output. It neither contacts Steam nor runs the Windows client.

## x86-64 Windows process/shared-memory probe

```sh
export LLVM_MINGW=/path/to/llvm-mingw-20260421-ucrt-macos-universal
"$LLVM_MINGW/bin/x86_64-w64-mingw32-clang" -O2 -municode -static \
  -Wl,--no-insert-timestamp tests/steam-ui/process-shared-memory.c \
  -o /tmp/steam-ui-process-probe.exe
"$LLVM_MINGW/bin/llvm-readobj" --file-headers --coff-imports \
  /tmp/steam-ui-process-probe.exe
```

Run the PE on an authorized Windows/Wine control first, then from an isolated
Madeira experimental prefix. The parent creates a named mapping, launches its
own child, waits 15 seconds, checks child exit and shared-memory content. Pass:
`steam-ui-process-probe wait=0 child_exit=0 shared_match=1`, process exit 0.
Nonzero is a test failure, not proof of a particular Wine/FEX defect. No child is
forcibly terminated on timeout. Keep the experiment separate from a game session.
The PE was compiled and inspected locally, and passed on Kusch in Build 12
and Build 13 (wait=0, child_exit=0, shared_match=1). Windows control execution
remains unavailable. Evidence: docs/STEAM_UI_RUN3_EVIDENCE.json.
This is a process-plumbing test, not a Skia raster test or CEF simulation.

## Build and activate the real-client experiment

1. Read docs/BUILDING.md and docs/LOCAL_IPHONE_REPAIR.md, initialize the pinned
   submodules and build required dependencies. Reuse a prepared native archive
   only when its corresponding source is unchanged. For this change rebuild
   `bash build/ntdll-unix/build.sh`; the host ObjC bridge recompiles with the app.
   Preserve licence notices and stage them with `bash build/stage-licenses.sh`.
2. Build an unsigned local validation target (existing dependencies required):

   ```sh
   xcodebuild -project app/Madeira.xcodeproj -scheme Madeira \
     -configuration Debug -destination 'generic/platform=iOS' \
     -derivedDataPath build/DerivedData CODE_SIGNING_ALLOWED=NO \
     MADEIRA_BUNDLE_IDENTIFIER=com.example.madeira.steamui \
     CURRENT_PROJECT_VERSION=9 IPHONEOS_DEPLOYMENT_TARGET=26.0 build
   ```

3. Inspect the FINAL Mach-O, including Madeira.debug.dylib in Debug builds:

   ```sh
   strings build/DerivedData/Build/Products/Debug-iphoneos/Madeira.app/Madeira.debug.dylib \
     | rg 'steam-ui-process|experiment-begin login-only|payload-wide debug channels'
   nm build/DerivedData/Build/Products/Debug-iphoneos/Madeira.app/Madeira.debug.dylib \
     | rg 'SteamUIExperiment|SteamUIEvidence'
   shasum -a 256 build/DerivedData/Build/Products/Debug-iphoneos/Madeira.app/Madeira.debug.dylib
   ```

4. Use Xcode's normal account/provisioning flow for this DISTINCT bundle ID and
   its `.JITHelper` extension. Do not rename/reuse the working application's
   provisioning profiles, uninstall it, or copy its Keychain/login caches. The
   target suffix `.steamui` is an intentional runtime isolation check.
5. Populate only the experiment's own Wine prefix with a complete legitimate
   64-bit Windows Steam installation. Required: steam.exe, steamclient64.dll,
   and matching bin/cef/cef.win7x64 (or cef.win64 / cef) webhelper and libcef.
   Headless Dock components alone are insufficient. Inspect hashes/PE versions
   before the run. Do not copy config/loginusers.vdf/ssfn files or credentials
   from another installation. Valve authentication remains mandatory.
6. In the EXPERIMENT'S Documents/madeira.cfg set:

   ```ini
   env.MADEIRA_FRONTEND = 0
   env.MADEIRA_EXPERIMENTAL_STEAM_UI = 1
   pool-split = 1
   ```

   Restart the experiment, enable JIT with its existing workflow and press
   `Steam UI Experiment` in the developer interface. The old `Steam Testing`
   button is NOT the controlled experiment: it arms extra historical probes.
   The new button starts a fixed login-only command through services and the
   virtual desktop. No -bigpicture flag is passed at this stage.
7. Keep raw Steam/device logs app-private or in ignored local artifacts. The
   observer starts at each log's existing EOF and emits only categorical
   ChromeMainDelegate/BrowserReady evidence from a bounded new-log tail. Missing
   observer output is inconclusive (rotation, file locations and a bounded tail
   can miss events). Host-surface-present includes non-CEF windows and is NOT a
   login/interaction success result. Existing Winios window logs provide window
   census evidence; pixel correctness and interaction need independent capture.
8. Record exact installed artifact hashes, helper/client versions, pseudo-process
   lifecycle, CEF startup, BrowserReady, window pixels and physical interaction.
   Never log sign-in tokens/passwords. Do not claim the CEF milestone before that
   evidence exists. Only then investigate Big Picture, Bluetooth and game return.

Local build note: the audited experiment reused unchanged baseline FEX/DXMT,
crypto/media/pairing archives and optional i386 resources, and rebuilt ntdll.
It was not a clean-machine dependency rebuild. The independent app and helper
were subsequently provisioned through Xcode, signed, installed and launched.
CEF and guest-probe execution remain pending; installation does not validate them.


## Stage the public full client reproducibly

This branch defaults to the owner's independent `com.kuschqin.madeira.steamui`
ID/team and displays Steam UI Lab. For your own device override
`MADEIRA_BUNDLE_IDENTIFIER` (retain `.steamui`) and `DEVELOPMENT_TEAM`; provision
both app and helper through Xcode. Its registered callback scheme is
`madeira-steamui`, distinct from the working app.

The existing Dock-only runtime lacks CEF. Do not copy its account directory.
Fetch the complete matching public package set into a NEW local staging folder:

```sh
python3 tools/fetch-steam-ui-client.py \
  --manifest tests/steam-ui/manifests/steam_client_win64_1792618285.vdf \
  --cache /path/outside-git/steam-packages \
  --output /path/outside-git/Steam
```

The tool selects the standard steamrow bootstrap, verifies each package's
size/SHA-256 against the explicitly saved HTTPS manifest, refuses path traversal
and symlink ZIP entries, and emits a full local inventory beside the output.
It does not independently validate Valve's manifest signatures. Keep packages
and output outside Git; the output must not already exist. Do not point it at a
live installation. Steam authentication/licensing remain Steam's responsibility.

Copy this new Steam directory only to the experimental app's
`Documents/wine/drive_c/Program Files (x86)/Steam`, using the normal device file
service. For a developer-only first run, also set `env.MADEIRA_ONBOARDING = 0`
in the experiment's cfg, so Dock's setup downloader does not replace this
separate full client. No pairing files or account caches need be copied.
The synthetic probe belongs at `Documents/wine/drive_c/steam-ui-process-probe.exe`;
copying it there does not execute it. Normal manual library/desktop launching
can be used for this diagnostic in a separate session.

Experimental CEF policy now overrides inherited VLOG with warning severity and
suppresses command-tail echoes. Raw Steam logs must stay app-private. The
categorical observer can miss initialization messages at this severity; missing
markers remain inconclusive. Interactive pixels and device crash evidence are
still required before declaring the login milestone.


## Current capacity experiment (Build 11)

Build 10's exact secondary-region approach failed actual iOS RX verification
and has been removed. Its host mock test and candidate remain at commit
29f5f6f, for diagnosis only. See docs/STEAM_UI_RUN2_EVIDENCE.json.

Use `tests/steam-ui/lab-madeira.cfg` only in the isolated app. Its sole new
capacity option is `pool-low = 1`; existing region C moves FEX buffers out of
the image pool. Do not copy it to the working baseline. No default allocator
or FEX change is needed. Relevant host regression checks:

```sh
python3 tests/host/check-pool-low.py
python3 tests/host/check-pool-split.py
python3 tests/host/check-jit-method.py
python3 tests/host/check-steam-ui.py
python3 tests/host/check-frontend.py
```

Require accepted region-C RX/RW mappings, main-pool tail consumption and
libglesv2/import results from the next device run. The JIT badge now remains
green after intentional debugger detach when a pool was successfully prepared;
it does not imply CEF rendering or game success.


## Atomic and actual chrome_elf import diagnostics (Build 13)

Build synthetic probes outside Git (no Valve DLL is redistributed):

```sh
"$LLVM_MINGW/bin/x86_64-w64-mingw32-clang" -O2 -static \
  -Wl,--no-insert-timestamp tests/steam-ui/atomic-refcount.c \
  -o /tmp/steam-ui-atomic-probe.exe
"$LLVM_MINGW/bin/x86_64-w64-mingw32-dlltool" \
  -d tests/steam-ui/chrome-elf.def -l /tmp/madeira-chrome-elf.lib
"$LLVM_MINGW/bin/x86_64-w64-mingw32-clang" -O2 -static \
  -Wl,--no-insert-timestamp tests/steam-ui/chrome-elf-heap.c \
  /tmp/madeira-chrome-elf.lib -o /tmp/madeira-chrome-elf-probe.exe
```

Place atomic and process probes at the experiment's drive_c root. Place
madeira-chrome-elf-probe.exe beside the matching official chrome_elf.dll in
Program Files (x86)/Steam/bin/cef/cef.win64. The import definition only names
GetHandleVerifier, not implementation code. Keep the official DLL unchanged.

In a fresh JIT-enabled session press orange Runtime Diagnostics. It runs all
three tests once, recording stdout/stderr and exit codes in
Documents/wine/drive_c/madeira-probe-results.txt. No Steam exe is launched.
Alternatively, for a connected, unlocked device with pairing/VPN already set up,
use the explicit app argument to reuse the existing JIT coordinator:

```sh
xcrun devicectl device process launch --device YOUR_DEVICE_ID \
  com.kuschqin.madeira.steamui madeira-runtime-diagnostics
```

Start a fresh process; a previous Wine session cannot run again. The developer
argument is gated by both the experimental bundle/flag and a once-only UI state.
It does not install pairing material, bypass consent, or auto-run Steam. Missing
pairing/VPN/debugger still fails through the existing setup flow. Do not assume
future availability merely because the Build 13 device run succeeded.

Observed on Kusch: atomic failures=0/counter=200000, process shared_match=1 and
child_exit=0, elf import/verifier plus four thread rounds with failures=0. All
three exit codes are zero. This rules out only these simple test failures. It
does NOT exercise all PA allocations, the exact CEF destructor order, software
rasterization or authenticated Steam UI. A macOS x86-64 build of the atomic
control could not execute (Bad CPU type); no Windows control was available.
Never describe these passes as a working Steam login or general FEX correctness.


## FLS lifetime/isolation probe (Build 14)

```sh
"$LLVM_MINGW/bin/x86_64-w64-mingw32-clang" -O2 -municode -static \
  -Wl,--no-insert-timestamp tests/steam-ui/fls-lifetime.c \
  -o /tmp/steam-ui-fls-probe.exe
```

Place this x64 PE at the experimental drive_c root. In Build 15, open a fresh
Steam UI Lab, press Enable JIT, then the orange FLS Diagnostics button.
Alternatively start a fresh lab process with argument `madeira-fls-diagnostics`;
the existing paired JIT coordinator
runs the single synthetic test and writes `drive_c/madeira-fls-results.txt`.
It never starts Steam. The normal orange diagnostic route remains unchanged.

Checks: a joined worker's callback ran once; freeing its now-empty FLS index
does not call it again; while a child holds its own FLS value, freeing the
parent's index only calls the parent's destructor; the child's value remains
intact and its own free calls its destructor once. Values are static records
with expected PID and callback count, so a wrong callback cannot corrupt a
foreign heap by freeing it. Waits are bounded; no forced child termination.
The expected process boundary/callback contract comes from Microsoft's
[FlsAlloc](https://learn.microsoft.com/en-us/windows/win32/api/fibersapi/nf-fibersapi-flsalloc)
and [FlsFree](https://learn.microsoft.com/en-us/windows/win32/api/fibersapi/nf-fibersapi-flsfree)
documentation. These are expectations, not a Windows control execution.


Build 15 device result: thread-exit-once=PASS, parent_once=1, wrong_owner=0,
child_exit=0, wait=0, result=PASS, fls-exit=0. The user ran the manual button;
version and launch route are confirmed by the app log. See
`docs/STEAM_UI_FLS_EVIDENCE.json` for artifact hashes. Do not repeat this basic
test as if Build 14 were still awaiting unlock; investigate the real CEF
allocation/free-callback workload next. Windows control remains unexecuted.

## Bounded real-CEF FLS observer (Build 16)

This is an optional diagnostic PE, not a callback lifetime fix. Apply only to a
separate worktree of Wine pin 9129e9684daaeae70da9435e7c6060e59392634e.
Keep the original source farm and the working app untouched. Example from the
experimental Madeira root, with LLVM_MINGW and a native build toolchain prepared:

```sh
lab_root="$PWD"
private_root="$(dirname "$PWD")/.madeira-install"
git -C wine worktree add --detach "$private_root/wine-fls-trace-src" \
  9129e9684daaeae70da9435e7c6060e59392634e
patch -p1 -d "$private_root/wine-fls-trace-src" \
  < build/wine-pe/steam-ui-fls-trace.patch
# Wine's relative ../../../../build/madeira_cfg.h include requires this layout.
# Inspect an existing private_root/build first; never replace existing content.
ln -s "$lab_root/build" "$private_root/build"
mkdir -p "$private_root/wine-fls-trace-build"
cd "$private_root/wine-fls-trace-build"
PATH="$LLVM_MINGW/bin:$PATH" ../wine-fls-trace-src/configure \
  --enable-archs=arm64ec --without-x --without-freetype \
  --disable-tests --enable-winegstreamer
PATH="$LLVM_MINGW/bin:$PATH" make -j4 dlls/ntdll/arm64ec-windows/ntdll.dll
```

Copy the resulting PE to a private staging file. Strip with
`$LLVM_MINGW/bin/arm64ec-w64-mingw32-strip`, then zero-pad to its PE OptionalHeader
SizeOfImage + 0x50000, matching build/wine-pe/build.sh policy. Compare named
exports and order with the baseline before use (1473 for this pin). The observed
Build 16 staged result is 1572864 bytes, SHA256
76494c640a59389e6285f2d437874a26a45eb9443a8f2855853297f1d515ef2c.
After the ordinary isolated Xcode build, overlay ONLY the generated app's
`arm64ec-windows/ntdll.dll`, re-sign the entire lab with its legitimate profiles,
verify strict signing, and check the final embedded PE hash. This PE diagnostic
is not in the Mach-O; separately check the final Mach-O explicit-launch marker.
Never commit the compiled PE, provisioning assets or Valve binaries.

In the isolated lab configuration add `env.MADEIRA_STEAM_UI_FLS_TRACE = 1`.
The launcher already sets MADEIRA_STEAM_UI_SESSION=1. Both flags are required.
First use a fresh process with `madeira-fls-diagnostics` to verify the observer
marker and the regression result. Then a fresh process with
`madeira-steam-ui-experiment` enables the existing paired JIT flow and launches
real Steam. Ordinary app launch does not auto-start Steam; credential input is
never automated. Capture a bounded run, terminate only the lab if it keeps
retrying, then copy Documents/madeira-log.txt to private storage. Live copy may
fail while the file is changing. Report this separately from Steam failures.

Host observer check: `python3 tests/host/check-steam-ui-fls-trace.py`.
This compiles the actual helper with mocked environment/TEB/sink and verifies
both gates, the 4096 output limit, payload exclusion and unchanged callback code.
It is not a Windows control. Build 16 actual device observations and hashes:
`docs/STEAM_UI_FLS_TRACE_EVIDENCE.json`. The first failing PTD callback has no
previous observed delivery; next investigate allocation/free history, without
removing Chromium checks or claiming an interactive login.


### Build 17/18 allocator metadata discriminator

The optional PE observer now recognizes the exact 31-byte chrome_elf PTD
callback at RVA 0x9c1e0 from the already-hashed official client. For its FLS set
and callback-begin, it follows the inspected non-page-aligned free path at
+0x65836..0x658ce: 2 MiB superpage mask, metadata page/slot-span offset,
bucket slot size, BRP-enabled root flag and the trailing 32-bit refcount.
All reads use NtReadVirtualMemory with exact-length checks; sentinel/unaligned
values, incompatible code fingerprints, unavailable mappings and out-of-range
slot sizes are rejected. PTD contents are never read. This is a version-specific
hypothesis test, not a general PartitionAlloc parser or allocator fix.

Build 17 emitted FLS records but NO allocator snapshots. Its 33-second real CEF
run did not reproduce the refcount assertion and recorded continued presents;
these are neither metadata validation nor interactive login success.
Build 18 adds at most 32 categorical skip records for index 2 per observer
instance: -1 callback unreadable, -2 code mismatch, -3 superpage/span unreadable,
-4 root flag unreadable, -5 bucket/size unavailable or invalid, -7 refcount
unreadable; 10+flag means BRP root flag differs from 1. A zero return means a
non-applicable event/value/page-aligned branch. Successful snapshot returns 1.
Keep each trace bounded to 4096 FLS events (each may add one metadata record).
Callbacks cached by index are observer metadata only; actual callback dispatch
continues to use Wine's unchanged structures. No Valve code is patched.

Host fixture tests the metadata calculation with only allowlisted synthetic
reads, including an 8192-byte bucket, while object contents remain unreadable.
Wrong fingerprint and partial-read cases must produce no metadata snapshot.
Read status evidence on device before interpreting missing snapshots.
Build 18 reuses the fully compiled Build 17 Mach-O, replaces only the diagnostic
ARM64EC PE and CFBundleVersion, and is then re-signed; it is not a separate full
Xcode compilation. Export/order and final bundle component hashes must be kept.

### Strict soft-reservation overlap experiment (Build 19)

Build 18 device evidence shows a real 16 GiB grant at 0x7800000000 followed by
an unbacked guard-prefixed soft grant covering the SAME interval. Before the
first failing PTD callback, the observed slot size is 8192 and refcount is zero.
This supports testing pool aliasing; it does not establish allocator corruption
as the sole cause. Build 17 also had overlapping grants without this assertion
inside its shorter capture, so the crash is not deterministic from overlap alone.

Opt in ONLY in the isolated lab with
`env.MADEIRA_STEAM_UI_STRICT_RESERVATIONS = 1`. It also requires the launcher's
MADEIRA_STEAM_UI_SESSION=1. Before an emergency soft grant, the native allocator
checks its complete returned range (including a guard prefix) against real Wine
views under virtual_mutex. On overlap it logs `[steam-ui-reserve]
reject-soft-overlap` and tries another existing candidate; if none remain, it
preserves the allocation failure. It does not add backing, remap a view, remove
protection or change normal app behavior with the flag absent. This is a limited
experimental check, not a complete address-space broker; it does not reserve a
new empty soft span against future concurrent native mappings or audit every
other fallback/cage. Do not advertise it as a generally collision-free allocator.

`python3 tests/host/check-steam-ui-reservations.py` compiles the real
find_view_range implementation and actual gated grant block with a mock view
tree under ASan/UBSan. It exercises interior/partial/guard-prefix overlap,
other tree branches, boundary-touch and disjoint ranges, balanced locks and
exact dual-flag default isolation. Rebuild build/ntdll-unix/build.sh, then the
full experimental Xcode app. Verify the reject-soft-overlap string in the FINAL
Mach-O; overlay the unchanged diagnostic PE if desired, then re-sign/install.
Capture real allocation failure versus refcount assertion as distinct outcomes.

### Offline interval audit and reservation ownership PE

```sh
python3 tests/host/check-steam-ui-pool-inventory.py
python3 tools/analyze-steam-ui-pools.py /private/path/build18-log.txt \
  /private/path/build19-log.txt --output /tmp/pool-inventory.json
python3 tests/host/check-steam-ui-reservation-probe.py
"$LLVM_MINGW/bin/x86_64-w64-mingw32-clang" -O2 -static \
  -Wl,--no-insert-timestamp tests/steam-ui/reservation-ownership.c \
  -o /tmp/steam-ui-reservation-probe.exe
```

Run that PE only in a FRESH isolated lab (or independent Windows control) with
`--isolated-reserve-only`. In Build 20, stage the compiled PE at the lab drive_c
root and launch a fresh Lab with `madeira-reservation-diagnostics`. The existing
paired JIT flow runs the fixed batch and writes
`drive_c/madeira-reservation-results.txt` with reservation-exit. The bundle suffix,
experimental flag and fresh-session gates still apply; ordinary app launch does
not run the probe. The existing runtime probe button does not execute this file.
Do not replace the passing basic probes. Build 20 is only locally prepared;
installation and actual probe execution remain pending device availability.
Exit 40 means overlapping grants, 70 means a capacity gate, 0 only means four
reported intervals are disjoint. No commit/access/free occurs. Terminate the
whole lab after any outcome; never run it in the working gaming app/session.
See docs/STEAM_UI_ADDRESS_SPACE.md for the interval arithmetic and limitations.

### Native mapping capability discriminator (Build 21)

Launch a fresh isolated Steam UI Lab with `madeira-native-vm-diagnostics`.
The same paired automatic JIT flow runs before the native probe; Wine/FEX is
not bootstrapped. Isolated bundle/feature flag, live debugger and fresh-session
checks apply. Copy Documents/steam-ui-native-vm-results.txt and the private app
log, then terminate only the lab process. No credentials or Steam files needed.

The public SDK's LP64 vm_map/vm_deallocate API is used because iOS rejects direct
inclusion of mach_vm.h. Compile-time assertions require 64-bit address/size.
The native header makes exactly 62 fixed PROT_NONE/NONE no-overwrite requests:
64 KiB and 16 GiB at every nonzero 16 GiB boundary below 512 GiB. It queries each
current native region, releases returned object-name ports, and deallocates
ONLY its own successful mappings immediately. Failed cleanup or a returned
address mismatch stops the run. No memory contents or foreign mappings are
accessed/modified. A zero completion code means sweep completed, not that every
mapping worked. Successful independent spans do not prove simultaneous capacity,
backing/commit access or CEF/JIT-execution capability.

`python3 tests/host/check-steam-ui-native-vm.py` tests the exact native header
under ASan/UBSan with Mach API fixtures, including successful/failed mapping,
cleanup/port failure and unexpected address. This is not an OS control.
Build 21 actual Kusch result: 8 successes at four high-band bases (both sizes),
54 failures kr3, no cleanup failures; see numeric CSV and hashed evidence in
docs/STEAM_UI_NATIVE_VM_EVIDENCE.json. Do not repeat this grid or unmap the
pre-existing lower regions; next attribute CEF's exact pool requests/contracts.


### Build 23: genuine i386 chrome_elf probe

This is a loader/heap/thread discriminator, not interactive CEF validation.
Compile the unchanged chrome-elf-heap.c with i686-w64-mingw32-clang and an import
library generated from chrome-elf.def using i686-w64-mingw32-dlltool. Use the
manifest-verified official win32 CEF package; do not copy authentication caches.
Stage the probe as madeira-chrome-elf32-probe.exe alongside chrome_elf.dll and
libcef.dll under the isolated prefix's drive_c/Steam32Probe/bin/cef/cef.win7/.
All three must be i386 PE files. In the .steamui app with the experimental flag,
launch with madeira-x86-cef-diagnostics through the paired automatic JIT flow.
Collect drive_c/madeira-x86-cef-results.txt and the private lab log. A zero exit
only validates this narrow probe. The frozen 32-bit Steam client is unsupported
by Valve since January 2026; full startup/server compatibility is unverified.

Build 22's canonical writable-section scanner is independently checked with
`python3 tests/host/check-steam-ui-pool-owner.py` (ASan/UBSan). Enable only with
both MADEIRA_STEAM_UI_SESSION=1 and MADEIRA_STEAM_UI_POOL_TRACE=1. It observes
known numeric pool-base pairs; it does not alter reservation behavior. Keep
MADEIRA_STEAM_UI_STRICT_RESERVATIONS=1 during real-client experiments.

Reproduce the Build 23 i386 executable (output must not already exist):

```sh
python3 tools/build-steam-ui-x86-probe.py \
  --toolchain /absolute/path/to/llvm-mingw \
  --output /private/path/madeira-chrome-elf32-probe.exe
```

With llvm-mingw-20260421-ucrt-macos-universal, the script reproduced SHA256
`0c469683f47e484c06e9f72888f99b0d61b4ea0e5389cb8cb455ceb86b1a65da`,
identical to the staged host candidate. This establishes build reproducibility,
not execution on the phone. No Valve DLLs are bundled by this script.


### Explicit genuine win32 client experiment (Build24)

After the narrow x86 probe has passed, use the official win32 manifest with:

```sh
python3 tools/fetch-steam-ui-client.py --architecture win32 \
  --manifest /private/path/steam_client_win32 \
  --cache /private/path/cache --output /private/path/Steam
```

The output must be new. This validates package size/SHA256 from the HTTPS
manifest; manifest signatures are not independently verified. Stage that complete
client under drive_c/Steam32Lab in the isolated lab only. Launch explicitly with
madeira-steam-ui-x86-experiment; default Steam UI Experiment continues to use x64.
All four launch files must have i386 PE headers. Do not rename an x64 DLL, mix
package versions, copy login caches or add update/authentication bypass flags.
Collect the lab log and Steam32Lab/logs privately. BrowserReady and interactive
login must be observed separately from loader success. This frozen Valve client
is unsupported and is not established as a maintained deployment solution.


When CoreDevice directory copy is unreliable, Build25 supports an optional
`Steam32OfficialClient` directory in the privately generated app bundle. Add
only the complete manifest-verified official staging tree before signing;
verify every file hash again, then sign/install the lab. Do not add it to Git.
The explicit x86 experiment imports it once into new `Steam32BundleLab`, via a
unique temporary directory and atomic move. Existing targets are preserved.
The x86 launch checks that directory before the manually staged Steam32Lab.
No resource import happens during ordinary launch or the default x64 experiment.


For the x86 client experiment launched through the 64-bit desktop, set
`env.MADEIRA_GDI_SHARED_SECTION = 1` in the isolated lab config before a fresh
launch. This existing Wine option ensures session GDI handles have guest-window
views. In actual Build25, the option produced a section-backed table and child
view and allowed the genuine Steam updater to run, whereas the initial run
faulted in i386 gdi32 get_gdi_client_ptr. A JIT allocation failure before Wine is
an invalid comparison, not evidence about this option. Leave the normal app
configuration unchanged. Allow official updates and record resulting binaries.


Build26 adds `env.MADEIRA_STEAM_UI_ALLOW_CRASHPAD = 1`, effective only together
with the native experimental session flag. The genuine helper's exact
`--type=crashpad-handler` command is admitted unchanged. Other --type children
remain denied. This tests the observed crashpad_client_win.cc144 self-termination
without suppressing Chromium checks or disabling crash reporting. Check the
final Mach-O for `event=admit kind=crashpad policy=experimental`, then require
actual device logs for validation. The installed Build26 test currently lacks
readable device results; zero-byte transfer failures are not results.
Host regression: `python3 tests/host/check-steam-ui-crashpad.py`.


### Build27 screen keyboard coexistence

In the isolated lab, a focused Metal UIKeyInput responder now owns text even
when Device Hub enumerates a Generic Keyboard. Raw printable hardware down
edges are deduplicated in that mode, key-up/shortcuts remain raw, and physical
Shift is preserved. Ordinary game routing stays unchanged. Backspace is enabled
for text held in the guest. Only ASCII VK mapping is currently implemented.
Validate on the real iPhone software keyboard, including insertion and deletion;
a successful host test or Mac keyboard event alone is insufficient. Never type
credentials for a diagnostic. Native session key-value logs are suppressed.

```sh
python3 tests/host/check-steam-ui-keyboard.py
python3 tests/host/check-hardware-input.py
```

Rebuilding win32u requires prepared FreeType include/library resources under
build/freetype-ios/build. A missing-library warning is not an acceptable final
UI build; verify FreeType in the final image. Do not stage private resources or
local symlinks into Git.


### Build28 genuine Big Picture direct-start discriminator

After interactive real CEF/authentication has been demonstrated, the isolated
lab supports config `env.MADEIRA_EXPERIMENTAL_BIG_PICTURE = 1` and explicit launch
argument `madeira-steam-big-picture-x86-experiment`. Both the original SteamUI
flag and .steamui bundle restriction still apply. This mode adds only official
`-bigpicture` to the existing genuine Steam command; the default launch stays
login-only. Preserve the existing prefix to test legitimate account persistence.
Compare with the observed desktop-to-Big-Picture loading stall, without changing
other options or patching Valve code. Require actual navigation/library/game
results; a startup background, BrowserReady or a successful build is insufficient.

### i386 default keyed-event / InitOnce discriminator

Build `keyed-event32-probe.c` with the pinned local LLVM-MinGW
`i686-w64-mingw32-clang -O2 -Wl,--no-insert-timestamp`, stage the executable as
`drive_c/steam-ui-keyed-event32.exe` in the isolated iDeck prefix, and launch with
`madeira-keyed-event-diagnostics`. This explicit argument excludes auto-Steam start
and uses the existing paired JIT flow. Read `drive_c/madeira-keyed-event32-results.txt`.
The PE writes no account data, compares default versus explicit keyed events, and
only runs contended InitOnce after both basic contracts pass. Zero-timeout unmatched
wait/release must return0x102; object-type-mismatch0xc0000024 is a failure.
Build35 failed defaults while explicit handles passed; Build36 per-process resolver
passes the same device test. Run `python3 tests/host/check-steam-ui-keyed-events.py`
for the production resolver ASan/UBSan concurrent/isolation/capacity regression.
This test does not prove CEF or library navigation stability; see latest POC results.

### SwiftShader Vulkan initialization discriminator (prepared, not device-run)

Compile `swiftshader32-probe.c` with the same pinned i686 LLVM-MinGW compiler:
`i686-w64-mingw32-clang -O2 -Wall -Wextra -Werror -Wl,--no-insert-timestamp swiftshader32-probe.c -o swiftshader32-probe.exe`.
Stage the PE at `drive_c/swiftshader32-probe.exe` in the isolated prefix; use a
fresh isolated developer runtime launch `cmd.exe /c C:\swiftshader32-probe.exe`
with existing authorized JIT workflow. No new automatic launcher argument is wired
for this probe yet; do not mistake the keyed-event argument for this program.
The program expects the existing official client at
`C:\Steam32BundleLab\bin\cef\cef.win7\vk_swiftshader.dll`, creates a Vulkan1.0
instance/device, then destroys them. It does not replace or patch the ICD.
Read `drive_c/madeira-swiftshader32-results.txt`. Output before each Vulkan call
allows an unhandled original failure to be distinguished from successful return;
its VEH prints only recognized exception codes and continues exception search.
A successful compile is not a Vulkan test result. Current status: prepared only.

Build40's separate browser A/B uses `--disable-software-rasterizer`, isolated-session
only. `env.MADEIRA_STEAM_UI_NO_SWIFTSHADER=0` restores the previous browser policy.
Run `python3 tests/host/check-steam-ui-software-3d.py` for production policy ASan/UBSan
coverage. Confirm the actual native policy marker AND loaded modules/UI on phone;
the flag's presence in the binary is not proof Steam honored it.

Build41 update: explicit `madeira-swiftshader-diagnostics` now runs this staged
probe through paired JIT. Missing/x64/non-isolated binaries are refused and
Steam auto-start is excluded. Build41 actual device reaches vkCreateDevice then
observes a C++ exception. The default software-rasterizer disabling experiment
was rejected after a different CEF assertion/black screen; it now requires
`env.MADEIRA_STEAM_UI_NO_SWIFTSHADER=1`, with unset/0 preserving old policy.

Build44: the SAME probe now returns vkCreateDevice0 and PASS on phone after
parent native correction of WoW GROUP_AFFINITY output attributes (12 ->16 bytes).
`python3 tests/host/check-steam-ui-affinity32.py` exercises production decoding with
ASan/UBSan, exact unaligned12-byte allocation, all fields preserved, ordinary/native
and malformed gates. This does not prove Steam UI stability or Bluetooth/game return.
