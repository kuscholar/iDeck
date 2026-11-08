# Linux Steam + Madeira on iPad: experiment log

Status: Phase 1 controls implemented; isolated Lab installed on the selected Air,
first launch blocked by device signature/entitlement/trust refusal. Host-only
Debian+HTTPS controls pass. No device Linux ELF, Steam UI/login/Big Picture,
licensed game handoff or stability success is claimed. See latest run below.
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
