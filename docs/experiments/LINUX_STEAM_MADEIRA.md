# Linux Steam + Madeira on iPad: experiment log

Status (run23): Actual Air ARM64 ELF, verified Linux image import, native
X11/RFB/Metal, user-authenticated genuine Linux Steam Big Picture and the full
Library have been observed (runs16–17). Browsing has severe delays and memory
pressure; this is NOT stable operation. Lab23 remains live and preserved. Native
game-file capability checks and real ARM64 helper-to-host controls pass on the
host; feature/default iOS builds are checked separately. The bridge still
returns diagnostic125, and no Madeira game/return cycle is implemented or
verified. Read the latest run and EVIDENCE.json for exact artifact boundaries.
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
