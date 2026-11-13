# Linux Steam + Madeira on iPad: experiment log

Status (run41): genuine authenticated ARM64 Linux Steam Library/BPM was seen
on Air in runs16–17, but stable browsing and a licensed Madeira game/return loop
remain unqualified. Current50 rendered genuine Store, then actual native crash
proved an unchecked fork page-table allocation (pt_copy_on_write+232). Minimal
fork failure handling passes25 actual HOST kernel controls plus existing16ELF
regressions; full52/final Mach-O/deep signing pass, device upgrade in progress.
No on-Air52 result yet. Account/root/games/saves and production/main preserved.
The compatibility bridge remains diagnostic125; no claim of actual game handoff.
Read latest Run41 continuation/EVIDENCE/CONTINUE for current process and artifacts.
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

## Run16 follow-up — genuine Big Picture home on the physical Air

The updater4056 completed with raw wait10752 (exit42), no guest/worker entries,
and its own native exit record. Only after checking that completion and exact
identity was it retired; fresh22/4057 then started in the same isolated container.
Steam recorded a fresh saved-auth `Success-OK` at2026-11-09 02:19UTC. No agent
credentials, Steam Guard operation or authentication-cache transfer occurred.

Actual screenshots initially showed the desktop Steam header with black content.
A fixed click on Steam's own Big Picture icon opened genuine onboarding. A center
click and Return advanced Quick Access, an informational parental-controls page
(no setup/security change), and Have fun. The final Return displayed the genuine
Big Picture home: game cards, news, and Steam navigation prompts. The private
`run16/after-finish-guide.png` was visually inspected. This is real on-Air rendering
and scripted input evidence, superseding earlier statements that no BPM UI existed.
It does not qualify physical touch/controller support, Library/details navigation,
game execution, return, or repeated stability. An earlier changing-artwork/clock
screen was an inactivity screen, not successful navigation.

The last resource window covered1325.005seconds, with peak footprint2,887,719,792
bytes,483 memory warnings, and~1.975 native CPU cores on average. Requested
memory, resident memory and logical guest-page/code counters are distinct; none
alone identifies an allocating layer. One CoreDevice log copy failed while the
exact app remained alive and screenshots worked; that failure was not a crash.
The planned next Right-key action never executed because automatic approval
review hit a usage limit. That is a tooling boundary, not a Steam failure.

On Nov9 the old4057 was absent; the cause/end time is unknown. A newer4320 in
the same installed22 bundle was foregrounded without termination and actually
showed completed ordinary16 diagnostics/status0. Its current receipt and screen,
not the stale updater result file, established its mode. Only that completed
identity was retired before the next isolated upgrade.

## Run17 — measure discard requests before changing reclamation

Source parent82b78613d532cd5f33cecd81da4bda27bad25ee2. LinuxRunner and libarchive
pins remain unchanged. The host hypothesis is that guest `MADV_DONTNEED` may
retain native backing: pinned `kernel/mmap.c` zeros anonymous memory but does
not release its native pages. A real ARM64 control touches64MiB, discards it,
samples public self-task footprint, verifies zero contents, then unmaps. Both
eager128MiB and grouped-lazy512MiB reservations reclaim **zero bytes** at discard;
unmapping does reduce footprint. This is host evidence, not proof Steam issued
the same requests or that this is its sole memory problem.

The minimal patch is observation only. Default-off `LINUX_LAB_MADVISE_STATS=1`
requires `LINUX_LAB_NATIVE_LOG=1`. `tools/build-madvise-stats.py` verifies the exact
pristine dependency pin and generates a copied mmap unit that counts calls and
requested bytes, then calls the original syscall unchanged. Independent relaxed
atomic totals cover DONTNEED and FREE, without addresses, argv or memory contents.
Requested bytes include failed/repeated calls; they are not unique allocations,
successful operations or reclaimed bytes. No runtime memory-policy fix is made.

The counted host control records exactly one67,108,864-byte DONTNEED call in each
case; the existing no-discard controls record zero. Five logging controls and
ordinary16 tests pass. Wrapper/log/task/mmap observation units were ASan/UBSan
instrumented; the rest of the dependency is not fully instrumented. Full feature
Xcode23 builds, final linked symbols/marker checks and deep-strict signing pass.
The unsigned Mach-O SHA256 is
`1ea23c88804781364b36624c38b44ddf4f6475e6eed1850432cf868616594be6`.
Default-off iOS unit compilation passes; a full default23 app build has not run.
Exact source bytes captured immediately after compilation are hashed in EVIDENCE.

After verified completed4320 retirement and Lab absence, the existing authorized
profile was checked against the Air, app, certificate and expiration. Only the
separate `com.kuschqin.ideck.freshtest` Lab was upgraded to23. The same private
root/auth/games/saves remain intact. Actual23/4942 initially shows the legitimate
Steam package extractor; the first28second sample records seven DONTNEED calls,
6,795,264 requested bytes and zero memory warnings. This proves on-device request
observation, not CEF/login/BPM or a reclamation fix.

Reproduce the host discriminator with `tools/test-page-footprint.sh`, a NEW private
`LINUX_LAB_PAGE_OUT`, prepared `LINUX_LAB_ARTIFACTS`, `LD_LLD`, the generated
`LINUX_LAB_PAGE_ARCHIVE`, and `LINUX_LAB_PAGE_DISCARD=1 LINUX_LAB_PAGE_STATS=1`.
For the feature build add `LINUX_LAB_MADVISE_STATS=1` to the recorded22 flags.
Never overwrite an app or control binary being tested. The next discriminator
is actual post-update Steam request growth against footprint and usable UI.
Bridge125 still launches no game; Linux teardown, Madeira integration, reliable
return and repeated stability remain open. No success sentinel/unload is justified.

Run17 continued: own4942 native initial-child exit10752 and current result
zero guest/workers verified before retiring its completed updater. Fresh23/4952
then recorded saved-authSuccess14:10:01UTC. At181seconds, footprint2.362GB and
2,725 DONTNEED calls requesting1.021GB; zero warnings in that window. Genuine
desktop Steam header rendered but its main content remained black. A bounded
fixed Big Picture icon click is being tested; transport success alone is not UI
success. Preserve this current session. Full default23 Xcode build and final
absence of observation/lazy/GPU policy symbols/markers also pass. Its first
sandbox build stalled; only that own host build was stopped and rerun with
normal authorized build-service access, without touching the Air session.

Run17 navigation follow-up: the same actual23/4952 shows the genuine Big Picture
home again, preserving completed onboarding. Input eventually selects Ratatan,
then its real details/activity page, the Steam menu, and the full **Library,
All Games40 / Installed0**. Private screenshots are hashed in EVIDENCE. These are
real Library and scripted menu/input milestones; minutes of delay, incomplete
transitional areas, screensaver activation and memory warnings explicitly fail
stable responsiveness. At947seconds, peak footprint2,620,332,816bytes and820
memory warnings; cumulative DONTNEED requests2,198,466,560bytes. No Install/Play,
password, Guard or account operation was performed. Bridge125 is unchanged.

## Run18 — conservative whole-backing discard experiment

This follows actual Air23 discard/pressure evidence, not a blind allocation retry.
`PrivateDiscard.inc` is included only by an explicitly selected copied mmap unit.
A nonblocking write-lock attempt preflights at most64MiB and requires every page
of every complete backing to belong exclusively to this same guest address
space, with exact offsets/refcounts. Only writable private anonymous data without
file identity, CoW, shared, executable or retained references qualifies. Allocate
ALL new untouched anonymous backing objects before changing any PTE; then retain
flags, offsets, reservations and logical accounting, invalidate the translated
range/generation and release old backing. There is no MAP_FIXED, mprotect, cap
increase or shared/COW/file rewrite. A busy lock, unsupported/partial range or
allocation failure uses the pinned original syscall. Its existing fallback
semantics are preserved, not claimed fully Linux-conformant or repaired.

The normal and forced-second-allocation-failure host controls each pass22 checks,
including retained references, a busy writer lock, permissions, alias/CoW parent
preservation, reservations, all-before-commit failure behavior and100 discard
iterations with a concurrent native reader. The real ARM64 guest lazy20 and
ordinary16 regressions also pass. Affected mmap/memory/control units use
ASan/UBSan; the remaining dependency is not fully instrumented. The file-identity
negative is a declared metadata fixture, not a real-file I/O claim.

The same aligned real ARM64 64MiB touch/discard fixture shows original eager and
lazy controls reclaim0bytes. With the prototype, grouped-lazy backing releases
66,699,336bytes of native footprint before zero-content verification. A64MiB
subrange of one128MiB eager backing deliberately remains on the original path
and reclaims0bytes. This establishes a bounded host effect, NOT an Air/Steam fix
or proof that all actual Steam allocations qualify. Requested/replaced guest
bytes are distinct from native footprint and must never be reported as physical
reclamation totals.

Failed controls are retained: a file fixture initially kept anonymous metadata
while expecting file retention; corrected the fixture. A COW harness incorrectly
omitted the loader's retained executable description and faulted in fd_retain;
supplied a real kernel-owned no-I/O description. An initial Bash3 empty-array
nounset failure occurred before tests. A tight native-reader stress timed out;
the optimization now refuses a busy write lock, and the fixture uses the pinned
reader quantum yield. A subsequent byte assertion read twice across original
in-place zeroing and could reject old-then-zero; it now makes ONE atomic byte
observation, without claiming whole-range atomicity. Fresh final controls pass;
none of these harness failures is attributed to the actual iPad session.

Reproduce: `tools/test-private-discard.sh` with prepared artifacts, LD_LLD and a
NEW `LINUX_LAB_DISCARD_OUT`. The generator's `--host-private-discard` refuses iOS;
`--host-fail-second` is host only. The separate explicit experimental build option
is selected by DEFAULT OFF `LINUX_LAB_PRIVATE_DISCARD=1`, requiring request stats
and grouped lazy pages. Lab24 checks the linked marker and logs only numeric
replacement calls/guest bytes. Its first build lacked the CMAKE command and is
being rerun with the already prepared dependency. It has not been installed.
Preserve current actualSteam23 until verified normal session completion; do not
replace a live session merely to deploy a candidate. Ordinary main/apps, accounts,
rootfs and saves remain intact; no FEX/Valve/vendor/security edit or new JIT claim.
The licensed game/return cycle and repeated stable operation remain unimplemented.

Run18 build follow-up: explicit feature24 full Xcode build succeeds with prepared
CMake. The actual final sys_madvise disassembly calls the exclusive-discard path;
count/byte symbols, startup marker and log marker are linked. Unsigned Mach-O
SHA256 `6d2336843c0380dcf1b911dffe722da027fd425f59cb3c98bb41d2b94565e33d`.
Source bytes were snapshotted at compilation, and the disposable exact-profile
candidate passes deep-strict signing. Full default24 build and final absence of
experimental markers pass; incomplete opt-in flags refuse before building.
**Lab24 is not installed or device-qualified.**

The actual23/4952 executable was reverified at09:41EST. Steam Power selection and
Return did not establish a normal exit; the later frame shows genuine inactivity
artwork/Away. Preserve the session. Its private kernel log reached the4MiB cap
at the last1560second sample, so later identical copied metrics are historical
capped observations, not fresh resource/exit evidence. The old runtime result
10752/zero workers is updater4942's result and cannot authorize retiring4952.
No current-session exit or complete cleanup is inferred. Next obtain actual
normal completion/absence before the isolated upgrade; never replace a live
session for a prepared candidate or treat an observer timeout as termination.
Source progress remains uncommitted/unpushed during the weekday09 local window
required by AGENTS. Main and all other worktrees/apps remain untouched. Goal
remains active; no game/return or stable-success claim/sentinel is justified.

## Run19 — current-session health survives append-log saturation

The previous goal turn made actual progress: real Air Library40/navigation,
conservative host discard controls and staged signed24. At09:46EST the same
actual23/4952 executable was still present and its screen showed genuine Steam
Away artwork. No termination, installation, input, authentication or lock action
was performed in this run. Normal Steam exit remains unverified. User approval
was requested ONCE to end this specific active experimental session and upgrade
to the concrete signed25; the reply is pending. Do not repeat that question or
interpret elapsed time as permission. CLI-only operation remains required.

**Observed failure:** the4MiB append cap prevents fresh runtime resource/exit
observations during a long session, while an old unidentified updater result
looks like completion. Lab25 keeps the existing append cap and adds a separate,
session-specific health JSON under the validated native private diagnostics
directory. It contains bounded numeric data, PID/build/native-log identity,
monotonic sequence/time, public self footprint/CPU and phase/limited tracked
entry counts. Atomic rename replaces this small receipt every10seconds on the
existing main runloop even after the append log stops. There is no new sampling
thread, signal owner, runtime restart or guest memory policy. A held extra native
directory descriptor is observation infrastructure, not reclaimed Linux state.

A completed initial call and zero tracked entries do NOT establish full native
quiescence or permit Wine/restarting Linux. Health updates can stop when the app
is suspended or the main runloop is blocked; missing/stale health is not process
death or a guest hang. Atomic rename prevents partial reads but is not a power
loss durability claim. Only fixed stage names and bounded build/count fields are
accepted; arbitrary guest/user strings are not written. Foreign native processes,
first-use file collisions, symlinks and failed temporary creation are refused,
preserving previous receipts and unrelated files. Output is0600 in a0700 private
directory. Steam/dependency/tool result reports now use schema2 and include PID,
Build and native log identity, so an earlier updater cannot masquerade as current.

Seven host logging modes pass, including actual capped-log continuation,
invalid payload preservation, temporary collision, native-fork owner refusal,
unknown/invalid counter handling and100 atomic updates with concurrent readers.
The final private health JSON was independently parsed to verify PID/log-name,
stage, cap, sequence, self metrics and permissions. Ordinary16 real ARM64 guest
controls and the live task-snapshot wait/touch/unmap/lock-contention regression
pass. Observer/wrapper/control units use ASan/UBSan; other dependency units are
not fully instrumented. No on-Air health-file validation is claimed.

Full feature25 Xcode build passes. Final health symbols, result identity markers
and the existing discard marker are linked; exact source snapshot and hashes are
in run19/final-linked25.json. Unsigned Mach-O:
`9811a585ff1e43a28ce33d7f1e6363ee6e9ea1f2a601c773f31eb3c6760ea1aa`.
Existing exact Air/profile disposable signing and deep-strict verification pass;
signed candidate SHA256:
`ba05a3b0ca88943ec002dc2329a3dbf8cce877219afae2c61820e30ba108c9c0`.
Full default25 build passes and its actual final Mach-O excludes experimental
health and discard symbols/markers. **25 is not installed**, and24 remains an
immutable earlier candidate. Existing actual23/auth/root/games/saves are intact.

### Real default library differs from the original bridge fixture

Read-only actual Air metadata confirms one library at `/Steam`, with no library
at the planned `/mnt/ideck/SteamLibrary`. The compatibility log references our
custom tool, but retained log references are not accepted-discovery, Steam Play,
ownership or game-execution evidence. System/UI logs were privately copied to
investigate the Power action; fixed categorical filtering found no matching
recent rows, which proves neither that an action was absent nor that exit worked.

The old syntax parser only admitted the planned shared root, so a legitimate
`/Steam/steamapps/common/...` request would be rejected. **After building25**, the
prepared source26 parser adds exactly that default library root while preserving
same-install executable/working containment, traversal and prefix-sibling
refusal, bounded arguments and frame validation. ASan/UBSan hostile/truncated/
mutated-frame tests pass for both fixed roots, including spaces and cross-library
escape attempts. Guest helper, VDF, IPC version and diagnostic125 response are
unchanged. This is still syntax validation, not native path resolution,
authorization or game execution. The parser change is NOT in the signed25
artifact; source is bumped to26 to prevent confusing different payloads with25.
No26 iOS build or device validation has run.

Next: retain the live23 session pending the user's requested active-session
boundary. After a genuine end/absence or explicit approval to end that experiment,
install only the isolated signed25 and verify real health freshness, memory
replacement and interactive Library/BPM. Independent next bridge work is native
filesystem capability/path validation and a bounded launch lifecycle, followed
by real Madeira integration; do not present diagnostic125 as a game launch.
Main/other worktrees/apps remain unchanged. Changes stay uncommitted outside the
weekday22–08 window. No FEX/Valve/security edit, credential/Guard automation,
combined binary release, success sentinel, scheduler unload or completion claim.

## Run20 — native file capabilities and actual compatibility-device controls (Nov9)

The preceding goal turn made concrete progress: candidate25 health identity,
actual Air default library evidence and a two-root parser fix. This run resumes
that work, rather than repeating the completed ELF/login/UI milestones. Mount
UUID, origin/branch/worktree and live exact Air process were verified. Remote
main remains2ac39be and experiment82b7861; LinuxRunner pin d1419782 and all
other worktrees/working installations are unchanged. Lab23/4952 with executable
install UUID B265FEBE-DE84-4F31-AB6A-235C8BF6F8F8 remains live. No device input,
stop, install, restart, credentials, trust, account or filesystem change occurred.
The previous one-time question about ending that session and installing25 is
still pending; no reply is inferred from a continuation or elapsed time.

### Failure, hypothesis and smallest useful implementation

The real library is `/Steam`, and syntax validation alone cannot safely translate
a guest request into a native executable path. The new `GameFiles` component
copies/validates the fixed request, selects exactly default or planned shared
library, and opens path components relative to trusted app-owned directory
handles. It never follows native symlinks, changes cwd, creates game storage or
executes commands. Executables must initially be singly-linked, native-owned
regular `.exe` files with limited x86 PE32/x64 PE32+ identity. The bounded header
check is NOT a complete PE verifier or a license check. ASCII names and refusal
of symlinks/bind mounts/multiply-linked executables are compatibility limits.

Handles pin observed inodes. Metadata/path revalidation detects tested file,
installation and working-directory replacement, but is NOT an atomic freeze.
Before future Wine path opens, the host must stop guest writers, obtain exclusive
storage ownership and retain Valve's legitimate authentication/ownership launch.
Linux auth does not automatically authenticate Madeira Dock's Windows Steam.

`GameFilePolicy` registers one native app-prepared Linux root data descriptor
before any guest task. A later Steam download may create a library normally;
each request opens the selected fixed subtree. Native policy validates and
closes temporary handles synchronously, recording only the newest completed
sequence, request counts, AppID, errno, library kind and PE machine. It retains
one root descriptor for one native app lifetime. No arbitrary native root can
be registered by guest IPC. `LabBridge` now validates the owned frame snapshot
instead of validating one frame and later copying potentially changed bytes.

With explicit `LINUX_LAB_GAME_FILE_POLICY=1`, compatibility-tool/native-log/
frontend opt-ins are required. The current atomic session health receipt includes
fixed numeric policy results, diagnostic-only=true and game-launched=false; no
paths, argv, environment, passwords or account payload. No sampler thread or
Wine launch is added. **The helper still returns125; no game is launched.**

### Tests and evidence boundaries

- 48 ASan/UBSan native capability/policy controls PASS: two libraries/PE machines,
spaces/nested working dir, file type/header errors, symlink/alias/traversal,
path/content/directory replacement, unknown/missing library, late library creation,
512 concurrent policy requests, native-owner refusal and descriptor accounting.
- One thousand rejected native file requests leave no transient descriptors.
- Eight concurrent threads submit512 requests; completed sequence/count remain
correct, and only one app-root descriptor is retained after completion.
- Three actual host LinuxRunner ARM64 executions invoke the existing compatibility
helper and real `/dev/ideck-madeira` device into native policy. Default/shared
synthetic game paths validate; outside symlink rejects. The real wrapper exits125.
All three actual health JSON files were independently parsed and checked.
- Seven existing native logging modes, ordinary16 ARM64 kernel controls, protocol
ASan/UBSan hostile/truncation/mutation cases and missing opt-in refusal PASS.
Only changed native wrapper/policy/log/control units are sanitized; the complete
interpreter dependency is NOT fully instrumented.

The synthetic AppID480 and128-byte PE identity fixtures contain no executable
game or Valve code and make no ownership claim. These are host/native contract
results, not actual Steam Play, Air policy, game or return evidence. Artifacts
and exact hashes are in private run20 and EVIDENCE.run20.

### Full iOS artifacts and default-resource correction

Feature26 full Xcode, final linked markers/symbols and exact-profile disposable
signing passed. Full default26 compiled and excluded runtime policy symbols,
but the subsequent resource audit FAILED: the project always copied the tool,
even when its flags were off. This is a real build isolation bug, not a device
runtime fault. The build phase now copies the three generated tool resources
only when enabled and removes only those three when reusing default build
products. Unknown files are preserved. Six actual build-phase fixture cases
PASS, including enable/disable/reuse, unknown-file preservation and invalid
frontend refusal. Source version27 distinguishes this build-rule change.

Full default27 PASS: final policy/health/discard symbols and markers absent,
LabCompatibility absent. Full feature27 PASS: final local symbols, policy/health/
default-library/discard markers and exact helper/VDF resource hashes inspected.
The first `nm -g` check omitted linker-local symbols; full `nm` and bytes proved
their presence. The initial sandboxed xcodebuild stalled; only that exact owned
host build was terminated, then CLI build-services access succeeded. No device
or unrelated build was terminated.

Candidate27 unsigned Mach-O SHA256 `04869ed0f989253744e33de721160b4c522abbb4509f4ece8a57dd4ae39c7d3e`.
Existing exact Air/profile signing plus deep-strict verification PASS; signed
SHA256 `c4336e4ff9c08bd25215d4624a4e2d0333c59fd7c0e7742f467887896e549cde`.
Default27 Mach-O SHA256 `10c669639dbde0b2ef2d1d8acd6fa848ea74f355d901f28f1aecf9816222f42c`.
Immutable source/app snapshots and final-linked27.json are under run20; signed
candidate is private run6/signed-lab27/LinuxLab.app. Candidate25 and26 remain
preserved. **None is installed in this run.** Current Xcode products are feature27;
use the explicitly selected immutable signed bundle, not an assumed build output.

Reproduce host contracts with new private output directories:

```sh
LINUX_LAB_GAME_FILES_OUT="$PRIVATE/run20-new-files" \
  bash experiments/linux-steam/tools/test-game-files.sh
LINUX_LAB_FILES_BRIDGE_OUT="$PRIVATE/run20-new-bridge" \
  bash experiments/linux-steam/tools/test-files-bridge.sh
python3 experiments/linux-steam/tools/test-compat-resources.py \
  "$PRIVATE/run20-new-resources"
```

The bridge test also needs the existing pinned host interpreter via
LINUX_LAB_ARTIFACTS and ARM64 cross linker via LD_LLD. Full experimental build
uses the previously documented frontend/TCP/packet/lifetime/worker/log/grouped
lazy-page/discard flags and verified root hash, adding
`LINUX_LAB_GAME_FILE_POLICY=1` to tools/build-lab.sh. Dependencies/private image
are not assumed available in a new worktree. Profiles, rootfs, Valve files and
raw logs remain outside Git; no combined Wine/Converter binary is distributed.

Next device experiment remains25 health/discard A/B after verified current
session end or the pending explicit approval. Only after that result should27's
native policy be qualified through an actual Steam Play request. Real all-native
Linux shutdown/storage lease, legitimate Madeira launch and restoration remain
required; limited counters0, initial return, native process presence or125 are
not substitutes. No new device success, stability, FPS or memory improvement is
claimed. Main/other worktrees/data unchanged; source remains uncommitted outside
weekday22–08. Goal ACTIVE; no success sentinel, scheduler unload or completion.

## Run21 — explicit child-thread joins; current Air white-screen evidence

The previous run made implementation/build progress, not a blocked/no-progress
turn. Current Air23/4952 and its exact B265FEBE installation executable were
revalidated17:19EST. Mount UUID matches, remote main2ac39be and experiment82b7861
are unchanged, and pinned vendor sources remain pristine. No live user test was
stopped, restarted or upgraded. The original one-time approval question remains
pending; continuing the goal is not treated as consent to that specific action.

### Current physical observation changes the failure focus

The fresh native Air screenshot is WHITE with a pointer/keyboard button. A
separate host observer using pinned RFBClient with shared ClientInit captured a
1280x800 white guest frame with pointer too. The app's existing viewer was
preserved; no keys/mouse/account input were sent. USB display observer ended
normally after2.008s,76 client bytes/5215 server bytes, no pair-record operation.
Native screenshot and independently decoded RFB agree. This narrows away from a
native-view-only issue, but does NOT eliminate a common RFB decoder/server or
guest-rendering problem. It is not current interactive Library evidence.

Current isolated Steam logs still update. Selected exact public renderer
messages at19:41/21:22/21:23 report
`x11_software_bitmap_presenter.cc(145): XGetWindowAttributes failed for window`.
That is not a proven root cause: windows may already be destroyed/stale, and
neither browser death nor the original failure is established. Initial broad
regex matches of the word crash included setup/history text and were rejected;
never turn those counts into crash events. Old unresponsive-browser entries
belong earlier sessions. Raw five selected logs and screenshots stay private;
only hashes/categorical evidence in run21/white-screen-evidence.json are used.
The capped kernel log and old updater4942 result are still not fresh exit proof.

### One hypothesis: body cleanup does not imply native TLS completion

Pinned task children use detached pthreads. GuestLifetime retires in a cleanup
callback, which precedes native TLS destructors. Sequential Madeira handoff
therefore needs actual native thread completion, not just zero task counters.

New UNLINKED JoinableGuests prototype registers successfully created child
handles under a native mutex, preserves positive pthread error semantics, seals
future starts and joins each actual handle. Initialization/seal/join belong to
one native owner thread/process. Creation failure/capacity/foreign owner/detached
attributes are refused. There is no cancellation, detach workaround, runtime
reset or timeout-as-death. A blocked pthread_join remains pending.

The copied task-archive generator's explicit `--join-guests` option changes
only that pinned child attribute and creation path and retains the existing
GuestLifetime cleanup. The default generated task.c remains byte-identical to
the earlier verified default source. Vendor task.c, FEX and ordinary app code
are not changed. This is NOT yet an app build flag or an installed device change.

Four ASan/UBSan host controls PASS:

- A real TLS destructor remains blocked after its entry body returns. The join
  remains pending until a separate test observer releases that destructor.
- 1000 injected native create failures leave no reserved/created child handles;
  capacity/seal/native owner/detached refusals are exercised independently.
- Actual ARM64 ordinary16 ELF controls pass with2 registered/2 joined children.
- A real ARM64 orphan survives initial return; the join waits2011ms, then its
  late marker exists and1 registered/1 joined child is observed. The child ends
  naturally; no stop signal is used. Runtime reentry continues to refuse EBUSY.

Existing default lifetime observe/signal/ordinary controls PASS, including the
ordinary16 guest checks. The copied task unit, native registry, wrapper and
controls are sanitized; the full dependency is not. The new component compiles
with -Wall/-Wextra/-Werror to an iOS arm64 Mach-O OBJECT, which is not a linked
app, physical execution or Steam/Wine result. The first shell fixture attempt
failed on macOS Bash3 empty-array/nounset before compilation; an explicit default
flag fixed it and v2 tests passed. A Python bytecode-cache permission failure was
handled with read-only compile() syntax validation, not broader permissions.

Limits: this registry covers CHILD guest pthreads only. Initial runtime worker
is already separately joined. Timer/profile/TTY/forwarder TLS, signal policy,
mappings/mounts/global resource release and exclusive game storage remain open.
The4096 cumulative slots are not recycled in this prototype; do not deploy it
into long Steam sessions without addressing reaping/capacity. Even all registered
children joined is NOT Linux quiescence, Wine permission or reset certification.
The prototype is absent from immutable/signed27; candidate27 remains unchanged,
uninstalled and preserved alongside25/26. No new full app build in this run.

Reproduce in a NEW private output directory with the pinned prepared host build:

```sh
LINUX_LAB_JOIN_OUT="$PRIVATE/run21-new-joins" \
  bash experiments/linux-steam/tools/test-joinable-guests.sh
```

Exact source/archives/test-log/actual screenshot/frame hashes are in EVIDENCE.run21.
Next: auxiliary worker ownership/join/stop, then signal and storage handoff;
current X11/window lifetime versus common decoder/server failure needs its own
discriminator. On-device25 health/discard A/B still awaits a safe end of current
23 or the existing explicit approval. Diagnostic125 remains NO GAME, with no
Wine/Dock/FEX/DXMT linkage or licensed game/return/stability proof. Changes remain
uncommitted outside local weekday22–08; preserve main/other worktrees/app data.
Goal ACTIVE. No success sentinel, scheduler unload or completion claim.

## Run22 — white-screen window-lifetime discriminator (Nov9)

Prior turn was actual progress: native child joins/TLS controls and separate
native/shared-RFB white-screen evidence. Current branch/origin/worktree/mount
were verified, previous replies reviewed, and exact live Air23/4952 B265FEBE
identity confirmed. No overlapping host X11 experiment was found. Main/other
worktrees/working apps and pinned vendor remain unchanged.

### Hypothesis and actual implementation

Steam logged XGetWindowAttributes failures. The specific hypothesis is that a
basic LinuxRunner X11/live-window or distro Xlib path could be generically broken.
A source diagnostic alone does not distinguish that from a destroyed/stale
window. Two new real ARM64 Linux controls isolate the layers without Steam,
account data, RFB decoding or the iOS native view:

- `x11-window-probe.c` implements bounded core X11 wire requests directly.
- `xlib-window-probe.c` links the actual distribution libX11/glibc; our minimal
  AArch64 glibc startup enters the real libc startup path. Its XError handler
  belongs ONLY to that synthetic test process, never Steam/CEF.

Both fork into two independent clients on a dedicated fresh Xvfb :97. Each
creates16 own windows, queries before/after mapping, reads64x32 pixel images,
destroys each window and checks the deliberately invalid window. Own windows
are disjoint and have different fixed colors. The X11 layout reference is the
[X.Org protocol definitions](https://cgit.freedesktop.org/xorg/proto/xproto/tree/Xproto.h);
no third-party implementation was copied into these diagnostics.

The root is a NEW private clone of the stopped, unauthenticated prepared run2
image. No loginusers/userdata configuration, active source DB user or overlapping
host experiment was found. The original clean root and Air prefix are unchanged.
Our ELF is installed through the actual guest VFS, not fabricated fakefs SQL or
host metadata. Every run has a new root/output and refuses an occupied :97 or
recognizable account configuration. Only its own spawned server is stopped on
normal guest exit. Observer timeout preserves the PID/live-state uncertainty;
it is not interpreted as guest death or an automatic restart permission.

### Evidence and what it rules out

Real wire-level control: guest0,2.994s host duration. Real Xlib control: guest0,
3.622s. Each has32 windows,64 successful live attribute queries,32 expected
post-destroy BadWindow failures,32 image reads and65,536 pixel comparisons.
For each client the two independent implementations produce identical hashes:
parent4133264837, child658546117 (FNV1a32 of controlled pixels). Each client reads
131072 image bytes. Exact library/Xvfb/ELF/log hashes and Debian versions are in
EVIDENCE.run22 and private run22/comparison.json.

This rejects an always-broken basic X11/live-window/Xlib/pixel path as a sufficient
explanation in this host configuration. It does NOT reject a Chrome multithreaded
window ownership/lifetime race, app copied-archive effects, shared memory/GPU,
long-session memory pressure, common RFB decode/server fault or Air-specific
behavior. The expected error on destroyed windows is a negative control; it is
not proof that Steam's failures have this same cause. No causal runtime fix,
assertion suppression, Valve/FEX modification or stable Steam result is claimed.

The first sandboxed control FAILED before useful X11 testing: Xvfb could not
bind local listeners, and a fakefs socket placeholder appeared before the failed
native bind; clients then gotENOENT. Fresh normal unprivileged socket-services
execution in a NEW root passed. This was failed setup, not reproduction of the
Air/CEF white screen. The original failed artifacts remain private. The raw
probe's parent error can be masked by a child's failure status; the child report
and server log establish that initial setup failure. No security setting changed.

### Actual Air response test

After host controls ended, one harmless F1 Steam-menu key was sent through the
existing paired shared display channel (two8-byte packets reported written).
No credential text/Guard/account action, exit/restart or installation occurred.
The subsequent actual native screenshot is still WHITE with a cursor; no Steam
menu/navigation response is visible. Packet writes do NOT establish Steam focus,
consumption of input, UI success, browser death or completed session. The old
private navigation utility has a hardcoded historical visually-verified scope;
that description is explicitly ignored for this run. The frame and actual
screenshots, not the generic label, are authoritative.

Current23, all saved auth/games/saves and signed25/26/27 candidates remain
preserved. The earlier one-time retirement25 approval remains pending, no
repeated question or consent inferred. No on-Air code/health/discard/native-file
policy qualification is added by these host tests. All new programs are source
only, outside the app target, and no new iOS build/install occurred.

### Reproduction and next step

Compile the freestanding wire probe with the existing AArch64 cross linker.
Compile the dynamic control with the actual root's regular ELF libX11.so.6.4.0
and libc.so.6 (guest symlink stubs are NOT native linker inputs), `-nostdlib
-fPIE`, glibc-start.S and interpreter `/lib/ld-linux-aarch64.so.1`. Both use
-Wall/-Wextra/-Werror. The new run-x11-window-control.py takes the pinned host
interpreter, a stopped unauthenticated private fakefs, one own ELF and a NEW
private output directory. Raw root/Valve/packages/logs stay outside Git.

Next distinguish the actual Steam window lifetime versus long-session pressure
with narrow numeric tracing and the already prepared25 health/discard device A/B
once the live session can safely end. Independently finish native stop/signal/
storage ownership and legitimate Madeira integration; do not replace the actual
Steam UI or game runtime. Bridge125 is still diagnostic, no game/return or
repeated stable operation. Changes remain uncommitted outside weekday22–08;
no main merge, success sentinel, scheduler unload or completion claim.

## Run23 — bounded window-lifetime tracer, forwarding verified on real Xlib

Prior turn was PROGRESS: both raw-wire and genuine Xlib tests passed, while the
actual Air stayed white after one menu key. The next hypothesis is whether a
narrow diagnostic can record real window query/destroy ordering without changing
the original client's return values or pixels. This is diagnostic preparation,
not a causal Steam fix or a redefinition of the Library/game/return goal.

### Minimal implementation and review correction

Own ARM64 Linux `xlib-window-trace.so` interposes ONLY XGetWindowAttributes and
XDestroyWindow. It forwards exact arguments and output pointer, returns the real
result and saves/restores errno around its diagnostics by source design. It
installs NO error handler, retry, new thread, pointer/title/property/pixel dump,
GPU/memory/assertion change, credential operation or Valve binary patch. Lazy
RTLD_NEXT resolution must still be qualified in real Steam's loader namespaces.
An unavailable original ends the diagnostic process125, never fakes success.

V1's per-process-file logger passed its ordinary/fork/cap host controls, but file
handle ownership across shared-VM/exec/descriptor-table changes was not proven.
It was replaced BEFORE any app/Steam integration. This was review of the probe's
design, not a discovered Steam failure. Its original source and binaries remain
private and immutable.

V2 writes numeric PID/TID/call/window/op/phase/result/monotonic events to the
caller's EXISTING private diagnostic stderr. It owns/closes no extra descriptor
and has no inherited logging mutex. A lock-free byte budget limits each budget
instance to512KiB with an explicit omission marker. Fork copies the current
budget; CLONE_VM shares it. Short writes/interleaving/cap make coverage partial;
an absent event is not proof a window or failure was absent. stderr must already
be directed to the app's private diagnostic sink. No arbitrary stderr content
is published; only strictly parsed numeric records are used.

### Actual controls, rather than compilation alone

The updated real Xlib/glibc client first queries/closes an actual display BEFORE
fork, then each process exercises its own16-window lifecycle. Four fresh,
unauthenticated root/Xvfb controls run sequentially:

- Normal plain and normal traced complete with identical complete report
  dictionaries, original success/error counts and controlled pixel hashes.
- Stress plain and stress traced add4000 successful attribute queries PER client.
  Both still finish all windows/images/negative controls with identical results.
- Normal tracing has130 parent/128 child numeric rows,33/32 successful queries,
  16 expected destroyed-window failures and16 destroy returns per process.
- Stress tracing reaches the explicit cap (parent524122 numeric bytes,
  child523976), then the real Xlib program continues to the same final pixels
  and counts. Missing tail records are explicitly incomplete, not success proof.

Pixel FNV1a32 values remain parent4133264837/child658546117. Plain/traced report
identity is actual evidence for tested returns/counters/pixels; source-level
errno preservation is not presented as a universal client/thread/loader proof.
The changed diagnostic and test code compile with -Wall/-Wextra/-Werror. Existing
helper/bridge/runtime paths are not modified. These are real HOST ARM64 Linux,
distro glibc/libX11 and Xvfb executions, not Air/CEF/window-manager/Steam proof.

Final v2 library SHA256:
`333057792adbb13e10a88219b09d422a2e5fa356ef860b35f2e88a4a74d56c19`.
The source build recipe (currently uncommitted by the time window)
reproduces exact hashes for the library and both test ELFs. Private run23
compiled-v2-source captures the exact tested source; EVIDENCE.run23 contains
source/dependency/artifact/log hashes and the full bounded-control observations.
Earlier run22's five source files were reconstructed AFTER those tests and
verified byte-for-byte against ALL five previously recorded hashes; they are
retained privately. Later warmup/stress/preload additions do not rewrite its
historical results or pretend to have been included in earlier test binaries.

### Reproduction, current boundary and next action

```sh
LINUX_LAB_XLIB_ROOT="$PRIVATE/inspected-clean-fakefs" \
LINUX_LAB_XLIB_OUT="$PRIVATE/new-xlib-artifacts" \
  bash experiments/linux-steam/tools/build-xlib-window-controls.sh
python3 experiments/linux-steam/tools/test-xlib-window-trace.py \
  "$PRIVATE/new-xlib-artifacts" "$PRIVATE/stopped-unauthenticated-source-root" \
  "$PRIVATE/new-xlib-controls" --ish "$PRIVATE/host/ish"
```

Use the existing explicit ARM64 linker via LD_LLD; native link inputs are actual
regular distro ELF libX11.so.6.4.0/libc.so.6, not fakefs symlink-text entries.
The wrapper installs ONLY own ELF data through guest VFS. No host SQL mutation,
Steam/account launch, Valve export, credentials or signing assets in Git.

V2 is NOT in any iOS target, bundle resource, signed25/26/27, installed Steam
root or current Air session. No device injection/restart/upgrade occurred in
this run. No actual Steam load/interposition has been established. Current23
remains preserved; the old retirement25 question is pending without repetition.
The bridge remains125, and complete Linux stop/storage/legitimate Madeira launch
and game/return are still required.

Next implement an explicit default-OFF app/launcher opt-in, trusted bundled-ELF
preboot VFS installation and fixed Steam-child environment, with default
exclusion and final artifact checks. Only real selected-process trace events may
prove activation; build/ELF/process presence is insufficient. The chosen pending
on-Air memory experiment remains25, not an unannounced substitution of a newer
candidate. Maintain the full interactive Library/BPM/licensed game/return and
repeated-stability objective. Main/other worktrees/vendor/FEX/Valve and all
working data unchanged; outside weekday22–08, source uncommitted/unpushed.
No success sentinel, task unload or completion claim.

## Run24 — explicit diagnostic Lab28, signed but not installed

The numeric Xlib probe is now integrated behind both a default-OFF build flag
`LINUX_LAB_X11_TRACE=1` and explicit launch argument `linux-steam-window-trace`.
A preboot native-init-only VFS installer validates the own bounded ARM64 shared
ELF, rejects symlink/conflict/stale staging, verifies bytes and publishes through
a no-overwrite link. No Steam/account files are edited. The ordinary launcher
bytes remain exactly HEAD; only explicit diagnostic startup adds the fixed
preload AFTER starting Xvfb/VNC and BEFORE Steam. The requested marker explicitly
says activation is unverified; no live injection or diagnostic success claim.

Actual host ASan/UBSan VFS controls pass8 modes/23 checks, resource phase passes
11 cases, launcher bytes match baseline, and existing16 ARM64/protocol/bridge
controls pass. Full feature28 and default28 Xcode builds pass. Final feature
Mach-O contains both ordinary/traced argv, installer and new entry point; its
bundled ELF is SHA256333057792adbb13e10a88219b09d422a2e5fa356ef860b35f2e88a4a74d56c19.
Default final Mach-O/resources exclude the diagnostic. Private run24 contains
exact source snapshot, logs and linked hashes. Existing exact Air-authorized
profile signs a disposable copy and deep-strict verification passes; signed
Mach-O fb0380093123fc9e9abff7ef31d868f9bfe540a76d202822447efaaa9533850a.
**NOT installed or device-qualified.** Private discard/game-file policy are off
in this trace candidate. Current build products are DEFAULT28; selected signed
candidates are immutable separate copies.

Correction: run22's new diagnostic startup filename overlapped an existing
tracked glibc-start.S. Restored the original exactly from HEAD before this
compile; diagnostic is now separately xlib-glibc-start.S. The updated build
recipe reproduces all three run23 control hashes byte-for-byte. Historical
tested binaries were not changed. No original-helper regression is concealed.

Air23 native4952 remains identity-verified in the last readonly query, preserved
without stop/restart/install/account action. The earlier retirement25 question
is pending; do not substitute28 or treat a capped log/updater exit as current
session exit. Ordinary build success is not Steam/CEF interposition, visible UI,
stability or game proof. Next independently test real unauthenticated Steam
activation in a new host root; actual device diagnostic waits for safe session
end or explicit approval. Bridge125 and incomplete Linux-stop/storage/auth/Wine
integration still block real game/return. No main/vendor/FEX/Valve edits, source
uncommitted outside weekday22–08, no completion sentinel or scheduler unload.

## Run25 — genuine host Steam login/input, diagnostic loader defect corrected

**Result boundary:** actual genuine ARM64 Linux Steam rendered the login window
in two host runs. In the second live session, fixed noncredential `ideck-test`
appeared in the username field, then ten Backspaces visibly cleared it. Each
operation wrote22 RFB packets, but the separate inspected screenshots prove the
response; packet writes alone do not. No password/real account/Guard/submit.
Private screenshots include transient login QR data and must NOT be published.
This is HOST interpreter/X11/RFB evidence, not Air/Metal/Bluetooth, Library/BPM,
licensed game/return or repeated stability qualification. Air23 is unchanged.

### Failed diagnostic and smallest discriminator

The v2 probe used in unsigned/signed Lab28 caused the first actual Steam host
attempt to end125 after installation verification, with zero ordinary trace
rows. A separate real glibc/libX11 plugin experiment distinguishes scope:
RTLD_LOCAL plain0 / v2-traced125; RTLD_GLOBAL plain0 / v2-traced0. Thus the
diagnostic itself has an unqualified loader-scope path. This is NOT the cause
of the Air white screen that predates the probe. Do not deploy Lab28's tracer.

V3 first uses RTLD_NEXT, then ONLY on miss obtains a fixed-soname existing
libX11 reference with Linux NOW|NOLOAD|LOCAL. It does not load a new dependency,
promote the plugin to global, deep-bind or change Valve binaries. One atomic
winning reference remains for cached symbols; concurrent losers close theirs.
This intentionally extends Xlib lifetime, so it is NOT a transparent unload or
all-loader-race test. Phase2 records numeric resolution route1/2 or fatal-125.
Original arguments, return/output and errno forwarding stay as before. The
Linux flag definitions were checked against glibc's own
[header](https://raw.githubusercontent.com/bminor/glibc/master/bits/dlfcn.h) and
[loader entry](https://raw.githubusercontent.com/bminor/glibc/master/dlfcn/dlopen.c).

The same4 local/global tests now all0, including actual before/after checks
that local plugin symbols remain outside global scope. Real Xlib normal/fork
and cap-stress plain/traced comparisons still pass with identical complete
reports and pixel hashes. Actual VFS installer8modes/23checks also pass. V3 ELF
SHA256 b24c76df23870634a81e29ef893f4359d71234f3fc86b2db4600d44bb1a6b432.
The real Steam/client and steamwebhelper private logs then contain actual
window-query/destroy events. The second live test snapshot has60 strictly
parsed rows across4 guest PIDs, zero observed false attribute returns; this
does not prove all windows/processes/errors were captured. Real Steam login
and input confirmation is separate from these numeric rows.

### Observer correction and reproducible boundaries

The first220s observer returned before the initial input probe. A subsequent
readonly native/port query found no owner/listener; that zero-packet probe is
INVALID as a Steam input failure. The exact cause of owner disappearance was
not established, and is not called a Steam crash. New observe-host-steam-trace.py
keeps its own parent/child alive during UI observations, accepts only a private
stop-request for its own directly created unreaped child, and explicitly
records intentional shutdown. The second test ends after242.386s with SIGTERM
by that owner, NOT a clean Linux teardown/Wine handoff or guest crash.

Own build-host-steam-trace.sh creates only separate copied packet/TCP/lifetime/
worker/logging/madvise/lazy archives from pristine d1419782; no installed root
or vendor/base archive is edited. Fresh private unauthenticated root copies
are used. The one short native socket directory uses system temporary storage
for AF_UNIX length; all data/logs/binaries remain external. No overlapping
runtimes, no account-cache transfer or host SQL metadata edits.

Reproduce scope tests using build-xlib-window-controls.sh then
`test-xlib-loader-scope.py ISH STOPPED_UNAUTH_ROOT ARTIFACTS NEW_OUTPUT`. For the
real client use build-host-steam-trace.sh and
`observe-host-steam-trace.py CONTROL OWN_ROOT OWN_PAYLOAD NEW_OUTPUT --seconds 600`.
Inspect the actual login frame before optionally using rfb-login-fixture.m's
fixed insert/erase; never submit or automate credentials. Its22 packets are
transport evidence only; inspect the inserted/cleared images separately.

### Lab29 and next device gate

Source29 gives v3 its own preboot path/marker and retains both explicit build
and explicit diagnostic-launch gates. Full unsigned feature/default iOS builds
pass. Initial sandboxed Xcode startup stalled and only that identity-verified
own build was terminated; authorized system-service execution passed without
changing accounts/lock/security. Final feature Mach-O SHA256
1693d0a89471b8376c65ab05f3a24864873ab7e457003b461be8558416b77f42
contains v3 entry/marker/path, and bundled ELF matches the tested hash. Final
default Mach-O excludes path/preload/diagnostic/tool resources; its hash is
unchanged from default28. Immutable private run25/lab29-unsigned retains feature
output; current generic xcode products are DEFAULT29. Lab29 NOT signed,
installed or on-Air-qualified. Lab28 signed artifacts are retained but its
trace experiment is superseded by the observed host loader defect.

One readonly exact Air query still identifies4952/B265FEBE; no Air input/stop/
upgrade/authentication action this run. Preserve the unanswered one-time25
retirement choice; do not repeat or substitute29. After actual end or explicit
approval qualify the selected health/discard A/B and, if needed, explicit v3
window trace. Full native stop including TLS/auxiliary workers/signals/storage,
legitimate Windows Steam/Madeira linkage, actual Play/game/return and repeated
on-Air stability remain open. Existing child joins do not certify full reset.
Bridge remains125. No FEX/Valve/main/other-worktree changes, no success sentinel
or scheduler unload. Source uncommitted/unpushed outside weekday22–08.

## Run26 — actual native worker joins toward sequential handoff

The previous turn made progress on genuine host Steam login/input but did not
qualify the Air white screen or any game. This experiment addresses an actual
handoff prerequisite: body-entry counters may reach zero before TLS destructors
finish. No counter-only result may authorize starting Madeira.

Own NativeWorkerJoins.c/h adds an isolated owned reaper for joinable TIMER,
PROFILE and TTY workers. FORWARD keeps its original join owner, captured under
a generation before joining; there is no duplicate join or thread-ID reuse
lookup after joining. Managed slots recycle only AFTER actual pthread_join,
including TLS. One native serial owner initializes/seals/finishes; seal closes
future creation, finish actually joins the reaper. Errors stay sticky and live
TLS can keep a join pending. No forced cancel/detach/reset or runtime permission.
The copied-archive builder's explicit --join-workers switches only these paths;
ordinary app settings/defaults remain off and no vendor source changes.

Actual host ASan/UBSan tests, not compilation alone:

- Both managed and original-owner joins remain pending after body count0 while
  a deliberately held TLS destructor is still active; only its release allows
  completion. This also passes with the ACTUAL pinned timer provider callback.
- 8 active slots reuse through10008 real joins with4 concurrent producers.
  1000 creation failures leave no leaked handle/counter; an injected join error
  leaves completion false even when the original body counter is zero.
- Foreign owner/fork and detached attributes are rejected. Test-only host
  failure injection cannot compile for iOS.
- Real ARM64 native-offload fixture creates2 genuine forwarding workers and
  preserves original caller ownership/return37. This is a harmless native
  handler, NOT Madeira or a game.
- Real timer/TTY providers,16 ordinary ARM64 controls and the existing7 default
  worker regressions pass. TTY uses the source's ALREADY EXISTING cleanup cancel
  on a private stdin pipe, not a new policy or any user's actual terminal. Its
  native fixture remains alive until actual joins finish.

Default generated source for all4 providers remains byte-identical to the
previous ordinary overlay. The default counter object's actual text section
is identical and references no join registry. The earlier immutable feature29
Mach-O remains unchanged and contains no new registry symbols. New code only
compiles as an iOS arm64 OBJECT: NOT app-linked/installed/on-device validated.
Private run26 retains exact tested source, object/archive/log hashes, controls
and regression evidence. Initial bash3 empty-array setup refusal and host-only
unused-code compile correction are retained separately from the final passing
full-controls-v2 run; no failed run is counted as passing.

This is still partial ownership, NOT complete Linux teardown or Wine permission.
In particular the existing actual profiler regression still has1 live sampler
after guests exit: the source loop is infinite. It needs an explicit cooperative
stop before a join can finish; counting it or suppressing it is insufficient.
Guest child tracking still separately has4096 cumulative identities; this new
worker-slot reuse does not remove that limit. Existing timer creation-error
semantics must also be qualified before enabling a new admission gate. No epoch
reset/resume, full guest-stop, signal/storage/global cleanup, actual Steam Play
Madeira launch or game-return is claimed. The next discriminating experiment is
cooperative profiler stop in an isolated copied archive, followed by actual
frontend shutdown and measured native/resource boundaries.

One readonly Air query revalidates old23/4952+B265FEBE. No device input/stop/
upgrade/account action; unanswered retirement25 choice remains, not repeated
or replaced with29. Main/other worktrees/apps/auth/games/saves preserved,
prototype uncommitted outside weekday22–08, goal active, no STABLE_SUCCESS or
scheduler unload.

Additional run26 checks: actual ThreadSanitizer managed-TLS, external-owner-TLS
and four-producer10008-reuse controls all pass without race diagnostics in the
tested own registry/harness. This is not coverage of all LinuxRunner races.
Actual iOS compilation with HOST join-failure injection is rejected by the
specific HOST-only guard and creates no object. Source/default/device limits
above are unchanged.

### Published source checkpoint after Run26

Source-only checkpoint `5cfce802f932f7fad6fc43e1d25efaa28552bafc` is signed off
and pushed to origin/experiment/linux-steam-madeira-ipad; remote readback
verified2026-11-09T22:02EST. Main remains2ac39beff91251d36f3ad6331d3f8402b3c10e18.
Per-run82b7861+dirty records describe their original exact tested snapshots,
not a claim the later checkpoint was their test-time HEAD. No raw binary,
Valve/rootfs/account/signing payload, working app or primary-worktree change.
Goal remains incomplete; native profiler stop and full device/game/return gates
above still apply.

## Run27 — cooperative profiler exit and release after real joins

The old actual profiler control retained sampler1 after guest completion. An
owned reaper cannot join an infinite sampler. This new explicit --stop-profile
copied-archive experiment requires --join-workers and adds an owner-only stop
request after actual initial guest return, child joins and worker-start seal.
Sampler checks outside profiler locks after its existing sleep, performs one
final existing dump and returns. A separate buffer-release API requires actual
worker/reaper joins and refuses any registered TLB producer BEFORE disabling
profiling/freeing table or caches. No forced cancellation, reset or revival.
The original ordinary/default profiler remains unchanged.

Three actual ASan/UBSan host controls pass: enabled, disabled/ordinary16, and
leaked-producer negative. Enabled controls collect133 actual ARM64 workload
samples each with0 dropped in these runs, then real joins complete. The final
file is nonempty/parsed and remains unchanged after joins. Logical retained
profiler allocations6291456bytes become0 after release; this is allocation
accounting, NOT physical RSS/peak memory or an iPad performance measurement.
The producer test deliberately registers one extra native TLB after joins:
release refuses EBUSY and keeps registration enabled until test unregister.
Wrong owner, early phase and open admission are refused; repeated release is
allowed and init after close cannot revive the sampler. Raw PCs/profile files
remain private; only numeric observations/hashes are published.

Default four generated provider sources and counter instructions remain
identical to Run26. The new iOS arm64 ARCHIVE compiles and contains actual
stop/release/owner-check symbols, while the prior feature29 final Mach-O is
unchanged and has none. No new App target linkage/sign/install/device test.
Private run27 retains exact snapshots, source/dependency/archive/object/log
hashes and controls. This builds on signed/pushed source5cfce80 and documentation
208e654; main remains2ac39be. Source-parent fields identify test-time baselines
and dirty snapshots, not a self-referential later commit claim.

These profiler buffers are only one resource category. Actual Steam/CEF exit,
all guest/native joins, memory/root/signal ownership, storage writers and
legitimate Madeira game/return still need qualification. Pre-execution failure
cleanup lacks a returned-call receipt and is deliberately NOT inferred from
phase6/zero counters. Registry restart/epochs are not implemented. Bridge125
remains diagnostic, no game or full on-Air stability proof.

One readonly current Air query still identifies old23/4952+B265FEBE, without
input/restart/upgrade/account action. Preserve the pending25 retirement choice
and raw QR/login data; don't repeat or substitute29. Next perform a real
unauthenticated Steam graceful-exit experiment using the join mechanisms,
then qualify signal/storage/resource boundaries. No main/FEX/Valve changes,
completion sentinel or task unload.


## Run28 — genuine host Steam closes, real thread joins and zombie reap complete

Test-time parent f962015e551bd95fedb60bcf284270f3c6445a47. New host-only
`build-host-steam-shutdown.sh` builds separate copied archives with actual guest
and auxiliary joins, cooperative profiler-stop support, existing packet/TCP/log/
lazy-page overlays and native signal lease. Nothing is enabled in an App target.
The ordinary ARM64 ELF control still passes all16 checks and reaps1 child.

The first profiling-enabled real frontend attempt stalled in setup before Steam
started; sampled VNC task was in connect/wait-for-signals, not an observed profiler
lock. Its owned observer intentionally stopped only this private child. A second
fresh clone with profiling disabled displayed the genuine Steam login window.
Only its visually selected close button was clicked (2 pointer packets); no
account/password/Guard/login action. The real frontend then returned status0,
all registered guest/native worker pthread joins completed, native init wait4
reaped7 children, full PID range2..MAX_PID had0 remaining entries, and the native
signal lease restored successfully. The owner observed natural native exit0 at
282.027s. This is actual HOST Steam shutdown evidence, NOT device/game/return.
The one profiling A/B pair does not identify a sole cause or reproduce an Air
failure. Both host sessions are now terminal; never reuse their old PIDs.

Before native helper process exit, self footprint was248202320bytes and resident
706707456bytes, versus1671552/2277376 before frontend. Anonymous charged guest
pages0, translated blocks/codewords0, translation-table instances1. The pinned
construct_task/native init path allocates an mm and translation table deliberately
retained here; source-consistent with this counter, but no per-mm identity was
recorded in the real run and it does not explain the whole residual footprint.
No pressure-relief/free/reset workaround or full reclamation claim. Remaining
root mounts/SQLite/native init/global caches/storage need an actual lifecycle.
DONTNEED requested bytes are not reclaimed-memory measurements.

Readonly actual prepared iOS archive inspection also found a strong external
`current` collision: LinuxRunner TLS versus wineserver regular common storage.
Prepared Wine source revision is not yet matched, and no combined link was
attempted at this stage. It is a concrete next linkage discriminator, not a
claim the whole combined App has failed or that renaming fixes runtime safety.
Private run28 retains exact binaries/source/log/frame hashes, startup-failure
samples, natural-exit receipts and the symbol inventory. Login/QR frames remain
private. Source-only evidence contains numeric observations and hashes.

One fresh readonly Air query again identifies old Lab23/4952/B265FEBE without
input/stop/upgrade/restart/authentication. Pending25 choice remains unchanged.
Main and other worktrees/data/vendor/FEX/Valve untouched. No actual Steam Play
Madeira game or return, no repeated Air stability, no STABLE_SUCCESS or unload.
Next isolate Linux task symbols in independent archives, then complete genuine
root/storage/mapping and Madeira integration rather than equating joins with
permission to start Wine.


## Run29 — isolate Linux task TLS before combining with Wine

Source-parent f962015e551bd95fedb60bcf284270f3c6445a47. A discriminating actual
iOS relocatable link of the ordinary Linux kernel archive plus the prepared
wineserver archive fails on duplicate `_current`. Linux defines task TLS; the
server defines a regular global. New explicit `LinuxSymbolNamespace.h` changes
ONLY the Darwin assembler label of Linux's declaration to
`_ideck_linux_current`, retaining its C identifier. No `-Dcurrent` token macro,
Objective-C selector rewrite, Wine/FEX/Valve edits or default target enablement.
Force-include only for LinuxRunner and Linux C adapters, NEVER Wine compilation.

`build-symbol-isolated.py` builds fresh host/iOS interpreter archives from exact
pristine LinuxRunner d1419782da2e299fe22f1ddb85c70ae3d1e276b1 and the existing
generated dirfd guard. Subsequent copied overlays inherit these compile commands.
Darwin asm labels include the leading underscore explicitly; preprocessed
assembly skips the C declaration. Build host and iOS configurations sequentially:
the pinned cross-compiler probe uses fixed BSD-incompatible `/tmp` templates and
concurrent configurations collided in one refused setup. No upstream/temp-file
cleanup workaround. Earlier failed output directories remain separate/private.

Actual results, with source/artifact hashes in private run29 and EVIDENCE.run29:

- Fresh host-v4/iOS-v5 static archives build and all Linux-only namespace audits
  pass. The adapter-forgotten-include negative object is correctly refused. An
  unqualified adapter could otherwise bind to Wine's ordinary global despite a
  namespaced archive: audit every Linux object, not just libish.
- Real host controls pass16 ARM64 ELF checks, two simultaneous native TLS
  threads remain isolated from a synthetic regular-global fixture, and actual
  Objective-C `current` selector spelling/dispatch remains unchanged. Own test
  harness/adapters use ASan/UBSan; this is NOT coverage of all LinuxRunner code
  or actual Wine runtime behavior. Native init mm refcount1/pgdir_used0 observed
  after this ELF, not attribution of real Steam's entire residual footprint.
- Actual kernel+wineserver pair relocatable link now passes with two distinct
  definitions: regular `_current` and TLS `_ideck_linux_current`. Engine/system
  references deliberately remain unresolved. This is NOT a full executable/App
  link or Wine execution. All-loading the engine too forces4 pre-existing gadget
  aliases and fails both variants; that stress case is separate from normal
  lazy App linkage and was not hidden with linker suppression.
- Readonly symbol inventory finds no shared definitions with12 prepared
  native archives (including wineserver) after isolation; pairing archive nm fails/incomplete, dynamic
  frameworks are outside this inventory. No complete combined-link claim.
  Primary Wine source pin9129e968 is clean/matches the baseline, but that alone
  does not establish the old prepared server archive's exact source provenance.

Reproduce with new private output directories (configure platforms sequentially;
explicit MESON/NINJA/LD_LLD from the prepared toolchain, as in earlier runs):

```sh
python3 experiments/linux-steam/tools/build-symbol-isolated.py "$OUT/host" \
  --platform host --meson "$MESON" --ninja "$NINJA"
python3 experiments/linux-steam/tools/build-symbol-isolated.py "$OUT/ios" \
  --platform ios --meson "$MESON" --ninja "$NINJA"
LINUX_LAB_NAMESPACE_BUILD="$OUT/host" LINUX_LAB_NAMESPACE_TEST_OUT="$OUT/controls" \
  bash experiments/linux-steam/tools/test-symbol-namespace.sh
python3 experiments/linux-steam/tools/test-symbol-pair-link.py \
  "$PREPARED_IOS/libish.a" "$OUT/ios/build/libish.a" \
  "$PREPARED_SERVER" "$OUT/pair-link"
```

No App build/sign/install, physical input/restart/termination or credentials this
run. Preserve old Air23/4952+B265FEBE and unanswered selected25 choice. Joined
thread/signal controls and symbol isolation are components, not authorization
to start Madeira. Still need native viewer shutdown, storage-writer boundary,
root/global lifetime and a real return path. One possible next discriminator
is retaining the dormant Linux kernel/root while completely ending/rejoining
frontend processes, then creating a new init child after a native game session:
this is a HYPOTHESIS, not implemented or proven by resetting consumed flags or
registry counters. Never remount/reinitialize over a live or ambiguous kernel.

No authentic Madeira game from Linux Steam Play, return, Bluetooth or repeated
Air stability. Bridge remains diagnostic125; no STABLE_SUCCESS or task unload.
Continue full product objective with exact final linked artifacts and real Air
evidence, preserving main/all other worktrees/app accounts/games/saves.


## Run30 — retained-root execution across four actual ELF guest waves (HOST only)

Parent35ff61c0ec5f59f1fe8d6299a5694af7452ff92b, exact pinned pristine
LinuxRunner d141978. Ordinary runtime's one-shot policy remains intact. A new
explicit copied-archive `--guest-waves` option requires `--join-guests`; the
registry can reopen admission only after owner-sealed, fully actually joined
children, with no sticky error/join underway. It never resets cumulative
handles/slots/errors and refuses ENOSPC at lifetime capacity. Default builds
return ENOTSUP. This API is a child ownership component, NOT full runtime reset,
Wine permission or a public reusable-session contract.

The separate HOST helper starts the original ordinary runtime once, actually
joins/reaps every guest, preserves native init1/root/mm, then uses the pinned
new-init-child/ELF loader to run three further waves. Each initial child has its
own actual native join; registered fork/thread children are sealed/joined each
wave before native wait4 reaps and scans the whole remaining PID range. No
mount_root/become_first_process/consumed-state reset on later waves. The original
API still rejects repeat calls. It is not enabled in any iOS App target.

Actual reproducible results in private run30/repro-final:

- Four actual ARM64 ELF executions in one process each preserve16 PASS report
  rows separately, guest wait status0. Native init/root/mm identities match.
  Registered child slots/joins progress2,4,6,8 without resetting history; no
  remaining PID2+ task after each reap. This is not four Steam launches.
- ASan/UBSan own registry/adapter/overlaid-task controls pass. Real held TLS
  remains unjoined even after body return; reopen refuses until real join.
  Uninitialized/open/sealed-unjoined/foreign-thread/cumulative-capacity gates
  behave as documented; disabled prototype is refused.
- All four existing join regressions pass: held TLS,1000 creation failures,
  ordinary16 ELF and orphan-child completion. New iOS arm64 registry object
  compiles, NOT final App link/sign/install/device execution.

Reproduce with a NEW private external output and prepared toolchain:

```sh
LINUX_LAB_ARTIFACTS="$PRIVATE_LAB" \
LINUX_LAB_RETAINED_OUT="$OUT" LD_LLD="$LD_LLD" \
  bash experiments/linux-steam/tools/test-retained-root.sh
```

The first attempt refused missing output parent before compilation; corrected
parent creation and later final per-wave report/gate controls rerun passed.
Raw artifacts/source hashes, per-wave reports and regression results remain
private; redacted EVIDENCE.run30 records exact source and binary hashes.

Limits: cumulative4096 child handles remain. No auxiliary worker epoch/restart,
profiler restart, signal re-acquisition cycle, native viewer shutdown, genuine
Steam stale sockets/CEF lifecycle, fakefs SQLite writer boundary, physical memory
reclamation or Wine/Steamworks handoff proven. Native init/root are deliberately
retained; no blind reset/free/mprotect/counter workaround. Next discriminate
actual genuine Steam shutdown then a new frontend child in the retained root,
with real auxiliary joins and signal ownership, before linking game execution.

One readonly query again finds exact Air Lab23/4952/B265FEBE; no input/stop/
upgrade/restart/authentication. Pending25 choice unchanged, do not repeat or
substitute. Main/other worktrees/apps/accounts/games/saves/FEX/Valve preserved.
Source/docs remain uncommitted outside weekday22–08 (20:01EST Nov10); remote
experiment35ff61c and main2ac39be verified. Full genuine Air Library/BPM ->
licensed Madeira game -> stable return/repeat remains active, not achieved.
No STABLE_SUCCESS or scheduler unload.


## Run31 — genuine Steam renders twice across retained-root shutdown/restart (HOST)

Parent35ff61c0ec5f59f1fe8d6299a5694af7452ff92b plus exact run30/31 source hashes
in EVIDENCE. Default one-shot App remains unchanged. An explicit copied-worker
archive `--worker-waves` option requires `--join-workers`. Only its native owner
can recreate the owned reaper after sealed, actually joined old workers/reaper,
zero active entries and no sticky fault. History/generation/error are not reset.
Default builds refuse ENOTSUP. No provider globals or profiler revival: this
experiment refuses profiling-enabled startup, preserving the old one-lifetime
profiler boundary. Child registry uses run30's separately gated admission.

A separate host helper uses one retained fakefs root/kernel/native init. It runs
the existing genuine Steam frontend once; after true initial/child/native joins,
it reaps all guest zombies and restores native signal ownership. It captures
another signal lease, explicitly reacquires the existing SIGUSR1/SIGPIPE policy,
reopens joined child/worker admission, removes only old private display readiness
paths and creates a new init child for the exact same fixed Steam launch/env.
No mount/become-first-process/consumed reset. Both real frontend exit statuses
are checked before proceeding. It is not linked into an iOS App target.

Actual test results (private run31/owner-authorized):

- Genuine login window visually inspected on BOTH waves, including new QR
  challenge. Initial black frames were startup delay, not final UI evidence.
  No username/password/Guard/submit action. Only each visually selected close
  button was clicked,2 pointer packets each, and normal guest exit followed.
- Same owned native process/root through both waves. Both initial statuses0;
  actual guest/native joins complete; init wait4 reaps8 then7 with0 remaining
  PID2+ entries; signal lease restoration succeeds twice. Owner observes
  NATURAL native exit0 after239.934s. This duration includes observation/manual
  inspection and close actions, NOT startup/performance or Library latency.
- 20 real owned worker/reaper waves pass host ASan/UBSan tests, preserving
  cumulative counters and managed/original-owner forwarder return values.
  Early/open/not-actually-finished/foreign-owner gates refuse; default refusal
  passes. All10 previous worker-join regressions pass, including real pinned
  timer, held TLS, TTY, forwarding, failures and10008 active-slot reuse.
- iOS arm64 registry OBJECT compiles; no new final Mach-O/sign/install/device
  test. LinuxRunner/vendor/FEX/Valve/ordinary targets remain unchanged.

The FIRST sandboxed host attempt failed before Steam: Xvfb could not bind local
listeners and x11vnc connect returned EPERM. It naturally exited native5 with
real cleanup; no Linux crash claim. The SAME immutable binary in authorized
host socket execution, after confirmed terminal root ownership, displayed both
real windows. No retry patch, ignored failure or suppression of Xlib/CEF checks.
Raw native samples/logs and QR frames remain private; publish only hashes/counts.
Both own observer children are now terminal; never act on their stored PIDs.

Reproduce in fresh private output/root with explicit prepared NINJA/toolchain:

```sh
LINUX_LAB_ARTIFACTS="$PRIVATE_LAB" LINUX_LAB_RESTART_OUT="$OUT/build" \
  NINJA="$NINJA" bash experiments/linux-steam/tools/build-host-steam-restart.sh
LINUX_LAB_WORKER_WAVES_OUT="$OUT/units" \
  bash experiments/linux-steam/tools/test-worker-waves.sh
python3 experiments/linux-steam/tools/observe-host-steam-trace.py \
  "$OUT/build/control" "$PRIVATE_UNUSED_ROOT" "$PREPARED_TOOL_BUNDLE" \
  "$OUT/observer" --seconds 600
```

Observer deadline/intentional termination is never a clean cycle success; real
close-window interaction and natural terminal receipt are required. Preserve
source/binary hashes and verify account-free root first, as observer does.

This is a HOST basic two-login-render/close/restart result, NOT authenticated
Library/BPM navigation, game/return, stability qualification or iPad validation.
No new Wine execution, Steamworks/license path, native iOS viewer/Metal/input
handoff, full storage-writer barrier or memory reclamation proven. Root/kernel
remain deliberately resident; cumulative4096 child handles and timer provider
creation-error limitations remain. No combined binary distribution until
component/proprietary converter exception obligations are resolved.

One readonly Air query again shows old23/4952+B265FEBE. No Air input/stop/install/
restart/authentication, pending25 choice unchanged/not repeated. Main/other
worktrees/working apps/accounts/games/saves preserved. Full actual Air Steam ->
licensed Madeira game -> stable return/repeat goal active; no STABLE_SUCCESS or
scheduler unload. Next move these qualified components into an explicit isolated
App lifecycle with native viewer/storage/signal ownership, then genuine bridge
Madeira execution, preserving the active user test.


## Run32 — native RFB task-completion boundary integrated into opt-in App32

Parent f6c1bcdb1bd4d405cccac360027112e6f8b65f2f. Previous run31 actual HOST
Steam restart is progress, not App return proof. Current native viewer's stop
only requests socket shutdown, so it cannot certify decoder/input callbacks
returned. New `LINUX_LAB_RFB_LIFETIME=1` uses a generated copy of exact pristine
LinuxRunner RFB source: one recursive admission lock guards start/input and stop;
actual decoder/input GCD blocks belong to a group; stop closes future admission
and notifies main after bodies/callbacks/autorelease pools return. No deadline
or counter-only completion. `LabRFBClient.m` includes original source unchanged
when disabled, preserving its license/notices rather than editing vendor.

In the explicit feature App, guest-return closes UI input and frame admission.
A client not yet connected cannot start after guest end (installation/start now
shares main-queue ownership). RFB completion clears callbacks, retained latest
CPU frame, viewport size and displayed frame. Pending main deliveries are dropped
when frame admission is closed. This is NOT Metal command-buffer completion;
runtime marker explicitly records gpu_completion_unverified=1. Existing ordinary
one-shot runtime and Linux child/native registries are not enabled/reset here.

Actual private run32 results:

- Four real loopback protocol/socket controls pass ASan/UBSan: stop-before-start
  then attempted start/input admits no connection; stalled handshake interrupted;
  actual raw frame callback and actual input-queue callback held deliberately.
  Completion remains absent during100ms hold and occurs only after release/return
  on main dispatch QUEUE. CLI dispatch_main queue affinity is not NSThread identity.
- Default original/wrapper compiled RFB instruction sections are identical at
  host O2. No changes to original pinned vendor file or ordinary behavior.
- Full Xcode feature32 build succeeds. FINAL actual Mach-O contains RFB completion
  and controller guest-close methods and explicit GPU-unverified marker. Immutable
  unsigned feature app hash1945259685fb50f4d932bc3b7e581f60f621804cab1166fd2193ea04b15a08b2.
- Full default32 builds, excludes these methods/marker and compatibility resources.
  Final default hash30805008c143d4706271a8d3b200b3b600f1b1f03e4e3378791c01d2999887d7.
  Current generic run32/xcode products are DEFAULT; feature copy is run32/
  feature32-unsigned/LinuxLab.app. No sign/install/on-Air App32 execution.

Generator initially refused a nonunique initialization token; corrected exact
match. Harness fixed its strong self capture, Python3.9 timeout classification
and CLI queue/thread assumption. Inherited unused-static/indentation warnings
are permitted explicitly in the host Werror compile; runtime checks/assertions
are unchanged. A premature final-link audit refused while Xcode still ran; the
same handle was re-polled to terminal success before final artifact inspection.
All exact source/generated/test/build hashes are in EVIDENCE.run32/private run32.

Reproduce source with build-rfb-lifetime.py NEW_OUT, compile own
rfb-lifetime-control.m + LabRFBClient.m + pinned RFBProtocol.c using Foundation,
ARC/blocks, ASan/UBSan, IDECK_LAB_RFB_LIFETIME=1 and include paths to generated
source, lab app and vendor app/LinuxRunner. Then test_rfb_lifetime.py CONTROL
NEW_OUT runs real localhost peers. Full normal build-lab.sh accepts the explicit
LINUX_LAB_RFB_LIFETIME=1 only with frontend=1, generates copied input and passes
flag to Xcode. The recorded direct Xcode builds reused verified private29 runtime
archives and prepared rootfs pin, with fresh run32 input/DerivedData paths; they
do not prove run31 backend join prototypes are included. Final App32 proof here
is only the native viewer task boundary.

Scope remains limited: group completion does not join GCD executor pthreads/TLS
or certify all captured-object/framework/GPU resource reclamation. iOS UIKit
behavior remains untested, no native storage-writer barrier or game handoff.
Next use a dedicated serial session-owner thread to integrate real backend joins/
signals/retained-root lifecycle, coordinate viewer and GPU/storage boundaries,
then verified namespaced Linux/Madeira linkage and actual licensed game/return.
Do not change consumed state or call zero counters a safe handoff.

ONE readonly Air query still identifies23/4952/B265FEBE. No input/stop/install/
restart/account action, pending25 choice unchanged/not repeated. Main and other
worktrees/working apps/auth/games/saves/vendor/FEX/Valve preserved. Full genuine
Air Library/BPM -> Madeira game -> repeated stable return is NOT achieved. No
STABLE_SUCCESS or scheduler unload; goal active.


## Run33 — dedicated retained frontend owner integrated; current transport cycle still unverified

Parent `3d565827eb82ad79f316b33ba86df22c764cecb2`; LinuxRunner stays pristine at
`d1419782da2e299fe22f1ddb85c70ae3d1e276b1`, other pinned dependencies unchanged.
Exact source/build/artifact SHA256s are in EVIDENCE.run33 and private run33.
Main and other worktrees/apps/accounts/games/saves remain untouched.

**Implementation.** Separate `LINUX_LAB_RETAINED_FRONTEND=1` plus explicit
`linux-steam-retained-frontend` argument enables a process-lifetime native owner
thread and mailbox. It retains the original root/kernel/native init; never resets
consumed/global state or remounts a live root. Original/default API remains one-shot.
Reentry requires the same native pthread, root and transport boundary, previous
zero guest status and an actually DORMANT backend. Foreign thread/root/context
changes are refused. The owner performs actual registered child/native/reaper
joins, profiler stop/buffer release and native-init wait4 reap/full remaining-PID
check. Only the explicit joined-registry wave APIs reopen admission; no counter,
handle/history reset. Profiling is refused,4096 cumulative child handles remain.
Owner thread must remain alive for this process lifetime; no rebinding contract.

Review found a missing signal boundary: joining backend threads alone did not
prove an embedded RFB decoder/input work item had returned. Current API therefore
requires a bound drain callback for embedded transport, invokes it AFTER real
backend joins/reap and BEFORE SIGUSR1/SIGPIPE restoration, and poisons the lifetime
on any error. App callback closes frame/input admission on main, waits on the
owner for actual RFB group completion, clears CPU display state and only then
acknowledges. It never blocks main or substitutes timeout success. Restart UI
is enabled only after backend DORMANT plus actual display completion. Late
connector work is wave-guarded. Legacy one-shot stage remains unchanged; separate
RETAINED_BACKEND_STATE records the current wave. Early/ambiguous failure preserves
state and disables restart, with no forced cleanup/Wine admission.

**Actual HOST evidence, distinguish exact source versions.**

- BEFORE mandatory transport callback was added, actual shared C backend on a
  dedicated pthread displayed two genuine Steam login windows, both visually
  inspected and closed normally. Same native process/root/owner: both return
  native0/guest0/DORMANT/reaped8, finally native process exits0 naturally.
  Total734.527s includes manual observation delays and is NOT startup performance.
  Source is pinned privately in run33/pre-transport-boundary-source/hashes.json.
  This does not validate the later embedded-transport API or App composition.
- Earlier ASan/UBSan own-adapter run remained black414s and was intentionally
  stopped. Uninstrumented follow-up eventually rendered real login, but agent
  requested stop before inspecting the latest frame. This observation mistake
  grants neither normal-close nor restart credit; no sanitizer causation claim.
- CURRENT callback API host fixture did NOT reach Steam or callback: Xvfb log0,
  x11vnc startup log184, no display-ready/Steam log. Own900.223s observer deadline
  intentionally terminated native process(-15), not a crash or cleanup result.
  Read-only native sample shows x11vnc sys_connect awaiting managed peer ACK;
  no Xvfb native thread in that later sample. Kernel PID6 exit status0 after
  ~23.873s is consistent with bootstrap cleanup, not sufficient role/cause proof.
- A further CURRENT-binary test on an independent account-free root lost its
  tool/observer session. Fresh identity query finds the original native PID
  absent but no terminal result receipt. Exit cause is UNKNOWN. Inherited Steam/
  x11vnc logs predate this launch and are explicitly excluded. No inferred crash,
  natural close, UI or cleanup success (private reconciliation.json).

**Smaller discriminator.** Pinned fs/sock.c's successful AF_UNIX connect writes a
managed fd pointer and waits for accept to establish unix_peer. Actual tiny static
ARM64 ELF using the ordinary host embed control demonstrates: early accept in a
forked child + byte roundtrip completes naturally0/0.356s; connect to own queued
listener BEFORE accept never returns within5s and is intentionally terminated.
No Steam/rootfs/CEF is needed. Standard Linux stream connect queues an accepted
connection before userspace accept: see the separate connect/accept paths in
[Linux v6.12 af_unix.c](https://github.com/torvalds/linux/blob/v6.12/net/unix/af_unix.c).
This proves a contract mismatch, NOT the sole cause of Xvfb exit or a socket fix.
No runtime networking patch is applied. Simply deleting the ACK is unsafe:
credentials, SCM_RIGHTS queues, shutdown and fd lifetime depend on peer ownership.
The actual source uses process/socket-ID native names, so a root-path/socket-name
length theory is not supported.

Reproduce only in a NEW private output (intentionally killed late case is expected
failure evidence, never a clean teardown claim):

```sh
LINUX_LAB_ARTIFACTS="$PRIVATE_LAB" LINUX_LAB_CONNECT_OUT="$NEW_OUT"   LD_LLD="$LD_LLD" bash experiments/linux-steam/tools/test-unix-connect-order.sh
LINUX_LAB_ARTIFACTS="$PRIVATE_LAB" LINUX_LAB_BACKEND_OUT="$NEW_BUILD"   LINUX_LAB_BACKEND_SANITIZE=0 NINJA="$NINJA"   bash experiments/linux-steam/tools/build-host-retained-backend.sh
```

**Build/regressions.** Full current feature33 Xcode and default33 builds pass;
actual FINAL feature Mach-O includes retained backend, actual join/wave APIs,
mandatory native drain methods, live-state and GPU-unverified markers. Feature
SHA256 `bceaf5cef1f93dc65df011a6bc288d103ef43538d8e6cefe5b4b8cbc13cdbbd6`.
Immutable private run33/feature33-boundary-unsigned/LinuxLab.app is UNSIGNED and
UNINSTALLED. Final default excludes retained UI selectors/live-state marker,
SHA256 `f9d2eafecc539eeb57c460ffdd7d4312b3de98cbc489c9718a5e09e418989df4`.
Generic Xcode products are DEFAULT, not the feature copy. Eleven actual Xcode
resource-phase synthetic cases pass; shell syntax/default C stub Werror pass.
Initial missing NativeSignalLease link was corrected by linking its actual source;
no assertion suppression or FEX/Valve/vendor patch. ASan applies to own host
adapters where specified, not the entire underlying interpreter/archives.

**Limits/next experiment.** No completed CURRENT callback backend+embedded viewer
Steam cycle. RFB task completion does not join executor pthread/TLS or certify
all captured objects/Metal command buffers/GPU/storage-writer reclamation. Kernel/
root stay resident. No Linux+Wine combined App execution or legitimate game/return
proof; compatibility bridge remains diagnostic125. Next establish exact Xvfb role/
exit and pre-accept lifetime; design pending-connect ownership/credentials/rights
and cancellation controls before a minimal copied-source fix. Then verify current
complete viewer/backend cycle, namespaced Madeira linkage, actual game/return.

ONE readonly Air identity query this run still observed Lab23 PID4952/install
B265FEBE (historical by next run; revalidate). No Air input/stop/upgrade/restart/
authentication, no profile/security/lock change, no Mac-unlock request. Prior
selected25 upgrade question remains unanswered; do not infer consent or silently
substitute33. No binary distribution until licensing/converter exception scope
resolved. Full actual Air Library/BPM/input -> owned Madeira game -> repeated
stable return goal is NOT achieved; no STABLE_SUCCESS or scheduler unload.


## Run34 — actual CASP/CoW deadlock discriminator, copied engine fix, real embedded RFB restart

Parent/published branch revision `815ddc555d7a1c3e10fdc067bf0ebf395ca0fdf7`.
Run34 remains UNCOMMITTED/UNPUSHED outside the required local weekday22–08
window (recorded Nov11 morning). Check current time before each future commit
and push. Main2ac39be and all unrelated worktrees/installations/accounts/games/
saves remain unchanged. Exact source/dependency/generated/final-artifact hashes
are in EVIDENCE.run34/private run34; LinuxRunner d141978 remains pristine.
Only normal app compatibility/build/runtime testing was performed; user prohibits
cybersecurity operations, security/lock changes and Mac-unlock requests.

**First discriminator/control.** Own copied-source diagnostics add fixed startup
stages/numeric child IDs and allowlisted Xvfb/x11vnc exit statuses, preserving
original shell limits/delays/Steam arguments. Current retained API with an EMPTY
native transport boundary actually displays/closes/restarts two genuine login
windows, both backend native0/guest0/DORMANT/reaped7; natural0/399.627s total.
This rejects an always-failing callback/API theory, but is not embedded-RFB proof.
Total includes operator observation delays, NOT a startup performance result.
No socket networking fix is applied: the earlier AF_UNIX ACK contract mismatch
remains a separate known limitation, not proven the sole cause of other freezes.

**New observed failure.** A new host control runs the REAL RFB decoder/input client
in the same process/main dispatch queue as the retained backend. First original-
engine test stays black562.18s. Two read-only samples show:

- one c_casp_pair owner inside mem_ptr waiting for MM write ownership during CoW;
- other CASP calls wait for pair_atomic_lock while their guest CPU execution
  retains MM reader ownership;
- Xvfb, x11vnc and the native RFB receive loop still exist. No login/close was
  sent in this failed test. Own bounded observer intentionally terminates it(-15),
  not a native crash, normal close or cleanup result.

Pinned task_run_current holds MM read ownership around CPU execution. Pinned
c_casp_pair takes a global pair mutex BEFORE faulting write-pointer translations.
Pinned mem_ptr drops its reader and waits for MM writer on CoW. This gives a
specific lock-order cycle; it is not evidence of a networking/DRM/auth problem.

**Tests before runtime patch.** Actual published helper function is extracted
verbatim into a native pthread lock schedule with a modeled MM translation/upgrade
boundary. Baseline serial32/64 writeback/mismatch/fault cases pass but controlled
CoW lock schedule deadlocks. Candidate moves write translations BEFORE the mutex;
strict ASan/UBSan serial cases and the same schedule pass. Initial test receipt
was REJECTED: a shim expression temporarily formed an out-of-bounds pointer and
recovering UBSan did not fail its exit status. Correct parentheses and
-fno-sanitize-recover=all are used in the passing v2 tests. This model alone is
NOT full Linux/ARM64/device evidence.

Then a genuine static ARM64 ELF executes CASPAL64, real fork,128 private CoW pages,
three CLONE_VM CASP contenders and a CoW writer, using real LinuxRunner MM/TLB/
gadgets. Baseline passes serial CASP then cannot complete CoW phase; native sample
reproduces the same lock cycle. Own10.456s bounded test intentionally stops it.
IDENTICAL ELF with the copied engine finishes naturally0/0.813s, all PASS rows:
serial compare/writeback,128-page CoW updates, child's unchanged original pages,
worker exit/wait4 and complete. That timing is a HOST microtest measurement,
never an iPad/Steam performance number. No orphan/timeout success credit.

**Minimal patch/integration.** Shared casp_order_patch.py supplies byte-identical
helper body to model and real copied archive build. Only emu/tlb.c is copied and
its engine archive member replaced; original archives/vendor/FEX/Valve unchanged.
Existing comparison/writeback, memory permissions and faults remain; no assertion
suppression, blind fault retry or protection workaround. Component GPL/license/
IOS terms retained, no exception granted for upstream work. Current change does
NOT qualify mixed CASP/STXP atomicity or existing CASP32 misalignment/cross-page
semantics. Valid architecturally aligned pairs share a page under the existing MM
reader guard. Do not expand this patch into an unrelated atomic rewrite.

Explicit LINUX_LAB_CASP_ORDER=1 requires Steam frontend + native diagnostics;
default0 uses original engine. App references the actual engine identity marker
and refuses a mismatch. build-lab.sh generates a separate engine copy and carries
it through the isolated runtime path. Native worker/guest joins, original one-shot
policy, retained kernel/root,4096 cumulative handle limit and profiling-off policy
are unchanged. Neither this patch nor DORMANT alone grants Wine permission.

**Actual real Steam + embedded-RFB result.** First candidate observer lost its
session; exact native PID35003 later absent, no terminal receipt. Exit cause
UNKNOWN: no fix/failure/crash/cleanup claim. A later single bounded owner saves
samples/results independently of tool-view disconnects; no service configuration
or second researcher. Fresh same-seed account-free root, SAME native PID38304/
root/owner, copied candidate engine + actual native RFB:

1. First genuine login window visually inspected. Fixed native test marker queues
   only the inspected window's close through the REAL RFB input queue.
2. Actual decoder/input task completion acknowledges on main dispatch QUEUE
   BEFORE SIGUSR1/SIGPIPE restoration; backend returns0/guest0/DORMANT/reaped7.
3. Second genuine login window visually inspected and normally closed, actual
   RFB completion again, backend0/guest0/DORMANT/reaped7.
4. Native owner pthread joined, final native process NATURAL0/453.777s total,
   including operator observation/analysis time. No credentials/Guard/login
   submission, no authentication/Library/BPM/game success claim.

Read-only90/240s samples lack the earlier CASP/MM writer cycle. These two cycles
support the targeted compatibility fix, NOT an all-freezes/stability guarantee.
Private frame images/QRs/logs are never committed; published evidence is categorical
plus SHA256. CLI dispatch_main queue affinity is checked explicitly, not assumed
NSThread initial-thread identity. PNG snapshots publish atomically in private out.
Host test does not implement Metal or qualify all framework/TLS/GPU destruction.

**iOS artifact/regressions.** Full unsigned feature34 builds. FINAL actual Mach-O
contains engine marker AND c_casp_pair translation miss calls BEFORE ___lock;
backend/native-RFB drain methods are also present (hidden locals require full nm,
not only nm-g). SHA256
874806065a69df3296932e3345307867088ad45178e3399d117c1fe29676b4a9.
Immutable private run34/feature34-unsigned/LinuxLab.app, source bundle ID
com.kuschqin.ideck.linuxlab. UNSIGNED/UNINSTALLED; no provisioning changes.
Full default34 builds separately, excludes marker/retained UI and FINAL assembly
still has original mutex-first order. Three actual prerequisite/invalid-flag
cases refuse BEFORE artifact writes. Shell syntax/source checks pass. Initial
cross compiler include placement before xcrun was corrected and iOS rebuilt.
Build/link results are NOT physical execution or game proof.

Reproduce with NEW private outputs, preserving active sessions:

```sh
python3 experiments/linux-steam/tools/test-casp-lock-order.py "$NEW_MODEL_OUT"
python3 experiments/linux-steam/tools/build-casp-order.py vendor/LinuxRunner \
  "$PRIVATE_LAB/host" "$PRIVATE_LAB/host/libish_emu.a" "$NEW_ENGINE_OUT"
python3 experiments/linux-steam/tools/build-host-retained-rfb.py "$PRIVATE_LAB" \
  "$QUALIFIED_JOINED_KERNEL_ARCHIVE" "$NEW_FRONTEND_BUILD" \
  --engine "$NEW_ENGINE_OUT/libish_emu.a"
```

Compile guest/casp-cow-probe.c + guest/clone.S with explicit ld.lld,
--target=aarch64-linux-gnu -march=armv8.1-a -nostdlib -static -ffreestanding
-fno-builtin -fno-stack-protector -O2 -Wall -Wextra -Werror -Wl,-e,_start.
The existing host-embed adapter runs it as /probe in a new private realfs root;
record bound/intentional termination versus natural completion separately.
Real frontend observer accepts --native-sample-after 90 (repeat for240/480),
owns exactly one child, and uses a900s experiment deadline. For embedded
control, only AFTER inspecting private latest-wave-N.png create its own
logs/close-inspected-wave-N marker; never automate credential fields.

**Next/full goal.** Current Linux Lab is still not a combined Wine app; bridge125
is diagnostic, not a game launch. Next build the correctly namespaced combined
Linux/Madeira target and establish explicit native GPU/storage/runtime lifetime
boundaries and genuine licensed game handoff/return. No reset/hidden token copy,
no new credential automation, no private entitlement/DRM workaround. Resolve
component/converter exception scope before combined binary distribution.

ONE readonly query observed existing Air23/4952/installB265FEBE. No Air input,
stop/restart/upgrade/login or phone/app data changes. Pending SELECTED25 upgrade
choice remains unanswered; do not repeat/infer consent/substitute34. Revalidate
identity before future device actions; never target stale host38304/35003. Full
Air ELF + authenticated interactive Library/BPM/input + Steam Play -> legitimate
Madeira game -> reliable repeated return/stability remain UNPROVEN. No stable
sentinel, scheduler unload, GO claim or goal completion.

## Run35 — full combined Mach-O, signed Lab35 and actual Metal completion boundary

**Phase/goal.** Full hybrid goal remains ACTIVE and incomplete. Parent/published
checkpoint815ddc555d7a1c3e10fdc067bf0ebf395ca0fdf7; Run34/35 work is dirty,
UNCOMMITTED/UNPUSHED outside the weekday22–08 local window (2026-11-11 midday EST).
Remote experiment815ddc5 and main2ac39be re-read; volumeUUID580CADCD-33F5-4D78-
9530-2287615873CA and completed migration checked. Preserve all worktrees/vendor/
FEX/Valve/apps/accounts/games/saves. CLI-only ordinary app development; no security
settings/locks/account credential changes or cybersecurity investigation.

### Hypothesis 1: qualified Linux and the actual Madeira runtime can link together

Prior kernel/server relocatable-object tests were not a full app. New
`build-hybrid-linux-runtime.py` starts from immutable Run29 namespace-ios-v5 and
its actual pinned iOS compile database/header/hash. Applies the individually
qualified packet/TCP/guest-wave/native-worker/log/advice/lazy/CASP copies, then
compiles ONLY Linux adapters with the forced namespaced TLS declaration. The
original Wine/FEX sources and compiler flags are untouched. New
`build-hybrid-app.py` stages THIS experiment's tracked source into a PRIVATE
project, supplements only explicit prepared build payloads, uses the Linux Lab
entry instead of @main in the private Swift copy, and links actual Madeira.
Neither normal source project nor installed working app is changed.

Prepared payload root iDeck-steam64-setup lacks initialized Wine/FEX submodules:
preflight rejected the parent-Git fallback before writes. Explicit read-only
dependency root iDeck has pinned Wine9129e968/FEXf59cab95. No FEX compilation or
source edits. Initial nonexistent FramebufferMetalPipeline.m assumption was
corrected: it is an inline header. Initial global OTHER_LDFLAGS accidentally
included Linux in the helper link and failed. Corrected private MAIN target
Debug/Release settings only; final helper excludes Linux. These failed attempts
are retained privately, never counted as successful builds.

**Observed evidence.** Full unsigned combined App35 builds. FINAL actual Mach-O
has ordinary Wine `_current` in __DATA,__common and Linux
`_ideck_linux_current` in __DATA,__thread_vars, one distinct definition each;
actual wine_process_start/server definitions,3770 FEXCore and5459 DXMT
definitions, genuine Linux frontend and the CASP-before-mutex instruction order.
Immutable private run35/hybrid35-unsigned/Madeira.app SHA256:
7a459f77fbee55840fba24f32cbf4b8c2147ede78bee91d472392b14f3f9419f.
Seven read-only FEX/archive inputs are unchanged. Reused compiled component
provenance is NOT re-established simply by the checkout's pinned source HEAD;
those components were not rebuilt in this run. Full linking is not initialization,
concurrent-runtime, Steam UI, JIT, game or return evidence. Bridge remains125.

### Legitimate development packaging, separate from runtime evidence

Existing main AND helper profiles match com.kuschqin.ideck.freshtest(.JITHelper),
cover the exact Air and allow debugging, expire2026-11-13 UTC; matching existing
login-keychain development identity verified. No account/login/new profile/key/
trust/security setting action. Disposable copy's Info.plist identifiers and
label explicitly set to the SAME existing Lab identity, **iDeck Linux Lab**;
immutable unsigned source retained. Existing tools/resign-app.py signs it;
normal-environment deep-strict verification returns0. Signed Mach-O SHA256:
5b41400c124fb3bc4ce710b9d4e0e8afbcff61be9a0be6c2d0c5e417298410f2.
Sandbox-only verification reported CSSMERR_TP_NOT_TRUSTED; normal existing system
verification passes without any trust changes. This is not an iPad refusal or
Linux crash. No signed/Valve/rootfs/profile/raw-log asset is published.

**Device boundary.** ONE readonly Run35 Air query still sees Lab23/4952/install
B265FEBE (historical identity, revalidate before acting). User instruction is to
preserve live tests. Old selected25 question is superseded by a materially changed
concrete **combined35 + subsequent same-Lab iterations** choice, now PENDING:
allow ending old Lab, preserve data, upgrade, then iterate, or preserve session
and continue offline. No positive answer yet: do not infer from time/continue or
repeat the question. No Air input/stop/upgrade/authentication this run. Phone,
production iDeck and Mac Allocator remain unchanged. Signed35 is ready but NOT
installed. Interpreter needs no JIT; Wine JIT remains untested in this combined app.

### Hypothesis 2: real Metal commands need a completion boundary beyond RFB drain

Previous boundary explicitly left GPU completion unverified. New isolated
`LabMetalDrain` tracks real MTLCommandBuffers and their actual main-queue
accounting bodies. Closing admission rejects future commands; drain callbacks
wait for existing GPU completion AND per-view accounting. Reopen is refused
while pending/notifying, including reentrant callback attempts. No timeout can
fake completion. The actual view is retained through the tracked callback.
Generated copy of pinned MetalFramebufferView wires this helper; vendor stays
pristine and component license/IOS notices retained. Controller disables frames/
input, waits actual RFB tasks, THEN closes Metal admission and waits before the
retained transport completion. Restart reopens only after drain, and refuses a
reported view GPU failure. Source flag IDECK_LAB_METAL_DRAIN is opt-in, default0;
`build-hybrid-linux-runtime.py --metal-drain` enables only Linux adapters.

**Discriminating test.** Actual HOST physical Metal device/queue, real4096-byte
blit and readback, two commands submitted after admission closure, two drain
subscribers, rejection of additional commands and reentrant reopen, then third
real command in reopened wave. Naturally0/PASS. Final bounded run0.132s is a
microtest host observation, NOT Steam/iPad performance. Sandbox MTLCreateSystem-
DefaultDevice initially returned nil/77 (unavailable, not success); normal host
GPU test passes without changing settings. Latest final source passes again.
This validates command + main accounting only, NOT driver thread destruction,
all native GPU resources, storage writer boundaries or permission to start Wine.

Actual iOS adapter compilation and full combined App36 pass. FINAL full Mach-O
has the real drain methods and both distinct current identities; immutable
run35/hybrid36-unsigned/Madeira.app SHA256:
de7db5cea7f02225845bf4c540ed31a06388bc236c246c1dd1139572f6a7acaf.
App36 UNSIGNED/UNINSTALLED (do not substitute for a user-selected artifact).
Default controller without Metal flag also actually compiles, no new category
calls. One sandbox Xcode attempt failed workspace/service access before build;
normal native Xcode build passes, no simulator substitution/system setting edits.
Python syntax and git diff --check pass. No full default-app rebuild claimed35.

### Reproduce using new private outputs, no live-session interruption

```sh
python3 experiments/linux-steam/tools/build-hybrid-linux-runtime.py \
  "$PRIVATE_LAB/run29/namespace-ios-v5" "$PRIVATE_LAB" "$NEW_LINUX_OUT" \
  --ninja "$PRIVATE_TOOLS/ninja" --metal-drain
python3 experiments/linux-steam/tools/build-hybrid-app.py \
  "$PREPARED_PAYLOAD_ROOT" "$NEW_LINUX_OUT" "$PRIVATE_LAB" "$NEW_APP_OUT" \
  --dependency-root "$PINNED_READONLY_DEPENDENCY_ROOT" \
  --llvm-mingw "$EXISTING_LLVM_MINGW" --build-number 36 --build
xcrun clang -fobjc-arc -fblocks -Wall -Wextra -Werror \
  -Iexperiments/linux-steam/app experiments/linux-steam/app/LabMetalDrain.m \
  experiments/linux-steam/tools/metal-drain-control.m \
  -framework Foundation -framework Metal -o "$NEW_METAL_CONTROL"
"$NEW_METAL_CONTROL"
```

Helpers require mounted external paths/new output and exact pinned inputs;
see private prepare-evidence/commands for concrete local payload/dependency roots.
Keep new builds large caches external. Manual packaging must use existing exact
main/helper profiles and a disposable copy; never invent an absent entitlement.
Source README/build instructions, not public binary permission. The unresolved
LinuxRunner/component proprietary-converter exception still blocks distributing
a combined binary; no new exception is granted for third-party work.

**Next.** If the pending upgrade permission arrives, revalidate old exact Lab
identity, preserve its data, install only the selected qualified experimental
artifact and exercise real Air ELF/Steam/input/close/restart with private logs.
Current35 is signed;36 is a separately qualified unsigned candidate and must be
signed/profile-rechecked before selecting it. Do not interrupt merely because
old observer tools lack a session handle. Meanwhile finish explicit shared-game
storage ownership and the actual existing Madeira initialization/JIT/license
contract. Diagnostic125 must remain visibly NOT game execution until a genuine
Steam-owned request reaches a supported authenticated Madeira launch. No secret
transfer, fake ticket, Proton replacement, one-session reset or FEX patch.
Repeated Air Library/BPM, Play->legitimate game->return/stability remain NOT
verified. No STABLE_SUCCESS, task unload, GO or goal completion.

## Run36 — actual ARM64 shared-library I/O and combined App37

**State.** Parent/published815ddc555d7a1c3e10fdc067bf0ebf395ca0fdf7; remote
experiment815ddc5/main2ac39be re-read. VolumeUUID580CADCD-33F5-4D78-9530-
2287615873CA mounted, migration complete. Weekday2026-11-11 13:45EST remains
outside commit/push window; Run34–36 preserved dirty/uncommitted. Previous goal
turn made real progress (combined35/36 + actual host GPU boundary), not a wait.
This run also makes implementation/execution progress. Full goal ACTIVE.

**Observed problem/hypothesis.** Linux root uses fakefs metadata. Handing its
backing data directory directly to a native Windows writer could leave Linux's
metadata inconsistent after native creation/rename. A SEPARATE realfs-mounted
Steam library should allow both engines to see the same ordinary files without
editing fakefs's metadata from the native side. This does not itself serialize
writers or authorize any game. Do not migrate existing default downloads to test
that hypothesis, especially while Air's old user session remains live.

**Minimal patch.** New SharedSteamLibrary.c mounts exactly
`<Lab Linux image root>/SharedSteamLibrary` at `/mnt/ideck/SteamLibrary` using
pinned LinuxRunner realfs. Creates private directories/empty guest mountpoint,
refuses hiding existing mountpoint files and duplicate native-lifetime mount.
Initial Linux owner only, before guest children; retained root keeps this mount
without remount/reset. Existing `/Steam`, client/auth/config, game files and
prefix are not copied, moved or silently registered as a new Steam library.
This is a normal VFS mount inside LinuxRunner, not Darwin/iOS mount changes.
No FEX, Wine, Valve/vendor source, lock/security setting or credential operation.

New source flag IDECK_LAB_SHARED_LIBRARY defaults0. Actual LinuxLabRuntime
calls it after native init/root and before child execution. Qualified runtime
builder enables it only through explicit --shared-library, Linux-only flags,
adding the helper object. Normal app/project/default runtime remain unchanged.

**Discriminating tests, actual execution.** Freestanding static ARM64 ELF SHA256
f0ff60e5ca3bb49425effefe1498d27c76538b4297d747040c7a50710de5c7d9:

1. HOST control constructs scratch fakefs root via existing LabDeviceFS schema,
   imports executable through Linux VFS, mounts the separate realfs library,
   executes real ARM64 instructions/syscalls. Guest reads native seed, creates
   directory with spaces, writes/fsyncs/closes, renames staging->installed;
   real fork child writes and parent wait4 joins it. Native checks actual bytes,
   rename and child's output. A second SERIAL native process over the SAME
   scratch data reads a newly written native seed, repeats and produces changed
   bytes. Final natural statuses0/0,0.501/0.082s HOST-only microtest timings.
2. SAME ELF through the **actual LinuxLabRuntime entry** with shared flag and
   scratch realfs root also completes two serial native processes. Stage/initial
   wait status0, original repeat-start guard still-16. Native sees actual guest
   writes/rename/child output; final natural0/0,0.257/0.041s host timings.
3. Both controls use ASan/UBSan with no recovery on OWN wrapper/helper code;
   pinned static dependencies are not sanitizer rebuilt. Kernel/engine/fakefs
   hashes recorded before/after and unchanged. These are NOT same-process Linux
   frontend restart, all-native teardown, Windows/Wine writes, Steam depot,
   Steamworks/licensing, physical Air or game-return/stability evidence.

Initial test helper lacked parent output creation; fixed. Resolving the ld.lld
symlink to generic lld lost the tool basename and failed before any guest; keep
its absolute ld.lld path (no symlink resolution). Failed attempt retained, not
runtime failure evidence. Final commands and exact archive hashes in receipts.
No tests use existing games/accounts or imply ownership from fixture AppIDs.

**iOS final artifact/regressions.** New namespaced iOS adapters compile; full
combined App37 builds unsigned. FINAL actual Mach-O has unique shared-mount
implementation, real do_mount call, Linux TLS distinct from Wine global and GPU
boundary methods. Immutable private run36/hybrid37-unsigned/Madeira.app SHA256
7cafbe4278cfbbd0c7587775d7b07bb9d544782c0467da52bfeed246ebd528a4.
Display iDeck Linux Lab; source bundle .linuxlab. UNSIGNED/UNINSTALLED. App35
signed and immutable35/36 preserved. Actual default iOS runtime object compiles
with new flag absent and NO shared-mount reference. Python syntax/diff checks
pass. Full default-app rebuild and Air runtime validation NOT claimed.

**Auth/launch contract findings.** Existing MadeiraDock.swift explicitly loads
Valve's genuine Windows client and invokes Valve LaunchApp under a legitimate
Windows client sign-in. Linux Steam's saved login is NOT that session or an
ownership certificate. ContentView's normal full launch requires JIT and its
existing initialization sequence, not merely wine_process_start. Current Dock
prefix is this App's Documents/wine; SteamUIExperiment can select wine-steam64.
Any future bridge must choose a separate Lab prefix and legitimate user sign-in
explicitly; no Linux/other-app token conversion or copying. Native GameFiles can
accept an explicit shared common-directory capability, but legacy
GameFiles_from_data looks under fakefs data and MUST NOT be mistaken for this
new mount's native source. Shared library is not yet registered in genuine
Steam or connected to the diagnostic GameFilePolicy. Bridge still returns125;
no actual game/start/return implementation credit from these storage tests.

**Air/current user gate.** ONE readonly query confirms success and SAME old
Lab23/4952/installB265FEBE. Revalidate before future action. No Air input,
stop/restart/upgrade/signing/auth action this run. The previous concrete
combined35 + subsequent same-Lab-iteration choice remains unanswered; no repeat,
inferred consent or substitution37. Preserve current authenticated user session,
production/phone/Mac Allocator and all worktrees. User-only boundary unchanged;
independent storage/contract implementation advanced meanwhile.

Reproduce in NEW external scratch outputs (no running-binary overwrite):

```sh
python3 experiments/linux-steam/tools/test-shared-library.py \
  "$PRIVATE_LAB" "$NEW_FAKEFS_OUT" --ld-lld "$PRIVATE_LAB/tool-bin/ld.lld"
python3 experiments/linux-steam/tools/test-shared-library.py \
  "$PRIVATE_LAB" "$NEW_RUNTIME_OUT" --ld-lld "$PRIVATE_LAB/tool-bin/ld.lld" \
  --runtime-entry
# Qualified Linux builder from Run35 accepts both --metal-drain --shared-library.
# Private combined app builder accepts --build-number 37; audit FINAL artifact.
```

**Next experiment.** Wire explicit shared-directory capabilities/path mapping
into a captured Steam launch request, with an actual exclusive runtime/writer
handoff and existing Madeira init/JIT/auth contract, not a synthetic successful
exit. A real on-Air selected qualified Lab upgrade/UI/close/restart still awaits
that unanswered current-session choice. No new profile/identity assumed, no
one-session reset, credential/Guard automation or DRM workaround. Converter
exception scope still unresolved for combined binary distribution. Full repeated
Air Library/BPM/input + licensed Madeira game + return remains unverified. No
STABLE_SUCCESS.json, scheduler unload, final GO or goal completion.

## Run37 — real guest IPC captures shared-game request; final native receiver linked

**Continuation/state.** Previous turn made source/execution progress (Run36
shared realfs/ARM64 controls/App37), not a wait. This run continues that work,
including the later repeated user instruction; no second researcher/experiment.
Published/source parent815ddc555d7a1c3e10fdc067bf0ebf395ca0fdf7, remote experiment
815ddc5/main2ac39be rechecked. Mounted UUID580CADCD-33F5-4D78-9530-2287615873CA
and completed migration confirmed. Run34–37 remain dirty/uncommitted/unpushed
outside weekday22–08 (latest check2026-11-11 16:25EST). Preserve all worktrees.
CLI-only ordinary app interoperability work, no FEX/Valve/vendor/security/lock/
Codex state or credential/Guard/trust changes. Full Air/game/return goal ACTIVE.

**Observed failure/hypothesis.** Native GameFiles_from_data still looked for
shared games UNDER fakefs data, whereas Run36 deliberately mounted a separate
native library outside it. Also, the diagnostic bridge discarded the request
once inspected. Explicit native library roots and a single owned request slot
should deliver real guest launch metadata to a later sequential Madeira host
without moving downloads or confusing receipt with execution/licensing.

**Minimal implementation.**

- SharedSteamLibrary now exposes a native-only directory-preparation API, usable
  BEFORE Linux init. Controller explicitly registers BOTH data and separate
  shared-library directory descriptors; mount reuses the same fixed path.
- GameFiles_from_roots resolves shared steamapps/common from that explicit root.
  Existing from_data API delegates with no new root, preserving legacy/default
  routes. Neither a PE identity nor a directory capability is license proof.
- GameFilePolicy retains one bounded8216-byte owned request snapshot. Slot is
  reserved under its existing mutex before file inspection, so concurrent work
  cannot overwrite or later repopulate a discarded slot with an old in-flight
  inspection. Native peek/discard are source APIs; discard is not game exit.
- Explicit --capture-launch requires --shared-library AND --metal-drain. All
  new flags affect Linux adapters only; capture/native-file flags default0.
  Actual guest device bridge inspects the request and emits only categorical
  counters/status/library/machine, never raw argv/frame. Arguments stay in app
  memory for the launch contract; no full request persistence/logging.
- Guest protocol remains V1, response **125, NOT launched**. No fabricated
  accepted-game status, shell command, ticket, ownership or exit result.

**Actual discriminating execution.** New freestanding ARM64 program uses the
REAL /dev/ideck-madeira write/read path in LinuxLabRuntime, not a native function
substitute. Native inspection opens a real own x86-64 Windows PE fixture from the
new shared source. Guest checks full16-byte response including125, exits0;
native host reads the owned request (AppID0x70000001 is a synthetic test ID,
not a Steam license), verifies arguments/folder and observes machine0x8664.
One request remains intact while busy; explicit native discard permits next.
Two concurrent native callers produce one pending slot and complete their joins,
then a new request can be captured. Ordinary/default GameFiles routes tested
positively alongside the new explicit shared source.

Latest actual controls use the SAME pre-init shared preparation and registration
as the controller. Capture ON and OFF naturally0. OFF still performs real device
IPC/file observation, returns125 and reports no pending request. Own wrappers/
helpers use ASan/UBSan without recovery; pinned static dependencies are not
sanitizer rebuilt. Before/after kernel/engine/fakefs input hashes unchanged.
Existing real fakefs-root/shared-files ELF roundtrip also repeats naturally0/0
after preparation refactor (0.612/0.197s HOST microtest, not Steam/Air performance).
Own PE fixture uses ExitProcess(7), but was only INSPECTED, NEVER executed. No
Steam client/login/owned game/physical-Air milestone follows from these tests.

One OFF-test initially expected Linux EAGAIN=-11 from a NATIVE POSIX API. Darwin
returns -EAGAIN=-35. Corrected the test to native errno, not production code;
that failed control is retained, not reported as a runtime capture defect.
No cybersecurity/attack test suite was run; these are normal valid-workflow
interoperability/concurrency controls over fresh private scratch data.

**Final-link discriminator and correction.** First full App38 built but final
nm showed native pending getter ABSENT: no product caller, hidden unused code
was stripped. A marker/build pass would have missed that missing receiver.
Added the REAL retained-owner post-frontend call to peek; only request sequence,
AppID/error and explicit not-started category enter the private result. Native
status says "Play request captured; Windows has not started." This callback is
not a runtime/writer/auth grant. Rebuilt qualified adapters and full App38.

FINAL actual Mach-O now has unique native shared-registration, roots resolver,
pre-init preparation and pending getter definitions, plus distinct Wine global
and Linux TLS. Actual final calls are present: guest bridge->inspection,
controller->shared registration and retained owner->pending getter, one each.
Immutable private run37/hybrid38-unsigned/Madeira.app SHA256:
fd4f26d0338f8ffd30795d874ba500923aab59ee0de6652150b8ab161d466824.
UNSIGNED/UNINSTALLED. Signed35 and immutable35/36/37 preserved. Default iOS
controller actually compiles with new flags0 and no receiver/registration refs.
Python syntax/diff checks pass; no full default-app runtime/regression claim.
The final auditor's tool handle later went missing; its completed final receipt
and call snippets exist. It was NOT restarted and no crash inferred.

**Device evidence/user gate.** ONE readonly Air process query confirms old
Lab23/4952/installB265FEBE. Additionally only the Lab's own last-native-log.json
receipt was copied read-only: build23/pid4952. It has no usable health_file path,
so no health transfer/CPU/UI inference. No Steam account/config/log extraction,
input/stop/restart/install/signing/auth action. No phone/production/Mac Allocator
change. Model/iPadOS remain historical target Air4/iPad13,1/27.2(24B119), not
freshly re-queried model/OS. Existing combined35 + subsequent same-Lab-iteration
choice remains unanswered. Never repeat it/infer consent from continue/time or
silently select38. Preserve the live user session and revalidate before actions.

**Reproduce with new external outputs.**

```sh
python3 experiments/linux-steam/tools/test-capture-launch.py \
  "$PRIVATE_LAB" "$NEW_CAPTURE_OUT" --ld-lld "$PRIVATE_LAB/tool-bin/ld.lld" \
  --mingw "$EXISTING_LLVM_MINGW/bin/x86_64-w64-mingw32-clang"
# New separate output + --capture-off checks the noncapture device IPC route.
# Qualified Linux builder: --metal-drain --shared-library --capture-launch.
# Private combined app builder: --build-number 38; inspect FINAL methods/calls.
```

**Remaining/full objective.** Captured path is still Linux syntax; native host
must map it using the shared directory, re-open/revalidate after ACTUAL writer
handoff, prepare the isolated Windows prefix/library metadata, and use existing
Madeira init/JIT plus genuine Windows Steam/Dock sign-in and LaunchApp. Linux
login, request AppID/PE and DORMANT alone do not authorize this. No secret copying,
Steamworks spoofing, DRM bypass, FEX edit or one-session reset. Native discard
control is source/host-tested, not an on-device cancellation/game-exit workflow.
Steam shared-library registration, Windows game execution, actual Wine teardown,
Linux return and repeated game cycles are STILL unimplemented/unverified. No
UI/Library/BPM/stability credit for compile/host/capture. Converter/component
exception scope still blocks combined binary distribution. No STABLE_SUCCESS,
scheduler unload, GO or goal completion. Next actual device upgrade remains at
the pending user choice; continue real host-side handoff implementation meanwhile.

## Run38 — C-contained shared library, Windows mapping and real Dock discovery

**State/previous turn.** Run37 was implementation/execution progress, not a
wait. Parent815ddc555d7a1c3e10fdc067bf0ebf395ca0fdf7; origin experiment815ddc5/
main2ac39be and all worktree heads re-read. VolumeUUID580CADCD-33F5-4D78-9530-
2287615873CA/migration verified. No overlapping researcher. CLI only, no FEX/
Valve/vendor/Codex-state/security/lock/credential/Guard/trust actions. Source
work remains isolated; publication may occur now that local clock is after22:00
2026-11-11. Verify fresh clock EACH commit/push; actual Git/remote receipt is
publication evidence. Full Air/game/return goal remains ACTIVE/incomplete.

**Observed architecture constraint.** Existing MadeiraDock.games resolves each
library and accepts only folders physically within its drive_c. Therefore simply
symlinking C:\SteamLibrary to Run36's external shared source is rejected. Do not
remove that ordinary-path guard. Existing WineProcessBridge argument parser also
supports quote grouping despite an older Dock comment saying space-only; do not
base a new argv transport on that stale comment. Windows launch/auth is still
through existing Madeira initialization and Valve LaunchApp, not direct unauthenticated
execution merely because the filename can be mapped.

**Hypothesis/minimal change.** Add explicit **--dock-storage** requiring capture,
shared-library and Metal-boundary flags. Default old layout stays unchanged.
New physical source is `<Lab root>/MadeiraPrefix/drive_c/SteamLibrary`, still
mounted at the SAME guest /mnt/ideck/SteamLibrary. Refuses any existing old
`<Lab root>/SharedSteamLibrary`, even before creating the new prefix; no silent
migration or hiding prior downloads. Registered native descriptor, not guest
path, selects it. Native rootfs fakefs data remains separate.

WindowsLaunchMap converts only that shared library's install/executable/working
paths to C:\SteamLibrary\steamapps\common; preserves NUL-separated argument
boundaries and maps known shared paths. Other arguments stay verbatim; no shell
or MADEIRA_ARGS string is produced. Default /Steam needs a separate storage
contract and is not silently mapped/copied. This is metadata, not a file/license/
writer/runtime authorization or a guarantee all Windows argument forms work.

LabWindowsLibrary prepares the isolated native prefix alias Documents/wine ->
Lab MadeiraPrefix, and only if absent creates the Windows client's libraryfolders
metadata pointing at C:\SteamLibrary. It preserves existing settings byte-for-byte,
accepts its existing matching alias, and refuses an existing different Windows
prefix without replacing data. The client directory constant is read from actual
SteamRuntimeFiles.relativeRoot (`Program Files (x86)/Steam`) at build time, not
assumed or copied from Linux auth. No AppID/license claim is written by this
helper. Existing settings are retained even if different; real Dock discovery
must still verify the library. Native controller invokes mapping/binding only
after captured request plus successful retained frontend return/DORMANT; report
contains categorical errors/counts, not raw argv. This prepares metadata only,
NOT permission to start Wine or exclusive shared writers. Protocol remains125.

**Actual tests/evidence.**

- Real ARM64 ELF/device IPC/capture repeats over the NEW physical C-contained
  storage. Own PE fixture inspected, Windows path/argv0/--level/"1 2" boundaries
  checked, native concurrency/next slot and old/default routes pass. Additional
  normal existing-layout fixture is retained and new layout refused without
  creating its replacement. Old-layout capture control separately passes.
  Wrappers/helper ASan/UBSan nonrecovering; static deps not instrumented. Before/
  after archive hashes unchanged. Neither probe is a licensed Steam game.
- Actual HOST Foundation prefix binding, alias identity, fresh config creation,
  idempotence, preserved changed settings and existing prefix/save retention pass.
  Original test input had been mutated by a partial earlier attempt; final test
  makes a NEW own-fixture-only scratch root, never copies user auth/data.
- Restricted execution's existing-settings atomic write reports Cocoa513 despite
  native owner/mode0644/no flags. Normal host execution passes WITHOUT chmod,
  trust/sandbox/system-setting changes. This is a test-environment boundary,
  not a claimed iPad fix. Failed attempts retained, not counted as success.
- Compile EXACT selected production DockGame/validAppID/validFolderName/game/
  depots/games/libraryRelative methods plus actual SteamKeyValues parser. Real
  generated Windows config discovers the C-contained synthetic manifest and
  correct C:\SteamLibrary install path. No permissive replacement of the guard.
  This is selected-method HOST discovery, not full Windows Steam/Valve acceptance,
  authentication, ownership, launch, gameplay or iOS execution. Synthetic fixture
  AppID0x70000001 remains test data only, outside the repository/application data.
- Read-only prepared prefix-template inventory138 entries: zero SteamLibrary or
  libraryfolders.vdf entries. This checks member-name collision only, NOT actual
  Wine initialization. No archive payload/account/registry content extracted.

**Full final iOS artifact.** Qualified namespaced Linux adapters and full combined
App39 pass. FINAL Mach-O has real binding/mapping definitions AND actual calls,
plus distinct Linux TLS/Wine global. Immutable private
run38/hybrid39-unsigned/Madeira.app SHA256:
ed727d64a7dcff813e1b60577385501ac39deb817ceb6c28001e39a72e6049ef.
UNSIGNED/UNINSTALLED. Old signed35/immutable35–38 retained. Actual iOS controller
with Dock-storage flag OFF compiles with no new mapper/binder refs. Python syntax/
diff checks pass; no full default app/device runtime success claim. Windows PE
fixture was never executed. No real Steam library registration/game-return proof.

**Air/user boundary.** ONE read-only query still confirms old Lab23/4952/install
B265FEBE. No device input, upgrade/stop/restart, auth/log transfer or signing this
run. Historical Air4/iPad13,1/27.2 remains target information, not a fresh OS query.
Pending combined35 + subsequent same-Lab-iteration choice is still unanswered;
no repeat/inferred consent from continue/time or silent selected-artifact
substitution39. Keep user session, production/phone/Mac Allocator/auth/games/saves.

Reproduce using NEW external outputs:

```sh
python3 experiments/linux-steam/tools/test-capture-launch.py \
  "$PRIVATE_LAB" "$NEW_CAPTURE_OUT" --ld-lld "$PRIVATE_LAB/tool-bin/ld.lld" \
  --mingw "$EXISTING_LLVM_MINGW/bin/x86_64-w64-mingw32-clang" --dock-storage
python3 experiments/linux-steam/tools/test-windows-library.py \
  "$NEW_CAPTURE_OUT/scratch-root" "$NEW_WINDOWS_METADATA_OUT"
# Qualified builder: --metal-drain --shared-library --capture-launch --dock-storage.
# Full private app builder: --build-number 39; verify FINAL calls, not just markers.
```

**Next/full goal.** Bring existing supported Madeira setup/auth/JIT UI into an
explicit isolated cold-start mode before attempting game handoff; it must not
initialize Linux simultaneously, auto-enter credentials or reset one-session
state. Then connect real Steam Play receipt -> clean frontend shutdown/exclusive
writer/runtime handoff -> legitimate Valve Windows client LaunchApp. Native
Windows UI/setup, actual Wine execution/teardown, same-app Linux return and repeated
licensed-game cycles are STILL incomplete. Linux shared-library registration and
existing default-library migration are not silently supplied by this metadata
helper. Actual Air testing remains at the explicit pending upgrade choice. No
secret copying, DRM/auth bypass, FEX edit or binary-license-exception expansion.
Combined binary distribution still blocked by unresolved component/converter
exception scope. No STABLE_SUCCESS, scheduler unload, final GO or goal completion.

### Run38 final-package correction after source checkpoint18f1aef

Scoped source checkpoint **18f1aef733d1831bdad73217dad5a3b5ca5feb00** was signed
off and pushed/read back on origin/experiment/linux-steam-madeira-ipad at
2026-11-11 22:23EST; remote main2ac39be unchanged. It publishes the Run34–38 source
controls, not device/game success. Private run38/source-publication.json records
actual remote readback. New findings below require a following scoped correction.

**Actual boot blocker, not link failure.** Read-only final App39 inspection found
NO LinuxLabRootFSSHA256 Info key and NO LabCompatibility/ideck-madeira,
compatibilitytool.vdf or toolmanifest.vdf. The full-link generator had not carried
the standalone Lab's boot packaging into the combined target. Earlier combined
App35–39 build/sign/link evidence is STILL valid only in that narrow scope;
none is a qualified frontend deployment candidate. In particular signed35 is
historical, **DO NOT INSTALL it** as a functional frontend. No user test/install
was interrupted by this discovery. A successful Mach-O link cannot detect missing
NSBundle resources or configuration; no prior device failure was invented.

**Smallest correction.** build-hybrid-app.py now reads the rootfs pin from ACTUAL
qualified Linux compile flags, writes it to its PRIVATE Info.plist, compiles the
existing OWN compatibility tool as real static ARM64 ELF, copies the exact two
tracked VDFs and wires that folder into the ACTUAL main PBX resource phase.
No Valve/rootfs/auth asset is bundled/copied. Actual phase identifier A3000003
was inspected, no ordinary source project change. Generator verifies FINAL
processed Info and resource hashes/ELF, not just prepared inputs. New read-only
verify-hybrid-package.py is reusable after a manual build, packaging or re-sign.

**Discriminating artifact test.** Real old App39 is rejected for missing compiled
pin. Fresh full App40 built FROM THE GENERATOR, not a hand-repaired reused product,
passes: final pin equals compiled macro, all three real resource hashes match,
compatibility tool ELF64/little-endian/e_machine183 (ARM64). Full build and actual
final runtime definitions also checked. This establishes required package inputs,
NOT successful on-device bootstrap/Steam/UI/game or licensing. Rootfs archive
remains private input in the existing app container, not in this app/repository.
See run38/hybrid40/package-validation.json and final40-linked.json for exact
final artifact/resource hashes. Preserve immutable unsigned40; prepare a separate
matching-profile .freshtest signing copy only. Recheck existing Air main/helper
profile expiry/device/identity; no account/trust/security changes.

Corrected40 is the prospective candidate, superseding broken-packaging35–39.
The pending user choice still governs ending old Lab23 before any upgrade. No
silent substitution, no new ask/repeated unlock request, no install/sign success
inferred from unsigned validation. Full original goal remains active and unmet.

Corrected40 final unsigned Mach-O SHA256
6cd4ea83aab910d3b1714f952ff21b0a6ab837d9a189b29b23d10a553e294516.
Matching existing Air main/helper profiles and development identity revalidated;
disposable .freshtest App40 signing + normal-environment deep-strict verification
return0, post-sign resource/pin/ARM64 verification also passes. Signed Mach-O
hash is in EVIDENCE.run38.packaging_correction.signing/sign40-verified.json.
**Signed40 NOT installed**, old Lab23 unchanged. No account/key/trust setting,
private entitlement, user-data migration or credential/Guard action. Old signed35
remains retained evidence only. Actual on-Air ELF/UI/game/return still unverified.


## Run39 — cold native setup, actual installer prefix conflict and isolated callback

**Scope/source/device.** Parent/source checkpoint
`4f57a96521a564afb5791def8d6d3dd70237d9a7`; origin experiment same and main
`2ac39beff91251d36f3ad6331d3f8402b3c10e18` on fresh readback. Migration complete,
required easystore UUID verified before writes. Same pinned Linux/Wine/FEX inputs,
ordinary source/main/other worktrees untouched. One read-only Air process receipt
still identifies old Lab23 PID4952 at its B265FEBE installation. This is process
identity evidence, not a fresh interactive/stability result. No device input,
stop, install, restart, credentials, Guard, trust, lock or settings change.

**Missing prerequisite/hypothesis.** A metadata-only Linux bridge cannot use a
fresh Madeira runtime until this isolated app has its own native setup, JIT and
legitimate Windows Steam authentication. Reusing the existing native UI in an
explicit cold process should establish that setup path without starting Linux or
resetting either engine's single-session state. It does not itself execute a
captured game request or prove Windows Steamworks interoperability.

**Smallest implementation.** The private full-app generator's new
`--madeira-setup` option adds `LabMadeiraSetup.swift` and a C startup selector ONLY
to its main target. Explicit `madeira-linux-lab-setup` is mutually exclusive with
Linux/other Madeira experiment arguments. It branches before the retained-Linux
argument guard, requires the Linux stage still be `idle`, prepares the existing
pinned private root and known native library binding, then presents the real
existing `ContentView`. Same original Metal-HUD/screen bootstrap, controller,
hardware input and authorized JIT URL handlers; no mock UI or credential entry.
The native ready notification drains at most16 queued URLs in memory; no raw URL
or account payload logging. `last-cold-setup.json` records categorical initial
setup facts only; it is NOT a continuing game-status monitor. UI actions remain
user-controlled. The original auto-start rule already excludes `madeira-` args;
no stored auto-start preference is overwritten to implement this exclusion.
The original IDeckState's own first-run preference initialization is unchanged.

**Discriminator exposed a real filesystem mismatch.** Run38's binding puts
`Documents/wine` at a symlink to the physical Lab `MadeiraPrefix`. The exact
production `SteamRuntimeFiles.destination` rejects that logical path. Read-only
source inspection also finds the initial root/hive checks in
`SteamRuntimeInstaller.prepare` and PE checks in `SteamUIExperiment.isPE` require
physical paths. This is a HOST reproduced installation prerequisite failure,
not an invented Air crash or evidence that authentication/networking failed.
App41 compiled/linked/packages correctly but cannot be treated as a qualified
native-setup candidate on that basis.

**Minimal targeted adaptation.** New `LabMadeiraPrefix` resolves only the known
`Documents/wine` -> this Lab's `LinuxSteamRootFS/MadeiraPrefix` binding. An
unrelated prefix/binding is returned unchanged. With `--madeira-setup`, the
builder wraps the two exact native prefix entry expressions in its PRIVATE
copies of `MadeiraDock.prefix` and `SteamUIExperiment.runtimePrefix`; source
contract drift aborts preparation. Production app sources, installer/PE/path
checks, FEX/Wine/vendor and original prefixes are not changed. The existing Dock
installer actually calls `prepare(prefix: MadeiraDock.prefix)`. Its downstream
checks now receive the physical Lab path rather than being removed/weakened.
Host control reproduces the old rejection, then the same exact method accepts
the physical-prefix destination, with ordinary/other-binding behavior unchanged.
No full network installer, native registry/Wine initialization or license result
is inferred from this test.

**Callback integration.** Existing inherited registered schemes include
`madeira-steamui`; when this Lab is re-signed as `.freshtest`, the actual callback
selector can prefer that working-app scheme. The cold Lab now registers ONLY
`ideck-linux-lab`, retained across a bundle-ID override. Exact existing callback
selection is tested, and final package validation checks the real processed
Info.plist. No external app or signing identity is changed. This is application
routing, not evidence of physical JIT approval or successful callback delivery.

**Local controls.** Own C mode selector compiled/run under ASan/UBSan and exact
selected production Swift auto-start/callback methods pass. Actual iOS entry
compiled with the new feature OFF has no cold-setup factory/URL/selector
references. Full unsigned App41 and42 build; real final41 C/Swift definitions
and ARM64 call sites, separate Linux TLS/Wine global `current`, rootfs pin and
all three own boot resources were inspected. App42 includes physical prefix
adaptation but precedes the isolated callback metadata correction. These are
retained intermediate artifacts, not device/UI success. Final corrected App43
results and exact hashes are recorded in the run39 evidence below/JSON.

**Reproduce with NEW private outputs.**

```sh
python3 experiments/linux-steam/tools/test-cold-setup-policy.py "$NEW_POLICY_OUT"
python3 experiments/linux-steam/tools/test-native-prefix.py "$NEW_PREFIX_OUT"
python3 experiments/linux-steam/tools/build-hybrid-app.py \
  "$PREPARED_PAYLOAD_CHECKOUT" "$QUALIFIED_DOCK_IOS" "$PRIVATE_LAB" \
  "$NEW_HYBRID_OUT" --dependency-root "$PINNED_DEPS" \
  --llvm-mingw "$EXISTING_LLVM_MINGW" --build-number 43 --madeira-setup --build
python3 experiments/linux-steam/tools/verify-hybrid-package.py \
  "$NEW_HYBRID_OUT/xcode/Build/Products/Debug-iphoneos/Madeira.app" \
  "$NEW_HYBRID_OUT/prepare-evidence.json"
# Only after permission to end the preserved old Lab and a matching-profile
# installation, the cold setup launch argument is madeira-linux-lab-setup.
# Never combine it with linux-steam-retained-frontend or other diagnostics.
```

Private artifacts: `.madeira-install/linux-steam-ipad/run39`. The rootfs archive
still comes from the same Lab's existing private input; no Valve/account/cache
transfer or bundled Valve/rootfs payload. Real native setup UI, own Windows
auth/JIT, Steam Play -> exclusive-writer handoff -> genuine Windows game -> full
Wine teardown -> Linux frontend restore and repeated Air cycles all remain
unverified/incomplete. The existing user choice about ending the live old Lab
and upgrading/iterating is still pending; no repeated question or inferred consent
from continuation/time. Combined binary distribution remains blocked by unresolved
component/converter exception scope. No STABLE_SUCCESS or task completion.


Final corrected App43 full Xcode build returns0. Actual final Mach-O SHA256
`6f32f08afa0c7e61fe8101f18efadde2c6d5da90df210ad1e9732e40c283382a`.
Required processed Info/rootfs pin/three ARM64 compatibility resources and ONLY
`ideck-linux-lab` callback pass final package validation. Actual ARM64 calls to
the C selector, Swift controller/URL handlers and both canonical-prefix overloads
are present; Linux TLS and Wine global remain distinct. Swift symbol lookup had
to use demangling (the raw type name is compressed), not a source/binary fix.
No Air install/runtime result follows from these artifact checks.

Disposable private .freshtest App43 signing and deep-strict verification return0;
post-sign boot resource/callback checks pass. Actual embedded main/helper profiles
match their bundle IDs and cover Air. Existing profile expiry2026-11-13T04:43:44Z,
so recheck before later use; this cannot be extended by re-signing. Signed Mach-O
SHA256 `23a23d1f4088bc26c0434636a1b3a32c0f66678af3eebc23b8581a3c0ce1ad02`.
**Signed43 NOT installed**, old user Lab23 retained. No new profile/account/key/
trust/settings/credential changes or binary publication. Exact private signing
receipt/hash and limitations are in EVIDENCE.run39.


## Run40 — opt-in Linux Steam library registration before first guest

**Starting state.** Source/remote experiment b12d781f624f22e8ea96fa0cc8f43d5ce844eb7a;
remote main2ac39be and all unrelated worktrees retained. Verified migration status
and required mounted UUID before writes. Same pinned LinuxRunner/Wine/FEX input
revisions; no vendor/FEX/Valve or ordinary app source edits. ONE current read-only
Air query still matches old Lab23 PID4952/B265FEBE. This does not establish live
interaction/stability. Existing user upgrade choice remains unanswered; no stop,
input, install, auth/Guard/trust, lock/settings action or repeated unlock request.

**Observed gap/hypothesis.** Shared realfs mount + Windows metadata mapping alone
cannot make Steam install to the mapped location. Default /Steam games are not
silently supported by the C-contained mapper. Register the fixed shared library
in Linux Steam's own libraryfolders.vdf before its first guest starts, then test
whether Valve actually sees/uses it. This run implements the registration, not
existing-game migration or a download-manager handoff.

**Minimal isolated implementation.** New --register-shared-library in the qualified
runtime builder requires --dock-storage and its existing capture/shared/Metal
prerequisites. Flag OFF is unchanged. The initial LinuxLabRuntime frontend path
calls the registrar as native PID1 after the shared mount/tool preparation and
BEFORE any guest child. Retained frontend restart does not rewrite it. The cold
native setup route never initializes Linux, hence does not invoke it either.
PID1 is a caller condition, NOT an exclusive-writer certificate: caller must own
the private root before guest execution; never call this against a running Steam.

A bounded256KiB text KV planner keeps existing raw entries/comments/unknown fields,
uses an unused numeric index, and leaves an already registered location byte-for-
byte. A fresh file registers both /Steam and /mnt/ideck/SteamLibrary. Handles
ordinary quoted/unquoted tokens, braces in quoted values/comments, BOM, key case
and legacy flat entries. Incomplete/unsupported metadata fails before publication.
The native VFS adapter preserves an exact old-file backup, writes/verifies an
O_EXCL stage, rechecks old content before rename and retains original file mode.
It never removes another attempt's pre-existing stage/backup or migrates games,
accounts, default config trees or manifests. A retained old stage/backup requiring
attention causes a startup error, not blind retry/deletion. Categorical V1 numeric
error/changed marker only; no account/file payload in logs. New-file permissions
and backup are private. No filesystem durability/ownership/authentication/game
permission is inferred from successful close/rename.

**Discriminating HOST tests.** Actual fakefs mounted root plus the realfs shared
source; own wrapper/helper compiled with ASan/UBSan, static dependencies not
sanitizer-rebuilt. Fresh and merge cases each execute a real freestanding ARM64
Linux ELF through the interpreter; its Linux open/read/close sees the actual new
library configuration, native guest status0. Merge retains other library paths,
unknown fields and byte-exact backup plus file mode; repeat is byte-identical.
An interrupted-publication fixture retains original/stale stage and starts NO
guest; harness0 means only that preservation assertion passed. The exact existing
SteamKeyValues reader independently reads default/retained/shared entries. This
is NOT Valve-client library discovery or successful storage/download/UI/auth.
Additional ordinary metadata controls cover existing modern/legacy/BOM/key-case,
last duplicate path semantics, incomplete file and bounded output.

Initial harness compile missed fs/path.h for AT_PWD; fixed own control header,
not LinuxRunner/runtime. Earlier outputs remain private evidence. Final host
receipt is run40/library-registration4/evidence.json; logs and source/archive
hashes are in EVIDENCE.run40. No credentials or actual games were used.

**iOS/regression boundaries.** Final22 namespaced iOS arm64 adapter units compile
with registration ON and exact copied pinned archives retained. The actual
Runtime object compiled OFF has no registration receiver reference, while the ON
object does. Other shared mount reference remains present. These are component
results, not a full default app, device execution or runtime permission. Full
private App44 is built separately below; no result inferred while compiling.

Reproduce with NEW private outputs:

```sh
python3 experiments/linux-steam/tools/test-library-registration.py \
  "$PRIVATE_LAB" "$NEW_REGISTRATION_TEST" --ld-lld "$PRIVATE_LAB/tool-bin/ld.lld"
python3 experiments/linux-steam/tools/build-hybrid-linux-runtime.py \
  "$NAMESPACED_IOS_BASE" "$PRIVATE_LAB" "$NEW_REGISTERED_IOS" \
  --ninja "$EXISTING_NINJA" --metal-drain --shared-library --capture-launch \
  --dock-storage --register-shared-library
# Feed NEW_REGISTERED_IOS into build-hybrid-app.py --madeira-setup --build.
# Never edit a rootfs or overwrite an app that is still being tested.
```

**Remaining/full goal.** Real Valve storage UI/repair/update behavior and Windows
depot installation in this library remain unverified. No game license, Steam Play
invocation, Windows game execution, full Wine teardown/Linux restore or repeated
Air cycle is supplied by this metadata step. Bridge stays diagnostic125. Preserve
old Lab23 and pending choice; prepare/verify future candidate privately and recheck
profile expiry/device before any permitted install. No public combined binary
pending license scope resolution. No STABLE_SUCCESS, scheduler unload or goal
completion. Fresh local clock governs every commit/push; if validation completes
after08:00 weekday, leave the scoped edits uncommitted/unpushed.


Final full App44 Xcode build returns0. Actual unsigned Mach-O SHA256
`9f1fdeb62f4e59279a637fb016e1964bc1f28d97be0221debb024e961ccfaa39`;
real ARM64 calls to shared_library_register, shared_library_plan and native setup
controller are present, together with distinct Linux TLS/Wine global. Final
processed rootfs pin/own ARM64 resources/isolated callback all pass. This full
build reuses prepared Wine/FEX/DXMT payloads; it does not re-establish their source
provenance or validate an on-device game. Exact receipt/log/input hashes recorded.

A separate disposable .freshtest44 signature is prepared from that unsigned app.
Fresh existing main/helper development profiles, Air coverage and certificate
match verified, including embedded-profile readback. Deep-strict returns0 and
post-sign final resource/callback checks pass. Signed Mach-O SHA256
`07dbcc4e890c4921ef3ab379a462c705893437679c3ad065215ddf2b14f4605a`.
**Signed44 NOT installed**; old Lab23 unchanged. Existing profile expiry is
2026-11-13T04:43:44Z; recheck at any later use, no account/profile/trust workaround.
Signed43 retained as previous candidate;44 adds registration. Do not silently
install an earlier build just because it was already signed.

Validation finished outside the allowed weekday22:00–08:00 publication window.
Latest fresh local time recorded in EVIDENCE.run40.publication. New source/docs
remain UNCOMMITTED/UNPUSHED in this isolated worktree, HEAD/remote b12d781; no main
merge/force push or new wait automation. Preserve these edits for continuation.
No actual Valve acceptance, new Air interaction, native game or stable return
cycle was observed. User-only boundary remains the existing live-session upgrade
choice; do not repeat/infer consent or stop that session.


## Run41 — authorized Air upgrade; actual UIKit scene boot failure

User explicitly replied **允许结束旧 Lab 并升级**. This supersedes the previous
pending live-session choice; continue authorized isolated upgrades/iterations,
without repeating consent/unlock requests. Unrelated apps/main/auth/games/saves
remain preserved. Daytime source/docs stay uncommitted outside the repo window.

Fresh Air app/process/profile/certificate checks matched old Lab23 and prepared
signed44. SIGTERM request returned0; immediate process query was too early, later
exact identity query found it gone, so NO force-kill occurred. Do not count an
OS app termination as a clean Linux or game-return boundary. Same .freshtest app
upgraded to real version44, without uninstall/reset. Existing Linux image marker
copied before/after matches; this is concrete marker retention, not new saved-login
or byte-level save validation. No account cache/credential export or migration.

First CLI launch failed locally64 because --device followed the positional app
arguments. Correct ordering before the app ID led to actual launch PID16066.
This local command error is not an iPad trust/signature/entitlement/runtime failure.
Actual native CoreDevice screenshot then shows Home, process query finds no44,
new cold result absent and native receipt remains stale23. Normal .ips capture
identifies actual44 by exact final Mach-O UUID; UIKitCore SIGTRAP/EXC_BREAKPOINT
at UIApplicationEvaluateRuntimeIssueForNoSceneLifecycleAdoption. No Steam/CEF
initialization or current native setup success is inferred from the launch ACK.

**Single hypothesis/minimal fix.** Combined generator inherited a SwiftUI baseline
Info with no UIApplicationSceneManifest after replacing its App entry with UIKit.
Copy the exact manifest already used by the standalone working Linux Lab, whose
scene delegate is LinuxLabSceneDelegate. New final package gate checks it; actual
old44 fails. No runtime, Valve, Wine/FEX/vendor or ordinary gaming code change.
Fresh full45 builds from the corrected generator; signing/install/device test is
recorded separately below as it completes. Prior44 link/resource/signature proofs
remain narrow and do not establish boot validity. Raw crash/screenshots/profiles
and receipts remain private under run41; only categorical evidence/hashes published.


Full corrected45 Xcode and disposable Air signing/final scene delegate + processed
manifest/pin/resources/callback checks pass. Later failed44 background PID16106
appeared before replacement; inspected Home screenshot and still-stale23 receipt
before ending that failed startup instance with SIGTERM. No force-kill issued.
Actual45 install command timed out after175s; subsequent native app list remains44,
no Lab process alive, and actual screen shows the Lab **Loading…** placeholder.
This is an in-flight installer state, not a Linux crash or fix validation. No
second installation or blind app launch is started while it remains pending.


### Run41 controlled45 result and shared-mount discriminator

Installer later committed45, verified by actual app list; no second installation.
First activation PID16132 showed black while scene callbacks/main health ran with
zero Linux workers/guest entries. LLDB batch observer reached connected, not
stopped; expressions/window reads failed. Health advanced sequence8->31 afterward,
so no debugger window/JIT result or dead/stuck-process claim. SAME45 binary with
explicit fresh --terminate-existing cold args produced PID16153: actual native
setup UI screenshot + new receipt prefix_bound=true, linux_stage_idle=true,
Windows_game_started=false. This proves the extra UISceneClassName proposal was
not necessary; exact prior black activation cause remains unmeasured, including
whether activation reused an existing process without applying new args. Extra
46 compiled but was NEVER installed; removed only those own unneeded proposal/log
edits. Real scene-manifest fix retained; main.m matches actual device-tested45.
Apple's sceneClass documentation informed the proposal, not causal proof:
https://developer.apple.com/documentation/uikit/uisceneconfiguration/sceneclass
The displayed Windows Steam32 VA guard was not lowered or treated as Linux Steam
failure; no Windows client/game/JIT execution occurred in this setup test.

Next fresh45 linux-steam-retained-frontend PID16155 reached a native mount guard,
returned Linux ENOTEMPTY(-39), poisoned retained wave1 BEFORE guest execution.
Actual directory inventory is only steamapps/common/Control, final directory
empty, date2026-11-08; exact path is created by the old own compatibility probe.
No account/Steam UI success is inferred. Preserve the original empty-mount guard.

Minimal opt-in --retire-empty-probe (requires explicit registration/Dock flags)
validates only this exact empty probe chain through Linux VFS, then rmdir of
empty known dirs before mount. Each rmdir still refuses nonempty directories;
any file, other name or symlink stops without hiding contents. No native host
rmdir behind fakefs meta.db, no file/manifest/game/save/auth removal or migration,
no one-session reset or blind retry. New native marker reports only directories
retired and files_deleted=0. Default OFF keeps prior behavior.

Actual HOST sanitizer controls7 pass: OFF legacy refused and normal empty mount
works; ON full/partial known empty chains mount, normal empty works; a save-like
fixture file and unrelated directory cause refusal with all content retained.
Own wrappers sanitized, static archives not sanitizer rebuilt. Integrated actual
ARM64 ELF reads after cleanup->mount->registration pass fresh+merge; interrupted
publication harness0 means preservation and NO guest, not Steam success. Private
receipts empty-probe-control and empty-probe-registration carry exact hashes.
iOS/runtime/App47 results recorded as they complete; current failed45 session
preserved until a verified candidate is ready. No actual Steam/game/return proof.


### Run41 actual47 update and exact restart discriminator

Full App47 Xcode and matched Air signing/package checks pass; actual same-container
install returns0 and device app list confirms47. First PID16191 logs exact empty
probe cleanup3directories/files_deleted0 and registration error0/changed1. Actual
Air screenshot shows genuine Steam updater extracting its official package. This
is not login/Library/game validation.

Updater completes with Linux wait10752 (normal exit42), native_error0, backend
DORMANT4/reaped1, zero guest/worker entries and real RFB/Metal drain completion
marker. Existing UI nevertheless says cleanup failed because it only accepts
status0. This contradicts its own successful cleanup receipt. Valve steam.sh
in the preserved private official tree explicitly defines/restarts on42.

After completed cleanup, fresh SAME installed47 launch PID16203 preserves the
updated prefix/auth. Real screen advances saved-login splash -> desktop Steam
chrome, content black at latest sample; no interactive Library proof yet. Keep
this active session. Raw screens/logs/transport credentials remain private.

Minimal source correction admits Linux-only reentry for raw0 or10752 after all
existing DORMANT/native-error/owner/root/transport gates. An automatic update
restart is limited to ONE per native app lifetime, only42 after actual viewer
drain and no captured game request. Repeated42 requires an explicit button,
other exits never automatically retry. Game/native-Wine gate remains status0;
this is not game launch permission or complete runtime teardown. ASan/UBSan
classification control checks all65536 wait statuses, error/phase/null/negative
controls and passes. Patch is NOT installed; do not interrupt active47 for it.
Full next iOS build and actual navigation evidence remain pending. No stable
Library/BPM/game/return claim. New source/docs remain uncommitted outside window.


### Run41 Store render -> transport0x3000 -> native allocation abort

Existing bounded USB app-local RFB observer with its own ephemeral private
transport key captured genuine Steam Store rendering, followed by Unexpected
Transport Error0x3000. One ordinary Library pointer click visibly changed the
menu/content; content became black and the dialog persisted. This is real input
consumption, NOT an interactive usable Library/BPM. No credential/Guard action or
Continue Anyway/error suppression. Before/after images remain private.

Actual current native log first shows a2MiB shared host mmap fail native12/
Linux-12 near mono661867733, then network utility100 exits signal9. Subsequent
network utilities exec then exit127; their real stderr says libcef.so failed to
map segment. Do not confuse this later loader failure with the original failure.
A normal Exit Steam radio selection was visually confirmed, but confirmation
observer found the app-local port already closed; no successful normal exit
claimed. Exact actual47 PID16203 crash report confirms SIGABRT with stack
NSAllocateMemoryPages -> NSData initWithBytes -> LRRFBClient update. No jetsam
or successful frontend/game return is inferred. An unexpected new47 PID16392
was observed idle, zero guests/workers, Home screenshot; identity inspected and
preserved before any next action, no competing local experiment writer found.

**One targeted failure-path hypothesis.** Pinned realfs_mmap creates a native
mapping then returns pt_map's error without releasing it in three branches.
pt_map's metadata malloc failure does not take ownership; anonymous and SysV IPC
callers already release on failure. New private-copy --file-map-cleanup releases
ONLY its newly created mapping on rejected transfer, preserving error/errno.
No PTE/cap/FEX/Valve/vendor change or retry. Default is OFF. This does not explain
or repair the first host ENOMEM, and no sole-root-cause claim is made.

Exact pinned realfs_mmap function with host-only deterministic pt_map failure
and actual native mmap/self Mach region coverage reproduces three baseline leaks;
fixed three failures release their mappings, three successes remain transferred.
Both wrappers use ASan/UBSan; no failure injection reaches an app/device. Initial
Darwin mincore oracle was rejected (successful return need not mean coverage),
replaced with Mach VM coverage; an Apple/Linux macro header-order harness error
was fixed. Original failed artifacts retained, final hashes in evidence JSON.

All22 namespaced iOS units compile with cleanup enabled and immutable base
archives unchanged. New own log exposes public self region_count, internal,
external, reusable and compressed totals to distinguish region/physical pressure;
no guest/native contents or memory limits sampled/changed. Full unsigned48 update
policy build/package/link pass after actual sandbox workspace-denial retry via
authorized CLI;48 not installed. Full49 adds cleanup/VM accounting and is building.
Do not claim signed/install/device fix success before actual receipts. Current
source/docs uncommitted/unpushed in daytime; main and all unrelated state retained.


### Run41 actual49: update handoff verified; separate renderer hang

Full49 build, final markers/package and disposable matching Air main/helper
profile signing/deep-strict pass. Actual signed Mach-O SHA256
3bc0669f34299cdf3742e82f3c0724db4d8f1b4d86f5b976ac07759d18c57801.
Idle unexpected47 instance was verified with zero guests and normal SIGTERM
ended it; no force-kill. Same-container49 installation returns0; independent app
list49 and actual launch/receipt PID16532 prove install/execution. No uninstall,
other app/phone/account/game/save or profile/security changes.

The official updater again extracts version1792618285 after reporting installed
version0. It exits42; actual native log confirms real backend/RFB/Metal drain,
IDECK_STEAM_UPDATE_RESTART_V1 automatic_count1 and retained RUNNING wave2 in SAME
PID16532. This is actual update/reentry proof, NOT full teardown/Wine/game return.
The repeated installed0/background-check pattern also exists in47; its role in
the failures is a hypothesis, not assumed cache corruption or root reimport.
Pinned DroidDeck installer/session were fetched and inspected again at f33d5b9:
https://github.com/Droid-Deck/DroidDeck/blob/f33d5b9e09ed27d68137aba4e711f8fca9eb93e9/tools/linuxfs/overlay/usr/local/bin/droiddeck-steam-install
https://github.com/Droid-Deck/DroidDeck/blob/f33d5b9e09ed27d68137aba4e711f8fca9eb93e9/tools/linuxfs/overlay/usr/local/bin/droiddeck-session
They align beta state and -clientbeta; no Android repair/sandbox/process logic
was copied and no live package/account state was edited.

Wave2 shows partial desktop chrome then black X11 cursor. Bounded current native
log has ZERO MMAP_FAILURE records, but this short window does not prove the
original allocation fault fixed. Actual CEF renderer guest267/thread272 emits
child_thread_impl.cc351 **Crashing because hung**, guest wait status5. Exact
Chromium126.0.6478.183 source identifies CrashHungProcess, not a generic crash:
https://github.com/chromium/chromium/blob/126.0.6478.183/content/child/child_thread_impl.cc#L349
Main267 samples persist at futex98 with small then unchanged cycle counts.
Before trap native footprint2,313,361,424, available692,905,968, region_count52593.
No sole deadlock/CPU/memory cause is established. Preserve current49 session.
No interactive Library/BPM/game/return/stability result or assertion suppression.

Final host full copied-backend file-map cleanup + own wrappers pass seven native
log modes and16 real ARM64 kernel controls; ASan/UBSan only own/overlaid units,
not the whole interpreter. Earlier ordinary-harness run used a join-required
archive without admission, so clone/thread cases failed; corrected original
lifetime+new log/cleanup archive passes, no runtime-provider reset.

Next add bounded numeric-only metadata for blocked ARM64 futex calls: op/expected/
bitset/timed plus syscall caller addresses, no memory dereference or arbitrary
register/stack/heap dump. Existing task-lifetime/nonblocking locks remain. Source
is added, tests/next build/device qualification pending. Do not change clocks,
budgets or watchdog behavior before this discriminator. Dirty source remains
uncommitted/unpushed outside weekday22-08, main unchanged, full goal ACTIVE.


Blocked-futex diagnostic source is now locally qualified: real host ARM64 ELF
creates a pthread-like guest, main actually blocks FUTEX_WAIT_PRIVATE, native
observer records operation128/expected0/no timeout/caller addresses WITHOUT a
memory read, then an ordinary guest wake and exit0 complete. Changed observer/
wrapper units ASan/UBSan. Existing real wait/touch/unmap/nonblocking contention
controls pass.22 iOS native units compile; App50 building, not signed/installed.
Op-defined registers only; syscall PC/number/blocking are rechecked before
accepting a best-effort row. No actual CEF wait/caller result until device data.
Pinned clock_gettime maps guest MONOTONIC to the same native clock futex uses;
no evidence for a clock patch or watchdog suppression. No such change made.


### Run41 continuation: actual50 native fork-copy fault and minimal allocation control

Actual50 PID16772 did NOT finish usable Library navigation. Exact device crash
Madeira-2026-11-12-141207.ips records SIGSEGV/KERN_INVALID_ADDRESS0 in
pt_copy_on_write+232, then mm_copy/copy_task/clone_task/sys_clone. Final signed
Mach-O UUID6e28a7a7-5261-321c-8e48-ea717f4af2d6 matches. Narrow disassembly
identifies a store through the returned child PTE; pinned leaf calloc is
unchecked. This is NOT the earlier47 NSData/RFB allocation abort. Final native
trace has18 mapping failures and max sampled67,702 VM regions; no exact Darwin
region cap or sole allocation-pressure cause is proved. Private crash/native
log/disassembly hashes are recorded in EVIDENCE.run41.actual50.

New defaultOFF --fork-map-failure overlays only private copies of memory.c,
mmap.c and fork.c. A fork-only checked PTE allocator returns NULL safely at
each level. The caller allocates before changing the source backing refcount,
charges even partially copied anonymous pages before releasing a failed child,
bump-invalidates source/destination generations and propagates failure through
mm_copy to clone ENOMEM. Reservation-copy failure is no longer silently lost.
Successful shared/private/PROT_NONE copies retain original semantics. Ordinary
pt_map allocator, engine allocator, budgets, clocks, watchdogs and Valve/FEX
are unchanged; unchecked allocations there remain real limitations.

HOST exact kernel baseline reproduces the same memory.c722 NULL PTE store.
Fixed25 controls pass: success plus every one of10 root/intermediate/leaf
allocations and both reservation allocations through actual mm_copy AND
clone. Parent backing bytes/flags/refcounts and anonymous accounting survive
partial-child destruction. Changed3units ASan/UBSan, not whole engine. Initial
harness lacked init-only exefile and hit fd_retain; corrected own harness opens
/dev/null before target. Source-line UBSan evidence is required, not any crash.
Private fork-map-control-v4 holds logs/receipt; device effect remains unverified.

Pure Linux link-control51 is prepared but PARKED/never installed; captured
fork fault is a better current discriminator. Current unexpected new main16901
has exact installed50 path but last-native-log still refers to dead16772; do
not call this a recovered Steam session or kill blindly. Revalidate state first.
Next full hybrid52 keeps same root/auth/game storage and only adds checked
fork failure handling. No successful Library/game/return/stability claim.
Run40+41 source remains uncommitted/unpushed during weekday daytime.


### Run41 final52 device outcome and next memory discriminator

Full52 Xcode/package passed;22 native units and linked disassembly show checked
fork allocations, source ref transfer after the NULL check, mm_copy partial-child
release and clone -ENOMEM before task_set_mm. Disposable matching Air signature
and deep strict verify passed. Same-container install exit0 and independent app
list52 confirmed. Actual new identity PID17010/installUUID
F62769EE-5E58-46FE-A783-946EB4673C2E; real official updater painted.

Later actual device crash Madeira-2026-11-12-144522.ips proves52 PID17010
SIGABRT from NSAllocateMemoryPages/NSData/LRRFBClient update. This differs from
50's fork NULL store, but does NOT prove the new fork failure branch executed
or that capacity improved. Last health sequence54/phase8 is historical, not live
now; guest149, footprint2,395,019,760. Final bounded native log has repeated
2MiB host file mmap ENOMEM12; exact counts/hashes in EVIDENCE.actual52.
No usable Library/BPM/game/return success. Home screenshot and unexpected newer
main17126 observed; preserved without kill/relaunch, don't assume it is Steam.

New reproducible HOST measurement (test-cow-backing.py) uses real pinned
pt_copy_on_write and actual parent user_write:64 adjacent4KiB guest writes create
64 distinct native CoW backings. Guest262,144 bytes round to1,048,576 bytes on
this16KiB-native-page host (ratio4). Child bytes remain0 and anonymous accounting
returns0. This measures rounded mapping capacity, NOT physical resident bytes,
exact VM region count or a Darwin region limit. Initial own format mismatch
failed Werror before execution; fixed cast, reproducible control passes.

Next discriminate whether co-materializing a native-page group of compatible
private CoW entries reduces this amplification while preserving mixed/shared/
protection boundaries, source offsets/file metadata, allocation rollback and
per-page accounting. No grouping runtime patch is yet applied. Pure Linux51
remains parked/uninstalled. No retry/assertion/cap/watchdog/FEX/Valve change.
Current allowed commit window reopened; publish only scoped source/tests/redacted
evidence checkpoint after review. Existing profiles expire04:43:44Z Nov13;
revalidate before further deployment, never bypass expiration or user approval.


## Run42: anonymous CoW native-page grouping (2026-11-12)

Baseline signed source e1a6005 now pushed/read back on the experiment branch;
main2ac39be preserved. Mount UUID and remote/worktree state reverified.
Current Air17126 belongs to installed52 and has its own receipt, phase0,
zero guests/workers, sequence1. No stop, relaunch, upgrade or credential action.
This supersedes earlier stale16772/17010 receipts; it is not a live Steam result.

Observed52 native file ENOMEM/RFB allocation abort remains the actual failure.
Hypothesis: compatible anonymous CoW pages amplify native mapping capacity.
New defaultOFF --cow-native-group overlays private memory.c, original vendor
unchanged. Only same-backed/same-flag/contiguous-offset private anonymous pages
inside one native-aligned group qualify. File/memfd/shared/ptrace use original
path; mixed protections/holes/backings/offsets stop expansion. Allocate/copy
before any mutation; no fallible operation after invalidation/commit starts.
Original parent/child accounting/refcount ownership stays per logical page.

Discriminating HOST test now reports64writes ->16backings and256KiB rounded
mapping capacity, compared with baseline64backings/1MiB. Same256KiB guest data.
Actual10 kernel controls pass (memory unit+harness ASan/UBSan): parent AND child
writes, partial group unmap, mixed protection/shared/hole, different backing/
offset, file fallback offset/fd retention and mmap/data failure rollback.
No physical RSS/native region limit/device benefit claim. First runner lacked
parent output directory; fixed own mkdir(parents=True), no kernel failure.

Existing7 logging modes and16 actual ARM64 ELF checks pass against grouped
copied memory archive.22 iOS units compile, no host failure injection in iOS.
Full unsigned53 building in private run42/hybrid53 (observer66631); preserve
this job and read its actual result instead of duplicating it. Not signed or
installed; no final Mach-O/device/grouping UI/game/return proof yet. Exact
artifact hashes and commands in EVIDENCE.run42 and private receipts.

Reproduce HOST: python3 experiments/linux-steam/tools/test-cow-native-group.py
ARTIFACTS NEW_PRIVATE_OUTPUT. Preserve profile expiration checks (main expires
2026-11-13T04:43:44Z); do not bypass expiry or infer crash from signing refusal.
Next finish full53, verify actual linked branches/marker and then qualify actual
Air Steam rendering/Library under normal memory pressure, preserving saved
auth/root/game/save. Goal active; no STABLE_SUCCESS or scheduler unload.

Full53 Xcode subsequently passed. Final actual unsigned Mach-O contains the
group marker and mem_ptr -> ideck_cow_native_group call; negative/error branch
and invalidation/release calls inspected in bounded disassembly. No host
injection symbol present. Final package/scene/rootfs/guest resources pass.
Old embedded47 profile expired; read-only Xcode profile inventory finds an
already-existing valid pair matching Air/Lab/helper/same certificate, expiring
Nov20 04:42:34/36Z. No account/profile/security change. Disposable53 signature
is running (observer70342); not installed yet. Do not repeat obsolete expiry
gate or restart a build already completed.
