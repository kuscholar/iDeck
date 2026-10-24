# Genuine Steam UI: Phase 0 architecture audit

Audit date: 2026-10-22. Scope is the Windows Steam route on a stock iPhone
15 Pro Max / A17 Pro using Madeira's existing debugger-granted JIT. This is a
source audit, not evidence of Steam CEF working on the current device.
Phase 0 completed before this branch's experimental runtime edits.

## Revisions actually inspected

| Repository | Revision |
|---|---|
| kuscholar/Madeira baseline | ee9fd2f4c21229dfce31a25c211d44df267336d8 |
| willfaust/Madeira main (remote checked during audit) | 279fd0f83170425db002fe25d6bd62f6355f497d |
| FEX, ios-port-2607 | f59cab95659e8add0c88f0c76ec1cf483c536dbf |
| Wine, madeira-lgpl | 9129e9684daaeae70da9435e7c6060e59392634e |
| DXMT, ios-port | 128b297c6e9a00014408dc68b4c2c2373b5813de |
| Madeira Dock | 72558e416a390f3669457930f09a389e54f49556 |
| deezhizyu/madeira historical HEAD | 97e2ce26e6dc9e4a38976f3b5deb9272d64558eb |

The experimental parent and its four direct submodules have independent Git
worktrees. They do not modify the main checkout's source. Nested dependencies
were inventoried from the prepared checkout at these same parent pins; they
are not all initialized in the experiment. A recursive SHA inventory follows.

## Required reading and evidence boundaries

Read current README.md, docs/BUILDING.md, docs/MADEIRA_DOCK.md and
STEAM_SIGNIN.md, and both historical STEAM_CEF_HANDOFF.md (274 lines) and
ARCHITECTURE_ANALYSIS.md (931 lines). The latter is an early proposal, containing
claims incompatible with the later handoff, e.g. debugger lifetime, physical
memory accounting, Linux-rootfs requirements and unavailable entitlements.
Those are not current platform guarantees. The handoff reports an interactive
login window and three unsolved failure families; its historical labels are
not results of this branch. No historical raw device run was replayed.

## Actual launch and process architecture

1. `app/Madeira/ContentView.swift::runWineFullSequence` checks JIT, applies
   per-game config, chooses the executable pool and starts the runtime. Its
   `startWineserver` / `startWineProcess` use the normal bridge entry points.
2. `app/Madeira/WineServerBridge.m::wineserver_start` seeds the prefix and uses
   pthread_create for `wineserver_thread_func`; the server is not an OS process.
   `build/wineserver/{main_ios,request_ios,fd_ios,mapping_ios,queue_ios}.c`
   implement its platform-specific event/IPC/object behavior. Do not assume
   changes to unused Wine unix files affect these compiled copies.
3. `app/Madeira/WineProcessBridge.m::wine_process_start` starts
   `wine_process_thread`, exports the session environment and enters
   `__wine_main` inside its exit guard. The normal launch can run explorer's
   desktop and cmd/services bootstrap rather than a bare application.
4. `build/ntdll-unix/process_ios.c::NtCreateUserProcess` reaches `spawn_process`
   and `ios_child_thread_entry`: each Windows child is a pthread in the same
   Mach task. It receives its own Wine process state/TEB/PEB and server socket,
   but not physical address-space isolation. A fatal native fault can still
   kill the whole app. Existing `[child-life]`/process/termination diagnostics
   must be distinguished from real OS process creation.
5. Wine's ARM64EC path loads xtajit64.dll. The pinned FEX implementation is
   `FEX/Source/Windows/ARM64EC/Module.cpp` (`ProcessInit`, `ThreadInit`), the EC
   entry/exit assembly and its dispatcher. It imports the host's alias/pool
   callbacks; native FEXCore archives link into the iOS host. Existing native
   object linkage and the bundled PE module are separate build inputs.
6. Software window drawing reaches `build/win32u-unix/driver_ios.c` surface
   flushing and `app/Madeira/Winios/Winios.m::winios_surface_present`. The host
   composites window DIBs; DXMT windows get per-window CAMetalLayer rendering.
   This is the existing display path for real Steam UI, not a SwiftUI copy.
7. `WineProcessBridge.m` tracks initial-process exit and eligible live children;
   ContentView and LibraryModel finish the session and restore UI state.
   One Wine session per app run remains a significant constraint: launching a
   game and returning to Steam is NOT validated by ordinary game launch.

## Dock intentionally avoids CEF; existing Steam Testing is different

`MadeiraDock.swift` describes the headless contract and selects dockhost.exe,
not steam.exe. `madeira-dock/src/main.c` verifies the installed
steamclient64.dll, loads it directly, resolves Steam API/CreateInterface entry
points and calls `sh_run_client`. `src/session.c` and `src/launch.c` perform
real sign-in, entitlement and Valve LaunchApp. Its `no_other_client` explicitly
refuses concurrent steam.exe / steamwebhelper.exe sessions. There is no missing
"start webhelper" toggle inside Dock: its architecture never starts the desktop
client. Preserve it; experimental UI must be a separate route.

The parent already has a `Steam Testing` button and `prepareSteamLaunch` in
ContentView. It generates C:\\steam-launch.bat, starts services.exe and then
Valve's steam.exe on explorer's desktop. The button also enables unrelated
historical probes (including a Mono IR capture) and is not a clean minimal
experimental mode. Some comments saying no 32-bit support are stale relative
to the current WoW64 farm. Do not use comments as executable capability checks.

`process_ios.c` already recognizes steamwebhelper: the browser instance is
forced to `--single-process`; `--type=` child instances are refused to avoid
multiple PartitionAlloc/V8 address-space cages. It is NOT a blanket prohibition
on the initial helper. The reporter and GPU-query gates are independent. Thus
simply removing the helper gate is both unnecessary and unsafe.

## Authentication, private data and client resources

Current Swift Steam sign-in uses the real public authentication service and
stores client tokens in the iOS Keychain. Dock transfers them through a
bounded, protected, one-use file. The UI experiment must not reuse, display,
log or synthesize those payloads. The first milestone uses Valve's own login UI
and a separate experimental app/prefix; the human completes Steam Guard.

The standard bridge historically publishes a fixed Steam game identity on a
non-Dock desktop session. That is unsuitable for the genuine client: the
experimental mode must clear SteamAppId/SteamGameId/SteamAppPath without changing
normal game behavior. Its generated command has no credentials or arbitrary
user-supplied switches. Existing raw command-line diagnostics are a privacy
risk: do not enable payload-wide tracing to get BrowserReady evidence.

SteamRuntime.swift pins three Valve CDN packages and a steamclient64.dll SHA;
its headless setup is not evidence a full matching UI/CEF tree is installed.
A real 64-bit Steam client, matching steamwebhelper/libcef, fonts and runtime
imports must be inventoried in the isolated prefix. No Valve binaries, games,
login caches or signed provisioning assets belong in this repository.

## Historical reconstruction: source yes, identical run not established

The public historical tree and its commit graph were fetched without checking
out Valve/game artifacts. Historical HEAD's gitlinks are:

- FEX: 053c385ecc9090702e4959a1d96752ea918a6110
- Wine: 7817e220384e895651f868ba4d97affcf21b3816
- research/dxmt: b4b89f0a5a1752da3982a7b6c5575506024bf253

GitHub's commit endpoints returned each exact SHA in its published upstream
fork. Therefore source retrieval is reconstructible at those pins. This does
not prove every older milestone has a complete build recipe or runnable binary.
Useful published milestones include:
`ce8033e` (CEF initialization), `1cade1bf0db9f819d4b9bf48a29b64cb1ade9d82`
(login-window ladder), `40af59eea99e957cc5ca2dfe167a562a48c9673c` (dwrite)
and `f6a6a87b1fa3902568755a56a355c61f76e42539` (early debugger detach).
The handoff itself was last touched at `2498bdf5915ce99f1a8ece2e916b715991c31fb9`.

Current source independently confirms dwrite is compiled AND explicitly archived
by build/ntdll-unix/build.sh, retains single-process CEF, and contains later
fault/backing-object probes. The historical inaccurate protection-strip label
has already been revised around `bus-reheal`; the code still retries protection
in some cases. Do not copy this as a new workaround or infer a fix for kr=10.
No FEX source changes are planned: its current AGENTS.md prohibits AI-generated
contributions. A historical document's different policy claim is not authority
to override current instructions.

## Build resources and missing inputs

Prepared baseline: Xcode 27.0 (27A266a), downloaded Apple Metal Toolchain,
CMake 4.4.4, Ninja 1.13.2, Bison 3.8.2, LLVM-MinGW 20260421 (SHA-256 in
BUILDING.md), LLVM source 8dfdcc7b7bf66834a761bd8de445840ef68e4d1a,
Rust aarch64-apple-ios target, pinned FreeType/GnuTLS/GMP/Nettle/FFmpeg sources.
Source provenance/licensing: README, BUILDING, LICENSING and component notices.
A clean-machine full relink remains unverified, as upstream BUILDING states.

The experimental checkout initially lacks native libntdll_unix, libwin32u_unix,
libwineserver, libdxmt_combined, four FFmpeg archives, libmadeira_rppairing,
FEX/build-ios and the optional i386 farm. All nine native archives are present
in the prepared baseline, which produced Build 8. Reuse/copy these only when
its source is unchanged; rebuild touched native components and verify their
symbols/markers in the final Mach-O. A compiled intermediate is not proof of
inclusion. The optional i386 farm was preserved from the official 0.1.3 IPA;
no new from-source i386 build is claimed. Microsoft VC runtime is user-supplied.
A separately provisioned experiment app/profile and full client installation
are device gates; don't overwrite the working app to obtain a result.

## Decision and smallest discriminating experiment

GO for an isolated first-login PoC investigation, NOT GO for usable Big Picture.
Add an off-by-default Steam UI mode separate from Dock and the old probe-heavy
button. Use only the existing services/desktop pipeline, a fixed safe command,
per-session diagnostics, and no fixed Steam game identity. First compare
flag-off versus flag-on launch plans locally; then build the app and inspect
its final Mach-O for the mode. A synthetic x86-64 PE child/shared-memory test
can separate pseudo-process plumbing from CEF before spending a device run.

Do not enable Big Picture or migrate Linux ARM64 Steam in this experiment.
DroidDeck is useful comparative architecture (Linux/proot/Gamescope/real CEF),
but adding a Linux ABI/ELF/process layer to iOS is not a shortcut established
by this audit. Next device evidence must identify the actual client SHA and
capture CEF initialization, BrowserReady and a drawn interactive login window.

## Nested dependency inventory at the prepared baseline pins
 f59cab95659e8add0c88f0c76ec1cf483c536dbf FEX (heads/ios-port-2607)
 b3fb4b9feafcd8d91c5cb510a4775143fdbef02f FEX/External/Catch2 (b3fb4b9)
 450bd2232225d6c7728a4108055ac2e37cef6475 FEX/External/Vulkan-Headers (450bd22)
 3e49836995c1dcb3df709440ad2f270b569c6a5f FEX/External/drm-headers (3e49836)
 442678a134e2d25e759c430cca32e06e9e142f1f FEX/External/fex-gcc-target-tests-bins (heads/main)
 71349ae6d14ac2e3e792730e240aecd8076cee6c FEX/External/fex-gvisor-tests-bins (heads/main)
 9ae29638f8000c1603f16385ed1cf6c4c23ee414 FEX/External/fex-posixtest-bins (heads/master)
 407c905e45ad75fc29bf0f9bb7c5c2fd3475976f FEX/External/fmt (407c905)
 8436195ad5e1bc347d9b39743af3d29abee59f06 FEX/External/jemalloc_glibc (8436195)
 ca1388fb9da8e69314dda222dc7b139ca84e092f FEX/External/range-v3 (ca1388f)
 2dae74bb693e42d850fb0adcc9045c5b71fbdeae FEX/External/range-v3/doc/gh-pages (2dae74b)
 812c2b9cf4310ffacf14e6b64066e78ab0c394b5 FEX/External/rpmalloc (812c2b9)
 650c98ece70da9e155e7ba1c2b3ee16004aae118 FEX/External/tracy (650c98e)
 3234af2c03549bc85656bfd3a86993bf1cd8aef1 FEX/External/unordered_dense (3234af2)
 5f418449c48f6ca3ad37c47ec632f17a561c0580 FEX/External/vixl (5f41844)
 e626a72bc2321cd320e953a0ccf1584cad60f363 FEX/External/xxhash (e626a72)
 9bfadd6a55fc92dbd37fa3ba089bf8b36622df4f FEX/External/zydis (9bfadd6)
 75a36c45ae1ad382b0f4e0ede0af84c11ee69928 FEX/External/zydis/dependencies/zycore (75a36c4)
 9f94388a339fcbb0bc95c17768eb786c85988f6e FEX/Source/Common/cpp-optparse (heads/master)
 128b297c6e9a00014408dc68b4c2c2373b5813de dxmt (heads/ios-port)
 d08488fcc82eef313b0464db37d2955709691e94 dxmt/external/nvapi (d08488f)
 9df86f2341616ef1888ae59919feaa6d4fad693d dxmt/include/native/directx (heads/main)
 72558e416a390f3669457930f09a389e54f49556 madeira-dock (heads/main)
 9129e9684daaeae70da9435e7c6060e59392634e wine (9129e968)
