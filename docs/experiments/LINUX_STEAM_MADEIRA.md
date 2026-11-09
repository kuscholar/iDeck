# Linux Steam + Madeira on iPad: experiment log

Status: Phase 1 now has actual Air ARM64 ELF evidence: Lab8 TCP control
completed status0 with17 PASS. Native Scene startup fixed. Full verified Linux
image import, native X11/RFB/Metal and genuine Valve Linux Steam login window
are now visually verified on Air. Run8 adds a host-verified installed diagnostic
compatibility tool and unsigned Lab15; active Air13 is preserved. No authenticated/interactive device Steam login,
Library/Big Picture or Madeira game/return/stability success yet. See run6.
Started 2026-11-06 America/New_York. Branch `experiment/linux-steam-madeira-ipad`.
This log is the resumption point; preserve uncommitted experiments between runs.

## Baseline and isolation

- Fork: https://github.com/kuscholar/iDeck; fetched `origin/main` at
  `2ac39beff91251d36f3ad6331d3f8402b3c10e18`.
- Separate worktree: `FunProjects/iDeck-linux-steam-ipad`. Original iDeck is on
  `fix/steam-runtime-entry` with pre-existing edits; none are imported or changed.
- Baseline gitlinks: FEX `f59cab95659e8add0c88f0c76ec1cf483c536dbf`,
  wine `9129e9684daaeae70da9435e7c6060e59392634e`,
  dxmt `128b297c6e9a00014408dc68b4c2c2373b5813de`,
  madeira-dock `72558e416a390f3669457930f09a389e54f49556`.
  These submodules are not yet initialized in this new worktree.
- LinuxRunner reviewed/fetched `d1419782da2e299fe22f1ddb85c70ae3d1e276b1`.
- DroidDeck reviewed `f33d5b9e09ed27d68137aba4e711f8fca9eb93e9`.
- Xcode 27.0 (27A266a). New worktree lacks native Wine/FEX/DXMT archives,
  PE farms, LLVM iOS/toolchain builds, Microsoft runtime and signing profiles.
  Existing private resources may be reused read-only after provenance checks.
- Lab identity: `com.kuschqin.ideck.linuxlab`, display name **iDeck Linux Lab**.
  Never fall back to the working app's bundle identifier to obtain signing.
- All new downloads/build trees/device artifacts belong under the private
  external `.madeira-install/linux-steam-ipad`, outside Git. No auth transfer.

## Phase 0: audited architecture

Read repository AGENTS/CONTRIBUTING, README, BUILDING, DISTRIBUTION, JIT,
BIG_PICTURE_ARCHITECTURE, MADEIRA_DOCK, STEAM_LIBRARY and STEAM_SIGNIN, plus
WineProcessBridge/WineServerBridge; LinuxRunner BUILDING/ARCHITECTURE,
SYSCALL_MATRIX/IOS_JIT, loader/bootstrap/task/exit/filesystem/graphics sources;
DroidDeck ARM64/x86 client docs and install/session/compatibility/proton wrappers.

**Reuse:** Madeira owns its Wine pthread, in-process wineserver and socketpair,
FEX/ARM64EC JIT, Win32 windows, DXMT Metal presentation and iOS input. Wine's
entry is `wine_process_start`, wineserver shutdown is `wineserver_stop`.
The library has a one-session-per-app-run guard: process-wide Wine/server/loader
state is not generally reset by the apparent stop functions. Do not remove that
guard. Existing controller/touch foreground/background and JIT pathways remain
unchanged in the production target.

Madeira Dock deliberately starts real headless Windows Steam client libraries
without steamwebhelper, authenticates through Valve, then asks LaunchApp. The
native owned-library downloader and sign-in are separate from the genuine Windows
Steam UI experiment. Linux Steam authentication does not automatically authorize
Windows Dock: separate legitimate sign-in may be necessary, with user involvement.
No token conversion, borrowed cache or forged Steamworks IPC is planned.

**Adapt LinuxRunner:** ELF loader + Asbestos interpreter/optional JIT + emulated
Linux syscalls/tasks + fakefs. ARM64 guest instructions do not execute directly.
Guest PIDs are tasks backed by host pthreads. Guest pages are 4 KiB, independent
of Darwin's page size. The optional native JIT has no physical-iPad qualification
in the inspected record; start interpreter-only to avoid FEX allocator/signal
conflicts. The first Lab target intentionally excludes Wine and graphics until
ELF/process semantics pass. Later the same target must acquire the Madeira
adapter; separate apps are not an end-to-end hybrid success.

LinuxRunner X11 is Xvfb/x11vnc; virglrenderer -> ANGLE GLES -> Metal is available
with separately built dependencies. It is not a generic Vulkan bridge. Missing
namespace/seccomp calls and partial memfd/rseq/clone semantics may affect CEF;
measure the first actual failure instead of assuming all are fatal. Rootfs
metadata uses fakefs/SQLite. No assumption that a Debian/Arch tarball can simply
be unpacked with host ownership semantics.

**Borrow DroidDeck interface conventions:** official `steamrtarm64/steam`, matching
channel/beta state, SHA-256 verified packages, normal `compatibilitytools.d` VDF
registration, `waitforexitandrun`/`run` verbs, AppID/installation/compatdata
metadata and child exit status. Do not import its Android PRoot, Turnip/Vulkan,
process killing, pressure-vessel probe substitution or runtime shims wholesale.
Probe current official manifests independently before acquiring packages.

**New native boundary:** bounded versioned request/response protocol with explicit
allowed verbs, positive AppID, app-private shared library paths, no shell command
execution, bounded arguments/env whitelist, lifecycle/result reporting. Start with
a harmless handler; actual game execution must route through Madeira's licensed
launch path. Sequential handoff must establish *all* Linux tasks have stopped
before Wine/JIT begins; a PID1 exit callback alone is insufficient. Full Wine
restart in the same host lifetime remains an explicit blocker, not solved here.

## Device evidence, 2026-11-06

Fresh CoreDevice inventory (including outside sandbox) lists both physical iPads
as unavailable; only simulators are connected. No substitute simulator evidence.
`device info details` for paired Kusch's iPad reports iPad Pro 11-inch, iPad8,1,
arm64e/arm64, eight CPU cores, iPadOS **26.7.1 (23H30)**, Developer Mode enabled,
manual pairing retained, last connection Nov 1. This is cached metadata, not a
live unlock/trust/signing or memory-capacity test. RAM/VA budget not measured.
Yilenda's iPad Air 4 is also unavailable. User was asked to connect/unlock and
identify the intended device. No app install, launch, profile or account changed.

## Licensing and release gate

New experiment code follows CONTRIBUTING; exceptions apply only to our work.
LinuxRunner/iSH/ios-linuxkit GPLv3 plus contribution-specific GPLv2 grants and
LICENSE.IOS are retained through pinned source. LICENSE.IOS's iSH App Store
permission is not a blanket exception for Apple's proprietary shader converter.
DroidDeck is GPLv3; this initial protocol is independently implemented using its
published interface conventions. Preserve notices if code is subsequently copied.
The initial Linux-only lab excludes Metal Shader Converter. A combined binary
requires an explicit component/linkage review; do not publish a combined IPA until
GPL/additional-permission and LGPL source/relink obligations are resolved. Private
builds are not a claim of distribution clearance. Valve binaries, rootfs caches,
profiles, pairing files, account data, games and raw logs never enter Git.

## Next gates

1. Build pinned LinuxRunner interpreter and the isolated Lab, run a freestanding
   ARM64 ELF control (host and actual iPad separately recorded).
2. Expand control to filesystem, clone/futex/wait, sockets/shared memory; capture
   numeric failure stage, not arbitrary guest output or authentication payloads.
3. Inspect official ARM64 Steam ELF/dependencies, build glibc rootfs/display,
   attempt genuine login/UI with user-entered credentials only.
4. After UI, register compatibility tool; validate harmless handler first, then
   authorized Madeira game launch and exit/return. No mock UI substitutes.

## Recurrence

User requested 305-minute recurrence until evidence-backed stable iPad operation.
Current tool catalog has no automation create/update capability (the old deleted
Madeira schedule is not restored). Recurrence is **not configured**. Do not edit
Codex databases/config or claim a schedule exists. Prepared continuation prompt
will be kept alongside this document; use official automation UI/tool when available.
Commit/push follows AGENTS time window; initial work began Friday 19:16 EST,
so changes remain uncommitted until an allowed window.

## Run 1: implementation and actual results (2026-11-06)

Current source checkpoint: uncommitted on the isolated experiment branch, based
on `2ac39be`. No commit/push outside the user's permitted time window. Do not
reset this work when resuming. Dependency pins and evidence hashes are in
`LINUX_STEAM_MADEIRA_EVIDENCE.json`; private root `.madeira-install/linux-steam-ipad`.
The separate original iDeck worktree still has its pre-existing modifications.

### Implemented

- Pinned LinuxRunner gitlink under `vendor/LinuxRunner`; no vendor/FEX source edit.
  Native Lab project/scheme, unique app ID/display/container, interpreter-only.
- Minimal ARM64 ELF control, freestanding compatibility-tool ELF, discovery VDFs,
  bounded native character-device IPC, syntax validation, duplicate-request guard
  and diagnostic status125. No arbitrary native execution API exists.
- Native bootstrap uses a parked PID1 and a joined child. `exit_hook` only observes
  status; one app lifetime is consumed even on failed launch. PID1's upstream
  halt_system calls host `_exit`; never use that as a sequential handoff mechanism.
  Complete task shutdown/resource reclamation/restart remains unimplemented.
- Small fakefs-backed `/dev` plus private metadata sibling; no host mknod/private
  entitlement. Root files currently use sparse realfs. Full fakefs distro import
  and correct metadata/symlink handling are future requirements.
- Host package acquisition verifies official size/SHA256, range resume and safe
  new-directory extraction; **not yet an iOS installation manager**. No Valve files
  or account cache enter source control.
- Categorical phase/result reporting; no authentication field handling. Raw loader
  stdout was collected only in a fresh, unauthenticated host control root.

### Experiment: non-directory dirfd contract

Observed: after creating normal Steam runtime directories, /dev/urandom and
Steam's data links, authentic client execution aborted LinuxRunner's
`path_normalize_target` assertion. A private diagnostic copy printed
`at=anon_inode:[unknown] requested=./.writable`, keeping the assertion intact.
LLDB could not finish a bounded host observation; only the identity-verified
experiment debugger/children were stopped. No phone process was touched.

Hypothesis: path normalization is reached before rejecting an invalid
non-directory dirfd. Discriminator: a small ARM64 ELF invokes
`openat(socket_fd,"./.writable",...)`, whose contract is ENOTDIR. The unchanged
runtime aborts (host subprocess signal6). The narrow patch checks descriptor
stat/mode before normalization and returns ENOTDIR, preserving the original
assertion. Same ELF passes after overlay; actual Steam crosses this point and
reaches manifest download. This establishes a missing error-handling contract;
it does **not** establish why Steam's specific fd became that object, full fd
conformance, CEF correctness or a sole Steam root cause.

The patch is kept in `experiments/linux-steam/patches/linuxrunner-dirfd.patch`.
`overlay-dirfd.py` verifies the exact pinned source and compiles the replacement
only into generated private libish.a. The native adapter calls its version marker,
so omission fails linking; final iOS Mach-O presence is checked separately.

### Host results

- Real ARM64 ELF through the interpreter: 12 categorical result lines pass,
  including entropy device, file read/write, shared mmap across clone, child wait,
  Unix socketpair, invalid dirfd, IPv4 socket creation, thread/futex and native
  bridge response. `complete=PASS` is a control summary, not a Steam milestone.
- Actual compatibility wrapper ELF with synthetic metadata reaches native handler,
  gets125 and exits with raw wait status32000. No game or ownership claim.
- Source C protocol: ASan+UBSan valid/truncated/hostile size/path/packed argv and
  byte-mutation tests pass. Five package tests pass: platform filtering, unsafe ZIP,
  official separators/contained symlinks,206 range resume, ignored-range200 restart,
  verified-cache reuse and corrupt complete-partial rejection (mock transport).
- Existing `check-frontend.py` and `check-ideck.py` pass. Swift compilation first
  hit a sandboxed default module-cache path; directing caches to private external
  storage passed. This was not a production regression.
- No device result. No comparative startup/UI/FPS/memory/thermal metrics.

### Authentic Steam loader and network results

Both official `steam_client_steamdeck_stable_linuxarm64` and beta manifests were
retrieved over HTTPS. Stable version1792618285 contains ARM64-native platform
packages; bins package SHA256 is in the evidence file. The actual Steam executable
is AArch64 ELF, interpreter `/lib/ld-linux-aarch64.so.1`, SHA256
`7faec98260d94ee3c8e801100f1e4af446f70042abafddd351aae7390e6fbc2d`.
Initial dependencies are libdl/libm/libpthread/libc/ld-linux. Pinned Debian ARM64
libc6 2.41-12+deb13u4 was independently fetched and hash-checked from Debian; only
regular library payloads were staged, with no maintainer scripts executed.

After ordinary sparse-root setup and the dirfd patch, genuine Steam logs its
startup, updater and manifest request, then exits. Correct channel argument
`-clientbeta steamdeck_stable` directs it to the official stable ARM64 manifest.
A fresh outside-tool-sandbox run still reports Steam `http error0` and cannot
complete bootstrap. No desktop/CEF/login display has been reached.

Important discriminator: a separate genuine dynamically linked ARM64 glibc
getaddrinfo control returns **-3 inside the tool network sandbox, 0 outside**.
Do not blame LinuxRunner DNS based on the sandboxed result. The same sparse-root
libcurl dlopen control returns0 (not loaded): its ELF lists additional SSL/crypto,
SSH2, zstd, Brotli and zlib dependencies not all provided by this minimal root.
It cannot yet distinguish TLS/CA/client networking failures. The Steam updater's
http0 is not proof that this separate libcurl dependency issue is its cause.
Next complete the pinned rootfs/libraries/trust store and isolate HTTPS before
attempting CEF. Do not bypass certificate validation or guess a network fix.

### iOS build / installation gates

The isolated LinuxLab arm64 Xcode build passes. The final linked app contains the
LinuxRunner loader, bounded bridge and dirfd version marker; guest ELF is AArch64.
This is not a simulator/device execution result. It has no display/Steam UI yet.

The untouched origin/main baseline build was attempted separately and fails at
`framework 'StikJIT' not found`: private runtime resources were not staged into
this fresh worktree. Their prepared copies exist elsewhere; no working app or
original dependency was changed to resolve this.

Development certificates exist for the authorized team, but no profile matches
`com.kuschqin.ideck.linuxlab`. One automatic signing attempt failed CLI
`No Accounts`/missing profile. This does not prove Xcode UI logout. User was asked
to select their existing team in the isolated project; never substitute the
production bundle identifier. No Lab installation or JIT activation occurred.
Cached Air4 metadata additionally reports iPadOS27.2(24B119), developer enabled,
paired but unavailable. The intended iPad still needs user confirmation/connect.

### Remaining gates and next experiment

1. User device connection/target confirmation and unique Lab development profile.
   Install the already buildable isolated Lab and retrieve its actual control
   results before claiming Linux ELF on iPad.
2. Complete LinuxRunner's authenticated/pinned Debian rootfs path and dependencies,
   retaining fakefs Linux metadata. Isolate actual HTTPS/TLS/update behavior using
   source `guest/network-probe.c`, not Steam's generic http0.
3. Bring up minimal X11/display and genuine Steam login/Library. Credentials and
   Steam Guard are user-only. No CEF/Big Picture/controller success yet.
4. Register tool in actual Steam only after frontend works. Host path/catalog,
   symlink/TOCTOU and Steam authentication/ownership validation are not implemented
   by the current syntax-only bridge. There is no Madeira launch or game return.
5. Resolve full Linux shutdown and Wine's one-session lifetime before sequential
   game handoff; concurrent mode and Steamworks integration are advanced gates.

The recurrence remains **not created**, owing to unavailable task-management
capabilities in this session. A prepared prompt is in
`LINUX_STEAM_MADEIRA_CONTINUE.md`; it is not itself a running automation.

Fresh end-of-run availability: Xcode `xcdevice list` reports both physical iPads
unavailable, deviceprep code-27 (LAN discovery); USB registry lists hubs/storage,
no iPad. This confirms the physical deployment gate persisted during this run.
No repeated signing/install attempts were made after the specific profile failure.


## Run 2: selected Air, CLI scheduler and complete Debian (2026-11-08)

The user selected **iPad Air4/iPad13,1**, iPadOS27.2(24B119). Fresh CoreDevice
connected over the local network; pairing/developer mode verified. The user
explicitly requires **CLI-only operation and no further Mac-unlock requests**.
No lock was bypassed, credential automated or OS privacy setting changed.

### Deployment, without replacing an installed app

The new default ID com.kuschqin.ideck.linuxlab still has no development profile;
one fresh normal CLI attempt failed No Accounts/missing profile. Valid certificates
and the existing team are present, so this is not asserted to be GUI logout.
An existing **com.kuschqin.ideck.freshtest** development profile covers this Air,
was current, debuggable and matched the available signing certificate. This ID
was **absent from the Air's installed apps**. It is separate from production iDeck
and from the already-installed Mac Allocator. The source default remains linuxlab;
only the disposable deployment build overrides PRODUCT_BUNDLE_IDENTIFIER.

Lab1 built, was signed in a disposable copy and passed deep/strict local signature
verification. CoreDevice install/readback succeeded as **iDeck Linux Lab**.
Readback confirms the old Mac Allocator keeps its previous URL/version. No phone
install, account, game, prefix or save changed. No Keychain/auth API is used by Lab.

Actual launch was refused by SpringBoard/CoreDevice10002 with the generic
**signature/inadequate entitlements/profile not explicitly trusted** message.
That is not a Linux crash or proof of which of those alternatives is responsible.
No probe file exists yet. User was asked to inspect the Air's exact launch prompt
and, if it is an untrusted-developer prompt, authorize through iPad Settings.
Do not automate trust approval or repeat Mac-unlock requests. No device execution
success is claimed merely because installation and local signing passed.

### Correction to the initial dirfd patch

Full Debian initialization exposed a real regression in v1: the common path guard
rejected utimensat(file_fd,NULL,...) used by touch. Upstream intentionally handles
that file-target operation through a path-normalization helper; it is distinct
from openat's directory-base contract. The initial broad patch was incorrect for
that path and is superseded by v2.

The patch now checks only non-empty **relative openat** requests with an explicit
base fd in fs/generic.c. Absolute paths ignore the supplied dirfd. Common path
normalization and its original assertion stay unchanged. The overlay restores
pristine fs_path.c.o when reusing a v1 private build and replaces only the generated
fs_generic.c.o. A required linked marker identifies
`IDECK_LINUXRUNNER_OPENAT_DIRFD_GUARD_V2`. Vendor/FEX source stays pristine.

Host controls now pass **14** result lines, including file-null utimensat and
absolute-openat-with-nondirectory-dirfd, plus the original failing socket-dirfd
case. Full Debian initialization, which failed at touch with v1, passes with v2.
The isolated Lab2 iOS arm64 build passes and its final Mach-O contains the v2
marker. Lab2 has not yet been installed/validated on Air; Lab1 remains the installed
control until the current user trust gate is resolved. Do not call a source fix
included on-device until the upgraded app/linked artifact is actually verified.

### Complete official guest dependencies

Initialized LinuxRunner's pinned libarchive gitlink
fc6563f5130d8a7ee1fc27c0e55baef35119f26c; retained BSD/file-level notices.
Host bootstrap/fakefs tools compile from pinned LinuxRunner source with those
public headers and macOS's system libarchive/sqlite. This is not a claim that a
new iOS libarchive was built. The other optional graphics/kernel submodules remain
uninitialized and are not prerequisites for interpreter controls.

All **103** Debian ARM64/all base packages from the exact upstream manifest were
size/SHA256 verified. The rootfs was assembled with LinuxRunner DebianBootstrap,
imported through native fakefsify, then configured **inside the Linux guest**.
No Debian maintainer script executed on macOS. Upstream OpenPGP audit exists but
was not independently repeated; our acquisition checks are the pinned manifest
and package SHA256 checks, not a newly verified repository signature chain.

Actual host guest execution reports glibc2.41, aarch64 and curl8.14.1/OpenSSL3.5.7.
Debian initialization completes, including normal update-ca-certificates. Genuine
ARM64 curl downloads the official stable ARM64 Steam manifest over HTTPS with
certificate checking enabled and exits0. This corrects the sparse-root diagnosis:
HTTP/TLS work in the full guest environment; it does not prove Steam/CEF works.

All **17 selected official ARM64 Steam/resource packages** are acquired and safely
extracted. Codec libraries include contained ../ symlinks; the extractor now
lexically resolves these, requires a regular target in the same verified package,
rejects root escape/chains/nested writes and retains hostile-archive tests.
Six package tests pass. A guest-only Steam overlay (6612 component members) is
prepared from those files; no credentials or binaries were patched or committed.
Full Steam root import/client startup remains the next discriminator before X11.

### Requested 305-minute task: created and dispatch tested

No native app task-management API is exposed in this session. The authorized
CLI alternative is a user LaunchAgent named
`com.kusch.ideck-linux-steam-ipad-305m`, with StartInterval **18300 seconds**.
It calls only the official Codex CLI, ensures its local daemon is started, then
queues/resumes **this existing thread** with the project/continuation instructions.
It uses the saved thread model; no second researcher or remote control is enabled.

The initial external Python-script approach failed under launchd's external-volume
permissions. It was replaced with direct CLI arguments stored in the LaunchAgent;
no permission was disabled or broadened. Small dispatch logs use the normal user
Library/Logs directory. Research/build/download artifacts remain on easystore.
`tools/configure-schedule.py` generates the reviewable plist; two argument/interval
regressions pass, including literal quotes/newlines/shell-like prompt content.

Actual launchctl bootstrap/readback/kickstart passed, last exit0 and interval18300
were read back; official CLI logs show a queued message. Because this thread has
an active writer, resume correctly deferred with an active-writer warning rather
than starting overlapping work. **An unattended full research turn after the
current writer releases has not yet been observed.** Registration/dispatch are
verified; never conflate them with completed future runs or product success.
Mac must remain powered/awake and storage available; sleep can delay timer work.

The continuation instructs the agent to unload only this job after actual repeated
Air Library/BPM/input/Steam Play->Madeira/game-return stability evidence, or upon
user cancellation. The LaunchAgent itself does not infer product milestones.
Stop/readback commands and exact private artifact paths are retained locally.

### Full-root assembly findings

An initialized guest-root export represents PAM.7.gz/pam.7.gz as a hardlink pair.
On the case-insensitive development volume, unmodified fakefsify fails EEXIST
while re-importing that same physical regular inode. A minimal two-member tar
reproduces it. The **host-only** importer patch accepts EEXIST only after NOFOLLOW
stat proves source/destination are the same regular inode on the same device;
a different-inode collision still fails. Both tests pass. It changes neither
Linux guest syscall semantics nor any OS permission. Vendor source stays pristine;
`build-rootfs-tools.py` builds a private patched host tool from the pinned source.
This is not a claim of general Linux case-sensitive filesystem support.

The combined root initially imported file payloads but lacked explicit /Steam
metadata because the overlay emitted children only. Actual guest cd /Steam failed;
therefore that attempt never executed the client. The overlay now explicitly
emits its outer directory and has an archive-metadata/payload regression test.
The corrected new root is steam-fakefs-v3; continue from its actual receipt.
No assertion/TLS/Steam binary bypass was used to hide either failure.


### Final run2 discriminator: accessat, verified v3 and real updater progress

The corrected full fakefs root genuinely starts Steam; with the openat-only v2
patch it still aborts. The captured host backtrace names **generic_accessat ->
sys_faccessat -> sys_faccessat2 -> path_normalize_target**. Therefore treating
openat as the only implicated caller was incomplete. Hypothesis: Steam also tests
relative access using a non-directory descriptor, which must return ENOTDIR
before common path normalization. The v3 patch adds only that accessat guard;
absolute paths and valid file-target utimensat retain their upstream behavior.
No original assertion or Valve binary is changed.

The same host suite now passes **16** result lines including faccessat2 on a
non-directory fd and faccessat2 absolute-path dirfd independence. Protocol
ASan/UBSan and six package tests pass. Full iOS arm64 Lab2 build passes; the final
linked Mach-O contains **IDECK_LINUXRUNNER_DIRFD_GUARD_V3**. The vendor checkout
remains pristine. Installed Lab1 has not been upgraded, so this is not device
validation of the new runtime patch.

A fresh bounded host observer using v3 and the complete unauthenticated root
records **Download complete (100%)** then **Extracting package**. At75.057seconds
the observer intentionally terminates it (SIGTERM, returncode-15). It has not
reported update completion; no display server/UI/login exists. It is neither a
natural crash nor evidence of a freeze. This is stronger than the sparse-root
http0 result, but only host interpreter/updater progress. Private receipt:
run2/steam-dirfd-v3.json. No performance comparison with Windows Steam is justified.

Next: preserve/check the pending user Air trust result and collect Lab1's probe
before upgrading. Independently resume the unauthenticated updater with a longer
bounded observer, then isolate its next actual failure or set up minimal X11.
Do not claim genuine interactive iPad Steam, compatibility-tool discovery, game
handoff, input, complete runtime shutdown or reliable return. The schedule's
fixed goal remains repeated stability on the selected Air, including the real
Steam UI and licensed Madeira game/return cycle. The native queue active-writer
warning deferred the manual dispatch; future unattended research is not yet proven.

Source checkpoint: **d662352ce36a390528959967a5e32c2f48057081**, signed off on the isolated experiment branch.
Only source, tests, pinned gitlink and redacted evidence were committed; no
compiled binaries, rootfs, Valve packages, profiles or raw logs. The following
documentation-only commit records this exact implementation revision.

## Run 3: direct Air observation, full-root adapter and display (2026-11-08)

Resumed from source b0989ee/d662352 with pristine experiment worktree and fetched
origin. Selected Air remains iPad13,1/iPadOS27.2. No production app/account/game
state changed. Device Hub's control tool failed to initialize its executor due
to the inherited symlinked writable root; no trust/sandbox setting was changed.
Authorized Xcode CLI outside the tool sandbox discovers the real paired Air,
reads passcodeRequired=false/unlockedSinceBoot=true and captures its actual screen.
No Mac-unlock request or lock bypass was made.

The installed Lab has no live process. One launch is refused CoreDevice10002.
**Actual Air screenshot explicitly shows Untrusted Developer.** This narrows the
previous generic signature/entitlement/trust alternatives to an observed user
trust gate. Local deep/strict signature verification still passes. User trust in
Settings is required; it is not automated. Pending async question explains the
Air action. No further launch/install retry was used for this unchanged gate.
Screenshot/profile identities remain private; no device ELF result is claimed.

### Genuine updater and its next failure

The same unauthenticated full-root ARM64 Steam updater completes download,
extraction and installation, then writes **Update complete, launching Steam**.
It naturally exits42 after268.075seconds (host interpreter only). The exact
Valve steam.sh sets MAGIC_RESTART_EXITCODE=42 and restarts on that value, so this
is consistent with its documented-in-source restart contract, not a crash.

A subsequent bounded launch verifies installation then naturally exits255 in
2.160seconds: **dlmopen steamui.so failed: libGL.so.1 not found**. This is the next
observed dynamic dependency failure, not a CEF/renderer diagnosis. Signed Debian
apt metadata refresh passes in13.373seconds. Installing libgl1, xvfb, x11vnc,
xauth, fonts-dejavu-core and dbus-daemon inside this private root passes in65.907s.
No host packages, TLS/GPG bypass, Valve binary or production root was modified.
Those times are host-control durations, not iPad performance measurements.

### Whole-distribution embedding control

Lab3 adds only an explicit **linux-distro-diagnostics** argument. It mounts
prepared Application Support/iDeckLinuxLab/DebianRootFS/data using fakefs and its
sibling meta.db, retains existing Linux metadata/devices, validates known device
node types/numbers, and executes a fixed non-authenticating Debian shell control.
The default ELF probe and original production target remain unchanged. Missing
prepared storage reports an error rather than creating a fake successful root.
No arbitrary shell/launch arguments are accepted from the app UI.

A private copy of the stopped initialized Debian base passes all six host adapter
results: ARM64 identity, glibc executable/dynamic link, filesystem/touch, entropy,
curl linking and completion; guest wait0 and repeat-start EBUSY(-16). The first
host invocation accidentally supplied a relative root and correctly got EINVAL;
the corrected absolute-root run is the valid result. This proves host embedding,
not Air execution or complete shutdown/restart. PID1 remains parked and the
one-native-lifetime limit is unchanged. Lab3 unsigned iOS arm64 build passes with
the v3 guard and explicit mode markers in the final Mach-O; not installed yet.
Host16 ordinary controls, diagnostic compatibility wrapper125, protocol ASan/UBSan
and all6 package regressions also pass after this adapter change.

### Real display transport control

An actual guest Xvfb :99 (960x540x24, no TCP listener) plus x11vnc on authenticated
host loopback5993 starts in this private root. The unchanged pinned LinuxRunner
RFBClient receives and decodes an actual frame. New source tools/rfb-capture.m
saves it through public CoreGraphics/ImageIO and explicitly labels Steam UI
UNVERIFIED. The observed image is an empty black X11 desktop with cursor. This
is display-transport evidence, not Steam paint or interactive login. The random
8-byte VNC password and all raw frames/logs stay outside Git.

Host capture compilation retains vendor source unchanged, suppressing its known
misleading-indentation/unused-static-header warnings and deprecated public DES
warning; no error suppression in runtime assertions is introduced. New control
code builds with Wall/Wextra/Werror. Full renderer/input/iOS integration remains
future work after the actual missing-library/display discriminators.


The direct-dependency ldd check after libGL lists GLib/GObject/GIO, GTK2,
PipeWire, PulseAudio, GdkPixbuf, EGL and VA. Their ordinary signed guest package
installation succeeds in29.354seconds. A fresh1280x800 X11 session really paints
Valve's **Updating Steam / Verifying installation** window; it then reports
**Could not load module vgui2_s.so**. That specific module's loader/dependencies
are the next discriminator. Neither an updater window nor frame capture proves
CEF, login or Library. No credentials were entered. Raw guest logs/screenshots
remain private. Air user trust remains pending and no Lab3 install is claimed.

The vgui2_s.so discriminator identifies **libopenal.so.1** via actual guest ldd.
Installing libopenal1 succeeds (9.467s). The subsequent real source-based X11
experiment advances past that loader error but fatals in
surface_linux.cpp1967: **glXChooseVisual failed**. The transport-only test had
explicitly disabled GLX; this configuration is inappropriate for Steam's VGUI.
The source control now enables Xvfb's GLX, with Mesa software libraries as its
next dependency. This is a targeted display-configuration hypothesis, not an
assertion workaround, FEX fix, or a claim the CEF renderer works.

Source guest/x11-control.sh and tools/run-x11-control.py now reproduce the
bounded actual display/client observation. They preserve old artifacts, reject
recognizable login state and serialize their own calls; callers must still check
for independent guest processes. Four policy tests pass with a mock executable
(no device/runtime evidence). Session wrapper exit0 means only session completion,
not Steam success: the real client fatal is retained separately in its own log.


### GLX discriminator result and next contract

Mesa libglx-mesa0/libgl1-mesa-dri25.0.7-2+deb13u1 were already installed transitively;
apt confirms them current (2.293s, no new packages). Therefore the discriminating
change was enabling Xvfb GLX, not adding an unverified renderer fix. The next
actual source-wrapper experiment no longer reports glXChooseVisual; Steam advances
then fatals in **controllerxinput_linux.cpp31**, asserting its pipe descriptors
are nonnegative. This does not prove pipe2's flags/status, EMFILE or a CPU bug.
No assertion was suppressed. Next capture the numeric pipe syscall result and
make an isolated ARM64 pipe/fcntl control before changing LinuxRunner semantics.
A separate unimplemented-clone-flag message is observed but is not established
as the cause of the pipe failure. No CEF/login/Library success is claimed.

At the end of run3, a read-only Air last-probe check still fails missing file
(CoreDevice7000). No user trust confirmation has arrived; no further launch or
installation was attempted. The scheduled305-minute continuation remains active.
The required next device action is the observed Air developer-trust prompt, not
Mac unlock. Linux Steam UI and game/return stability remain unverified on iPad.

### Exact pipe failure: traced and isolated, not suppressed

A separate host observer is generated by build-pipe-observer.py from the exact
pinned fs/pipe.c, linked against a PRIVATE COPY of libish.a. Vendor sources,
base archive/binary, iOS build and ordinary pipe behavior are unchanged. It logs
only the first64 pipe2 flags/status/guestPID values; never user buffers/paths.
Final diagnostic Mach-O contains its marker. In the same real Steam startup,
guestPID11 pipe2(flags=0x90000) returns **-22/EINVAL**, followed by the controller
fatal. Other ordinary/CLOEXEC calls succeed. This is not evidence of EMFILE.

ARM64's O_DIRECT bit is1<<16, O_CLOEXEC1<<19, so0x90000 requests a packet-mode
pipe plus CLOEXEC. Checked both pinned kernel/fs.h and the authoritative
[Linux ARM64 UAPI](https://github.com/torvalds/linux/blob/master/arch/arm64/include/uapi/asm/fcntl.h).
[Linux pipe2 semantics](https://man7.org/linux/man-pages/man2/pipe.2.html) require
packet boundaries and discarding an unread packet tail on a short read. The
pinned fs/pipe.c rejects everything except CLOEXEC/NONBLOCK, explaining this
exact missing feature. Do NOT silently remove O_DIRECT, replace the assert or
pretend stream pipes implement packets.

New freestanding **guest/packet-pipe-probe.c** compiles ARM64/Werror and executes
under the same runtime. Actual result: stream creation0 and roundtripPASS;
exact Steam packet flags return-22; packet semanticsBLOCKED; guest exit1. This
is an intentionally reproduced failure, NOT a passing compatibility test. It
also contains future boundary/short-read/CLOEXEC/nonblock checks that must pass
after a real implementation. Actual packet operations have not run yet.
No runtime behavior fix is claimed; packet support, duplication/fork, polling,
EOF/cancellation and fcntl behavior need isolated tests before another Steam run.
This identifies a concrete startup blocker, not a sole cause for all future CEF.

Run3 implementation checkpoint: **93ea5138d58bd6e84a2267b210f6dd7d541bb623** (signed off). Remaining Air
trust and genuine packet-pipe semantics are unresolved; no stable Steam claim.
All bounded host sessions ended before the checkpoint; do not target stale PIDs.

## Run 4: packet-at-creation implementation and genuine CEF startup (2026-11-08)

Resumed clean branch72fb27f; fetched origin and checked all worktrees. Baseline,
submodule pins and production apps stay unchanged. Fresh Air details confirm
**iPad13,1, iPadOS27.2(24B119)**, connected. One read-only result check still finds
no Lab probe. No trust confirmation arrived; no launch, install, signing, Mac
unlock request, credential action or security-setting change was made. Installed
Lab1 remains the old control; later unsigned builds are not on-device evidence.

### Observed failure, hypothesis and implementation boundary

Run3 proved actual Steam pipe2flags0x90000 -> EINVAL and ordinary pipesPASS.
Hypothesis: a genuine packet-at-creation implementation permits that startup
contract without weakening Valve assertions. The optional generated lab archive
now includes **app/PacketPipe.c** only with build-pipe-observer.py --packet-pipes.
Non-packet calls retain the original pinned implementation. No vendor/FEX/Wine
source or base archive is overwritten; hash receipts verify the base archive is
unchanged. The immutable private output contains its included source snapshot.

The implementation uses local native datagrams for packet boundaries, splits
large writes at4096bytes and discards a short-read packet tail. Shared endpoint
state implements reader/writer lifetime, queued EOF/HUP, EPIPE/SIGPIPE, dup/fork,
custom poll/epoll notifications and bounded cancellation. No native guest PID is
treated as a Darwin process. All native endpoints remain nonblocking; guest
blocking semantics use the existing wait/signal integration.

Two discriminating tests rejected naive native passthrough:

- A64KiB native buffer fills at15packets and reports ENOBUFS(-105), not EAGAIN.
  The final adapter enforces16 guest packet slots and has larger native buffers
  for protocol overhead. Full queue returns EAGAIN and sleeps/wakes correctly;
  it does not spin on misleading native POLLOUT or remap all resource errors.
- Native FIONREAD reports37 for payload packets3+2. Metadata records actual
  payload lengths under serialized native I/O; the guest sees5, then2 after
  a short read discards the first packet tail. Native protocol overhead is not
  exposed as Linux data.

The first prototype/test incorrectly expected O_DIRECT on the read endpoint.
[Linux create_pipe_files](https://github.com/torvalds/linux/blob/master/fs/pipe.c)
sets it on the writer only. The adapter and reproducer were corrected against
that independent source before the final conformance claims. The original
creation EINVAL finding remains valid. No CPU capability or packet flag is
fabricated to bypass a check.

**Explicit incomplete contract:** packet-to-stream conversion via F_SETFL, and
opening a packet writer without O_DIRECT, return EOPNOTSUPP with bounded numeric
diagnostics. Ordinary stream-to-packet conversion is not implemented either.
This is packet-at-creation support, not a full Linux pipe replacement. Splice,
SCM_RIGHTS transfer of these descriptions, and all possible ioctl/async behavior
are not qualified. Do not assume this partial surface cannot affect later UI.

### Discriminating tests and regressions

The unchanged baseline still fails exact Steam creation flags with EINVAL.
The corrected ARM64 standalone basic control passes under the adapter and writes
its current report. **15 contract cases plus complete =16PASS lines** cover
large-write splitting, short-read discard, zero/nonblocking I/O, byte counts,
dup/queued EOF, writer-only flags, epoll read/drain/HUP, bounded capacity/refill,
closed-reader EPIPE/full poll masks, fork lifetime, blocked epoll/writer wakeup,
signal cancellation, bad-output-pointer cleanup and partial-install EMFILE.
The explicit unsupported conversion is tested as a limitation, not emulated
Linux success. The changed host translation unit is ASan/UBSan-instrumented;
prebuilt base libraries are not wholly instrumented, and leak freedom is not
inferred from this. No sanitizer error was observed in these bounded controls.

The published tools/test-packet-pipes.sh reproduces baseline failure and adapter
success in a NEW private root/output. Ordinary16 ARM64 controls and diagnostic
compatibility-wrapper exit125 remain passing with the packet-enabled archive.
The game bridge still launches no game. Five observer-boundary tests pass,
including rejection of durations over600seconds. No unrelated broad suite was
repeated after already passing.

### Final iOS build inclusion (not device execution)

LINUX_LAB_PACKET_PIPES=1 is an explicit Lab-only build flag, off by default.
It copies/patches a private iOS archive, preserving original generated archives.
Only this target's link search path selects it. Lab4 adds explicit
**linux-packet-pipe-diagnostics**, a separate PacketRootFS and current
last-packet-probe.txt. Missing/conflicting controls report errors. It has no
Steam login fields, in-app Steam root importer, Steam display frontend or Madeira
linkage. The default regular control and existing app/prefix remain unchanged.

The complete unsigned arm64 build passes. Final executable contains both
IDECK_PACKET_PIPE_V3 and IDECK_LINUXRUNNER_DIRFD_GUARD_V3, the diagnostic argument,
and the exact source-built packet ELF. Source/archive/app hashes are retained.
One intermediate provenance check incorrectly treated Meson's relative file
entry as cwd-relative; resolving it against entry.directory fixes that build.
No source workaround or security change was made. **Lab4 is not signed,
installed or run on Air**; no on-device packet, rootfs or Steam claim.

### Actual Steam/CEF observations

With packet support, the prior controllerxinput pipe assertion is absent in the
bounded host runs. A helper-specific loader log then proves missing libibus;
actual ldd additionally identifies NSS/NSPR/accessibility/XKB. Normal verified
guest apt installation supplies those and the previously missing SDL graphics
probe library (13.596s host only). No host packages, GPG/TLS checks or Valve binary
were altered. Keep the installed-package inventory and raw logs private.

Genuine steamwebhelper/CEF now executes, creates real logs and records
**BrowserReady**. A first90-second wrapper exceeds its cleanup bound and is
terminated at140.116s; this is observer termination, not a spontaneous client
crash. A second helper run finishes its92.572s display-session observation. The
same immutable packet-v5 binary was observed for a longer300seconds; wrapper
finishes at305.386s. Its actual1280x800 framebuffer shows Valve's
**Unexpected Transport Error:0x3009**, with restart/continue/exit choices. No
choice was clicked. This is a real Steam error window, not interactive login,
Library or Big Picture success. These UI observations use packet-v5; later final
contract/iOS artifacts also correct a full-and-closed poll mask and add bounded
unsupported-mode diagnostics. Do not silently equate their exact binaries.

CEF logs contain cpuinfo initialization and inotify/D-Bus warnings, but inspected
[Chromium PreSandboxInit](https://chromium.googlesource.com/chromium/src/+/refs/heads/main/content/app/content_main_runner_impl.cc)
logs cpuinfo failure without making it fatal. This source is a reference, not a
verified match to the precise bundled CEF revision. Do not claim the cpuinfo
message alone killed the renderer or is the0x3009 cause. BrowserReady and
WebUITransport.GetTransportInfo entries coexist with the real error dialog.
No credentials, Guard approval or account-cache transfer occurred.

### Next experiment and remaining gates

1. Preserve pending Air user-trust action; after confirmation collect Lab1 before
   upgrading only its isolated container. No repeated unchanged unlock/trust asks.
2. Use the final packet artifact's bounded conversion/reopen diagnostics to rule
   out that documented limit in0x3009. Trace categorical WebUI/client transport
   establishment/close status and specific socket/FD-passing failures. Do not
   restart blindly, change timeouts or select Continue Anyway as a substitute.
3. Continue actual rootfs/X11/RFB integration in the iOS Lab as useful alongside
   compatibility diagnosis, then qualify real Air input/login/Library/BPM. Physical testing
   remains required; host screenshots and compilation do not satisfy it.
4. Compatibility discovery, licensed Madeira handoff, game/return, coexistence,
   memory/performance and repeated stability all remain unverified.

The user LaunchAgent readback now shows runs2, last exit0 and interval18300s;
this continuation prompt actually arrived and progressed source/build/test work.
Future scheduling through sleep/storage outages is not guaranteed. No success
sentinel was written and no scheduled task was stopped. Raw screenshots, logs,
package/rootfs payloads and signing assets remain outside Git.

Run4 source checkpoint: **7ae2fe5222f1d35f4b473fc563815129039518a0** (signed off). Final contract/iOS artifacts
are linked and hashed; actual Steam UI still reports0x3009, and Air trust/device
execution remains pending. All bounded host sessions ended; no stale PID action.

## Run5 — real Linux Steam login/input on the host; Air remains unverified

Baseline/source parent for this run: `d9142c3` on the isolated experiment branch;
LinuxRunner remains `d1419782da2e299fe22f1ddb85c70ae3d1e276b1`. Storage UUID and
migration completion, branch/origin/worktrees and remote state were checked before
writes. The production/main worktrees, FEX, Valve binaries and installed apps were
not changed. Exact generated-source, archive, executable and private evidence
hashes are in the adjacent EVIDENCE.json. The recurring task remains active.

**Observed failure and discriminating evidence.** The final packet adapter ran
for240seconds without its unsupported conversion/reopen diagnostics, but genuine
CEF's two local WebSockets repeatedly failed with HTTP403. Fixed read-only CEF
queries showed valid numeric transport ports and boolean key presence; request
metadata showed the expected Steam origin/localhost/Upgrade values. No key,
cookie, auth header or WebSocket payload was returned or logged by the diagnostic.
Steam's own `GetIPCConnectionDetails` logs identify `lsof` exit127. Read-only
inspection of the exact official steamui.so confirms that it invokes lsof to find
local socket ownership. Neither that check nor any Valve code was patched.

**Hypothesis and minimal change.** Installing genuine Debian
`lsof4.99.4+dfsg-2` and its dependencies through normal verified apt changes127
to1: the command now exists but finds no socket owner. LinuxRunner had neither
TCP proc tables nor nonzero socket inode identities. The isolated copied-archive
adapter now assigns stable identities to actual guest open descriptions and
supplies their real native TCP endpoints/state through proc TCP tables and the
per-PID net view. Dup/fork shares description identity; retained fd tables and
references protect collection against closes. Native host PIDs are never reported
as guest ownership, no fake Steam peer is inserted, and Steam still makes its own
connection and authentication decisions.

The interface follows the relevant
[Linux TCP proc format](https://kernel.org/doc/html/v5.12/networking/proc_net_tcp.html).
Debian's unmodified lsof initially caught an IPv6 header error; the
[lsof4.99.4 parser](https://raw.githubusercontent.com/lsof-org/lsof/4.99.4/lib/dialects/linux/dsock.c)
expects `remote_address` for IPv6, rather than IPv4's `rem_address`. Correcting
that contract removes the warning and makes the actual IPv6 owner test pass.
This is intentionally partial ABI support: guest-visible descriptor-backed TCP
only, no orphan/TIME_WAIT inventory, UDP or complete network namespaces. Queue,
retransmission and timer accounting are not implemented; their columns are zero
placeholders and cannot support performance conclusions.

**Tests and corrected test setup.** The checked-in `test-tcp-view.sh` reproduces
base exit1 (4PASS/13 expected FAIL), then17 positive TCP checks. Its optional
Debian test executes the actual lsof in the ARM64 guest and checks the actual
owner PID over IPv4 and IPv6, giving19PASS. Changed units use ASan/UBSan; this is
not whole-runtime instrumentation. The inherited socket unit still emits20
compiler warnings; the new net unit compiles with Werror. Correctly linking the
embedded Lab adapter against the new archive also gives all16 ordinary ELF
controls, diagnostic bridge exit125, repeat-start EBUSY and protocol-sanitizer
success. A prior CLI fixture lacked the embedded urandom/bridge nodes and failed
those two requirements; it was the wrong adapter for that regression test.
All15 Python tests (including6 X11 observer boundaries) pass. The first new shell
runner exposed Bash3.2's empty-array/set-u behavior; an explicit numeric CPP gate
fixes the runner, and the complete fresh-output reproduction then passes.

**Actual Steam UI evidence.** One sanitized Steam observation stalled before
UI/debug-page creation and exceeded its cleanup bound (410.776seconds), showing
an inherited proc task-list alignment diagnostic. Its cause was not established.
A separate unsanitized artifact with the same final TCP semantics then records
HTTP101 on both genuine transport WebSockets and displays Valve's real Steam
login window. A native pinned RFB client clicks the actual account field, types
`ideck-input-control`, then Ctrl-A/backspace removes it. Separate real frames
visually confirm both states. No login was submitted and no credentials/Guard or
account-cache transfer occurred. The bounded360second display session ends0 at
366.673seconds. This is a **host interactive login-form milestone**, not account
login, Library, Big Picture, iPad execution or repeated stability.

Raw frames contain a transient official login QR challenge; they and all raw
logs/payloads remain private. Public evidence records their hashes only. CEF debug
is explicit `--cef-debug` and defaults off. Steam's verified endpoint on this Mac
is IPv6 `[::1]:8080`; unrelated Docker owns IPv4 port8080 and was left untouched.
A diagnostic that connected to IPv4 first was observing that other service,
not a Steam failure. One earlier manually ended observer left X99 artifacts,
which were removed only through the guest filesystem after verifying the private
root was stopped. The observer now refuses existing X99 state instead of silently
reusing/deleting it. A bounded native stack sampler timed out without producing
an artifact; a resource sample found the observer already ended. No stack or
CPU/memory measurements are claimed from those attempts.

**iOS implementation/build boundary.** Unsigned isolated Lab5 adds
`linux-tcp-diagnostics`, TCPRootFS and last-tcp-probe.txt. Build gates
`LINUX_LAB_PACKET_PIPES=1 LINUX_LAB_TCP_VIEW=1` overlay only copied generated
archives; the default ordinary target path remains unchanged. The iOS SDK lacks
macOS's tcp_fsm header, so the adapter translates the documented BSD numeric
state ABI explicitly using the public TCP_CONNECTION_INFO API. Actual iPad
behavior is still a required control. Full Xcode build passes; the final Mach-O
contains TCP_V1, packetV3, dirfdV3 and diagnostic-argument markers, and the exact
embedded TCP ELF matches the host-executed control by SHA256. Lab5 is NOT signed,
installed or run on Air. The installed old Lab1's single current probe read still
returns missing-file CoreDevice7000, with no user trust confirmation. No repeated
launch/install/trust prompt or Mac unlock request was made.

**Next experiment.** Bring a clean portable fakefs plus genuine X11/RFB/Metal and
input into the isolated iOS frontend, then run the controls and genuine UI on Air
once the user-only trust boundary is satisfied. Inspect fakefs metadata, symlink
confinement and hardlink preservation; do not copy a live root, the host's browser
session/QR state or another app's login data. Only user interaction with the
actual iPad Steam interface may establish account login. Steam-discovered Play,
licensed Madeira execution, shutdown/relaunch, game return and repeated physical
stability remain unimplemented/unverified. No GO assessment or success sentinel
is justified yet; continue the experiment.

Run5 implementation checkpoint: **fef1bb73214e223f4e5d641422236f29198ede4c** (signed off). Genuine host login/input and unsigned Lab5 are evidenced separately; no on-Air success or final GO.

## Run 6 — physical Air execution and complete frontend integration

Parent `9e1bc1a0bf317aaa7cc660ac2d53f25aa6dfba34`; remote main remains
`2ac39beff91251d36f3ad6331d3f8402b3c10e18`. LinuxRunner and nested
libarchive remain pristine at the pinned revisions in EVIDENCE.json. The
verified external volume and all unrelated worktrees are preserved. Existing
Air-authorized `.freshtest` development identity is reused only for this isolated
Lab, with the same app container; production iDeck and Mac Allocator are untouched.
Fresh Air details report iPad13,1 / iPadOS27.2(24B119). User explicitly completed
developer trust. No Mac GUI/unlock, credential entry or security bypass was used.

**Implementation.** Added a stopped-fakefs portable-image exporter, preserving
Linux metadata/symlinks/hardlinks, refusing native-parent traversal and inconsistent
hardlinks. It excludes runtime state, host bindings and Steam browser/account/cache
locations. The source must still be known unauthenticated; guards do not prove
absence of all secrets. Two missing non-executable PAM/pam manual symlink payloads
are explicitly recorded/omitted; missing required files refuse export. The clean
image is2008460373 bytes,27834 entries/4028749898 payload bytes, SHA256
`07676e4c820a7cca7c9db46df80e681de6a294260e37273a9f1a8e0c479921ea`.
It retains578 copyright files and is private, not committed/distributed.

The native importer verifies the build-pinned SHA256 through an owned immutable
stage, imports fakefs with the pinned BSD libarchive, restores native cwd, and
publishes only a complete root. Existing roots require the same pin and remain
writable for this app's own updates/login. Failed installs clean only their own
stage, preserving the original image and existing roots. Actual host import,
cwd restore, root reuse and wrong-pin preservation controls passed. This host
import used system libarchive; it was not evidence for the iOS static dependency.

Explicit `linux-steam-desktop` plus build feature flags adds genuine Xvfb/X11,
authenticated app-local RFB into pinned LinuxRunner Metal display, absolute touch
and native keyboard forwarding without native account fields/key logs. It starts
Valve's original ARM64 Steam in desktop mode with remote CEF debugging disabled.
RFB readiness checks the guest VNC PID's real TCP listener using genuine lsof,
rather than kill0 or a stale file. No hardware controller or physical input success
is claimed. Linux shutdown/reuse and Madeira integration remain incomplete.

**Failure1: X11 native IPC.** The first host embedded clean-root test could not
connect to X11. A direct test using pinned realfs_mknod proves FIFO creation
changes native cwd. A relative socket prefix then returns ENOENT; an absolute
prefix survives and transfers real data.8 checks pass. The native adapter now
uses an absolute prefix and verifies same-inode /private/var→/var alias only if
needed for Darwin's104-byte sockaddr_un limit; oversized paths fail closed.
No kernel/FEX patch. A one-variable host retry advances beyond X11, then exits
through Valve InternalAPI_Init failure. No login frame was captured from that
clean embedded run. Exact-environment ldd separately reports unresolved
ARM64 `libnm.so.0`; this is a dependency finding, not yet a proven sole cause.
The generic Valve32-bit-dependency message does not identify the actual ARM64 ABI.

**Failure2: native startup.** After trust, actual Lab6 PID2604 stops in UIKit
`EvaluateRuntimeIssueForNoSceneLifecycleAdoption`, SIGTRAP on the main thread,
before any Linux result. Lab8 adds UIApplicationSceneManifest plus UIWindowScene
connection and retains the single controller/runtime across reconnects. Full
build, final Scene symbol/pin, existing-profile signing and deep-strict checks
pass. Actual Air Lab8 TCP control exits0 with17 PASS and visible real result UI.
This is device execution; it does not prove Steam UI. Apple documents this SDK
requirement at https://developer.apple.com/documentation/technotes/tn3187-migrating-to-the-uikit-scene-based-life-cycle .

**Failure3: full image import.** Air Lab8 verifies the image but fails import.
Lab9 adds categorical import type/code/source-line/cwd metadata. Actual result:
archive error type0, code79/EFTYPE, copied tools/fakefs.c line251 (header iterator
stops before EOF), cwd restored. A fixed tiny UTF-8 PAX fixture against the SAME
pinned no-iconv libarchive reproduces ARCHIVE_WARN(-20)/79 in C/US-ASCII locale:
`Pathname can't be converted from UTF-8 to current locale.` The system library
control accepts it in both locales, explaining why the earlier host import was
insufficient. With en_US.UTF-8 the pinned library succeeds. A proposed thread-scoped UTF-8 locale passes six host sanitizer wrapper checks,
but actual Air Lab10 cannot create that locale (`utf8_locale_ready=false`), so no
import is attempted. That implementation is rejected/removed rather than assuming
macOS locale availability on iOS. The static dependency was not sanitizer-built.

A second fixed archive discriminator preserves the already validated UTF-8 filename
bytes using per-entry PAX `hdrcharset=BINARY`. Pinned no-iconv libarchive in the C
locale accepts this entry and returns the exact byte path/payload/EOF; seven native
ASan/UBSan wrapper checks pass. The same global PAX flag alone still fails and is
explicitly tested. No charset warning is ignored and no names/content are dropped.
The exporter now declares raw filename bytes per entry. A new private image is
being generated from the hash-verified original image, changing only these PAX
headers. The Air import remains pending until the new image's actual receipt.

**Checks/limits.**24 Python regressions pass, including9 portable-image tests;
8 real socket/cwd checks;7 archive-header wrapper checks; full iOS builds8/9/10 and strict
signing pass. Raw image/packages/profiles/device logs/screenshots remain private,
with selected hashes in EVIDENCE.json. No FEX/Valve/vendor/main edits, no game,
authentication or full stable-success claim. Next build/deploy the byte-path image and read its import receipt and
actual guest logs/display after the byte-preserving image, then isolate the real Steam dependency/startup failure.

**Actual Air11 result.** The byte-path image SHA256
`8afdfb2b9dfa76eef305865ec64994451a7cf953fd1bc2eb3a53fd10d066d84a`
is2013920423 bytes,27834 entries with the same4028749898 payload bytes. It changes
only per-entry PAX headers from the verified original. Lab11's actual current-pin
receipt records `imported=true`, `cwd_restored=true`, error0. The genuine Linux
Xvfb/x11vnc framebuffer appears through native RFB/Metal (black desktop/cursor).
Actual Valve ARM64 Steam runs update/verification and accesses the official manifest,
but XOpenDisplay fails even while VNC's earlier X connection works; no login success.

**Failure4: C path ownership.** Native `fileSystemRepresentation` bytes were
stored across the frontend autorelease pool, despite retaining the NSString.
A native host ASan fixture reproduces heap-use-after-free on the same lifetime,
exitSIGABRT. Apple explicitly requires copying these bytes outside their memory
context. The adapter now malloc-copies the validated absolute prefix for the
single native runtime lifetime. No unsafe all-descendant free/teardown is claimed.
Nine real Darwin socket/cwd/owned-prefix wrapper checks pass with ASan/UBSan.
Actual Lab12 advances beyond XOpenDisplay to the same InternalAPI_Init failure
as the clean host root. This supports the X11 ownership repair, not UI success.
Final signed Mach-O contains the actual owned-prefix helper symbol.

**Next dependency discriminator.** Exact ARM64 steamclient.so ldd under the
production environment reports missing `libnm.so.0`. Added explicit Lab-only
`linux-steam-install-dependencies`: normal signed apt install of pinned
`libnm0=1.52.1-1`, followed by exact-environment ldd and fail-on-missing check.
It never accepts a guest command, bypasses apt authentication or accesses account
state. The first host control installs the package but exits100 because the clean
image omits var/log/apt. Creating the normal log directory fixes this separate
packaging precondition; the same production control then exits0 and real ldd
resolves libnm0 with no missing entries. Actual Lab13 final build, final helper
link/sign/deep-strict and device install pass; explicit dependency control is
launched on Air. Read its result before a fresh native lifetime's Steam launch.
No interactive Library/BPM, controller, Madeira game or return success yet.

**Actual Air13 dependency result and active Steam run.** Normal Debian HTTPS
package acquisition/install completes, then the ldd/marker control exits0 with
`dependencies-complete=PASS`. A missing PTY log warning remains; no error was
ignored by the script. Only this completed diagnostic native lifetime is ended.
The same signed Lab13 is relaunched with `linux-steam-desktop`, retaining the
same image/root. Actual new steamwebhelper reaches CEF/browser initialization;
the previous InternalAPI_Init fatal is absent in the current sample. The frame
is still a black X11 cursor desktop, not an interactive Steam login. Keep this
active session for bounded observation before any restart or speculative patch.

Final regression: ordinary host16 ARM64 controls plus diagnostic125 wrapper,
protocol ASan/UBSan and6 package tests pass. The final signed Lab13 Mach-O
contains Scene/TCP/packet/dirfd/frontend markers plus the owned-prefix helper
and fixed dependency mode; source and artifact hashes are in EVIDENCE.json.
No final GO/Library/BPM/game/return/stability claim is justified.

Run6 implementation checkpoint: `d8650325a90534452317e0b13d0c40a41e626e38` (signed off). Current real CEF logs
record BrowserReady65536 and popup/BrowserReady131073, but the actual collected
frame still does not show an interactive login. Preserve this session; neither
BrowserReady nor this checkpoint establishes UI/Library/BPM success.

**Visual milestone / current human boundary.** Inspection of the13:57 private
`frontend13-later.png` confirms the actual official Steam login window on Air:
account/password controls and genuine Steam QR challenge. The previous text entry
was written before that frame was viewed and understated this result. This is a
real login-window display, not yet verified input or successful authentication.
User has been asked to authenticate directly via the genuine interface/Guard.
Keep this exact native session alive; no restart or credential automation. Once
the user acts, do not export/copy this root or login state to another installation.
Raw QR frames remain private; public evidence is hash-only. Library, BPM,
licensed Madeira launch/return and repeat stability still remain open.

## Run 7 — prepare safe Linux-to-Madeira lifecycle boundary

Parent `a894282f73865786a1d0e2bec9f7feb1a2ab5750`; branch/origin/main and actual
external mount UUID revalidated. The previous goal turn made actual progress
(Air genuine Steam login-window display). Fresh CoreDevice process inspection
confirms the same installed Lab13 session still exists. User login/Guard question
remains pending. No new device installation, restart, key entry or auth inspection
was performed; preserve that session. New work is independent host/build evidence.

**Observed failure/hypothesis.** `ideck_linux_lab_run()` joins only the initial
thread. Its `guest-exited` stage therefore cannot authorize native game handoff.
A new freestanding ARM64 ELF forks a child, handshakes, then exits its parent.
The native adapter returns0/guest-exited while the real child is still in the
virtual task table and writes a second marker two seconds later. This directly
reproduces the lifecycle gap, without Steam/account/game resources. A separate
fresh-root control signals only the virtual Linux namespace from its parked
PID1 context; the child exits with signal15 and cannot write its late marker.
No Darwin PID/process or active device session is signalled by these controls.
Neither case removes the one-native-runtime guard: repeat start still returns-16.

**Minimal instrumentation.** Optional `LINUX_LAB_GUEST_LIFETIME=1` compiles a
pinned pristine kernel/task.c copy into a new archive. Pending starts are counted
BEFORE pthread_create (covering queued threads); failed creation retires the
reservation. The outer task_run_current cleanup retires successful starts AFTER
nested TLB/fiber cleanup. The manually created initial embedding thread reserves
on the same contract. Underflow invalidates the count rather than advertising0.
The original vendor/base archive is hash-checked and unchanged. No FEX, CPU/JIT,
Valve, stop/restart or gaming-path semantics are changed. Default builds disable
this feature and the query reports-95/unsupported, not a false clean state.

**Discriminating checks.** Real ARM64 observe/signal controls now see the native
count remain1 after initial exit and drain0 after child cleanup. Standard16 ELF
controls (including real clone/thread/futex and diagnostic bridge roundtrip) pass
against the copied archive. A separate explicitly HOST-ONLY negative archive
returns EAGAIN from child pthread creation: the ELF exits512, as expected; kernel
rollback leaves no live guest tasks or native reservations and restart stays-16.
The test passes by recognizing that failure, not by calling its guest a success.
The changed task unit and control wrapper are ASan/UBSan instrumented; all other
static dependency units are not. Python24 regressions pass. Default-feature
runtime and full iOS builds are verified separately; final results/hashes are in
EVIDENCE.json. An initial harness-only macOS Bash3.2 empty-array/set-u error was
corrected by passing an explicit0/1 compiler definition; no runtime claim was
based on that failed invocation.

**Final artifact boundary.** Unsigned physical-arm64 Lab14 builds with tracking
and with default flags off. The first tracked artifact dead-stripped the unused
query; adding a categorical `last-runtime-session.json`/dependency-session count
consumer retains the real query and hooks. Final Mach-O symbols and lifetime
marker are inspected, not inferred from compile output. Tracked Mach-O SHA256
`9e3d7020a5599181f46aea8d8c237e4733fac72d006e33878f2e703341247f75` is preserved
in private `run7-tracked-unsigned`. Lab14 is NOT signed, installed or on-Air tested;
the existing Lab13 login is preserved.

**Limits/next experiment.** Zero tracked guest entries is stronger than initial
process exit but still does not prove every native TLS destructor, VM mapping,
background service or Mach handler is safe for Wine/FEX. No callback grants Wine
launch permission, no reusable restart is enabled, and the compatibility bridge
still returns diagnostic125. After human genuine Steam login/input qualification,
verify Library/BPM and Steam compatibility-tool discovery; separately measure full
native cleanup/VM/signal ownership before actual Madeira startup and return.
No combined Wine/MSC binary was distributed. No game/return/repeat-stability
success or scheduler-unload sentinel is justified.

Run7 implementation checkpoint: `09d23478c611b6193f4e12d691d63c2d89e00bbd` (signed off).
Installed Air Lab13 remains run6 code `d865032`; the new Lab14 is unsigned/build-only.

## Run8 — real tool installation and preserved Air login

Parent `310c6a85a03762f297d6395e97fda31ed4b6a26d`; external mount, branch, exact
origin/remote main and experiment state revalidated. Same physical Air13 native
process identity and actual15:15 screenshot show genuine Steam login with empty
credentials/expired QR, not authenticated Library. Human login/input question
remains pending. No app upgrade/restart, credential action or account-state copy.

**Failure/hypothesis/test.** The frontend lacked actual custom-tool installation.
An opt-in preboot fakefs/VFS installer now takes only the signed native bundle's
bounded ARM64 ELF and two VDF assets. It installs a complete versioned directory
before any guest tasks run, reuses only exact matching files, rejects symlink
parents/non-init callers, and preserves conflicts or an existing staging area.
It cleans only files created by this attempt. Publication relies on that sole
preboot writer; generic rename is not an adversarial cross-host no-replace API.
The six real VFS control modes cover24 checks under wrapper/installer ASan+UBSan;
the static dependency is not fully instrumented. Actual installed ARM64 helper
execution on the separate unauthenticated host root returns diagnostic125,
outer shell0 and exactly one native bridge request. Synthetic AppID480 is merely
a contract fixture. No Steam-discovered Play, owned game or Wine session exists.

`LINUX_LAB_COMPAT_TOOL=1` requires frontend opt-in; default0 leaves runtime
behavior disabled. `linux-steam-compatibility-diagnostics` is explicit and
conflicts with other launch modes. It reports only numeric categorical results
in `last-compatibility-control.json`, with the fixed guest diagnostic result in
`LinuxSteamRootFS/data/tmp/ideck-compatibility-results.txt`. Bundled NSData assets
are held through the asynchronous native lifetime. The VDF leading slash in
`/ideck-madeira %verb%` follows Valve's install-relative Proton toolmanifest
convention; it is not an arbitrary host shell path. See the primary
[Valve ARM64 tool manifest](https://github.com/ValveSoftware/Proton/blob/experimental_11.0/toolmanifest_arm64.vdf).

**Actual frontend boundary.** One real host Steam/X11 discovery attempt used only
a stopped, separate unauthenticated root. Its180-second observer plus50-second
grace terminated its owned native child, status-15; that is not a Steam crash.
No tool-discovery or interactive UI success was obtained. Current Air13 remains
the stronger real login-window evidence. No diagnostic patch was inferred from
D-Bus/Vulkan warnings.

**CLI display discriminator.** A new host-only bounded public usbmuxd observer
supports only ListDevices and Connect to the exact selected device/app port5993,
with ephemeral Mac127.0.0.1 listener, backpressure and byte/time bounds. It never
reads pairing records or changes trust/security/locks. The generated app-local
RFB display password is private and distinct from Steam login. Both ordinary and
shared ClientInit attempts were rejected by current13's exclusive server;
zero frame/input was delivered and its original native viewer remained active.
A separate host-only2x2 RFB wire fixture proves shared ClientInit1 is actually
sent; it is not device or Steam UI evidence. The optional future-build
`LINUX_LAB_SHARED_DISPLAY=1` adds genuine x11vnc -shared, default0. This flag is
not deployed or device-validated. No LLDB attach or guest pointer/key action was
performed; supported CLI debugger help alone was inspected.

**Build/regression evidence.** Full unsigned physical-arm64 Lab15 feature build
passes. Final Mach-O actually contains installer/runtime entrypoints and shared
command; its helper SHA256 exactly matches the host-executed installed helper.
Artifact is saved privately in `run8-lab15-unsigned/LinuxLab.app`, NOT signed,
installed or on-Air run. Full flags-off build passes; installer symbol/shared
command absent. Diagnostic assets remain bundled but inactive (an initial test
incorrectly expected them absent; the observation was corrected, not hidden).
Ordinary16 real ARM64 controls, diagnostic125 wrapper, protocol sanitizers,
6 package checks and34 Python tests pass. No FEX/Valve/vendor/game/main edits.
Hashes for source dependencies, receipts and private evidence are in EVIDENCE.

**Reproduction.** With the pinned prepared external artifacts and toolchain,
run `tools/test-tool-install.sh` using a NEW `LINUX_LAB_TOOL_OUT`. For the actual
installed-helper experiment, compile `tools/tool-runtime-control.c` with
`app/{LinuxLabRuntime,LabDeviceFS,LabBridge,LaunchProtocol,ToolInstall}.c`,
`IDECK_LAB_STEAM_FRONTEND=1`, `IDECK_LAB_COMPAT_TOOL=1`, `GUEST_ARM64=1`,
`ENGINE_ASBESTOS=1`, `ISH_INTERNAL=1`, the pinned host include/build directories,
the copied TCP/packet libish.a and original libish_emu/fakefs/sqlite3. Run it only
on a stopped unauthenticated host fakefs: arguments are root, own resource folder,
absolute guest socket prefix and `diagnostic`. Do not use/copy the active Air root.
For Lab15 build, use the existing build-lab.sh/toolchain/root SHA8afdfb2b... with
frontend, packet, TCP, lifetime, compatibility and shared-display opt-ins. No JIT
is required for these interpreter controls. Actual logs/commands belong privately.

**Next boundary.** User completes genuine Steam login/Guard and qualifies actual
input, Library/BPM. Preserve current session until then. Once it ends, qualify
optional installed-tool diagnostic on Air, then actual Steam discovery/Play.
Full Linux/native cleanup, legitimate Madeira authentication/game launch and
same-app return remain required; diagnostic125 and zero live-counter are not
permissions to remove existing single-lifetime guards. No STABLE_SUCCESS or
combined converter-linked binary distribution is justified.

Run8 implementation checkpoint: `e61ed82a3c8075e62b3c8eb88fb58b3061868693` (signed off). Actual installed
Air13 remains run6 code; Lab15 is an unsigned saved build only.

## Run9 — native signal state outlives all guest entries

Parent `c59f16aaab1e3b3353197ec30790f9b1cced7a3d`; exact external volume, branch,
origin and current main/experiment remote revisions verified. Fresh CoreDevice
shows the same Lab13 executable/process alive. User login/Guard reply is still
pending; no device input, restart/upgrade, auth inspection or debugger attach.
The preceding goal turn made actual source/build/bridge progress; this turn adds
a concrete handoff failure discriminator, not a completion claim.

**Observed failure and hypothesis.** Pinned kernel/init.c installs native SIGUSR1
and ignores SIGPIPE in become_first_process. No inverse API is evident. Joining
initial execution, empty guest task table and even the run7 native lifetime count
may therefore leave process state unsuitable for a new Wine/FEX owner.

**Discriminating execution.** New HOST ONLY `tools/native-state-control.c` installs
its own sentinel native handlers/masks before calling the real ARM64 interpreter.
It runs the standard16-control guest, waits for no guest table entries AND zero
native reservations, then reads native sigaction (without logging addresses).
SIGUSR1 still matches the actual LinuxRunner handler; SIGPIPE is still SIG_IGN;
both previous actions differ. All8 ownership/lifetime/reentry observations pass,
standard16 ELF checks pass, native reentry remains-16. A separate injected child
pthread-start EAGAIN archive yields real standard-probe exit1/wait256; its zero
reservations/table entries still leave the same signal owners, all8 checks pass.
This negative control is expected guest FAILURE, not successful guest execution.

The first harness incorrectly reused wait512 from the older orphan probe and
failed its expected-status assertion. The standard probe's real failure wait is
256. This expectation was corrected and both cases rerun into a new output
folder; initial logs retained privately. No runtime fix was claimed from that
failed harness or from the corrected host control.

**Minimal patch/regression.** Only two standalone host tools are added. Wrapper
and copied task-hook units use ASan/UBSan; static remaining dependency units do
not. Original vendor/base archive, FEX, Valve, app target and active Air runtime
are unchanged. Reproduce with `tools/test-native-state.sh`, prepared host/lifetime
and explicitly negative HOST ONLY archives, LD_LLD and a NEW private external
LINUX_LAB_NATIVE_STATE_OUT. Hashes, exact archive pins and results are in EVIDENCE.
No extra Xcode rebuild or app installation is evidence for this host-only work.

**Next targeted change and limits.** A native signal ownership lease must capture
prior actions before Linux init, establish serialized full quiescence, reject
foreign-handler changes, and restore only owned state before any native game.
Never restore signals while a Linux guest can still run. This experiment does
not yet implement that lease, full cleanup, native restart or Wine coexistence;
those remain independent requirements. Actual human Steam login, Library/BPM,
Steam Play, legitimate game launch/return and repeat device stability are still
unproven. Preserve the existing one-lifetime guards and all working app data.

Run9 host-discriminator checkpoint: `6fb631d9acdb9ba3c0dae3dab1e015ad21487d42` (signed off).
Installed Air13 and saved unsigned Lab15 remain unchanged.

## Run10 — isolated native signal lease, fail-closed real-runtime control

Parent `72b6763a70ae7bed5751e23f3a9cee5a8e7315db`; storage UUID/migration, branch,
origin and clean prior checkpoint verified. The preceding goal turn made actual
progress by reproducing surviving signal ownership. Fresh exact Air identity and
15:27 physical screenshot confirm SAME Lab13 genuine login, empty credentials,
expired QR. The human authentication/input boundary is still pending. No device
input, upgrade/restart, password/Guard/auth inspection or debugger attach.

**Targeted implementation.** Separate NativeSignalLease.c/.h captures pre-Linux
native signal actions and records exact expected Linux USR1 and ignored PIPE
ownership. Operations belong to one native owner thread; other signal setters
must be serialized too, because POSIX sigaction has no atomic compare-and-swap.
Release requires the native caller's actually measured runtime-returned,
future-starts-disabled, guest-task/native-entry/other-worker0 assertions. Unknown
counts MUST stay negative. The current Lab has no complete other-worker census
and MUST NOT claim zero. This component cannot accept guest IPC readiness or
launch Wine, reset a runtime or authorize any game itself.

Before restoring either action it compares BOTH handlers, flags and masks.
Foreign-owner changes poison the lease without overwriting that policy. On
syscall/readback failure, including possible partial restoration, no retry or
clean-handoff result is allowed. Such OS failure paths are not fault-injected in
this run. A successful signal-resource release alone would still not prove full
VM/TLS/filesystem/Mach-state cleanup or restart safety.

**Tests and real-runtime discriminator.** Five real native OS policy-fixture
modes pass ASan/UBSan: exact original restoration/incomplete gates, claim conflict,
foreign handler, same-handler foreign mask and same-handler foreign flags.
Wrong-thread operations and unknown/incomplete counts are refused. These use
explicit component-contract fixtures, not measured Linux full-quiescence claims.
A separate control executes the real ARM64 standard16 probes and real lifecycle
archive. Guest table/count drain0; the lease records actual Linux handlers. With
other workers correctly UNKNOWN (-1), release returns EAGAIN and preserves BOTH
actual Linux handlers. Owned bookkeeping cannot be destroyed; it lives until
this one host test process exits. No Linux-runtime signal restoration, game
start or full native shutdown was performed. No claim of leak-free teardown.

A standalone iOS-arm64 object compiles with Wall/Wextra/Werror. The component is
NOT referenced by the Lab Xcode target and no app Mach-O includes this candidate.
Do not infer a deployed fix from that object. Installed Air13 and saved unsigned
Lab15 are unchanged. The optional native-state-control test branch leaves the
original run9 discriminator default unchanged; its regressions are recorded
privately. Reproduce with tools/test-native-signal-lease.sh, NEW private
LINUX_LAB_SIGNAL_LEASE_OUT; add LINUX_LAB_SIGNAL_LEASE_REAL_RUNTIME=1 plus the
prepared host/lifetime archive/LD_LLD to run the actual Linux refusal case.

**Remaining worker ownership.** Pinned source d1419782 also creates native
pthread providers in util/timer.c, optional kernel/guest_profile.c, fs/tty-real.c
and kernel/native_offload.c. The native-handler forwarding path also exists on Apple iOS; only macOS
posix_spawn is excluded there (run11 correction of the earlier stub inference).
This is not evidence that any other providers are stopped. The profiler sampler
has an unbounded loop when enabled. None of these are covered by the current
guest-entry count. Next measure/explicitly exclude each provider before enabling
lease integration. Do not use an arbitrary delay or assert count0 to hide them.

All source/receipt hashes are in EVIDENCE. No vendor/FEX/Valve, primary app/main,
account/game/save or security change; no compiled binary/rootfs/QR/raw logs in
Git. Bridge125 remains diagnostic. Actual human login, input/Library/BPM,
Steam-discovered Play, licensed Madeira game/return and repeat stability remain
required; no STABLE_SUCCESS or goal completion is justified.

Run10 component checkpoint: `9348bb8eebe9d4de2076f6f057c923e41e1cccd7` (signed off); unlinked and
not deployed. Installed Air13 and saved unsigned Lab15 remain unchanged.

## Run11 — tracked native workers and actual Air compatibility diagnostic

Parent `bc2bf2c9a1f4ecdb18c98fe840be7eb49b4f4067`. Storage, branch/origin/current
remote and prior user/session state revalidated. User explicitly resumed work.
No subagents or simultaneous runtime experiments. Four native providers now
have optional copied-archive pending-through-cleanup counters: real timers,
optional profiler, real TTY reader and native-handler output forwarders. The
worker counter snapshot is separate from guest entries, fails closed on invalid
accounting, and cannot authorize signal restore, Wine or restart. Provider error
handling semantics are preserved; ignored upstream timer/TTY start errors are
not claimed fixed. Original archives/vendor/FEX/Valve remain unchanged.

**Correction with compiled evidence:** !__APPLE__ stubs do not apply to iOS.
Apple iOS retains in-process native handlers and their forwarding workers;
only HAS_POSIX_SPAWN is macOS-specific. Actual iOS native_offload object contains
handler + worker-start references without posix_spawn. Earlier run10 inference
was incorrect and is corrected in resumption/evidence docs.

Seven host controls pass with sanitized wrapper/task/worker units (remaining
static archive not fully instrumented): concurrent roles including pthread_exit,
actual periodic timer/free, real TTY reader on this test process's OWN stdin pipe
with upstream cleanup/cancellation, real ARM64 guest exec of a fixed harmless
native handler with2 output forwarders and controlled exit37, actual optional
profiler still live after standard16 guest controls finish, underflow invalidation,
and explicitly HOST ONLY pthread EAGAIN reservation rollback. No terminal/security
settings or other process input is touched. Profiler is intentionally alive until
that one host test process exits, not cleanly stopped. Lab embedding does not
call the CLI profiler initializer. Actual iOS compilation rejects the HOST-only
failure-injection macro; that expected failure emits no object.

Full unsigned Lab16 feature build passes, worker marker/helper/query/report key
actually linked. First exported-only nm check missed the LOCAL runtime query;
full nm confirms it, without changing runtime/export policy for the verifier.
Saved unsigned Mach-O SHA04443ce0c80f0c5b62b72866aea03fe7bd8cb86eaa5a7b1a13bca91e9485ddd0.
Full default-flags-off iOS build plus ordinary host16/diagnostic125/protocol/
package6 checks pass; disabled count reports-95 rather than invented0.
LINUX_LAB_NATIVE_WORKERS=1 requires explicit guest lifetime tracking. It reports
linux_worker_entries categorically after sessions; no signal lease is linked.

**Actual Air sequence:** Fresh process3054 superseded old2676. It was initially
on home; activation WITHOUT terminate-existing kept3054 and showed a completed
ordinary16 diagnostic/status0. Therefore the old login wait was no longer an
active session. Existing exact Air/profile/certificate/expiry were revalidated;
disposable Lab16 signed/deep-strict verified and installed ONLY into the existing
isolated freshtest container. Same root/auth/game/save storage preserved; no
production/MacAllocator/phone app changed. Actual explicit compatibility diagnostic
PID3186 returns status0, native_bridge_requests1, native_guest_threads0 and
linux_worker_entries0. Guest installed-helper output diagnostic-tool-roundtrip=PASS.
This is synthetic AppID480/125, NOT genuine Steam-discovered Play or licensed game.

After identity-verified successful completion, a fresh explicit Linux Steam
frontend PID3190 starts. Shared authenticated local USB display observation now
succeeds alongside native viewer: actual1280x800 genuine account startup splash,
no mouse/keyboard/password/Guard automation. A selected account splash is not
successful authentication, Library/BPM or stable UI proof. Later observer reports
connection refusal; fresh authoritative CoreDevice lists NO Lab process, proving
3190 ended rather than treating timeout as termination. Current crash/jetsam file
listing contains no new matching report. Runtime-result file absent and private
guest stdout has no fatal/assertion; cause remains UNKNOWN. User was asked whether
they force-closed the app; question is pending. No blind restart or sole-cause
OOM/JIT/worker-counter conclusion.

Next discriminator is private native runtime logging: actual iOS compile uses
LOG_HANDLER_DPRINTF, whose pinned kernel/log.c writes fd666, while the Lab has
no connection for that descriptor. This explains missing native diagnostic
coverage, not the process exit itself. Preserve app/auth state, inspect delayed
exit reports, then bound a reproduction with native evidence. No new login
request unless actual genuine UI requires it. Controller/touch qualification,
Library/BPM, licensed Madeira game and return/repeat stability remain incomplete.
Source/artifact/receipt hashes are in EVIDENCE; raw logs/frames/QR/profiles stay
private outside Git. No success sentinel or goal completion is justified.

Run11 implementation checkpoint: `8eaf7b61703d77f8d206faafebb180a17da525d5` (signed off). Lab16 is actually
installed/device-diagnostic-validated; its first Steam process ended, cause unknown.

## Run12 — actual Air memory pressure and isolated page amplification

Parent6661cf39b42872795500d54b9c0173a560d0538f; external UUID/migration, branch,
origin/current remote, pins and unrelated worktrees revalidated. Same isolated
Air app/container/auth/root preserved, no new trust/login/Mac-unlock request.

**Observed failure and minimal diagnostics.** Steam process ended without a guest
result. Feature-flagged LINUX_LAB_NATIVE_LOG=1 redirects ONLY copied kernel/log.c
from the unconnected fd666 to bounded4MiB app-private0600 logs. Suspect auth/argv
keyword lines are omitted wholesale; raw logs remain PRIVATE regardless of this
filter. No typed-input trace, Steam stdout collector, new native thread, memory
limit change, assertion suppression, runtime restart or FEX/Valve/vendor edit.
Lab18 samples public self-task footprint/resident/virtual and iOS available-memory
at1Hz on the main runloop and records real memory warnings. Available memory is
an instantaneous snapshot, not reserved capacity or permission to raise limits.

Five host modes pass: privacy/cap, macOS public metrics, real ARM64 kernel events
with fd666 closed plus standard16 guest controls, nonprivate directory refusal,
symlink refusal. Logging/task/wrapper units sanitized, remaining static units not.
Default host16/diagnostic125/protocol/packages6 and full default18 Xcode build
pass. Final default Mach-O excludes the opted-in kernel bridge. Feature17/18 full
builds and final bridge/resource code linkage inspected; disposable exact-profile
signing/deep-strict verification/isolated install succeeded. Air17 diagnostic
returns0/request1/guest0/worker0, not a genuine Steam Play or game launch.

**Actual physical Air evidence.** Two17 Steam processes3308/3365 and18 process3571
ended SIGKILL9/no core dump. For18,111 actual self-metric samples reach footprint
3,004,584,152bytes with available1,683,240bytes, and4 actual memory warnings,
then SIGKILL. Footprint+available is about3.006GB on this4,056,186,880byte-memory
Air. This strongly supports memory-limit pressure, NOT a formal jetsam report
or proof of the exact allocating layer. Resident1,683,734,528 is a different
metric; no compression-only diagnosis. No new matching crash/jetsam report found.
Scene-based lifecycle callbacks were not yet logged: empty app_states cannot
exclude background transitions. Memory-warning callback was actually observed.

Official Activity Monitor45.976s trace finalized naturally but started AFTER3365
ended. All matching app tables are empty, so no per-app CPU/ledger results are
claimed. Attempted guarded SIGINT found the profiler already gone and sent no
signal. Current3600 is a DIFFERENT unclassified app instance; preserve it until
state verified. Old launch18-steam.json actually describes the completed Lab17
diagnostic3533. Its controlled upgrade termination is NOT spontaneous failure
evidence. Actual18 Steam is real-launch18-steam.json. The initially unchecked
shell dependency was corrected before the final successful18 installation.

**Next discriminating test already executed on host.** Pinned LinuxRunner makes
large private writable anonymous reservations lazy; first access materializes
each guest4KiB page with its own native mmap. Actual unsanitized interpreter
control on a16KiB-page Apple host writes/verifies IDENTICAL64MiB. A128MiB eager
reservation adds67,174,472byte footprint; a512MiB lazy one adds270,876,888bytes
(4.0324x), both guest0 and successful unmap. No Steam/account/rootfs involved.
This proves this allocation amplification in the control, not its entire share
of actual Steam memory. No allocator fix exists yet in this checkpoint.

Reproduce: tools/test-page-footprint.sh with prepared LINUX_LAB_ARTIFACTS, LD_LLD
and NEW external LINUX_LAB_PAGE_OUT. Next isolate a copied-memory.c feature flag
that materializes contiguous absent pages only inside BOTH the same native-page
group and same lazy reservation; retain existing data refcount lifetime, guest
protection, unmap/COW semantics and logical anonymous cap. Do not introduce
unowned shared slabs, blind mprotect/retry, global memory-limit or Wine/FEX edits.

Hashes/exact artifacts in EVIDENCE.run12. Private run12/raw logs/frames/profiles
stay outside Git. Native restart/signals/full handoff still unqualified. Genuine
Library/BPM/input, Steam-discovered Play->licensed Madeira game->return and
repeated stability remain incomplete; bridge125 is diagnostic, no STABLE_SUCCESS.

## Run13 — bounded lazy-page grouping and actual Air updater completion

Parent ca8216c; pinned vendor/base archives unchanged. The run12 real guest test
identified independent guest4KiB/native16KiB allocations. This isolated experiment
does not implement a shared slab allocator or alter FEX, COW, JIT, Valve or host
memory limits. Default-off LINUX_LAB_LAZY_PAGES=1 generates a copied memory.c
only after exact pinned-source checks. Under the existing write lock, a fault
materializes contiguous absent neighbors inside BOTH its aligned native-page
group and SAME reservation, stopping before any existing PTE. Original data
refcounts own the mapping until all its guest pages are released. Protection,
shared mappings and logical anonymous cap stay intact; this can materialize/charge
neighbors earlier, and does not cure overhead in independent COW/sparse paths.

**Discriminating tests.** Same unsanitized ARM64 interpreter64MiB touch/verify
now adds68,517,936bytes for lazy vs67,158,064 eager (1.02025x), compared with4.0324x
in run12. Actual base+grouped guest20-control contract passes: unaligned reservation
edges, demand zero, independent data, per-page protections/EFAULT, partial unmap/
hole/fixed replacement, COW child vs parent, and PROT_NONE reservation enabling
only first/tail pages without exposing adjacent pages. Both base+grouped ordinary
16 controls pass. Wrapper/grouped memory.c ASan/UBSan; remaining static units
not fully instrumented. No iPad or Steam semantics inferred from these host tests.

**Build/deploy.** Full feature19 Xcode build and final lazy/log/resource/scene
markers/symbols verified. Separate all-default-off full19 build passes, final
Mach-O lacks lazy/log bridge. Actual old3600 was resumed without restart and
visibly completed16 checks/status0 before upgrade. Matching existing Air/app/
certificate/profile/expiry checked; disposable19 signed/deep-strict verified,
installed ONLY same isolated freshtest container, preserving auth/root/games/saves.

**Actual Air19 process3625:** genuine updater UI is visible, completes extraction
and logs Update complete, launching Steam then Shutdown. Initial guest raw
10752 = exit42, guest/worker counters0, not native crash. During217s/220 public
self-metric samples peak footprint1,018,481,440bytes and0 actual memory warnings;
scene foreground/active logged. Prior18 had ~3GB pressure, but client/update
states differ, so do not claim a controlled whole-Steam percentage reduction or
stability. Source screenshot after update is black, NOT working Library.

Only AFTER verified exact3625/status42 completion was a fresh SAME19 native
post-update launch requested. CoreDevice10004 could not determine its PID;
subsequent authoritative list is empty and receipt stays3625, so no Linux crash
or successful new session is inferred. A plain launch AFTER verified absence
is the next discriminating action; do not assume it displays Library yet. No account
credential/Guard automation, root/cache transfer, existing working app overwrite,
Mac unlock request or live test interruption. Preserve its new identity and
collect real UI/input/resources next. Old last-runtime-session.json may be stale
until the fresh session returns; never replay it as current completion proof.

Reproduce copied archive with tools/build-lazy-pages.py and explicit new output;
use --sanitize for semantic controls, unsanitized for resource measurements. Run
tools/test-lazy-pages.sh with LINUX_LAB_LAZY_ARCHIVE and NEW external
LINUX_LAB_LAZY_OUT. tools/test-page-footprint.sh accepts optional
LINUX_LAB_PAGE_ARCHIVE and NEW output. Feature iOS build adds
LINUX_LAB_LAZY_PAGES=1 to existing documented frontend/lifetime/worker/log flags.
Scene lifecycle logging is diagnostics only; no foreground/background policy edit.

Exact receipts/hashes in EVIDENCE.run13; private raw artifacts not in Git. Native
restart guards and incomplete full shutdown remain. Bridge125 is diagnostic,
no real Play/licensed Windows game/return or repeated Library/BPM/input stability.
No STABLE_SUCCESS or combined-binary distribution/GO assessment is justified.

Run13 post-update update: the verified-absent plain launch succeeds actual3640
with fresh19 receipt (same install CFAF156B-6A09-41F4-AF18-0899415498BC). At78
samples footprint2.103GB/available903MB, no warning, guest black/cursor. Memory
still grows: updater success is not whole-client memory/stability success. Keep
this session active and inspect real UI/resources; no blind restart or sole
root-cause claim. Old10752 is previous3625 completion, not this process result.

## Run14 — actual CPU/classes and prepared CEF GPU-path discriminator

Parent9c69a1b. Run13 next Steam3640 was NOT stable:443.001s sample window,
footprint2,984,712,880/available21,554,512bytes,15 memory warnings then actual
SIGKILL9. Account shell/header visible, library content black before/after
Library/View clicks. Shared local display input was transported and cursor moved,
not useful interaction proof. Exact fresh Steam SetLoginState Success-OK at
2026-11-09T00:59:02 establishes saved legitimate login, no agent credentials/Guard.
Requested10s ActivityMonitor capture ended0.988152s Device disconnected, TOC only
kernel0; no app CPU results from that trace and no observer signal sent.

**Single diagnostic hypothesis.** New20 only adds public RUSAGE_SELF CPU totals
and existing pinned anonymous/Asbestos atomic counters to the private1Hz log.
No allocation/cache/cap/JIT policy edit or new thread. Counts are independent
noncoherent observations: anonymous guest pages are logical, code words exclude
block metadata/disconnected blocks, neither equals physical footprint. Five host
logging modes pass including real ARM6416 checks and initial zero counters/CPU
fields; changed wrapper/log/task units sanitized, rest archive not fully. Actual
flags-off iOS unit Werror/no Linux-counter dependency check passes, not a full
new default20 app claim. Full feature20 build/final counter/CPU symbols and markers
verified, disposable exact-profile sign/deep-strict/install preserved same Lab.

**Actual mode correction:** first20 process3801 visibly completed ordinary16
diagnostics instead of requested Steam; its low-memory samples are NOT Steam
measurements. Only after report/identity/screen proved completion was it retired.
Fresh3836 after verified absence runs real Steam, completes updater42/counters0
again (client logged prior unclean shutdown). No update/hash verification bypass.
Exact completion verified before retirement; fresh3845 after absence is current
real Steam. Source noarg still selects diagnostics; launch intent alone is not
proof of actual runtime mode. The uncommitted20 overlay was reconstructed from
parent+known file edits and labelled reconstruction, not a captured source snapshot.

Actual3845 by229.001s:647.189688 cumulative CPU seconds (~2.82614 native core
equivalents), logical anonymous582571pages, translated words105855912bytes/
608461blocks/13tables,17 cap/12 pressure flushes, footprint2,271,353,136bytes,
peak2,406,455,288 and3 memory warnings. Busy computation is observed; no sole
cache, allocation or rendering-cause inference. Do not sum logical guest counts
as physical memory or advertise this as a stability/performance improvement.

**Prepared next discriminator21, not yet deployed:** current GPU log names
ANGLE/Mesa llvmpipe, a guest software GL path. Default-off
LINUX_LAB_CEF_DISABLE_GPU=1 adds ONLY Steam's own -cef-disable-gpu in this Lab.
The official ARM64 ELF contains that switch; binary unchanged. Production command
C string on/off compiles Werror and passes shell syntax (3fixedargv/switch0or1).
Full feature21 build and FINAL actual command/policy/CPU/class markers inspected;
immutable unsigned bundle plus existing-profile signed/deep-strict copy prepared.
No Wine/game GPU, FEX/Valve, sandbox/security/auth or assertion changes. This does
not establish the switch's effect or fix; actual helper flags/render/input must
be tested. Never replace active20's binary or terminate it just for a timeout.

Current actual20 PID3845/install9BB06401-21A9-40BF-A202-C0ACE2F64FA8, console18291,
private run14 active-session20-postupdate.json: REVALIDATE before action. Next
collect complete resource/UI/exit evidence, and only after session ends test21
against real Library and input. Keep auth/root/games/saves. No credential/Guard
automation or Mac unlock request. No JIT physical activation inferred from pinned
LinuxRunner host/Simulator documentation. GPU framebuffer Metal presentation is
separate from actual guest GPU acceleration.

EVIDENCE.run14 has exact hashes/receipts; raw logs/frames/rootfs/signing/Valve data
stay private. Full stable Library/BPM/input -> Steam Play -> licensed Madeira
game -> reliable return remains open, bridge125 diagnostic. No success sentinel,
goal completion, combined-binary release or scheduler unload is justified.

## Run15 — effective GPU-disabled helper; lower memory, black UI persists

Checkpointa395868. Actual20 process3845 eventually SIGKILL9:339s samplewindow,
2,988,678,120byte footprint/17,589,272available/26warnings,3.19native cores. Only
after authoritative absence installed prepared21 into same isolated container.
Steam3992 legitimately updates/exits42/counters0. Exact identity/completion
rechecked before retirement; verified absence then fresh21 Steam4025. Actual
helper01:59:12 has --disable-gpu and --disable-gpu-compositing, not just native
policy marker. No Valve, sandbox/security/auth/gameGPU patch or credentials.

Physical screenshots remain black guest/cursor, no working Library/login/BPM.
Before debugger attempt ~650s samplewindow stays~853MB/peak994MB,0warnings,
~0.215nativeCPU cores. This avoids previous pressure during observation but is
NOT a functioning UI fix. Client startup/update states differ; no controlled
whole-client speed/memory improvement claim. Preserve data, no retry/assertion
or memory-limit workaround.

**Failed stack attempt, material caveat.** Read-only authorized LLDB intended
to capture module/function names only then detach. SB device commands returned
Started rather than completed. One hyphenated script name was rejected before
execution. Standard CLI sequence then still reached state2(Attaching),0threads,
detachfalse; NO actual stack. Immediately later authoritative process list empty
and console SIGKILL9. This termination is confounded by incomplete debugger
attachment; NEVER classify as spontaneous Linux crash or memory-pressure event.
No password/Guard/guest-memory expressions or security/lock changes. No further
debugger attaches; next diagnostic runs inside app without attachment.

## Run16 — bounded nonblocking task diagnostics,22 built and installed

Parenta395868. New opted-in ideck_linux_lab_log_tasks runs every10s, bounded
first1024allocatedIDs/128rows. Trylocks protect task lifetime/general state;
busy locks are skipped and limitations explicit. Numeric tid/tgid, instrumented
wait, last syscall, cycles/fault counters only, writes occur AFTER kernel unlock.
No comm/argv/register/address or arbitrary memory reads, no new sampler thread,
allocation policy, runtime restart, signal/FEX/JIT/Valve/vendor edit. Last syscall
may have already returned and snapshots are not coherent stopped frames.
Stage<7 refuses not-yet-initialized table; flag-off stub is empty.

Five logging host modes PASS. Separate real ARM64 guest waits on fixed own-file
markers, touches/verifies64MiB and unmaps. Native tests prove startup refusal,
held-pids-lock refusal without recursive blocking, held task2-general-lock skip,
live/post-exit snapshots and new-row payload absence. Wrapper/log/task-hook units
ASan/UBSan, remaining dependency units not fully instrumented. First privacy
test wrongly searched unrelated PROCESS_EVENT address fields in whole log and
failed; corrected scope to LINUX_TASK* rows, reran NEW output, finalPASS. No
runtime privacy defect/fix claim from that test expectation.

Full feature22/default22 Xcode builds pass. Final feature actual task symbol and
numeric/GPU1 markers linked, default final lacks sampler/lazy/GPU1 payload.
Immutable unsigned saved, exact existing-profile disposable signed/deep-strict.
Only after authoritative4025 absence installed same isolated Lab22, auth/root/
games/saves untouched; fresh explicit Steam launch now requested after absence.
Actual mode/receipt/Air task rows not qualified yet. Interpreter noJIT.

Reproduce: tools/test-task-logging.sh with prepared LINUX_LAB_ARTIFACTS,
LINUX_LAB_LOG_ARCHIVE, LD_LLD, NEW external LINUX_LAB_TASK_LOG_OUT. Same documented
feature build flags;22 adds private diagnostic only, GPU1 matches21. Next verify
actual new native session and sampler output, finish legitimate updater42 if
required, then inspect CEF task waits/progress. No repeated debugger or active
session replacement just for timeout. Raw evidence hashes in EVIDENCE.run15/16.
No actual Library/BPM/input, Play->licensedMadeira game->return/repeated stability
yet; bridge125 diagnostic. Keep full objective/schedule, no success sentinel.

Run16 actual follow-up: fresh22 PID4056 receipt/mode verified.11 real numeric
task samples on Air and physical screenshot shows legitimate Steam updater
extracting package.110s resource window peak991791880bytes/0warnings. This
qualifies on-device sampler execution, NOT CEF/Library/login/UI stability.
Preserve this active updater until actual current completion is verified.
