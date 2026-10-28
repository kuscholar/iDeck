# Current 64-bit Steam migration

User goal (2026-10-27): replace the legacy-client target with genuine current
64-bit Windows Steam, validate on Kusch through interactive UI, then Big Picture.
This document records experiments, not completion.

## Isolation / reproduction

- Explicit `madeira-steam64-experiment` launches desktop/login-only current
  Steam; `madeira-steam64-big-picture-experiment` additionally requests Big Picture.
- Only those arguments select `Documents/wine-steam64`. Ordinary launch retains
  the established `Documents/wine` baseline until migration is validated.
- The experiment creates a new prefix from the bundled blank template and stages
  a full matching AMD64 client under `drive_c/Program Files/Steam`. No account
  caches, games or saves are copied; the user performs authentication/Guard.
- App identity stays the same to avoid another free-signing slot; prior signed
  Build67 is retained privately as a binary rollback. Neither primary Madeira
  nor its baseline checkout is modified. No FEX or proprietary-binary patches.

Fetch the current Valve HTTPS manifest at
`https://client-update.akamai.steamstatic.com/steam_client_win64` and use
`tools/fetch-steam-ui-client.py --architecture win64` with separate staging.
The tool checks all package sizes/SHA256 against the HTTPS manifest; it does
not independently validate Valve's manifest signatures. Never commit Valve files.

## Build69 first device run

- Source starting point e3d845e plus local issue1/64-bit migration changes.
- Official manifest/package version1792618285; actual steam.exe,
  steamclient64.dll, cef.win64/steamwebhelper.exe and libcef.dll are AMD64.
- Full Xcode69, production launcher/selector/startup-failure checks and deep
  development signing passed. Signed/installed on Kusch and launched with the
  explicit64-bit argument. Native snapshot verifies independent prefix and
  successful actual64-bit Steam main-process/updater startup.
- Actual device map was512GiB with extended-va=0 and increased-memory=1. This
  does not establish the issue1 iPad map or entitlement requirements.
- Valve updater verified the absent install manifest, downloaded250911KiB,
  extracted packages and entered Installing update. At the initial bounded
  snapshot no CEF process or interactive Steam login was observed. Installer
  thread samples still showed filesystem/string work; not sufficient to call
  a deadlock or UI success.
- Private artifacts: .madeira-install/steam64-current/ (manifest/inventory,
  provenance69.json, build/sign/install/launch, native69-stable.txt and bootstrap
  snapshots). Never publish raw account/device logs.

Next: distinguish updater progress/completion from installer failure, then
collect actual AMD64 CEF launch, VM grants and first fatal if any. Do not bypass
login/licensing or disable allocator assertions. First milestone is interactive
login; authenticated Big Picture/home/navigation is a separate gate.


## CEF gate and signing correction

Actual Build69 updated successfully at15:16:09 and spawned AMD64 cef.win64
webhelper. Loader base libcef=0x71ddc70000; guest fatal0x71e4593404 therefore
RVA0x6923404. Preceding journal: two real16GiB grants, then16GiB and
~32GiB failures (c0000018/c0000017). A later fatal is not automatically a
BackupRefPtr failure; the historical brp-contain label is overbroad. No
BrowserReady/login success observed.

IMPORTANT: launch69-fresh.json retained SAME PID25625 and same log session.
SIGTERM was intercepted under debugging; the attempted SIGKILL timed out, and
fresh process listing still showed25625. Thus this is NOT a clean-process
reproduction and does NOT exclude updater/pseudo-process allocation lifetime.
No further launch should be called a fresh trial without PID disappearance and
new start timestamp. The lab has no authenticated account or running game.

Xcode GUI verified the user IS logged in, Personal Team. Existing certificate
and matching profiles successfully sign normal builds via unsigned build plus
tools/resign-app.py. The CLI No Accounts diagnostic was misleading and must
not trigger another login request. A separate private minimal GUI device build
then explicitly failed: Personal development teams do not support Extended
Virtual Addressing. Existing main profile lacks that grant. No entitlement
bypass, account purchase or credential automation was performed. A simulator
probe build success was discarded; only device signing error counts here.

Unsigned normal Build70 with selected64-bit prerequisite/path corrections
compiles successfully, not installed yet. Do not overwrite Build69 while its
termination state is unresolved. Next discriminator is a true fresh-process
launch after completed official install; if same allocation failure persists,
inventory all real/soft/cage/FEX owner intervals and design disjoint backed
reservations. Do not borrow Social Club's partial-backed/overlapping pool
workarounds or suppress allocator assertions.


## Verified clean restart after human app close

User closed iDeck; process list confirmed old app absent. New launch69-clean.json
created PID25956 at15:38 with a new log start; this IS a clean post-update run.
CEF launched at5.689s, the two same real16GiB pool grants succeeded, then later
16GiB hints failed c0000018 and ~32GiB fallback requests failed c0000017.
Loader libcef base71e0540000 makes allocation caller RVA209937a and fatal
RVA6923404; chrome_elf base71de060000 makes the guard reservation caller RVA4e0ca.
First journal nrip was not attributed by nearest-base guessing. No refcount
root-cause claim. Snapshot suspended/copied/resumed strictly serially.

Current ownership: FEX has a real16GiB reservation7c..80; two PA grants occupy
73ffff0000..7800000000 and78..7c; V8 holdback7200000000..73ffff0000 consumes
almost8GiB. Furniture/JIT/native mappings occupy the remainder. Three16GiB PA
pools plus16GiB FEX already consume64GiB, leaving no room for cage/furniture
in the currently used high64GiB band. This is a current-layout bound, not a
proof every legal layout/device is impossible. Existing arena-mb cap is not
a validated fix: its lower candidates overlap measured IOKit mappings, and
blindly shrinking/disabling FEX could break translation rather than fix CEF.
Need a measured genuinely available alternative region or supported reduction
in reservation demand; no overlapping fake grant is permissible.

Raw/hashes in private clean-evidence.json. Normal Build70 unsigned compilation
passes; existing ordinary/feature/isolated-prefix host tests pass. No new patch
claims interactive64-bit Steam. All earlier account/game state in wine remains.

## Build71 disjoint compact-layout discriminator

Hypothesis: the existing16GiB FEX reservation at7c..80 blocks the third16GiB
PA pool, although the emulator may need less capacity for login. A double-gated
MADEIRA_STEAM_UI_SESSION=1 + MADEIRA_STEAM64_COMPACT_LAYOUT=1 experiment reserves
FEX at7100000000..7200000000 (4GiB) using real no-overwrite Mach mapping and the
existing FEX_ONLY registration/versioned consumer handoff. Furniture ceiling is
7100000000. Cage holdback remains7200000000..73ffff0000; guard PA reservation
73ffff0000..7800000000; other PA slots78..7c and7c..80. These five half-open
intervals are disjoint. The ordinary allocator geometry remains unchanged.

This deliberately caps experimental emulator capacity; it may exhaust under
CEF threads or games. No FEX source edit, fake allocation success, fixed-overwrite
mapping or assertion suppression. Failure to reserve is checked; no alternate
experimental arena location is silently accepted. Existing baseline behavior
remains outside both gates. Tests verify exact gates/disjoint intervals and
no-overwrite/failure-check source integration with ASan/UBSan. All37native
units/full Xcode71 compile; final Mach-O marker verified, normal manual signing
passed. Device result recorded next; not a claimed fix until observed.


## Build71 actual result: partial capacity improvement, not login

In-place install first timed out; app inspection still showed69, old PID then
absent. One retry succeeded; Build71 launch uses a new installation identity.
Native log confirms real FEX7100000000..7200000000 kr0, registered/published and
CONSUMED by each ARM64EC child. PA grant#1 at7c, guard#2 at73ffff0000, #3 at78
all succeed, totalling48GiB. Subsequent guard request16GiB+64KiB fails three
hints and32GiBfallback; fatal remains. This proves the prior FEX slot conflict
was real but resolving it is insufficient: actual demand includes a fourthPA
pool. No soft grant success appears in this snapshot.

Four16GiB pools already require64GiB before FEX/cage/furniture, exceeding this
layout's high64GiB band. A shrinking/moving-only change within the same band
cannot fit all four. Need an independently demonstrated additional real region
or a compatible source-built browser with smaller compile-time pools. Do not
assert a magic flag fixes it: upstream Chromium126 partition_alloc_config.h
allows DYNAMICALLY_SELECT_POOL_SIZE only for an IOS build, not its Windows
binary. partition_address_space.cc unconditionally initializes regular andBRP
pools. The iOS source fallback is not activated by faking a Windows version.
Official source reference:
https://github.com/chromium/chromium/blob/126.0.6478.127/base/allocator/partition_allocator/src/partition_alloc/partition_address_space.cc
https://github.com/chromium/chromium/blob/126.0.6478.127/base/allocator/partition_allocator/src/partition_alloc/partition_alloc_config.h

Compact layout remains an explicit private experiment, not the ordinary product
baseline or public release. Heavy-game FEX capacity is unverified. Current
milestone: native64Steam/updater runs; interactive64CEF/login/BPM NOT achieved.

## Next timing discriminator (Build72)

Explicit madeira-steam64-early-vm-experiment invokes the existing bounded62call
native probe in a C constructor before application main/SwiftUI/explicit Metal
initialization and before Wine. Linked framework constructors may already have
run: this is not a bare-kernel probe. It writes only a separate private diagnostic
file, never maps over existing regions, never accesses mapped memory and releases
all successful own mappings. Ordinary launches never invoke it. Full72 compile,
ASan/UBSan native probe tests and development signing pass; phone result pending.

Fresh regular-stage native probe in PID26162 completed62requests:8successes,
54failures; only7000000000,7400000000,7800000000,7c00000000 supported the tested
16GiB regions. Need early timing control before attributing to initialization.


## Build72 early probe / CEF source compatibility gate

Actual installed72 constructor probe completes62requests,8successes54failures,
identical tested16GiB homes to the later probe. No additional aligned16GiB
region was found before application main. This rules out moving only the
explicit SwiftUI/Metal initialization as a sufficient solution for tested
regions; linked framework constructors remain outside this timing control.
Private native72-early-results.txt and early72-evidence.json record hashes.

Current Valve libcef/chrome_elf version strings are126.0.6478.183. Import audit
of the actual unmodified AMD64 webhelper requires77libcef symbols. Compared
against upstream CEF6478 commit a5d51ba9db7ee74a523dc247bd09ec91ba4d7446, eight
required names are absent from all public include headers:
cef_set_minimum_font_size, cef_set_preferred_contrast,
cef_set_reduced_motion_enabled, cef_generate_gpu_report,
cef_is_gpu_compositing_disabled, cef_is_hardware_acceleration_enabled,
cef_get_device_scale_factor_for_screen_rect, cef_set_force_device_scale_factor.
This is header-name evidence, not full ABI validation. A stock smaller-pool
CEF build is NOT established as a drop-in Steam browser. Need matching Valve
extension source/ABI semantics and full API-hash/struct compatibility; do not
fake exports or hashes. ValveSoftware/cef public repository lookup failed;
upstream request to update Valve customized source remains public issue12226:
https://github.com/ValveSoftware/steam-for-linux/issues/12226

Official CEF instructions require150–200GB and matching platform toolchain:
https://github.com/chromiumembedded/cef/blob/master/docs/master_build_quick_start.md
This Mac has~5.6GiB internal free and no staged Windows CEF toolchain; external
easystore has capacity, but moving storage alone cannot supply matching Valve
extension source or a verified Windows build toolchain. No giant incomplete
source checkout, unknown replacement binary, custom credential request or paid
service was started. No authentication/DRM changes.

The unsuccessful compact layout is now explicitly opt-in with an additional
madeira-steam64-compact-layout argument in future builds; ordinary64-bit
experiments should not silently use a known-insufficient reduced emulator arena.
Installed72 retains the tested71switch behavior; this final source-only gating
change is not yet installed. Current runtime objective remains UNCOMPLETED:
interactive64Steam/login/BigPicture has not been achieved. Further work is
was blocked at that checkpoint on a demonstrably larger usable VA map or a
compatible smaller-pool browser path. Subsequent hybrid experiments below
continue that investigation. Scheduled automation remains cancelled.

## Hybrid browser workaround (Build72/73; not full AMD64 CEF)

Discriminator: can the current official AMD64 Steam main process1792618285
communicate with the last official i386 webhelper1769731672? The complete
official i386 CEF tree is package-verified on the host. Both its libcef and the
current AMD64 library identify as126.0.6478.183; equal Chromium versions do not
prove Steam IPC/API compatibility. No login cache is copied from the working
prefix. This hybrid still needs a 32-bit guest window and is not an iPad low-VA
fix or a successful all-AMD64 runtime.

The separately authored AMD64 wrapper in tests/steam-ui/hybrid-webhelper.c
forwards arguments to the unmodified official i386 helper. All Valve bytes stay
unchanged and the original AMD64 helper is backed up with a verified hash.
The wrapper logs numeric lifecycle events only. Host ASan/UBSan forwarding and
Werror PE compilation pass.

Actual trials, private artifacts under .madeira-install/steam64-current/:

- First Build72 trial PID26368 never exercised the wrapper: Steam verified its
  expected7501976-byte helper, detected the93184-byte wrapper, and restored the
  original through its updater. bootstrap log is decisive; do not count this
  as a CEF compatibility failure.
- Second trial used recognized per-process -noverifyfiles,
  -nobootstrapperupdate and -skipinitialbootstrap for this private discriminator
  only. The wrapper executed as AMD64, but compact layout rejected its real
  i386 child at guest-window-reserve with c0000017 (wrapper receives1359).
  This layout is inappropriate for the hybrid; no assertion bypass was used.
- Build73 restores normal furniture/FEX geometry. Actual PID26457 created the
  i386 child, which reserved7900000000..7a00000000 and loaded official i386
  libcef at796fe20000. CEF entered its message loop. No CreateBrowser,
  BrowserReady or visible login appeared in the bounded sample.
- Wrapper v2 retained Steam's original working directory (numeric
  cwd-has-steam=1), with the same no-window result. The no-bootstrapper-found
  message ALSO exists in the previously working i386 client logs, so it is
  not a root-cause finding. UI mode7 also occurs in old logs; mode alone is
  not evidence that an unsupported enum caused the failure.

Evidence: hybrid-evidence.json, native72-hybrid-frozen.txt,
native73-hybrid-first.txt, native73-hybrid-v2.txt, hybrid-v2-results.txt and
private Valve browser logs. Their raw contents remain outside Git. A successful
message loop is not a successful Steam login or IPC compatibility result.

## Direct child identity discriminator (Build74)

Hypothesis: the wrapper's additional process identity interferes with Steam's
browser handshake. build/ntdll-unix/steam64_cef32_redirect.h and a small
NtCreateUserProcess hook test this by routing the exact experimental helper path
to its official i386 sibling before opening its image. The real Steam caller
then receives the real browser PID directly. No intermediate wrapper is used.

Requires all three gates: MADEIRA_STEAM_UI_SESSION=1,
MADEIRA_STEAM64_DIRECT_CEF32=1, and WINEPREFIX ending /wine-steam64. Only the
exact C:\\Program Files\\Steam\\bin\\cef\\cef.win64\\steamwebhelper.exe path
is eligible. NT/DOS paths, ImagePathName and argv[0] must agree; argument suffixes
are preserved, caller-owned parameter buffers remain intact, and a contract
mismatch fails explicitly. Ordinary and full AMD64 modes remain unchanged.

Restore the original official AMD64 helper before this test, so normal updater
verification remains enabled. Host ASan/UBSan production UTF16 path/gate tests,
all37native units and full Xcode74 pass. The final linked debug dylib contains
the direct-route marker (unsigned SHA256
41a7ca2181eff1bdb437c8e8eee3091720991c6b52d18e6393c12a50fe71889f).
Development signing verifies deeply. Installation/device handshake/UI results
are a separate gate and must be recorded after observation.


## Build74: protocol-matched AMD64 Steam with official i386 CEF

The current October2026 AMD64 main and frozen January i386 helper have different
embedded HTML IPC schemas:169 versus162 messages, with CMsgBrowserCreate field
numbers changed. This is a concrete compatibility difference, not a captured
proof of which packet caused the previous no-window trial. The read-only
`tools/audit-steam-browser-schema.py --require-identical` compares embedded
descriptors; matching schemas alone do not establish runtime compatibility.

A controlled workaround uses official AMD64 client1769025840 (SteamTracking
manifest commit9dcc2d649a4f6eac9aec4b7a8910ba81bf56e925) and the official i386
CEF/helper1769731672. Both expose169 identical message schemas and CEF126.
Steam's own updater installed the pinned official packages over HTTPS. Actual
device steam.exe was read back, PE Machine8664 and SHA256
59a148465588c1edccde1f049343d2745835fdb80052669b870783538ce1e6c9, matching the
reference official package. Loader evidence confirms steamclient64.dll and the
redirected i386 libcef.dll. No Valve executable is patched. This OLD snapshot is
a compatibility experiment, not a security-current shipping Steam release.

The real login window was visually observed. The user entered credentials and
completed Guard; actual17:10:04 SetLoginState Success/OK confirms authentication.
The user then cancelled the Windows Steam Service maintenance dialog. The
authenticated UI remains at a spinner. Two fixed Big Picture requests were
acknowledged, but no usable home/library was observed. This is not full AMD64
CEF success, game validation, or a resolution for the low-VA iPad issue.

The post-auth native fault is exactly contained in the actual i386 Wine
atlthunk.dll image: guestRIP6bdc1310, modulebase6bdc0000, RVA1310. Disassembly
identifies AtlThunk_FreeData's locked increment at pool+1004; native fault
address7928ef1004 matches. Wine places executable thunk code and mutable pool
metadata inside one native16KiB page, although guest code protection is4KiB.
Hypothesis: protection/SMC coupling faults while freeing an ATL window callback.
The exact host protection mechanism and causal relation to the spinner remain
unproven. Code-buffer guard warnings begin BEFORE successful login and are not
proof of exhaustion or the cause of this fault.

Build75 adds an explicit diagnostic that runs64 direct public ATL callbacks and
64 USER-window destroy callbacks which free the thunk inside WM_NCDESTROY. The
observer logs only its own stages/offsets and never handles exceptions. Launch:
`madeira-atlthunk-diagnostics madeira-steam64-experiment`, with the i386 probe
staged as wine-steam64/drive_c/steam-ui-atlthunk32.exe. Result:
C:\madeira-atlthunk-results.txt. No Steam login or account data is touched.

The separate LGPL Wine overlay in build/atlthunk/atlthunk_ios.c preserves the
original notices and ABI. It pads the executable area to16KiB and moves mutable
metadata to the next host page. It does not disable protection or change FEX.
Build instructions are in tests/steam-ui/README.md. The overlay is NOT part of
Build75: the planned original-versus-overlay device test must precede any fix
claim. The built overlay's AtlThunk_FreeData uses pool+4004 as verified in PE
disassembly.


### ATL control result (Build75)

The first attempt failed at debugger-pool placement before Wine and did NOT run
the probe. A fresh session then ran the original DLL. All128 cycles PASSED while
the native snapshot still recorded the same pool+1004 protection fault and an
undecoded atomic-store instruction0xb8e50305 (AArch64 code emitted by FEX). Guest
VirtualQuery reports RX code and RW data even though they share one16KiB native
page; the host journal reports PROTECTION_FAILURE with currentprot5. No FEX
source is modified. This independently reproduces the page/protection coupling
but also proves the fault need not stop this synthetic process. It therefore
MUST NOT be described as the sole root cause of the authenticated Steam spinner.

Build76 is a disposable repack of successful Xcode75 with ONLY BundleVersion76
and the LGPL i386 ATL overlay. Original DLL SHA256
7454d6cd4d57ca2a6982175c47e1f8996738d79634f841a0575b398ef9ddabaa;
overlay SHA256 a9e1a6a61b1dfe18a6634ec90ad2f5fe5b9885410b8317593fdd873833c0fee1.
Both signing and installation passed. The identical probe is the next gate.


### ATL A/B result (Build76)

The same device probe passes128 with the overlay. Actual data offset changes
4104→16392; same-native-16k-page changes1→0; guest protection remains codeRX and
dataRW. The original's two pool+1004 native protection faults and undecoded
atomic stores disappear. Both runs retain one unrelated native type6 teardown
trap after completing the probe; this is not zero total native exceptions.
This validates the page-separation patch for this ATL contract. It does NOT
prove the earlier Steam spinner is fixed. Build76 then launched the matched
AMD64 main/official i386 browser directly with -bigpicture and saved login.
Visible home/navigation/game are pending fresh evidence. Redacted hashes are
in IDECK_STEAM64_EVIDENCE.json; raw logs remain outside Git.


### Build76 first visible authenticated Big Picture

Fresh saved-login Success/OK at17:40:14 and BrowserReady at17:39:58/17:40:03.
Actual desktop window title Steam Big Picture Mode, i386 browser SP BPM popup.
Device Hub visually showed Welcome to Big Picture over actual home/game tiles
at17:41. This proves visible authenticated Big Picture with the AMD64 main and
official i386 CEF hybrid. It does not prove native AMD64 CEF, input/navigation,
game launch or stability. The UI took roughly90seconds from launch, including
Steam/friends initialization; missing-persona JS errors still occur yet did not
prevent this first visible home. Do not label them the sole blocking cause.


### Build76 input gate

The user reports physical virtual-A does not pass the welcome. Existing helper
confirms XInput connected/HID1 and startup foreground match. Its500ms sampled
button counter can miss short taps, so unchanged count2 is not proof that no
physical button edge arrived. Native snapshot continues to300seconds without
the ATL fault; Steam/browser threads continue server waits and message work.
No hard-freeze root cause is established. Mouse-button messages reach BPM's
Windows HWND. Next use bounded native hit/touch-path counters and a triple-gated
fixed Enter/Right/Escape helper test; never inject credentials or arbitrary keys.


Build77 actual fixed Enter command returned diagnostic-key-sent; subsequent
DeviceHub screenshot shows unobscured genuine Big Picture home/recent game
tiles. Keyboard input reaches the UI and dismisses the welcome. This is stronger
than a dispatch ACK alone. Remote mouse does not trigger native touch hit logs;
physical virtual-pad hit/publish verification remains separate.


Held-A discriminator: user held virtualA for about3seconds. Native touch
press17:54:27 torelease17:54:31, active1/accepting1; Windows helper change
counter0→2 while BPM selection does not activate. This confirms a button edge
reaches XInput. Source host HID report/decoder regression passes. The remaining
Steam controller path is not proven equivalent to normal keyboard input.
Next one-variable environment test: SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS=1.
SDL documentation defines default0 and enabling gamepad input for background
apps. Steam main and visible CEF window belong to different pseudo-processes;
this is a hypothesis about focus filtering, not an established cause.
No binary or cached controller configuration is modified.


Build78 SDL-background trial: user reports stuck again. Keyboard Enter had
opened a real game detail page; current freeze versus pad-input filtering needs
a fresh Escape/snapshot discriminator. Source78 native post-merge samples show
requested/merged D-pad bits8,2,1 correctly reaching the shared input state.
No final SDL-fix claim.

Prepared opt-in alternative: existing helper polls XInput and converts A/B,
D-pad/left-stick into balanced Enter/Escape/arrow pulses ONLY while the actual
foreground visible window has exact Steam Big Picture Mode title AND belongs
to steam.exe/steamwebhelper.exe. It requires the existing diagnostic triple gate
plus MADEIRA_STEAM64_MENU_KEYS=1; default off. It never changes the XInput/HID
snapshot and emits no keys for game/non-Steam windows. Repeat only directions
after400ms then120ms; A/B are edge-only. Host tests cover ordinary/foreign-prefix
refusal, focus/connection loss, holds, repeats/dead-zone and extended key-up
encoding. Windows x64 helper Werror passes. This is a UI-input workaround, not
a fix to Valve's controller pipeline. Pending device validation.

Corrected the newly introduced diagnostic arrows to use VSC_EX/E0 flags; plain
scan codes could describe keypad keys in CEF. Ctrl+1/Enter preserve their
nonextended encoding. The earlier Right trial's exact causal attribution is
therefore limited; visible keyboard Enter/detail response remains established.


## Build78 fresh native failure: signed own-TEB load

Actual freeze-period native snapshot has two faults at address180c with x18=0,
host instruction b9980e48 (ldrsw x8,[x18,#180c]). Caller is exact wow64.dll
RVA1c854; the fault PC is a rewritten native TEB access, not an inferred CEF
base. Faulting Mach thread has registered TEB7931520000, PEB7900310000. Wine
TEB.WowTebOffset is a signed LONG at180c. The existing iOS x18-zero Mach decoder
supports unsigned-immediate LDRX/LDRW/LDRB/LDRH and signed register/unscaled
loads, but lacks unsigned-immediate LDRSW. It therefore declines this precise
legal field read. This is a different failure from the repaired ATL protection
fault. It precedes user freeze; no sole-root-cause claim for all hangs.

Minimal native patch adds only this signed field read, gated by session1 and
isolated wine-steam64, exactRn18/x18zero/field180c/encoding. The existing outer
Mach-thread registry must supply the thread's own TEB; no process-global or
sibling fallback is introduced. It preserves sign extension and other registers
and uses the existing successful-instruction PC-advance path. Host fixture
ASan/UBSan checks exact observed instruction, wrong-prefix/flags/register/offset/
encoding refusal and negative signed offsets. Native/device regression pending.
Build79 is only a prepared helper-overlay trial; NOT installed before this
failure investigation. Native build uses primary generated headers READ-ONLY
while all compiled objects/output stay in this standalone checkout.


Build80 device sequence: visible saved-auth Big Picture home, exact fixed Enter
opens owned Hot Roads details. Official Steam begins its210.88MB installation;
UI shows8percent. No credentials, purchase or EULA automation. First35second
native snapshot has no original native fault, but new signed-load handler was
NOT exercised yet. Thus actual latest compiled fix inclusion is verified while
causal device-fix validation remains pending. UI keyboard fallback remains OFF
and SDL background returns0 for this run.


## Build80 observed native repair and game-launch gate

The later246second native80-play-attempt snapshot ACTUALLY records
[steam64-teb-ldrsw] own registered TEB field; signed load completed. The added
path is therefore linked AND exercised on-device, with no original UNHANDLED
in that bounded snapshot. This validates the specific instruction contract;
it does not establish all UI freezes fixed. Steam appmanifest confirms Hot
Roads1819280 installed StateFlags4, build7695775,221125214bytes. The Play input
attempts still leave no Steam gameprocess entry; no game execution claim.

At22:47 EDT continuation the prior lab process was absent. Revalidated device
and existing build, then launched Steam's supported -applaunch1819280 with
saved prefix. Native log confirms parameters appended and JIT enabled. This
separates UI dispatch from the game/runtime path; initial36second snapshot has
no game launch yet. No new credential entry, license bypass or source change
in this run. Work is now isolated on experiment/steam64-hybrid; main remains
e3d845e. Commit/push only after fresh local-time checks under the user's rule.


The fresh supported-applaunch trial ACTUALLY starts the game: Steam gameprocess
log22:51:11 tracks app1819280/hr.exe, and DeviceHub visually shows its standard
Unity screen-resolution/graphics configuration window over Big Picture. This
proves the Steam-controlled game process launches; gameplay/main-menu rendering
remains unverified. No purchase/EULA/auth automation occurred. Next a narrowly
gated diagnostic Enter may target only the foreground/unambiguous visible
steamapps/common game window, never an account dialog.

Review found the new browser redirect's allocated path buffers were not released
on existing early-denial returns. Clean up only those three new allocations on
each such return; normal behavior and old allocations are unchanged. Native
recompile/full app follow-up required. Research progress stays on the isolated
experiment branch; no public release or main-baseline merge.
