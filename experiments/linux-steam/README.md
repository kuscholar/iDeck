# iDeck Linux Lab

Private-development experiment, not an alternative product release. See
[investigation/status](../../docs/experiments/LINUX_STEAM_MADEIRA.md).
The ordinary Madeira target is untouched. This separate UIKit target links the
pinned LinuxRunner interpreter, a minimal native embedding adapter and a bounded
diagnostic compatibility bridge. An explicit experimental desktop frontend links the pinned RFB/Metal display,
root importer and input adapter. Physical Air TCP execution is verified; interactive
Steam login/Library is not yet verified. It **does not link or start Madeira**.

## Build and controls

Initialize `vendor/LinuxRunner` at the recorded gitlink. Host and iOS builds need
Xcode, Python3, Meson1.9.2, Ninja and `ld.lld`. Keep tools/build outputs on the
verified external volume; a private venv is suitable. No graphics, Linux kernel,
shader converter, FEX modifications or JIT permission is needed for these controls.

```sh
export LINUX_LAB_ARTIFACTS=/Volumes/easystore/GitHub/FunProjects/.madeira-install/linux-steam-ipad
# Put Meson, Ninja and ld.lld on PATH, or set MESON/NINJA/LD_LLD to their full paths.
bash experiments/linux-steam/tools/test-host.sh
bash experiments/linux-steam/tools/build-lab.sh
```

The host script compiles and actually executes ARM64 Linux ELF programs through
LinuxRunner; this is macOS evidence. The iOS script builds scheme LinuxLab for
physical arm64 and embeds the same probe. Open `LinuxLab.xcodeproj`, choose your
own development team, and generate a profile for `com.kuschqin.ideck.linuxlab`.
Override only this Lab ID if another unique development ID is necessary. Never
replace the working iDeck ID to obtain signing. Install the signed Lab with
CoreDevice only after verifying the intended iPad is online and app slots allow
installation. Do not uninstall apps to make room.

On launch, the Lab runs its control once and shows categorical results. It writes
`Library/Application Support/iDeckLinuxLab/last-probe.txt`. Copy/read this file
through the development app container to establish *device* execution; a build,
process presence or a host result does not suffice. The interpreter requires no
JIT. Reopen the Lab for another control; no restart-in-place capability is claimed.

`test-host.sh` also runs the real freestanding compatibility wrapper with
synthetic Steam metadata. It returns **125** intentionally: native diagnostics
received it, but **no game launched**. Raw wait status is `125 << 8 = 32000`.

## Narrow compatibility fix

`patches/linuxrunner-dirfd.patch` is a GPL patch to LinuxRunner, applied by
`overlay-dirfd.py` only to generated private `libish.a` inputs. It rejects a
non-directory dirfd with `ENOTDIR` for relative openat/accessat before normalization.
Absolute paths and legal file-null utimensat retain their upstream behavior.
Version3 passes16 host probe lines; the required linked marker is
`IDECK_LINUXRUNNER_DIRFD_GUARD_V3`. The initial common-path v1 was incorrect for
utimensat and is superseded, and openat-only v2 missed the observed accessat caller. The original path
assertion stays. The vendor checkout remains pristine. A linked version function
is called by the adapter so a build omitting the patch cannot silently pass.
The control reproduces the original abort without this patch, and tests the errno
with it. The patch does not establish a complete CEF or filesystem fix.

## Official Steam acquisition control

The host-only `tools/steam_packages.py` selects official `*_all` and
`*_linuxarm64_linuxarm64` packages, validates size/SHA-256, resumes partial files
and extracts to **new** private per-package staging directories. It rejects path
traversal, encrypted entries, case collisions and unsafe links. Official ZIPs use
some backslash separators and three contained library symlinks; these are checked
and normalized. Hashes come from HTTPS metadata, not a Valve signature system.
This is not yet an in-app repair/update/activation manager. Extraction failures
can leave a partial new staging directory; it never repairs over an existing app.

```sh
curl --fail --location --output "$LINUX_LAB_ARTIFACTS/steam_client_steamdeck_stable_linuxarm64" \
  https://client-update.steamstatic.com/steam_client_steamdeck_stable_linuxarm64
python3 experiments/linux-steam/tools/steam_packages.py \
  "$LINUX_LAB_ARTIFACTS/steam_client_steamdeck_stable_linuxarm64" \
  --block bins_linuxarm64_linuxarm64 --cache "$LINUX_LAB_ARTIFACTS/packages" \
  --extract "$LINUX_LAB_ARTIFACTS/steam-parts"
```

The isolated loader control uses that actual client plus the pinned Debian ARM64
glibc package. `ideck_linux_lab_steam_probe` is a fixed desktop/channel launch,
not the UI integration. Do not run this stdout-collecting loader diagnostic against
an authenticated root. Its current sparse root lacks complete distro/display/CEF
dependencies; see the evidence and next test in the investigation document.

## Compatibility discovery and IPC

When the real frontend is ready, install `compatibilitytool.vdf`,
`toolmanifest.vdf` and the source-built ARM64 `ideck-madeira` executable together
in `$STEAM_ROOT/compatibilitytools.d/ideck-madeira-lab/`. Do not change existing
Steam tool choices or claim discovery until tested in Steam itself.

The wrapper supports only `run` and `waitforexitandrun`. It captures positive
AppID, install directory, executable, cwd, optional compatdata and at most32
arguments in a fixed8216-byte v1 frame. It uses LinuxRunner's virtual
`/dev/ideck-madeira` device (lab major242); no guest PID is treated as a Darwin
process and no socket/command injection is used. Each open accepts one validated
request and returns a bounded16-byte response. The current handler always reports
not-launched125. A separate native host filesystem/catalog/ownership validator and
Madeira adapter are mandatory before any real execution is enabled.

Initial syntax validation permits ASCII paths under the Lab's explicit shared
library prefix, forbids traversal/sibling-prefix escapes and checks packed argv.
It does **not** validate symlink races, executable file type, app manifests,
licenses or host path authority. There is deliberately no host execution API to
reach by bypassing those unfinished checks. Non-ASCII game paths, Steam query
verbs, cancellation, complete shutdown and Steam-discovered tool operation remain
future gates. Synthetic fixture480 is never submitted to Valve as a game launch.

## Attribution and binary boundary

Built on [Madeira/iDeck](https://github.com/kuscholar/iDeck),
[LinuxRunner](https://github.com/mxhm11cr/LinuxRunner), iSH and ios-linuxkit.
[DroidDeck](https://github.com/Droid-Deck/DroidDeck) supplies architectural and
compatibility-tool interface references; no Android wrapper code is transplanted.
Upstream source/licenses remain in the pinned submodule. The fakefs metadata
adapter retains GPLv3; new-code converter permissions do not expand upstream
grants. This Linux-only binary excludes Apple's shader converter; distribution
of a future combined binary needs a fresh licensing/linkage review. Do not publish
private logs, rootfs/Valve/game payloads, profiles, pairing files or account data.

Reproduce the sparse root separately (a **new** destination is mandatory):

```sh
python3 experiments/linux-steam/tools/prepare-loader-control.py \
  "$LINUX_LAB_ARTIFACTS/steam_client_steamdeck_stable_linuxarm64" \
  "$LINUX_LAB_ARTIFACTS" "$LINUX_LAB_ARTIFACTS/loader-new-root" --use-host-dns
# Use a bounded observer when running this fixed, unauthenticated host diagnostic:
# host-embed <new-root> --steam-loader-probe
```

This preparation script was actually run on a fresh fixture. It verifies the
reviewed stable snapshot and Debian libc6 hash, extracts only regular glibc
libraries, and does not execute a package script. It is intentionally insufficient
for Steam UI: no complete distro, trust store, display server or client platform
set. `--use-host-dns` is for host tests; use the iPad's own resolver when adapting
bootstrap to iOS. Network restrictions of an execution sandbox must be distinguished
from guest failures. Keep raw diagnostic stdout private and never use an
authenticated root for this loader probe.


## Complete-root and recurring continuation status

The full pinned Debian base was assembled/imported and initialized in the guest;
its genuine ARM64 curl verifies Valve HTTPS successfully. `build-rootfs-tools.py`
builds host-only bootstrap/import helpers. Its separate fakefs hardlink patch
accepts only an existing same regular inode, preserving rejection of conflicting
files. `make-steam-overlay.py` emits a guest-only archive from validated component
staging, including directory metadata; never unpack it over the working app.
The latest host Steam experiment reached update download100% and extraction
before a deliberate bounded observer termination. No Steam UI is implemented.
See the investigation for exact commands/evidence and unresolved display gates.

A macOS user LaunchAgent `com.kusch.ideck-linux-steam-ipad-305m` is loaded every
18300seconds/305minutes. `tools/configure-schedule.py` generates its plist from
explicit CLI/thread/project/prompt/log arguments. It uses official CLI
`app-server daemon start` and `queue --resume`; no Codex databases, credentials,
lock state or OS privacy settings are altered. The existing thread's active
writer deferred the actual test dispatch; unattended research is not yet proven.
Read back with `launchctl print gui/$(id -u)/com.kusch.ideck-linux-steam-ipad-305m`.
Stop only this job upon user cancellation or repeated evidence-backed actual Air
Steam+Madeira stability with
`launchctl bootout gui/$(id -u)/com.kusch.ideck-linux-steam-ipad-305m`.
Mac sleep/storage availability can delay work. User explicitly requests CLI-only
operation and no further Mac-unlock questions.

The Air deployment uses a previously uninstalled separate development ID
com.kuschqin.ideck.freshtest with an already authorized matching Air profile.
Source default linuxlab is unchanged; production and Mac Allocator apps remain
untouched. Installed Lab1 currently gets SpringBoard's generic
signature/entitlement/trust refusal. User inspection of the actual iPad prompt
is pending. Do not infer a Linux crash or claim device execution from signing
and installation alone. New unsigned Lab2 has not been installed on Air.

## Lab3 full Debian control

`linux-distro-diagnostics` is an explicit app launch argument, using only the
prepared app-private `Library/Application Support/iDeckLinuxLab/DebianRootFS/`
with `data/` and `meta.db`. It runs a fixed ARM64/glibc/filesystem/entropy/curl-link
control and writes `last-distro-probe.txt`; it never logs into Steam or takes
arbitrary guest commands. Missing rootfs is an error. The source does not yet
provide an on-device rootfs importer. Do not copy an actively written fakefs
SQLite database or another app's account/prefix. This mode is host-validated and
compiled for iOS, but not device-validated yet.

```sh
# Build host-embed using test-host.sh first, then use an ABSOLUTE private,
# stopped, initialized Debian fakefs copy:
"$LINUX_LAB_ARTIFACTS/host-embed" /absolute/private/debian-copy --distro-probe
```

`tools/rfb-capture.m` is a host-only actual-frame probe using the pinned vendor
RFBClient/RFBProtocol. Compile with Foundation/CoreGraphics/ImageIO and the vendor
header include directory. It takes port, private8-byte password-file and NEW PNG
output path. The observed host Xvfb frame (960x540) has only a cursor. No UI/input
success is inferred from this capture; no RFB or Metal source was copied/modified.

Reproduce the host display/client test (ONLY a stopped, unauthenticated Lab root):

```sh
python3 experiments/linux-steam/tools/run-x11-control.py \
  "$LINUX_LAB_ARTIFACTS/host/ish" /absolute/private/steam-fakefs \
  "$LINUX_LAB_ARTIFACTS/new-x11-observation" --steam
```

The fixed guest script starts Xvfb :99 and authenticated loopback VNC5993, launches
only the official stable Steam desktop executable when requested, observes90s and
cleans up its own guest processes. The outer observer is bounded140s and serializes
its own callers. Verify no independent guest is already using that root first.
Known login-state files refuse this raw-log control without reading their contents;
the guard cannot prove a caller-selected root contains no secrets. Use a fresh
unauthenticated root, never the working app/account. Session exit0 does NOT assert
Steam exit0 or UI success. Four observer policy tests cover missing-root/login-state
refusal, preserving old output and not promoting a zero mock exit to Steam success.
Guest logs are copied privately (bounded1MiB tails); never add them to Git.

The next observed Steam blocker is packet-mode pipe2. A separate bounded
trace-only host binary can be built with `tools/build-pipe-observer.py` (source,
existing Meson build, Ninja path, NEW private output). It copies the archive and
never changes the base runtime/vendor. `guest/packet-pipe-probe.c` is a static
ARM64 reproducer: ordinary pipe succeeds, actual Steam packet flags0x90000 fail
EINVAL in this pin. Current exit1 is expected failing evidence, NOT test success.
It has future packet-boundary/short-read/CLOEXEC/nonblock assertions; never make
these pass by dropping O_DIRECT or suppressing the Steam fatal. See investigation
for primary UAPI references and exact trace. No device pipe test has run yet.

## Packet-at-creation experiment (run4)

Packet support is now implemented in a separately generated lab archive; the
pinned baseline still reproduces EINVAL. Enable it explicitly:

```sh
export LINUX_LAB_PACKET_TEST_DIR="$LINUX_LAB_ARTIFACTS/new-packet-test"
bash experiments/linux-steam/tools/test-packet-pipes.sh
LINUX_LAB_PACKET_PIPES=1 bash experiments/linux-steam/tools/build-lab.sh
```

The first command needs a prepared host Meson build and NEW test output. It
reproduces baseline failure, then basic success and16 contract-result lines under
an ASan/UBSan-instrumented changed host unit. The second builds unsigned Lab4;
confirm IDECK_PACKET_PIPE_V3 in the final Mach-O and exact ELF resource hash.
No signed IPA/device success is implied. `linux-packet-pipe-diagnostics` runs its
fixed embedded ELF in app-private PacketRootFS, reports to last-packet-probe.txt,
and consumes one runtime lifetime. Default builds keep the feature off.

Packet boundaries, truncation, EOF, bounded capacity, byte counts and tested
poll/dup/fork/cancellation behavior are implemented. Dynamic packet/stream
conversion is explicitly unsupported; read the investigation before claiming
complete pipe compatibility. Ordinary stream paths/base archives/vendor remain
untouched. Build receipts include immutable changed-source snapshots and hashes.

At run4 the genuine host Steam client advanced to CEF/BrowserReady but displayed
Unexpected Transport Error0x3009. Run5 below supersedes that host login result.
The next discriminator is WebUI/client transport, including unsupported packet
mode operations and FD passing, not assertion suppression. iPad developer trust
is still pending. This source target still lacks an iOS Steam display frontend.

The X11 observer now accepts `--seconds 1..600` (default90) with a bounded cleanup
allowance. It preserves exact per-run private logs. A300-second run is not a
stability claim. Keep captures private, and never run raw-log controls on an
authenticated root or copy another app's login state.

## Guest TCP ownership and genuine login (run5)

The actual CEF page's two local WebSockets returned HTTP403. Steam's own log
identified its missing `lsof` command; normal Debian apt installation supplied
4.99.4+dfsg-2. It then returned1 because the runtime lacked TCP tables and stable
socket inode identities. No Valve binary, authentication check or FEX was patched.

`tools/build-tcp-view.py` overlays a NEW copied archive only: stable actual guest
socket descriptions, `/proc/net/tcp{,6}` and the per-PID net view. The inventory
uses retained guest descriptor tables and native TCP connection state, not host
PIDs or invented peers. It is partial: only guest-visible descriptor-backed TCP,
no orphan/TIME_WAIT inventory, network namespace implementation, UDP or queue/
retransmission accounting (those counter columns remain zero). Treat it as an
explicit experimental feature, not a complete Linux network ABI.

Reproduce the negative baseline,17 positive controls and optional19-control
Debian `lsof` test, with all other Lab runtimes stopped:

```sh
export LINUX_LAB_TCP_TEST_DIR="$LINUX_LAB_ARTIFACTS/new-tcp-test"
# Optional: a stopped, unauthenticated fakefs with Debian's real lsof installed.
export LINUX_LAB_DISTRO_ROOT="$LINUX_LAB_ARTIFACTS/private-prepared-root"
bash experiments/linux-steam/tools/test-tcp-view.sh
```

The final unsanitized host artifact then gave two genuine HTTP101 handshakes and
displayed Steam's actual login UI. Native RFB click/type/delete of the fixed public
text `ideck-input-control` was visually verified; no login was submitted. Raw
frames include transient login QR material and MUST remain private. This is a
host milestone, **not iPad login, Library, Big Picture or stable game/return**.
The sanitized Steam observation instead stalled before UI and reported an
inherited proc-list alignment diagnostic; no sole cause or clean full-runtime
sanitizer claim. Changed-unit contract tests pass separately.

`run-x11-control.py --cef-debug` explicitly requests the genuine client's local
developer endpoint; default off and the unauthenticated-root guard still applies.
Inspect ownership before connecting. On this host Steam used `[::1]:8080` while
an unrelated service already owned IPv4 port8080; never stop that service or
confuse its HTML response with CEF. Do not log cookies, headers, WebSocket frames,
authentication keys, account values or arbitrary Runtime.evaluate results.
Only fixed read-only metadata/boolean queries were used. The observer now refuses
an existing X99 lock/socket rather than deleting a possibly active display.

Prepare unsigned isolated **Lab5** with both explicit runtime gates:

```sh
LINUX_LAB_PACKET_PIPES=1 LINUX_LAB_TCP_VIEW=1 \
  bash experiments/linux-steam/tools/build-lab.sh
```

After authorized isolated signing/device trust, `linux-tcp-diagnostics` runs the
embedded ELF in its separate TCPRootFS and writes `last-tcp-probe.txt`. Lab5's final
Mach-O and embedded ELF were checked; it has NOT been installed or executed on
Air. No iOS Steam display/rootfs importer or Madeira game handoff exists yet.

## Complete frontend experiment (explicit opt-in)

Use a STOPPED, known unauthenticated private fakefs; never a working app's root
or cached login. Export through `tools/export-clean-root.py`, retaining the JSON
image receipt and SHA256. This exporter omits account/browser state and host
bindings; it is not an account migration. Rootfs/Valve/package files stay private.

```sh
export LINUX_LAB_PACKET_PIPES=1 LINUX_LAB_TCP_VIEW=1 LINUX_LAB_STEAM_FRONTEND=1
export LINUX_LAB_ROOTFS_SHA256=<sha256-of-your-verified-clean-image>
# CMAKE, NINJA, MESON and LD_LLD must resolve to the prepared private tools.
bash experiments/linux-steam/tools/build-lab.sh
```

After matching-profile signing of a disposable Lab copy, stage that exact image
in its own app container as `Documents/LinuxLabInput/steam-rootfs.tar.gz` and
launch with `linux-steam-desktop`. No production identifier or account cache
fallback. The importer verifies the build pin, writes only an owned stage and
preserves existing roots. Read `last-root-import.json` under the Lab's Application
Support directory; import success alone is not Steam UI success. One runtime per
native app lifetime; no reusable shutdown/game handoff guarantee. No JIT is needed
for this interpreter target. Failed import requires an explicit fresh native Lab
lifetime; never retry over active runtime state automatically.

`tests/archive-header-test.c` compares a fixed UTF-8 PAX fixture, global-only
BINARY header and per-entry BINARY header. Link against the pinned no-iconv
libarchive (not system libarchive) and run with ASan/UBSan in C locale. It checks
the original warning plus exact filename bytes, payload and EOF preservation.
The exporter uses the successful per-entry header; it never strips Unicode names. The iOS SDK requires the Scene manifest/delegate included
in this Lab; building against SDK27 without it fails before Linux can run.

`linux-steam-install-dependencies` is an explicit alternative mode in the frontend
build. It uses normal signed apt metadata to install only pinned libnm0, writes
`last-dependency-setup.json` plus private guest logs, and verifies steamclient.so
ldd has no missing entries. It never accepts arbitrary shell commands and does
not start Steam or access accounts. Restart only after completion to use
`linux-steam-desktop` in a fresh native runtime lifetime. Conflicting modes refuse.
