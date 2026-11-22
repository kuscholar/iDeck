## Run83 follow-up — full refresh of a quiet real X11 desktop

At 21:15 EST the selected Air still returned Build86 PID 29952. Health
reached 24774, the frame count stayed at 17022, Play remained zero, and
the white guest crop matched the earlier observation. The read-only
profile inventory again found no exact valid main/helper pair among four
entries. No device input or lifecycle action.

Test the narrower hypothesis that an idle x11vnc cannot deliver a static
frame on a full refresh after the first incremental request. A real
1280x800 Xvfb/x11vnc pair ran twice under LinuxRunner, in separate private
fakefs copies, with the Lab viewer and framebuffer pool. The generated
RFB implementation matches Build93's source byte for byte. Each run
observed one initial frame, one incremental write with no additional
frame during the idle observation, then one accepted full refresh and
a second decoded frame byte-identical to the first. Both finished with
two decoded updates, two published frames, and zero pool exhaustion.
This rejects the hypothesis on this host fixture. It demonstrates that a
freshly decoded frame can be visually identical, including during a
successful refresh. The Air white-screen cause remains open.

Run the following from the experiment root after verifying the stopped
host source root and idle port 5993. The first run passed. Its initial
replay was refused before starting a guest when a historical test's
temporary filename existed in the source root. The final runner uses a
dedicated name and cleans it up within its own cloned guest. The second
run passed with the final runner and left the source database unchanged.

```sh
python3 experiments/linux-steam/tools/test-real-x11-refresh.py \
  "$PRIVATE_LAB/host/ish" "$PRIVATE_LAB/run52/x11-state-clean-root" \
  "$NEW_PRIVATE_OUTPUT"
```

Hashes, package binaries, host receipts and Air snapshot metadata are in
`run83.real_guest_static_x11_refresh`. Build93 remains unsigned and
uninstalled pending matching development profiles. Once safe to upgrade,
compare the actual Air refresh counters with its framebuffer count and
guest crop. If decode and publication advance but the Air still displays
white, inspect current X11 composition before changing the transport.
Steam Play, a licensed game, and repeatable return are all unverified.

## Run83 follow-up — distinguish an incomplete RFB update from a quiet display

At 16:10 EST the exact Air Lab still returned Build86 PID 29952, health
22941, 17022 frames, zero Play, and a white guest crop matching the prior
readback. No input or lifecycle action. A fresh read-only profile check
found zero exact usable Air main/helper entries among four. No repeat of
the failed account/provisioning probes.

The existing one-shot Lab refresh receipt confirms a local write. The
new before/after connection counters distinguish no framebuffer update
started, a partial decode, and a complete decode. Sample again once,
nominally two seconds after the successful write, only if the same viewer
is still attached. Count a decoded message even when it has no rectangles.
These are numeric observations; an RFB server update carries no request ID.
Confirm visible changes separately with frame counters and a screenshot.

Use the Run83 `wake-wire-v2` host recipe with a fresh output directory.
All nine real loopback cases passed under ASan/UBSan. Including the first
good frame, the silent, partial, and empty-update cases respectively show
started/decoded/published counts of 1/1/1, 2/1/1, and 2/2/1. The complete
pixel update delivered a second verified fixture frame. The existing
lifetime and wake cases passed in the same suite.

Use the exact runtime90 evidence commands for the RFB source generator
with frame-pool enabled and the two ARM64 adapters (`LabRFBClient` and
`LinuxSteamViewController`). Redirect their outputs and generated include
path to a fresh tree, copy the runtime archives, and replace those two
objects with `xcrun ar rcs`. Member checks confirmed that only those two
objects changed, excluding the archive symbol index. The original runtime
hashes and LinuxRunner pin match. Run the Build92 private app recipe with
this new runtime tree, fresh app output, and build number 93. Xcode and
package checks passed. The final Mach-O contains both atomic increments,
both loads and the controller's baseline/request/delayed sample calls.
See `run83.build93_refresh_decode_progress` for hashes.

Build93 is unsigned and uninstalled. Once both matching Air development
profiles are available and the existing session can be safely replaced,
reproduce the white screen, send one full refresh, and compare the new
receipt with a real guest crop and independent frame count. The current
bridge still returns diagnostic125. No Windows game cycle or stable
return has been observed.

## Run83 follow-up — Build92 CLI provisioning renewal attempt

At 13:01–13:03 EST, the previous Apple Development identity was still
available in the local keychain. Both archived Lab profiles had expired
at 04:42 UTC on November 20. An isolated two-target `xcodebuild`
`-allowProvisioningUpdates` probe first used manual signing and the two
exact historical profile names. Xcode declined both with no matching
profile. A second probe targeted the selected Air and used automatic
signing with the exact certificate, which Xcode rejected as conflicting
settings. With Xcode's documented `Apple Development` identity type,
automatic provisioning returned `No Accounts` and no matching profiles.
All three probes exited 65. The two bundle IDs and existing team were
used throughout. No device registration flag was supplied. A fresh scan
of four local profiles still found no usable exact Air main/helper pair.
This is the CLI account/provisioning result for this invocation. App
compilation and runtime were not exercised by these probes.

Read-only Air observation confirms existing Build86 PID 29952, health
sequence 21819, 17022 frames, zero Play and the same white guest crop.
Build92's unsigned binary hash still matches its prior audit. There was
no Lab termination, signing of Build92, install, or device input. Obtain
the two renewed development profiles from an authorized Apple Developer
session. Require exact bundle/extension, Air device, existing certificate
and validity matches before signing a copy of Build92 and rechecking
the active Lab. See `run83.build92_cli_profile_renewal` for hashes and
results. Play, game execution, return and stability remain unverified.

## Run83 follow-up — recheck the selected Play request before native Dock handoff

At 11:01 EST the exact Air still showed Build86 PID 29952, health
sequence 21082, 17022 frames and zero Play submissions. The guest crop
matched the earlier white image with cursor. Read-only inventory at
11:01:32 EST found zero valid exact Lab main and helper profiles among
four entries. The running session was left in place.

The Lab-selected Valve option could survive a stale request or missing
shared executable while native Dock asynchronously finished its Steam
connection preparation. Carry its capture sequence with the option.
After preparation and the existing JIT/session checks, verify the same
staged sequence and recheck its physical executable through the retained
shared-library descriptor. Refuse on error before the existing Steam
sign-in handoff. A normal Dock launch with no staged request keeps its
usual launch option and needs no shared-library check.

Run `test-dock-selection.py` with a new private output. Its Swift/C
controls passed matching, stale/replaced, and late missing file cases,
as well as ordinary Dock, real sparse launch-option keys, and request
ownership. Run the existing `test-capture-launch.py --dock-storage`
against the pinned Lab host archives with a new output and the recorded
LLVM/MinGW tools. Its sanitizer control passed the real Linux ELF bridge
and shared-file revalidation. It inspected the included own PE fixture.

Replay the Build91 private app command with the unchanged
`runtime90-late-recheck`, fresh output, and `--build-number 92`.
Unsigned Build92 passed Xcode and package validation. The final ARM64
Dock async resume calls the validation after its Wine session check and
before the existing Steam handoff. Builds, dependencies and device
observation are indexed in `run83.native_dock_final_shared_recheck`.
Build92 has neither been signed nor installed. The exact valid Air main
and helper profiles are still required for a fresh deployment. Once
deployment is available and the prior session is safe to replace, check
a physical full-frame refresh before attempting Steam Play. The bridge
still returns diagnostic125. Windows gameplay, return and repeat
stability remain unverified.

## Run83 follow-up — separate wineserver return from pthread join

At 05:55 EST Build86 PID 29952 still reported 17022 frames, zero
Play, health sequence 19251 and the same white guest-area crop. No
Air mutation. A read-only inventory at 05:57 EST again found no
valid exact profile for the Lab main app or helper.

A successful server pthread join does not establish whether
`wineserver_main` actually returned. In the private Lab adaptation,
the normal return now carries a distinct zero or nonzero token.
The existing early `pthread_exit` path carries neither. A failed
join, no handle, or unrecognized outcome cannot produce a known
main result. The existing bounded native receipt records the new
numeric field. Production bridge sources and runtime guards are
unchanged. This supplies one exit observation, not full Wine
cleanup or consent to restart Linux.

Run `test-wine-initial-join.py` with a new private output. Three
host sanitizer modes passed. Real pthread joins used the exact
generated stop routine and generated return values, including a
thread directly exiting with `pthread_exit(NULL)`. Existing
initial-thread TLS, observer failure and server-join controls
also passed. The actual ARM64 iOS bridge and observer objects
partially link.

Fresh unsigned Build91 reuses the exact qualified runtime90 input.
Replay the Build90 app command with that runtime, new output and
build number 91. Its Xcode package and final ARM64 symbol audit
pass, including the token call after server main, separate
fatal-exit call, actual join call and the receipt field. See
`run83.wineserver_main_result` for hashes. No sign or install.

Next on Air still requires the exact valid main/helper development
profiles and the completed or explicitly authorized end of the
old session. The compatibility bridge remains diagnostic125.
Neither Windows gameplay nor repeated return to Steam is verified.

## Run83 follow-up — full Build90 late-handoff link

At 00:50 EST Air Build86 PID 29952 still reported 17022 frames and
zero Play, with health sequence 17419 and the same white guest-area
crop. There was no device mutation. At 00:50:37 a read-only inventory
of four local signing entries found zero valid exact matches for the
Lab main app or helper. The current session remains in place.

Fresh unsigned Build90 completed the full Xcode build and package
validation with the Build89 feature flags and the same LinuxRunner
pin. Use the Build89 runtime and app commands with newly named private
paths and build number 90. The final ARM64 Mach-O's exact setup method
contains the physical-file recheck and exact sequence rollback before
the ordinary terminal reserve drain and native setup factory. It
also contains the explicit restart's C discard call and the one-shot
RFB refresh handler. Host-tested controller and Swift bridge source
hashes still match. Build90 has not been signed or installed.

The evidence index `run83.linked_build90_late_recheck_candidate` contains
exact final call sites, source/dependency and artifact hashes. No
cause of the white frame or on-device fix is claimed. Use a matching
valid Air Lab main/helper development pair and preserve the old
session until it ends or there is specific authorization to stop it.
Then test a single physical full-frame recovery before attempting
Play and native launch. Windows execution, return and repeat
stability remain unverified.

## Run83 follow-up — recheck again before opening native setup

At 19:45 EST Air Build86 PID 29952 remained alive, with health 15587
and no new frames beyond 17022. The white crop hash matched and Play
remained zero. There was no device action. A read-only scan of four
local entries found zero valid exact development profiles for both
the Air Lab main app and helper.

A file can become unavailable after post-drain validation while the
user considers opening Madeira. Reuse the exact sequence/file check
on that action before the terminal reserve drain. On failure, retire
only the matching Swift snapshot. Keep the C request until the user
chooses the existing discard-and-restart action. A conflicting Swift
sequence leaves both sides untouched and blocks setup. No new
automatic restart, Wine admission or licensing behavior.

Run `test-native-setup-entry.py` and `test-dock-selection.py` with
fresh private outputs. The exact controller methods with counted
stubs verify no terminal drain or setup on either recheck failure
path, and no automatic Linux restart. The real Swift C ABI refuses
zero and wrong sequence values before accepting the exact one.
Both host regressions passed. Separately compile the ARM64 iOS
controller with the recorded runtime89 flags and the Swift bridge
with the harness's extracted model definitions. A relocatable link
resolves the discard symbol. This change is not in the earlier
Build89 binary and has no new final App, signature or Air test.

Commands, source, dependency and artifact hashes are in
`run83.staged_file_recheck_before_native_setup`. The current Git
window still excludes commit and push. Preserve active Air86. A
valid exact main/helper profile pair and a completed or specifically
authorized end to the current Lab are still needed before physical
testing. No Windows game, return or stability proof.

## Run83 follow-up — full Build89 handoff-link verification

At 14:40 EST the selected Air4 still reported
Build86 PID 29952, health 13756 and 17022 frames. The guest-area crop
matched its earlier white frame. Zero Play requests and no Air input
or lifecycle action. A read-only inventory of five local profile
entries found no valid exact main/helper pair for the Air Lab and
existing certificate.

A private unsigned Build89 passed the full Xcode build and package
validation with the already qualified Build88 flags and LinuxRunner
pin, rebuilt into fresh external directories. Staged App build input,
compiler flags, archive hashes and final Mach-O hash are indexed under
`run83.linked_build89_handoff_candidate`. Reproduce using the Build88
runtime and app commands with new private outputs, build number 89 and
the compiler temporary directory on easystore. The already recorded
host capture controls still match the sources byte for byte.

The final binary has a direct call in the retained-owner block to the
physical-library recheck before launch mapping, VDF binding and native
staging. The same exact-symbol disassembly identifies the read-only
validation calls, explicit restart discard and the retained one-shot
RFB handler. The evidence lists only these targeted call sites.
Build89 is neither signed nor installed. This is app integration
evidence. It adds no actual Steam Play, Windows execution or return
validation. Changes remain local outside the Git window. On-device
recovery still requires a matching valid profile pair and a completed
or specifically authorized end to the existing Air test.

## Run83 follow-up — recheck the game file before staging

At 09:34 EST Air Build86 PID 29952, health 11924 and frame count 17022
had the same white-area crop as the preceding device observation.
Zero Play requests and no device mutation. The seven-entry local
profile check again found no valid pair for the exact Air development
bundle, helper, and signing certificate.

The controller now checks the exact pending capture against the
registered physical shared library after a clean Linux frontend
drain, before path mapping, VDF binding or a Madeira request.
A missing, invalid, default-library, or stale capture remains unstaged.
The check is read-only, releases its descriptors, and preserves the
pending sequence for explicit restart recovery. It checks the current
file and path; it is not a cross-phase identity promise or storage
lease, and adds no game execution or licensing path.

Run the existing `test-capture-launch.py --dock-storage` recipe and
repeat with `--capture-off`, each with a fresh private directory.
The host ARM64 probe captured a valid synthetic PE. The native check
then refused it after it was removed or replaced with an empty file,
and accepted it when restored. Invalid, stale and default-library
requests were refused. The capture-off regression and all 48 existing
native file controls passed. No PE was executed.

Using the recorded runtime88 compiler flags, GameFilePolicy.c and
LinuxSteamViewController.m compiled for ARM64 iOS and
`xcrun ld -r -arch arm64` resolved the controller's new policy call.
This is a relocatable link, not a final runnable App. Artifacts and
dependency hashes are indexed in `run83.post_drain_shared_file_recheck`.
The branch remains uncommitted outside the Git window. The next
physical test still needs matching valid profiles and an ended or
specifically authorized existing Lab session. No refresh, Play, game,
return, or stability proof was added on Air.

## Run83 follow-up — recover from an unstaged Play request

At 04:29 EST Air Build86 PID 29952 reported health 10093 and 17022 frames.
The guest area crop matches the 23:21 white frame, including the pointer.
No captured Play and no device action. The two known exact Air profiles
expired before this observation. A read-only scan of the standard local
profile stores and the signed candidate inspected seven entries and
found zero currently valid exact matches for either bundle. No profile
or account action was attempted.

An unstaged Play capture remains owned by the C slot after a failed
Madeira handoff. On the explicit retained-frontend restart button,
discard only the still-matching unstaged sequence after the frontend
and display drained. A request already owned by Madeira refuses
restart. A mismatched sequence leaves the slot and display untouched.
The existing ordinary Metal reopen gate then governs the next Linux
wave. The button says it discards a Play request. This path grants no
Wine admission and performs no automatic retry.

Use the existing `test-capture-launch.py --dock-storage` recipe, with
fresh private output. The actual host ARM64 ELF and bounded IPC reject
a wrong sequence without freeing the capture, allow the exact discard,
then admit the next request. The synthetic Windows PE is never executed.
`test-native-setup-entry.py <new-private-out>` compiles the exact
restart and setup methods with counted host stubs. It verifies refusal
while the display is undrained, native ownership, stale discard and
Metal failure, as well as one explicit restart and a normal restart.
Both host controls passed under ASan/UBSan.

Replay the recorded runtime88 controller compile with a fresh output
path, once with and once without `IDECK_LAB_NATIVE_SETUP_TRANSITION`.
Both ARM64 iOS objects pass; only the transition object imports
`ideck_game_file_policy_discard`. This change has no new full App
link or device test. Evidence hashes in `run83.unstaged_handoff_retry`.
Next Air test still needs an exact valid main/helper development pair
and the authorized end of the existing Lab test. Diagnostic 125
remains; no game start, game exit, return, or stability claim.

## Run83 follow-up — late white frame and scoped refresh checkpoint

At 23:21–23:22 EST Build86 PID 29952 still responded to numeric health
queries. The guest area had changed from the screensaver strip to white,
with its pointer visible. Two screenshots were identical over the
60-second sampling interval, and the count stayed at 17022. Seven frames
had arrived since the last sample at 18:39. That rules out treating the
earlier frame stall as an uninterrupted decoder stop throughout this
period. It does not establish that the client recovered its interactive UI
or identify which display component accounts for the change. Play remains
zero; there was no input or app lifecycle action.

The exact two snapshots, crop hash, source pin and bounded copies of
Steam's current log files are indexed under `run83.post_idle_white_frame`.
Recent Steam log lines did not establish an interactive foreground view
at this time. No interpreting generic crash-related text as a proven crash.

The signed Build88 main and helper profiles both still matched the Air
development bundle and device and were within validity when read. The
earlier expires at 04:42:34 UTC Nov 20. The standard local Xcode stores
had no later exact match. Authorization to end a live
session and revalidation at install are still prerequisites. Keep the
existing Lab in place. Next physical discriminator is one full-frame
request on Build88 after reproducing the symptom, then a real screen and
frame readback. Genuine Play, licensed Windows game execution and
repeatable return are still unverified.

## Run83 continuation — after the sign-only checkpoint

18:39 Air check: the system notice is gone from the screenshot; no Codex
input. Same Build86 PID 29952 and frame count 17015, health 6555, zero Play.
The partial frame remains. Build88 is signed and verified but uninstalled.
The earlier profile expires at 04:42:34 UTC Nov 20. Revalidate at install
and preserve the old live session until it ends or there is explicit
permission to end only that Lab.

Seven host controls now pass. The partial-reply case proves the receipt
can be true while a guest frame remains stale, and the blocked reader
drains on ordinary viewer shutdown. Current Air has not run this test.
Changes are local outside the approved Git window.

## Run83 continuation — exact refresh linkage and Air signing

At 18:35 EST the same Build86 PID 29952 remained alive. Health 6530
still counted 17015 frames and zero Play requests. A system account
notice was covering the visible residual Steam frame. This belongs
to the physical device user. No input was sent and the Lab was
neither stopped nor upgraded.

Build88 was signed in a separate private copy using the existing exact
Air development profiles and certificate. The main app and helper
both matched the bundle IDs and the physical device. Deep-strict
signature and embedded profile checks passed, and signing preserved
the binary's `__TEXT,__text` SHA-256. The earlier helper profile expires
at 04:42:34 UTC on 2026-11-20. Revalidate the profiles before any later
install. Neither signature nor linkage verifies runtime recovery.

The prior audit used a generic disassembly option with the Mach-O
parser and accidentally retained unrelated instructions. Re-run
`xcrun llvm-objdump --macho --disassemble --dis-symname '<exact block>'`
on Build88. The exact block passes ten bytes to `write:count:` and
calls the completion block. Only the bounded audit is now indexed.
The original private output remains intact. See
`run83.refresh_signing_and_device_notice` for exact hashes.

Resume after the device user handles the system notice. Recheck the
existing session before any authorization-gated Lab test. Keep the
current Air application, accounts and saves. No new physical Steam
interaction, Windows execution, repeatable return or stability proof.

## Run83 continuation — full-frame refresh candidate

Air Build86 PID 29952 still shows a partial idle frame. At 13:10 EST,
health 4584 records 17015 snapshots, only two up from 08:01–08:03, and zero
Play. No app input, restart, signing or upgrade. Keep the existing session
until a physical wake or an authorized end to the current test.

Fresh private Build88 implements one full-frame RFB request in the existing
CLI input opt-in. Six host tests passed and the full unsigned iOS Mach-O
contains the new handler, queued send and receipt fields. The physical test
is a single refresh while reproducing the fault, a new local-write receipt
and independent picture/frame readback. No Air refresh, game or return
validation. See `run83.full_refresh_discriminator` for hashes. These scoped
changes remain local outside the Git window.

## Run83 follow-up — long-idle display stops producing frames

At 08:01–08:03 EST Air Build86 still had the exact existing PID 29952.
Four screenshots separated by roughly 90 seconds had the same cropped
guest content: a narrow strip of Steam artwork over a black lower area.
Health advanced 2729 to 2738 while the frame snapshot count stayed at
17013. The frame pool reported no failure and no Play request arrived.
This observation extends beyond the earlier brief black-to-art transitions.

The native append log is capped. The numeric X11 watcher ran its full
120-sample quota well before the stall, so its last focus/gallery state
cannot identify the current layer. Steam logs have no new fatal,
unresponsive or installation marker in this interval. Current evidence
locates the symptom at or before delivery of the next framebuffer
snapshot. It cannot distinguish Steam rendering, Xvnc, or the viewer
transport reading path. No input, install, or restart was performed.

Use the existing read-only receipt and health recipe for the exact Air
PID, then `sips -c 1400 2280` on each private capture to exclude system
chrome. Reproducible hashes are under `run83.long_idle_frame_stall`. Avoid
blind input to the obscured guest. A normal touch/readback on recovered
art, or a separately authorized Lab display recovery if stalled, comes
before game installation. The commit window had ended, so this evidence
remains in the branch worktree for the next permitted checkpoint.

## Run83 continuation — native server exit receipt

Same live Air86 PID 29952 still alternates between Steam idle artwork and a
black loading frame. Health 220 and 248 show frames 1161 and 1279 with no Play
request. No input or restart was performed. Keep Air86 in place. The device
boundary remains a physical tap while Steam artwork is visible, then a real
Install and Play check only after the interactive content returns.

The Lab-only native receipt now retains the actual wineserver pthread join
status, distinct from an absent handle or a failed join. Three real host
pthread modes passed with ASan/UBSan and the full unsigned Build87 iOS package
linked the observer in the real bridge. Build87 reuses the exact runtime86
Linux archive and was not installed. No game exit, all-worker drain, or
return claim. See `run83.wineserver_join_receipt` for exact evidence.

## Run83 continuation — black transition and wake transport

Current Air Build86 PID 29952 showed black with a loading indicator and
then genuine Steam screensaver art about 30 seconds later with no added
test input. Health 193 to 196 and frame calls 989 to 1003 confirm the same
live session. Dispatch sequence remains 11 and captured Play requests remain
zero. Preserve the active session. One physical tap while artwork is visible
is the next device discriminator. Verify the actual post-tap screen before
targeting Install or a library selection.

The host ASan/UBSan loopback now checks that the exact Lab wake packet
sequence arrives as move, press, release. Four existing RFB lifetime cases
also pass. This narrows the problem beyond intermittent host-fixture
coalescing and does not verify Air transport or Steam-side wake handling.
No new iOS build was deployed. See `run83.wake_wire_control` for hashes.
The actual game installation, licensed Madeira launch and repeatable return
are still open.

## Run83 continuation — repeated ARM64 stack regression

The same Air Lab86 PID 29952 still renders Steam screensaver artwork. Escape
was acknowledged as Lab event 11. The artwork continued to rotate after the
settling interval. Latest health 175 shows 914 frame calls, 223 successful
guarded stack reservations in 223 requests, and zero Play requests. A
physical wake tap is still the device test boundary. No installer or terms
screen is visible.

The opt-in retained-root regression now runs the exact guarded stack
shape through a real ARM64 ELF on the current host archive. Default and
opt-in modes each pass four waves with 16 assertions per wave. In the
opt-in mode the stack has a 64 KiB inaccessible guard, protection for the
usable stack, and a new thread that runs through the guest clone/futex path.
Each wave was joined and reaped with the same init/root/mm. Host counts
confirm exactly one additional eligible and successful reservation per wave,
with zero reservation failures. The harness default still exercises the
ordinary ELF fixture. A first default run caught macOS Bash treating an empty
array as unbound; both modes passed after correcting that harness issue.

Reproduce using the earlier retained-root command and a fresh private output.
Add `LINUX_LAB_RETAINED_STACK_ARCHIVE` pointing to the prepared host
`run83/stack-host-v1/libish.a` to select the new case. Raw fixture output and
device captures stay private. Host results do not establish an Air game
handoff or a return to Steam. Keep the current Air session available.

## Run83 follow-up — Steam screensaver transition and handoff controls

The brief black view during idle transitioned to Steam artwork in the same
Air86 PID. Webhelper recorded a screensaver transition at 05:46:25–31 UTC.
Numeric X11 showed the same two mapped 1280x800 windows and the same focus
before and after. Frame count advanced to 625. The capped native log has no
fault rows before its cutoff. Health counts 222/222 matching stack
reservations and zero Play requests. One wake on visible art delivered ACK
10. Its immediate readback still showed artwork. Preserve the session and
recheck the settled frame before any game action.

Host rechecks of the actual Dock selection, request staging and initial Wine
pthread/TLS join passed. The continue path still depends on a real installed
owned title and valid Play request, then verified shutdown and licensed
Madeira launch. Steam reports two libraries but zero installed app manifests
at startup. No game launch, game exit or return is verified. The initial Wine
join marker covers one thread. Full Wine worker/FEX/display quiescence needs
separate evidence before any return implementation can revive Linux.

After wake ACK 10 the next physical observation was still rotating Steam
screensaver artwork. Build86 health 140 and frame 684 were read back from the
same live PID. The safe interaction boundary is now one user tap on visible
screen-saver art, then the genuine Install control when it is visible.

## Run83 Air86 Library, Big Picture and navigation verified

The Air4 rendered the real Steam Store after the official updater. One
Library click led to the actual list, covers and news. The first Big Picture
click produced a tooltip. A repeat after the Library finished loading entered
Big Picture. Right moved focus to Ratatan and Enter opened its details. These
fixed Lab CLI events went through existing RFB input, with screen readback.
Physical touch and controller tests remain pending.

Health sequence 105 reports 220 successful lazy reservations on 220 matching
stack requests, zero placement or metadata failures and zero game requests.
Two bounded observers produced 62 successful native log copies through health
70, with two transient copy failures. No guest fault was observed in the
successful snapshots. The append log later capped, limiting claims about
faults after that window.

Ratatan is offered as Install, with 1.68 GB required. The Up/Enter path
highlighted Install but displayed Steam search instead of an install
destination. Idle artwork then covered the view. One wake moved the pointer
and eventually restored the game details. Back was acknowledged, but search
remained visible. The current path still needs a direct tap on the visible
Install control from the user. If prompted, the user should choose the
isolated `/mnt/ideck/SteamLibrary` and decide personally on any game terms.

Preserve Build86 PID 29952, installation
`6A3F5231-4CEE-4904-8743-2B76549237BA`, receipt
`kernel-29952-1220594-27127000.log`. Both bounded observers finished.
No game install, Play request, Madeira game or return verified. Goal active.

## Run83 Build86 installed and running on Air4

Build 86 passed full Xcode build, package verification, matching Air app and
helper profile and certificate checks, deep strict signing and final signed
Mach-O verification. The final binary dispatches guest mmap to both the
bounded lazy path and ordinary mapper. Its SHA-256 is
`c1baf24ffb241118393e230851a393ef4baf225ca721ee3924987e3d28bdb7f2`.

The prior failed Build85 was still black, with 996 frame calls and zero game
requests. CoreDevice confirmed its normal termination and absence before one
same-container install. Build86 version, installation
`6A3F5231-4CEE-4904-8743-2B76549237BA` and PID `29952` read back. The Lab
launch uses the retained interpreter with ISH_JIT=0. Receipt
`kernel-29952-1220594-27127000.log` matches the install. The first Air health
record counts 9 eligible requests and 9 successful lazy reservations, with
zero placement or metadata failures. It also shows zero game requests.

Bounded observer `monitor86-stack-private.py` in private workspace session
43870, artifacts under `run83/bounded86-stack-private`, follows startup and
ends at the first guest fault or 480 seconds. Preserve this session. A true
Library, BPM and game-return check remain pending.

## Run83 — glibc MAP_STACK reservation discriminator

Build 85 stopped at a thread-stack mapping request before clone. The requested
size was 0x410000 bytes and protection was PROT_NONE. Build 86 adds the
default-off `--lazy-stack-reservation` option. It routes this exact anonymous
MAP_STACK shape through LinuxRunner's existing lazy private VMA path. The
qualifying request retains guest address selection. Normal mappings still use
their existing paths. Post-cap health reports request, reserved, no-hole and
metadata-failure counts.

On Mac, the base and patched Linux kernel libraries both passed real syscall
handler tests covering guard read/write refusal, stack protection, zero-fill,
fork isolation, partial unmap, final cleanup and excluded mapping shapes. The
patched mmap translation unit and fixture ran with ASan/UBSan. This exercises
the host implementation. The Air test still needs to show whether the request
uses the new path and whether Library remains interactive.

The exact copied-archive builder and host test are
`experiments/linux-steam/tools/build-lazy-stack-map.py` and
`experiments/linux-steam/tools/lazy-stack-map-control.c`. The run83 evidence
record pins command and input/output hashes. Current Air85 PID 29444 remains in
place while the new binary is qualified. Full goal stays active. The Windows
bridge still returns diagnostic 125.

## Run82 Air85 Library result and follow-up (November 19, 00:19 EST)

On the selected Air4, Build 85 retained interpreter session PID 29444 rendered
the actual Store and Friends. One Library click was acknowledged. The center
went black. The startup observer and first-fault observer both exited. The
latest read-only CLI process check confirms the same PID and installation. A
fresh physical screenshot shows a black canvas and the Lab controls. Health
sequence 2566 reports zero Play requests.

The first fault follows a different path than Build 84. The saved instructions
match the current official ARM64 CEF executable at ELF 0x62fdc5c. Its helper
calls pthread_create and checks whether the return was zero. Guest tid 368
attempted anonymous MAP_STACK with length 0x410000 and PROT_NONE. It returned
ENOMEM. The retained call trace contains no later clone before the trap.
The initial failure log has zero realfs MMAP_FAILURE rows. Later capped-log
health reports 245 eligible shared-file attempts, 154 successful allocations
and releases, and 91 capacity refusals. The reserve reached 16 MiB peak and
zero live bytes. This verifies its use on Air and leaves Library stability
unresolved. The failing stack request is below LinuxRunner's 16 MiB threshold
for anonymous PROT_NONE lazy reservations.

The next discriminator uses the existing lazy reservation path for the exact
observed no-hint private anonymous MAP_STACK request. Guard access, partial
protection, fork, unmap and excluded mappings need real Linux syscall tests.
Keep the active Air session during qualification. See run82 in the evidence JSON
for source and artifact hashes. The game bridge still returns diagnostic 125.

# Run82 ACTUAL85 on Air29444: owned reserve prepared; preserve bounded test

2026-11-18 ~17:13EST. Signed85 installed/readback85, install58512AB8-BA56-48B3-
8F9D-96373A0FB1C9. Fresh old84/29037 black/noPlay normallyended once/absent;
no uninstall/data change. Before intendedlaunch, system already had85idle29384:
receipt85 butphase0/guests0/workers0/framepreps0/reservestate0 and Home screen,
retained_argument0. Guard refused overlap. After fresh exactidle proof, normalend
29384/confirmabsence, ONE correct retained interpreter launch29444. No Linux
crash/trust/credential or active Steam-test interruption inferred from prewarm.

CURRENT29444 receiptkernel-29444-1194383-255887000.log, actual state1 reserve
prepared16MiB/nativepage16384; activation0/blocks0/no debugger or preparedarena.
InitialrealUI is officialSteam updater extraction, NOT Library/BPM. Actual
bootstrap extraction22:10:03UTC/updatecomplete22:13:16UTC; wait live startup.
Active bounded observer WORKmonitor85-reserve-private.py unifiedsession3977,
private run82/bounded85-reserve-private,300s/read-only, stopsfirstfault. Do not
launch another observer/researcher/build/reinstall/restart. Latestcounters0
mapped/attempts, so allocator adoption and UI benefit remain UNTESTED. Read
actual summary/health/screens before any nextinput. No EULA/Guard automation.

HOST11module/13realLinuxPTE+memfd/10health gates, fullXcode85/finalsignedcalls/
matchedAirprofiles/deepstrict/text preservation PASS. Details below. GoalACTIVE,
bridge125 diagnostic/no game/return/stability, no STABLE_SUCCESS/unload.
Main2ac39/originexperiment9733746 unchanged; weekday17:13 outsideGitwindow,
leave editsuncommitted/unpushed. CLIonly/noMacunlock/security/FEX/Valve edits.

# Run82 / Build85: owned shared-file VA reserve, HOST-qualified; device test next

2026-11-18 ~17:08EST. Same HEAD9733746228f405670734b80b7b1c1964080ea84a /
originexperiment; main2ac39 unchanged, mount UUID580CADCD-33F5-4D78-9530-
2287615873CA verified. Git window CLOSED: scoped source/tests/docs remain dirty,
no commit/push. Continue this active writer; no parallel researcher.

Air last observed16:46: Build84/PID29037/install8858F329-3E17-444F-842C-
67CA4AAB61B0, receiptkernel-29037-1181169-763346000.log, real header but black
centralLibrary/noPlay/submitted0. Preserve until fresh identity+physicalscreen
check; no old EULA prompt/action, no credentials/Guard/lock/Mac unlock requests.

Run81 actual failed262144Bfilemaps/16MiBreserve-release success motivated ONE
allocator experiment. New default-off --shared-file-reserve owns16MiB preguest
PROT_NONE nativeVA; only originalENOMEM + regularnativefile sharedRW/offset0/
nativepage-aligned <=16MiB may map actual samefile into a free OWN span.
No guessed guest addresses, shared-file copy, mprotect/check suppression or
syscall retry loop. Old observational map/headroom probes MUST be off. Existing
PTE data references release live mapping only at lastref/failedpt_map transfer;
replace with ownedemptyreservation. Failure quarantines/poisons, never repairs
unknown VA. Terminal native setup refuses live/quarantined state; do not claim
this proves full Linux/Wine reclamation or game handoff. No FEX/vendor/Valve edits.

HOST PASS:11 realDarwin ownership/capacity/failure modes/800concurrentallocations;
13actualLinux realfs/sys_mmap64/PTE/fd modes include sharedalias/partialunmap/
fork/memfd seals+closedfd/data+metadatafailure cleanup. Nativehealth10gates and
post-logcap prepare/map/release/drain pass. Changedunits+ownhelper ASan/UBSan,
not wholedependencies. OriginalENOMEM HOST-injected, NOT actual iOS fragmentation.
Reproducible new scripts app/SharedFileReserve.[ch], tools/build-shared-file-
reserve.py/shared_file_reserve_patch.py/test-shared-file-reserve[-integration].py.

Private run82/runtime85 + hybrid85 fullXcode/package PASS; signed85 matches
existing Air app/helper/device/cert/unexpired profiles, deepstrict and exact
__TEXT preserved. Actual final reserve/old stack+pread+caller16/PTE/framepool
calls checked, HOST injection and oldprobes absent. New85 has NOT been installed
or device-run in this checkpoint. Build != runtimefix. Source identity still
com.kuschqin.ideck.freshtest/iDeckLinuxLab, existing container preserved.

NEXT single discriminator: revalidate exact current84 receipt/process/noPlay and
physical black screen; if still failed, normalend only Lab once, confirmabsence,
upgrade qualified85/verifyinstalledversion and launch interpreter0 once. Observe
structured reserve counters (including afterlogcap) and firstfault/actualUI;
bounded controls only after visibleview. Don't overwrite binary while testing.
Full goal ACTIVE: genuine repeatLibrary/BPM + Play->licensedMadeira game->return
stillunproven, bridge125 diagnostic. No STABLE_SUCCESS or scheduler unload.

# Current Run81/Build84: distinct compositor shared-map ENOMEM; HOST reserve prototype next

2026-11-18 ~13:40EST. Preserve Air84PID29037/install8858F329-3E17-444F-842C-
67CA4AAB61B0/receiptkernel-29037-1181169-763346000.log, ISH_JIT0/noarena/debugger.
No active build/LLDB/RFBrelay/boundedobserver. Initial observer41863 completed300s;
after-Library observer completed at firstfault. LatestCLI1/action0, health45,
noPlay/submitted0. ActualStore+Friends rendered, oneLibraryclick then central
black withFriendsstillvisible, not Library/BPM success. Do not repeat old EULA
request while no EULA visible. Main2ac39/originexperiment9733746 reverified13:32;
nine scoped files dirty, outside Gitwindow, no commit/push. All other apps/state
preserved. No STABLE_SUCCESS/unload or Mac unlock requests.

Actual84 diagnostic works:416code-only callerrows/maxframe15 before firstfault,
61distinctmatches/53unique in exact actualCEF. Re-read officialELF218132264B/SHA
891d85f97231fcafa5763b7140039c5d3cbbb99f2a42ede08de5991abcbc3cdb. FirstCURRENT84
fault Compositor286/group279/PCe84ae060→ELF635e060, NOT prior82Chrome_ChildIOT/
CrashHungProcess. Twooccurrence rows are SAMEfault. Static actualELF reference
nearcaller7a15364 is BitmapRasterBufferProvider; no invented exactsourcecause.
Main279pretrap16frames nowavailable (older8insideWaitMany), symbolizerresults
current84-callers-at-first-fault-private.json. Raw allprivate run81.

Most useful CURRENT discriminator: fourMMAP_FAILURE rows before firsttrap,
twoactualDarwin262144BsharedRWfilemaps offset0→ENOMEM (Compositor286 +browser188).
Samefd16KiBsharedRWcontrol succeeds;262144Bread-onlyshared/privateRW/anonymousRW
allENOMEM. ReleasingOWN16MiBPROT_NONEreserve thenfreshOS-selectedsamefd262144B
sharedRW succeeds andunmaps. Original-12 preserved. Nearbyfootprint2.26GB/
available745MB/regions52.9k. Supports contiguous usable nativeVA fragmentation/
placement hypothesis, NOT totalRAMexhaustion/strict64kcap proof; concurrent
allocationactivity remains uncontrolled. Different from Run80 finitefirsttrap
0MMAP_FAILURE/CrashHung and subsequentlateStore recovery; don'tconflate them.

NEXT independent HOST prototype: a bounded16MiB nativeVA reserve for eligible
regularfileMAP_SHARED/RW/offset0/nativepage-aligned maps ONLY after realENOMEM.
Use only addresses insideOWNreservation, never guest/arbitrary addresses; no
blind loop/retry or mprotect workaround. Preserve real sharedfilebacking/bytes,
validate ownership/lastref release, capacity/error paths, quarantine failures,
no-fallback ordinary paths and proper teardown. No production/sourceintegration
until meaningful realDarwin mapping/alias/refusal/concurrency tests PASS. This
prototype is PLANNED, not implemented. Keep current84 alive while HOSTwork.
Potential future Lab-only flag/copiedrealfs +data_release ownership hooks, no
FEX/Valve/vendor/JIT/ordinaryMadeira/sourceapp identity changes; not yet designed
or qualified, no successclaim. Future device test only after fullbuild/sign/link.

# Current: actual Build84 diagnostic, Air PID29037 — preserve startup

2026-11-18 ~13:31EST. HEAD9733746228f405670734b80b7b1c1964080ea84a,
experiment/linux-steam-madeira-ipad origin kuscholar/iDeck. Main2ac39 unchanged.
MountUUID verified. Nine scoped source/test/docs files dirty, outside Git hours;
no commit/push. No FEX/Valve/vendor/working-app/auth/save/security/lock changes.

Live Air Lab Build84 PID29037, install8858F329-3E17-444F-842C-67CA4AAB61B0,
receiptkernel-29037-1181169-763346000.log. ISH_JIT0/no debugger/preparedarena.
Oldfailed82/28690 normallyended after fresh identity/black/CLI1/noPlay; same Lab
upgrade install0 independently apps84 readback, then launch once. Data retained.
Earlyhealth2 phase7/21guests/activation0/nativeemission0, updater only. No true84
interactive frontend,16caller,game orreturn proof yet. No overlapping build/LLDB.

User black report WAS verified. Run78 motion-only/Escape/F1 failed; normal same82
recovery Run80 updater completed18:14:11UTC/verification18:14:20, new loginSuccess
OK18:15:13 without credentials. Account spinner thenblack; fresh X11 mapped
windows briefly then9allunmapped/focus0. Uncapped1119606B first-traplog has
0MMAP_FAILURE and2occurrences SAMEtid286/group281/PCe83d1504. Actual post-update
CEF218132264B/SHA891d85f97231fcafa5763b7140039c5d3cbbb99f2a42ede08de5991abcbc3cdb;
unique36B disk62714f4->ELFPC6281504, savedEBAF6800->ELF99a6800/BL99a67fc->6281514
matches prior exact-source CrashHungProcess, NOT independent two faults/canary/
nearestexport cause. Higher8frame main281 stops insidewait, producer UNKNOWN.
Later realStore fullyrendered by13:25 (exactreadytimeunobserved); so firsttrap
is NOT proven toexplain all subsequent black duration. ONE LibraryACK1 then
white dropdown/fullblack again; temporal sequence is NOT clickcausation proof.
No Library/BPM/game/return recovery. Current user has NO visible EULA to accept;
do NOT repeat old acceptance request or automate terms.

84 adds explicit diagnostic --blocked-wait-frames16; originaldefault4 and8 kept.
Same guard/helperbody, no arbitrary payloads/page materialization/wait/watchdog
changes. Symbolizer0..15/bounded256/all ambiguities. HOST42realPTE ASanUBSanWerror
and realownedELFframe15 unique/duplicate controls PASS. Fullruntime/Xcode/package,
actualSIGNEDhelper16/776B+sampler and oldstack/env/pread/pool/PTE/hash/headroom
linkage/deepstrict/text preservation PASS. Existing authorized profiles match
Air+main+helper+certificate+expiry; no GUI/account/security changes. Prior83wake
motionfixcompiledbutaction9UNUSEDthisrepro; do notclaimitrepairsoriginalblack.

ACTIVE bounded read-only observer WORKmonitor84-callers-private.py unified
session41863, max300s, health10s + nativeoncephase8. Do not start overlapping
observer/researcher orkillcurrentstartup. Artifactsrun81/bounded84-observer-private.
Use WORKobserve84-private.py UNIQUE_TAG for physicalscreenshot+identity. Do not
use old82controls/oldPIDs. NEXT current84 pre-watchdoghighercallers + firstfault,
exactcurrentELF matching, then onecause-specific test. UI stillmustbeactually
visible/interactive. No arbitraryblack clicks/terms/password/Guard/trust
operations. CLIonly NEVERMacunlock. FullgoalACTIVE/bridge125NOTgame/noReturn/
noSTABLE_SUCCESS or schedulerunload. Allrawprivate, hashesEVIDENCErun80/81.

# Current: user black screen confirmed; same82 recovery Run80 starting

2026-11-18 ~13:11 EST. Live Lab is now Build82 PID28690, SAME installation
25CA5426-78C8-4811-B23C-E35E716AF926; receipt
kernel-28690-1180035-983450000.log. Old Run78/28190 ended normally after user
reported black and exact process/health/noPlay checks. No reinstall/upgrade,
no debugger, no native arena, ISH_JIT=0. Existing accounts/rootfs/games/saves
preserved. Current source HEAD9733746, five scoped dirty files remain uncommitted
outside weekday Git hours. Private Build83/run79 unsigned/uninstalled.

User report overrides prior EULA as CURRENT screen. Real Air13:02 black; same
Linux RFB framebuffer also black. Pointer-only0,0 visibly moves pointer but does
not restore content. One Escape/CLI31 fails. One F1 creates white left panel,
real screenshot still black/white: no actual menu recovery. No Enter, click,
terms acceptance or credentials. Not stable and not solely Metal composition.
Native cap cannot establish later absence of faults. Fresh private browser logs
show screensaver hide/close18:00:58/59UTC then resource activity18:04:33, not a
proven fault cause. All current raw evidence/hashes in run78 JSON.

Old28190 got ONE normal SIGTERM. Immediate listing still showed process, later
read confirms absent. First launch CLI exit64 (option order, did not execute),
corrected command/fresh no-overlap gate launches28690 exactly once. Official
Steam updater is visibly extracting; health4/phase7/21guests, zero code emitted.
This is NOT interactive recovery. Current helper WORK
observe82-recovery-private.py UNIQUE_TAG ->run80; navigation helper
nav82-recovery-observe-private.py ACTION UNIQUE_TAG uses28690/exact new receipt.
Do not use old run78 controls. Do not touch unknown black/auth/EULA buttons.

NEXT preserve startup/updater42 normal restart and inspect real screenshot.
Once genuine Library/BPM is visibly interactive, restore Ratatan installation
EULA for human reading/acceptance. No account transfer/Guard automation,
no main/FEX/Valve/security/lock/Codex/working-app changes, no Mac unlock request.
Full goal ACTIVE; no STABLE_SUCCESS or scheduler unload. Bridge125 still only
capture, no actual Windows game/return. Do not call83 a black-screen fix.

# Current: Run78 genuine tool selection passed; waiting at game EULA

Updated 2026-11-18 around 12:10 EST. HEAD/origin experiment remain
9733746228f405670734b80b7b1c1964080ea84a; origin/main remains
2ac39beff91251d36f3ad6331d3f8402b3c10e18 (remote read-back at noon).
Mount UUID verified. Outside allowed commit/push hours: leave changes dirty.

Preserve live Air Build82 PID28190, installation
25CA5426-78C8-4811-B23C-E35E716AF926, receipt
kernel-28190-1162536-327396000.log. Same no-arena interpreter run, ISH_JIT=0,
zero native code emitted. No reinstall, restart or debugger this continuation.

Actual Steam Big Picture Properties > Compatibility dropdown displays our
custom `iDeck Madeira (Lab, diagnostic only)` alongside official tools.
ACK19 opens list; ACK20/21 focuses custom tool; ACK22 selects it and the real
Properties UI displays the selected name. No Linux Proton game execution used.
Back23/24 and left27/28 return to focused Ratatan Install. ACK29 opens Install;
a later read-only screenshot shows /mnt/ideck/SteamLibrary selected, 2.94GB free,
1.68GB required. ACK30 reaches official Ratatan EULA. User has been asked to
read/accept on Air. DO NOT automate acceptance, infer it from elapsed time, or
send blind input. Preserve EULA until a fresh reply/state. No depot completion,
Play, native bridge invocation, game or return demonstrated.

Wake limitation: center ACK9 while cursor already centered failed; real blank
header motion ACK10/26 restored menu/game. Keyboard navigation still allows
screensaver. Candidate action9 first moves at most8px, then center press/release;
width<2 refused, masks remain0/1/0 and all gates/throttle retained. Exact-method
ASan/UBSan test fails original on no displacement and passes candidate including
8 repeated-center cases/17 negatives/10 actions/1 narrow refusal. Source and
regression edits isolated. Private Build83/run79 copied runtime, full Xcode,
package and final Mach-O motion/guard/pointer sequence checks PASS. Existing
stack/env/pread/callers/PTE/hash/headroom/pool linkage retained. Build session63955
and verifier90435 finished; NO active build/debugger. Intentionally unsigned,
NOT installed or device-tested. First stack verifier expected absent signed83;
corrected unsigned verifier passes (test-path mismatch, not Linux failure).
Active Build82 remains unchanged. Evidence/hashes in run79 JSON.

NEXT after human EULA: inspect real download to shared library, verify actual
AppID/manifests/content before Play, then diagnostic125 capture and legitimate
Madeira launch/return work. For current UI use WORK nav82-noarena-observe-private.py
ACTION UNIQUE_TAG, observe82-noarena-private.py UNIQUE_TAG. Identity checks
28190/82 precede input. Latest sequence30, health1352, file_policy.submitted0.
Actual input/RFB dispatch ACK is not UI proof. X11 watcher capped120 rows and is
stale after this multi-hour run; do not treat it as current focus/map evidence.
Screenshots/health/raw logs stay private run78; redacted hashes in JSON.
Full goal ACTIVE; no STABLE_SUCCESS, no scheduler unload, no main/FEX/Valve/
security/lock/Codex/working-app/auth transfer changes; never ask Mac unlock.

# Latest Run78 ACTUAL Library/BPM/wake/input PASS initially — preserve28190

HEAD9733746228f405670734b80b7b1c1964080ea84a, originexperimentmatches/main
2ac39beff unchanged11:40EST. MountUUIDverified. DocsdirtyoutsideGitwindow; no
activeLLDB/build/ish/otherresearcher. CurrentSAME82/28190/install25CA5426-78C8-
4811-B23C-E35E716AF926/receiptkernel-28190-1162536-327396000.log. Noarena/
ISH_JIT0/activation0/allnativeemission0; noinstall/debugger/sourcechange.

ActualLibraryACK1 eventually40games/covers/news, screenshotafterLibrary82f.
BPMACK2initialblackthenunobservedgap. Fresh11:41stillSAMEPID/health1212, actual
genuineSteamart/screensaver. ONEwake9ACK3ACTUALLYdismisses tofullBPMhome;
RightACK4TombRaider->Ratatan, EnterACK5detailsInstall1.68GB, RightACK6Controller/
ACK7gearwhite. ThisisrealUIresponse, NOTdispatchonly/processexistence; not
continuous3hourUI/repeatedcoldstart/gamecycle/physicaltouch/Bluetooth proof.
NOgameinstall/Play yet, bridge125/noReturn/fullgoalstillACTIVE. Exactprivate
screens/health/hashesJSONrun78. Logcapped, laterabsenceoffaultNOTproven.

Currentsettingsgear EnterACK8 posted via WORKnav82-noarena-observe-private.py
activatesettingsNoArena82o; inspectactualscreenshot/ACK beforeANYnextinput.
NEXTgenuineSettings->Properties->Compatibility toverifycustomiDeckMadeira
discovery/selection, THENsharedWindowsdepots/download/SteamPlaycapture. Preserve
currentinteractive session/auth. Neverblindclickblack/authscreens/community
text, automatepassword/Guard, replaceworkingapp, editFEX/Valve/security/lock/
Codex/main/otherworktrees oraskMacunlock. NoSTABLE_SUCCESS/unload.

# Latest Run78 LIVE same82/no-unused-arena PID28190 — preserve current updater

SourceHEAD9733746228f405670734b80b7b1c1964080ea84a, docsdirtyoutside08:00
Gitwindow. Canonicalbranch/origin unchanged. NewPID28190/Build82 SAMEinstallation
25CA5426-78C8-4811-B23C-E35E716AF926, receiptkernel-28190-1162536-327396000.log.
Oldfailed28066freshhealth124/noPlay/CLI3/frame548/all8X11childrenunmapped/focus0
thenexactprocessidentitynormalLab-onlySIGTERM. Nootherappdata/processchanged.
SAMEsignedbinary82 noinstall/debugger/startstopped/terminateexisting; omitONLY
linux-steam-native-jit-prepared setup, keepISH_JIT0/TERM/limit200000/soft4MiB/
cacheoff/64KiBpread/8callers/headroom/allpriorflags/rootfs/auth. Nativefaultshim
foroptionalemitternotinstalled/used; interpreterearlyenv-offpathverifiedsource.

Actualhealth3phase7/21guests/activation0/allnativeemission0/noPlay; realofficial
updaterrenders. Earlybaseline96regions/5.39MBfootprint then307regions/16.94MB,
vspriorprepared15489/132.94MBbeforeLinux. Thismeasuresoverheadremovalonly; not
peakRAM/fix/UI/repeatedstability. Finite125575Blog0fault/0mmapfail; laterunknown.
WORK observe82-noarena-private.py NEWtag ->run78; nav82-noarena-observe-private.py
ACTION TAG supportsfixedwake9butONLYonactualSteamart/screensaver, neverblack/
authUI. collect82-noarena-private.py NEWtag numericmarkerlog/private; xstate82-
noarena-private.py NEWtag numericwindows. NoactiveLLDB/build/otherresearcher.

NEXTletnormalupdater42restartcomplete, actualdesktop/Library/BPM/inputthen
wake9discriminator ifscreensaver. Comparefirstfault/VMtomatchedprepared82; no
blindrestart/newruntimepatchduringcurrenttest. Last82hadStore/chromebutfailed
LibraryACK1+2 thenBPMACK3/rootblack/allwindowsteardown, capped1271mappingfail/
17faultrows. NoWake9deviceproofyet. FullgoalACTIVE/bridge125NOTgame/noReturn/
noSTABLE_SUCCESS/unload. CLIonlyNEVERMacunlock/security/lock/Codex/FEX/Valve/
main/otherapps/authsavechanges. RevalidatecurrentPIDbeforeanyaction.

# Latest: Run77 failed UI repeat / Run78 unused-arena control preparing

HEAD9733746 pushed; docsnegative82/run78pendinguncommitted (outside08:00window).
Exact82/28066/25CA5426-78C8-4811-B23C-E35E716AF926 stilllive untilfreshcheck.
No Librarysuccesson82; ACK1+2didnotselectLibrary, BPMACK3blackthenall8X11
childrenunmapped/focus0/frame548/health87noPlay. Wake9NOTsent. Nativeappalive,
notuseractivegame. Cappedlog4194272B/1271MMAP_FAILURE/17guestfaultrows, actual
CEFunchanged891d85f..., first285zygoteCrashHungchain/later353readfault/mmap
stormdistinct. Stablelogcopyaftercapworks; priorCore7000notcrashproof.

Nextonehypothesis: removeUNUSED120MiBpreparedRX+aliasfromISH_JIT0 control.
Actualstartupregion111->15489/footprint5MiB->133MiB beforeguest. SAMEsigned82,
NOrebuild/install, sameallotherflags/env/prefix/rootfs/auth, omitpreparedarg/
debuggerpreparation; existingordinaryinterpreterpathdoesnotneedJIT. Fresh
exactfailed28066/noPlay/allwindowsunmapped beforeLab-onlynormalterminate,
launchoncewithoutstartstopped/terminateexisting, requireactivation0/emission0.
CaptureactualVM/realLibrary/BPM/input; no blindblackclick orsolecauseclaim.
Run78executionPENDING, doNOTassumereplacementPID. Preserveallotherapps/main/
FEX/Valve/security/lock/Codex/account/game/save. CLIonlyNEVERMacunlock.
GoalstillACTIVE/bridge125NOTgame/return/noSTABLE_SUCCESS/unload.

# Latest Run77 ACTUAL82 Air28066 — preserve current updater/session

Source779ccfd1e7247f1dfdedd4f17ffdcd5478c8f45e (check HEAD). Actual installed82
installation25CA5426-78C8-4811-B23C-E35E716AF926, MachOUUID4F0781FB-43F0-3EC5-
A12A-BEC09882D6AD. NewPID28066/receiptkernel-28066-1161226-896401000.log;
NEVER target old27711. Prior81 exact fresh screen/health/CLI11/noPlay captured
then normal Lab-only termination; data-preserving82upgrade installCLI0. New
launch withoutterminate-existing, ISH_JIT0/same120MiB7680pagepreparation.
LLDB11450 normalBPdelete/detach/quit COMPLETE; noactiveLLDB. Initialattach was
asynchronous, firstcontinue saidprocessnotlaunched; afteractualSIGSTOP continued
normally; nootherPID/lock/auth changes. Newhealth2phase7/21guests/zeroemission/
CLI0/noPlay. WORK observe82-private.py NEWtag writes run77; noinput/restart.

ONLY newwake9centercontrol; same81 runtime/rootfs/flags. FullXcode/package/
deepstrictsigning/Airprofile+cert/finalMachOwake+pread+priorpolicies/hosttests PASS.
Not newUI/wake success yet. Letgenuine updater42restart finish, screenshotactual
desktop beforefixed Library/BPMinput. Onactualscreensaver onlyone wake9, wait
nativehealthACK thenphysicalscreenshot. Neednewnavhelperuses28066/build82/
newreceipt andacceptsaction9 (old81helperMUSTNOTreuse). No newruntimevariable
or blindauth/blackinput. Retain current until discriminating test.

Prior81 actual genuineLibrary/BPM/rightRatatan/detailsInstall1.68GBpositive;
no repeatedstablecoldstart/gamePlay/Madeira/return/physicaltouch/Bluetooth.
Bridge125 diagnostic; nogoalcomplete/STABLE_SUCCESS/schedulerunload. Nextafter
wake: configureactualcustomtool/sharedWindowsdepots andlegitimatePlay capture.
CLIonly NEVERMacunlock/security/lock/Codex/FEX/Valve/main/otherapps/authchanges.

# Latest Run76 UI positive / Run77 fixed wake candidate (07:50 EST)

HEAD031216f (inspect current HEAD); exact81/27711/F6A1A1A0/native receipt
kernel-27711-1158218-211890000.log still LIVE. Actual Library and BPM home render;
Right changes Ratatan selection; Enter opens real Ratatan details/Install1.68GB.
Private run76 screenshots81d/e/rightf/detail81m and health49/60/75/135 hashes in
EVIDENCE. No game installed/Play/bridge/game return; physicaltouch/Bluetooth/
repeated stability UNVERIFIED. Keep successful current session until next build
fully qualified. Screensaver art/Away recurs, fixed header clicks/Escape unreliable.
Actual freshhealth239, screenshot-centerwake81n stillart/noPlay. Native CLI ACK11.

Host shared RFB center control fixtures4PASS but actual USBmux5993 Connect
refused BEFORE auth/input; do not repeat unchanged route or infer Steam crash.
Run77/Build82 runtime/fullXcode/package/signing/finalcalls PASS, ONLY new Lab CLI fixed centerwake9
with existing gates/throttle. Source and realhealthwriter sanitizer controlsPASS.
Not installed/devicevalidated yet. WORK build82-private.py completed;
revalidate process/build and finish link/sign before any authorized Lab upgrade.
Same81 flags: ISH_JIT0/TERM/limit200000/prepared120MiB/soft4MiB/cacheoff/8callers/
64KiBregularpread/headroom/priorguards; vendor/FEX/Valve untouched. Existing
observe81-private.py NEWtag safe read-only; no active LLDB. After upgrade never
reuse oldPID/receipt. No success sentinel/unload/fullgoal claim.

# Run76 ACTUAL81 Air27711/updater; boundedpread effect PENDING

REVALIDATE27711/installF6A1A1A0-96AF-4AE1-8741-54FEBE61E072/receiptkernel-27711-
1158218-211890000.log. Build81signedSHA3b196e64..., MachOUUIDBC97841B-CB98-
3615-B94B-1BFBECA1757E. Sourceparent7e41ff0; pending5sourcefiles+docs inspectHEAD.
ONLYnew --bounded-regular-pread: privatecopiedsys_preadregularrealbackend/
request>64KiB<=16MiB/nonmemfd/validranges, one64KiBscratch. Partialprogress/
EOF/errors visible, no newallocation/backendfailure retry orfakebytes/checkpatch.
SameISH_JIT0/TERM/limit200000/soft4MiB/cacheoff/8waitframes/headroom16MiB/
prepared120MiB7680pages/allother80flags. LLDB42160 normaldetachquitCOMPLETE.
Health3phase7/20guests/zeroemission/CLI0/noPlay, actualUIlarge-readresult PENDING.
Workspaceobserve81-private.py NEWtag ->run76; noactiveLLDB. Keepcurrentalive.

FullXcode27nativeobjects/finalpackage/actualsignedpread->64KiBhelper/copy/cleanup/
logger/noHOSTinject/otherprioractualcalls/deepstrict/textPASS. HOST34realPTE/fd/
regularpread cases ASanUBSanWerror: original5170447Bread forcedallocrefusal
ENOMEM/0backend; candidatefullcorrectbytes/79backends/64KiBpeak/onealloc+free.
Independentbackendrefusal sameerrno, no claimactualAirfailuresiteproven. EOF/
short/partialerrors/offset/refcounts/cleanup/pipe/actualmemfdexclusion PASS.
PrivateHOSTv1missingprototypefixed, finalv4; allnegativeartifactsretained.

InstallCLI81timedout120sexit2; no blindreinstall. Actualappsreadback81/F6A1A1A0/
containeraccessible plusprocessesnone; launchedTHATinstalledpackagewithout
terminate-existing. Priorfailed80exact27183/black477/CLI1/noPlay normallyended.
DoNOTtargetoldpid. Source75actual8callers exposedFontServiceThread.MatchFamilyName
wait and earlierBlinkDiskDataAllocator.DoRead pread5170447ENOMEM->PCHECK212;
causalitybetweenfailureandfontreplyunknown.80hadlatermemoryguardsrefuse3/4,
notfixedby34HOSTtests. NEXTlet81updater/normal42restart complete; boundednative
logmarker IDECK_BOUNDED_REGULAR_PREAD_V1 actualrequested/fullresult/backend_error/
copy_failed; comparefirstfaultandknownactualUI. NavigateONLYactualdesktop,
no blindblack/authinput. FullgoalACTIVE/bridge125NOTgame/noSTABLE_SUCCESS/unload.
CLIonlyNEVERMacunlock/credentialsGuardtrustautomation/security/lock/CodexDB/
FEX/Valve/main/otherworktree/app/auth/game/savechanges.

# Run75 ACTUAL80 eightcallers PASS; firstBlinkpreadENOMEM/fontwait; preserve27183

REVALIDATE27183/installF2945DF6-17DF-4ACE-862A-CBF29069CAC4/receiptkernel-27183-
1145336-891225000.log. Latest06:35processinventoryEXACT;health1102/1120 current,
Steamdesktopchrome/blackcontent, LibraryACK1/frame477nochange/noPlay. Noactive
hostLLDB/build/ish. Source80changespending scopedcommit (inspectHEADf4fe4f4).
Original8frameobserverACTUALLYworks(count8/154frame7rows);31codewindowsunique
inexactCEF/glibc. Capped4,194,217B log20MMAP_FAILURE/19guestfaults, finiteonly.
Actual80CEF218132264B/SHA891d85f... copied, matches79. No3hourUIstabilityclaim.

First80faultThreadPoolForeg280/group277/parent156 genericBRKE83D1504 is NOT
same79CrashHungProcesscaller. Actualprecedingpread67 fd31/buf3017204020/
size4ee50f/offset0 returnsENOMEM12. ELFcallerA7CED84+rodataDoRead/Blink
 disk_data_allocator.cc212/Likelyfilecorruption matchesexactChromium126 fullread
PCHECK. Main277highercaller580A6E4/rodataMatchFamilyName/font_service_thread.cc55
andhistogram, sourcepostsMojoquerythenWaitableEventWait59. CausalityUNKNOWN;
laterzygotechildpingmissing/networkservicerestarts cannotbeassumedfirstcause.
No Valve/assertion/watchdog/origin/securitychanges. FullprivatehashesEVIDENCE.

NEXT preserve27183; isolateexactrealregular5MiBsys_pread scratchmallocENOMEM
vsbackend onHOST. A possibledefaultoffbounded64KiB scratchpath requiresfull
bytes/EOF/offset/errors/refcounts/cleanup/nonregular/default regression proof
beforedevice. No blindresource retry/capraise orredesign. Existingpinned
LinuxRunner fs.c sys_pread allocates size+1; fdopsrealfs_pread returnsmappedhost
preaderrors too, so distinguishfailure sites. Do notinferfilecorruption/auth
failure merelyfromgenericfataltext. Workspaceobserve80-private.py NEWtag ->run75.
LLDB64232 detachedquitcomplete; sameISH_JIT0/TERM/limit200000/soft4MiB/cacheoff/
prepared120MiB/other80flags. Currentbridge125NOTgame; noLibrary/BPM/repeated
stability/game/return/noSTABLE_SUCCESS/unload. CLIonlyNEVERMacunlock/credentials/
Guard/trustautomation/security/lock/CodexDB/FEX/Valve changes.

# Run75 ACTUAL80 Air27183/updater; expandedcaller result PENDING

REVALIDATE27183/installF2945DF6-17DF-4ACE-862A-CBF29069CAC4/receiptkernel-27183-
1145336-891225000.log. Build80signedSHA0782a91d..., MachOUUIDBB889FC2-AD13-
3C61-B54B-CC211F263B71. Sourceparentf4fe4f4 (inspectHEAD forcheckpoint).
ONLYnewexplicit --blocked-wait-frames8 with existingobserver, default4 unchanged.
SameISH_JIT0/TERM/limit200000/guestsoft4MiB/cacheoff/headroom16MiB/allotherflags/
prepared120MiB7680pages. LLDB64232 normaldetachquitcomplete, noactiveLLDB.
Health4phase7/21guests/actualzeroemission/CLI0/noPlay. Workspaceobserve80-private.py
NEWtag ->run75. Keepalive, noanotherpatch/restart duringactiveupdater/test.

HOST28realPTEASanUBSanWerror4/8frames/longerchaintruncation/no-materialization/
locks/permissions/generation/accounting PASS, invalid6refused. OwnrealELFframe7
uniqueandduplicateinputambiguous testsPASS. FullXcode27nativeobjects/finalpackage/
actualsignedsampler->helper8bound392Boutput/unchangedinitial+retainedstackpolicy/
deepstrict/text PASS. NOTactual8CEFcaller/UIproofyet. AllprivateART/run75,
exacthashesEVIDENCE. Converterexceptionbinarydistribution remainsunresolved;
onlysourcepublishing, noValve/rootfs/profile/auth/rawlog Git.

Prior79actualStorecontentthenLibraryACK1/black.1453005Buncappedlog0MMAP_FAILURE,
2same282/group277Chrome_ChildIOT BRKreports. CurrentAirCEFactual218132264B/
SHA891d85f... unique36Bdisk6271504/ELF6281504/biasE2150000; savedcallerEBAF6800
BL99a67fc->6281514 sameexactRun60CrashHungProcess, notoriginalinvalidread or
canary. Main277last4cycles1571145624 frozen, untimedfutex393/ffff4390;4frames
stopatWaitManyImpl candidate, HIGHERcallerunknown. CurrentexactCEF/glibc17byte
matchesuniqueinsuppliedmodules. No timedwait/lostwake/allocator solecauseclaim.
Old26979exactblackframe253/CLI1/noPlay normallyendedbeforedata-preserving80;
neverusestalepid. NEXTcaptureboundednativewaitrowsBEFOREwatchdog; require
count>4/frames4..7thenexactmodulebytes/sources, no nearestexport/functionguess.
ObserveactualdesktopbeforeLibrary/BPM/fixedinput. Bridge125NOTgame, fullgoal
ACTIVE/noSTABLE_SUCCESS/schedulerunload. CLIonlyNEVERMacunlock/credentialsGuard/
trustautomation/security/lock/CodexDB/FEX/Valve changes.

# Run74 ACTUAL79 Air26979/updater; keep live, initialpolicy verified

REVALIDATE26979/install317D045A-A99D-40EC-9524-ADCDEE6032C0/receiptkernel-26979-
1144278-955785000.log. Build79 signedSHA640de536..., MachOUUID573D6CBE-C292-
3CD5-A5FD-445E65ED875F. NewLinuxSteam-onlysoft4MiB policy; initialactualfile
/tmp/ideck-steam-stack-policy.txt readssoft_kib4096/hard_kibunlimited. NOT
perCEFstackattributes orUIeffectproof. SameISH_JIT0/TERM/limit200000/cacheoff/
allpreviousflags and120MiBprepared7680pages. LLDB55790 normaldetachquitcomplete;
health2/15 phase7/genuineExtractingPackage/actualzeroemission/CLI0/noPlay.
Workspaceobserve79-private.py NEWtag writesprivate run74. No activeLLDB.

Sourceparent4eb7b86; scopedcheckpoint mayfollow (inspectHEAD). FullXcode/
27nativeadapterobjects (NOTunittests)/34actualPythonunits/envASanUBSan/X11gates/
actualsignedinitial+retainedpolicycommandreferences/deepstrict/text PASS. Initial
broadunittestdiscover errorwasCLIimport; correctedmodulesall34pass, artifactkept.
Hostfinalv2 real32threads4waves/allstacks/barriers/joins/numericreadback/policy
failureblockslaunch PASS. GuestVM32MiBlessat8activethreads, notDarwinRSS or
Steamperformance. Newdefaultoffflag onlyguestsoftlimit, hard/Darwin/explicit
pthreadattributes/nativecaps/FEX/Valve/vendor unchanged. Allartifactsprivate.

Old26573 was exactfailedwhiteBPM/frame450/CLI2/noPlay before normalSIGTERMand
sameLabdata-preservingupgrade. Run73 had actualLibrary game list/widgets after
ACK1; BPMACK2 white loading, nofullstability. Never targetoldPID. NEXT preserve
26979, observeupdate/normal42restartpolicyreadback/realdesktop then onlyknown
Library/BPM/navigation. Captureboundedfault/mmap/UIevidence, no guessingornew
patchduringactiveexperiment. Currentbridge125NOTgame; noPlay/game/return or
repeatedstabilityproof/noSTABLE_SUCCESS/schedulerunload. CLIonlyNEVERMacunlock/
passwordGuardtrustautomation/security/lock/CodexDB/FEX/Valve changes.

# Run74 preparing79; same78/26573 actual Library response, BPM white loading

REVALIDATE26573/installD31078A3-9BA2-40D7-A412-A71F41903558/receiptkernel-26573-
1142335-625714000.log. Same78/emitterOFF/prepared120MiB. Later real desktop
returned; Library fixedevent nativeACK1 -> visible Librarygame list/widgets,
partialcontent. BigPicture fixedevent nativeACK2 -> blackthenwhite loading,
health118/138frame448/noPlay. Actual Libraryresponse is positive partialUI,
NOT repeatedstability orBPM/game. Appendlog cappedbyhealth105; don'tinfer nofault.
Observe onlycurrentactualUI, no blindnavigation onwhite/auth/updater.

HOST real32pthread/glibc2.41 productionpolicy/default/cacheoff/soft4MiB tests
PASS: activeguestVM69943296->36388864B, 32MiBless; threadstack8->4MiB,
soft8->4MiB, sameunlimitedhard. NotDarwinRSS/Steamperformance. Defaultcommand
byte-identical, enabledonlyfixedpolicy, invalidgate2 refused. Newdefaultoff
--pthread-stack-soft-limit is LinuxSteam shellonly, afterX11, bothinitial/
normal42restart. Checkssoft/hard/readback; nohard/Darwin/explicitpthreadattributes/
FEX/Valve/vendor changes. Cachemarker removes misleadingstackunchangedclaim.
FullprivateBuild79 preparingrun74; NOTinstalled/devicevalidated. Finishfull
regressions/finalMachO/signing; revalidatecurrentAirUI/user/game beforeupgrade,
preserveanyrecoveredinteractiveUI. If eligiblefailedsession, authorizedsafeLab
upgradepreservesdata; retainISH_JIT0/TERM/limit200000/prepared120MiB/allotherflags.
Workspacebuild79-private.py; currentobserverobserve78-off-private.py NEWtag.
FullgoalACTIVE/bridge125NOTgame/noSTABLE_SUCCESS/schedulerunload.

# Run73 SAME78 emitter-off live26573; comparison inconclusive, preserve

REVALIDATE26573/installD31078A3-9BA2-40D7-A412-A71F41903558/receiptkernel-26573-
1142335-625714000.log. Source4eb7b86 published. No newinstall/source/runtimebinary;
SAMESHA40a96814..., ONLYISH_JIT=0 added, TERM=dumb/limit200000/guestcacheoff/
headroom16MiB unchanged. Stillnormalprepare120MiB/7680pages/ownoffer. LLDB7090
BPdeleted/normaldetachquitCOMPLETE. Actualhealth6phase7/20guests andhealth43
phase8/138guests, activation1 butEMISSION0blocks/0segments/0bytes. Activation
alone is NOT guestemitter use. Actualgenuineupdater/saveduserdataLoading, then
blackX11; NOinput/game. Workspaceobserve78-off-private.py NEWtag writesrun73.

Uncapped1952362B log131MMAP_FAILURE/0guestfault observed. First2MiBsharedfile
original+fullRO/private/anon fail12;16KiB succeeds; releaseown16MiB thenfullnew
sharedmap/cleanup succeeds, originalerror preserved. This is NOTUIrepair or
proofnativeemittercause; A/B INCONCLUSIVE because native allocation patterns/
failures differ. No roleinference fromhistoricPIDnumber matches, no suppression.

NEXT keepthissession while HOST-only genuineglibc default-stack softlimit
comparison is prepared. Need peakguestVM/realstacksize/hard-limit/function proof
before ANY newAirparameter/restart. DoNOTblindlowerstack/patchmmap/enablePIC;
no broadsmallPROT_NONE lazy change withoutmremap/signal correctness. On freshUI
observe ONLYknownnavigation ifactualdesktopappears; preserveanynewuser/game.

Old26470 endednormally after freshblackframe719/CLI1/noPlay/identity. Main/
allworkingapps/phone/auth/games/saves/FEX/Valve/vendor preserved. CLIonlyNEVER
Macunlock/credentialGuardtrustautomation/security/CodexDB/lockchanges. Fullgoal
ACTIVE/bridge125NOTgame/noSTABLE_SUCCESS/schedulerunload. Rawartifactsprivate,
hashesEVIDENCE; scoped signedoffprogress onlyexperimentbranch allowedhours.

# Run72 actual78 native guestfault after Library; next SAME78 ISH_JIT=0

Revalidate current26470/installD31078A3-9BA2-40D7-A412-A71F41903558/receipt
kernel-26470-1141058-841604000.log. Full78/27units/finalinitial+retainedguestenv/
matchingprofiles/deepstrict/text PASS. ActualLinuxJIT and both cacheoff policy
markers observed. ActualAirlibc1716616B/SHA70fa4c4c matches realHOST32thread
control: guestVM33816576B less withunusedcacheoff, SAME8MiBthreadstacks; NOT
DarwinRSS/Steamperformance. Air4/iPad13,1/27.2(24B119) refreshedNov18.
Saved-auth realdesktopchrome thenONE Libraryclick nativeACK1 -> blackscreen,
noLibrary/BPM/game. Snapshot2463728B uncapped has0MMAP_FAILURE/29guestfaults;
first268/libcefPCe7fb2cf0 reads unmapped5200740079 (no solecause claim). Unique
36Bsite matchedretainedofficialELFfile5e52ce0, notreportedbiased5e55cf0.
Current78 same120MiBpreparedarena/200000attemptbound/JITactivation1. LLDB51014
normaldetachquitCOMPLETE. No repeatedinput/install, no presumeddeadPID.

NEXTONEdiscriminator afterfreshstate/failurecheck: SAMEsigned78 SHA40a96814...
SAMEprefix/data/flags, stillstandardpreparethe same120MiBownRXregion, ONLY
addhostenv ISH_JIT=0 (TERM=dumb/ISH_JIT_BLOCK_LIMIT200000 unchanged). Pinned
jit_init returnsbeforeemission; require actualzeroattempt/segment/bytecounters
plusrealELF/UIobservations. This does NOT patchFEX/Valve or throwaway the VA
region, avoiding thatresourceconfound. Hostnative/interpreter basicELF controls
alreadyqualified, realCEFstillneedsdeviceA/B. DoNOTlowerstacksize/changePIC or
makeanotherguess whilethispending. Workspaceobserve78-private.py NEWtags writes
run72; next runtimeA/B shoulduseNEWrun73artifactdirectory/config/receipts, not
modifythe binary or previousartifacts. Preserve any new user/game session.

Prior77/26281 endednormally onlyafterfreshblackfrozen148/noCLI/noPlay. Actual77
headroomprobe: full4198400B file/sharedmmapENOMEM,16KiBworks/fullRO/private/anon
fail12; releaseown16MiBPROT_NONE succeeds, newfullsharedmapping+cleanup succeeds,
originalguesterrorunchanged. Supports native VAheadroom, NOTUIrepair/solecause.
Sourceparentf559d75; currentRun72sourcecheckpoint pending scopedallowed-hour
review. CLIonlyNEVERMacunlock, credentials/Guard/trustautomation/security/CodexDB/
FEX/Valve/vendor changes. Main/allworkingapps/phone/auth/games/saves preserved.
FullgoalACTIVE/bridge125NOTgame/noSTABLE_SUCCESS or schedulerunload.

# Run71 Build77 live26281: preserve, observe headroom trial and UI

Revalidate PID26281, installation9FF89F76-2D81-4E41-BBDF-759B66E71511 and receipt
kernel-26281-1139093-574003000.log before acting. Full27units/Xcode/finalcalls/
exactAirprofiles/deepstrict/text preservation PASS. Installed same isolated
com.kuschqin.ideck.freshtest, saveddata intact. StandardLLDB56990 detached and
quit normally. Actual early16MiB PROT_NONE reservation prepared1/error0; JIT
selfcheck result0, health5 phase7/21guests/activation1/200000attempts/158945
segments/124991884bytes, genuine SteamExtractingPackage. These are NOT actual
interactiveLibrary/BPM/game/return proof. Do NOT restart/reinstall or clickupdater.
Workspace/observe77-private.py NEWtag writesrun71. On first genuine eligible
mmapENOMEM, inspect IDECK_VA_HEADROOM_PROBE_V1 phase=trial in bounded native log:
reservation_released/fresh_mapping/map_errno/trial_released. No such trial was
observed yet. Then inspect realUI and only known navigation on visibledesktop.

ONLYnew77change: default-off --va-headroom-probe.16MiB untouchedPROT_NONE
reservation BEFORELinux; first eligible shared-file ENOMEM releases ONLY its
own reservation and tries one NEW OS-selected mapping; immediate cleanup,
original guest result/errno unchanged. No MAP_FIXED/hints/payloadaccess/retries.
Host8contractgroups,30exact hook-fixture and30default-regression cases pass.
These are not native capacity/UI fixes. Even a success-after-release cannot
alone distinguish contiguous VA holes from other mapping resources. No capraise.

Old76/26017 normalSIGTERMended after fresh blackscreen/frame317frozen/noCLI/noPlay
and exactidentity; NEVERtargetoldPID. It stayed alive~3h butUIfailed, PTEguard0.
Actual76log18MMAP_FAILURE; first2MiB completefile nativeENOMEM, 16KiB sharedmaps,
fullRO/private/anonymous fail12. No solecause orphysicalRAMexhaustion claim.
Rawartifacts/hash manifests private. Sourceparentf2f881e; inspect currentHEAD
for publishedcheckpoint. Onlyexperimentbranch signedoff/push in allowedhours.
Main, workingapps, phone, auth/games/saves/FEX/Valve/vendor untouched. CLIonly,
NEVERMacunlock, passwords/Guard/trust automation/security/CodexDB changes.
FullgoalACTIVE, bridge125diagnostic, noSTABLE_SUCCESS or schedulerunload.

# Run70 Build76 actual Air JIT/updater live26017, preserve

REVALIDATE26017/install97F66ABD-8575-49D3-850D-DC81AEC86C90.76signedinstalled
sameisolatedLab, preserveddata; standardinteractiveLLDB exactprepareBP,
freshRX120MiB/7680pagewrites/ownoffer/normaldetachquit95332COMPLETE. Actual
health2phase7/21guests/activation1/attempts200000/segments158956/code124992084,
pool3frames0errors/PTEfail0. ActualgenuineSteamExtractingPackage screenshot,
NOTLibrary/BPM/game/return. Preserveactive76; no duplicateinstall/restart/input
onupdater/auth. Workspace/observe76-private.py NEWtag writesrun70. Letnormal
42restart happen, inspectactualUI thenONEknownLibrary/BPMinputwithACK+screen.

Newdefaultoff --map-pte-preflight ordinarymapmetadataallocations BEFORE oldmap/
refcountmutation; failedrangeemptyPTEprune+ENOMEM, backing/accountingrollback.
OriginalHOSTreproduces EXACTnull+26880/0x6900;18realwholekernelASanUBSan cases
allallocations/fresh/replace/PROT_NONE/refs/accounting/metadatacleanup/retryPASS.
9healthgatesPASS, fullruntime26units/Xcode76/finalactualcalls/deepstrict/actual
Airprofile+textpreservationPASS. GuardbranchNOTyetexercisedonAir. InitialiOS
buildermissingbrokerheaderfixed innewruntime76-v2, failedoutputretained.
OnlyONEnewruntimechange vs69, sameISH_JIT_BLOCK_LIMIT200000, noPIC/capraise/
watchdogmask. NoFEX/Valve/vendor/security/CodexDB/lock/credentialGuardtrustedit.
CLIonlyNEVERMacunlock. Existingmain/apps/auth/games/savespreserved. Fullgoal
ACTIVE/bridge125diagnostic/noSTABLE_SUCCESS/schedulerunload. Newsourcecheckpoint
pendingfreshallowed22+localtime; previous9c9cfc6pushedonlyexperimentbranch.

# Run69 actual75 PTE-map crash; preserve newer25946

DoNOTtarget25808: actualOS22:02:20.4471EST SIGSEGV0x6900 atpt_map_accounted+432,
mem_pt_new uncheckedleafcalloc+index; signed75UUID57A9D87D matches. ONE Library
notification22:05 AFTERdeath, transport0/nativeACK0; NO Library/inputproof.
22:08 screenshot home; freshprocess25946 sameinstall1FBC... preservedunknown,
no blindkill/restart/upgrade. Revalidate receipt/process/UI before action.
RuntimeISH_JIT_BLOCK_LIMIT200000 applied; no completeUI/game/return stability.
Next ordinary-PTE failure negativecontrol and checkedpreflight+rollback with
backing/refcount/anonymous-accounting preservation. No PIC or secondhypothesis.
Sourceownedchanges+tests reviewed, checkpoint pending freshdate22+window.
Main/allworkingapps/auth/games/saves/FEX/Valve/vendor untouched. CLIonlyNEVER
Macunlock/passwordGuardtrustautomation/security/CodexDBedits. Bridge125still
diagnostic/fullgoalACTIVE/noSTABLE_SUCCESS/schedulerunload. Rawcrash/frames
private, hashesEVIDENCE. OriginalphysicalAir ELF +LinuxJIT succeeded, NOTfullgoal.

# Run69 SAME75 boundedemitter live25808; preserve, noUIproofyet

REVALIDATE25808/install1FBCBFC7-895D-4127-A67B-A6FB54A336C5. SAMEsigned75
binarySHA65ade143... SAMEprefix/RX120MiB/prep/allflags, ONLYruntimeenvadds
ISH_JIT_BLOCK_LIMIT=200000 (TERM=dumb unchanged, noPIC). Old25523failed
black~22min/15.65Mfulltranslationattempts/segments159610plateau/hashguard2;
normalSIGTERM after freshnoPlay/CLI0/frame335freeze. DoNOTtargetold25523.
Hostimmutableengine+sameownedELF limit2 arithmeticchecksum+16syscalls PASS,
actualattempts2/mixednative+gadgets. New25808standardLLDBattach/preparedBP,
publictools/lldb_prepared_jit.py withNEWprivateconfig,7680pages/offer/normal
detach PASS. No liveLLDB session61400 (quitcomplete). Actualhealth3/phase7/
20guests/JITactivation1/attempts200000/segments158931/bytes124992112, pool3
frames0errors. UpdatedUI stillunverified; observe SAMEsession (workspace/
observe75_limit_private.py NEWtags writesrun69), no duplicateinstall/launch.
NoMemorycapraise/watchdogmask/Valve/FEX/vendor/security/CodexDBchanges, no
credentialGuardtrustautomation. CLIonlyNEVERMacunlock. Main/allworkingapps/
auth/games/saves preserved. FullgoalACTIVE/bridge125NOTgame/noSTABLE_SUCCESS.
Countercorrection: st_blocks countsjit_translateattempts evenafternativepool
full, NOT allsuccessfultranslations; segments/bytes trackinstalledcode.
SourceOWNdirtyweekdaycommitpushCLOSED(last21:50EST); checkfreshlocaltimebefore
commit/push. Forkremoteexperiment971cea/main2ac39be revalidated21:50.

# Run68 initialJITworks but UIblack22min; unlimited25523 ended, nextbounded

DoNOTtarget25523: normalSIGTERM completed after fresh identity/noPlay/CLI0/
frame335frozen andactualblackscreen. Same75 remainsinstalled, UUID1FBCBFC7-
895D-4127-A67B-A6FB54A336C5. NewprewarmPIDmayexist; revalidate/preserveunknown
session. Lastnative receipt25523/health119/15648001jit_translate calls but
159610segments/124989800bytes plateau. Hashgrowthguardactuallytriggered2
onAir whileappalive; NOTgeneralOOM/CEFfix. CEFmain271 signals3 butremained
alive/nonzombie/cyclesadvanced; historicalwebhelperunresponsiveNOTnew75proof.
FullgoalACTIVE/LibraryBPM/game/returnFALSE/noSTABLE_SUCCESS.
NextONEexistingflag ISH_JIT_BLOCK_LIMIT=200000 only, SAMEsigned75/prefix/
120MiBregion/allotherflags, no reinstall/build/capraise/watchdogmask. Host
actualmixednative/fallback limit2 arithmetic+16syscalls qualification in
workspace/native-block-limit-host-private.py pending. Harvest beforedevice.
ThenstoppedNEWPID via existingAirLab, standardinteractiveLLDB +resolved
prepare_debuggerBP, public tools/lldb_prepared_jit.py acceptsONE newprivate
configpath (doNOToverwritepreviousconfig/receipt). Modearg remains linux-
steam-native-jit-prepared. Allcode/offercounts/imageUUIDgates; freshownedRX
only, noPCskip/FEX/Valve/vendoredits/credentialsGuardtrustautomation.
CLIonlyNEVERMacunlock/security/CodexDBchanges; preserveworkingapps/main/data.
SourceOWNdirtyweekdaycommitpushCLOSED(last21:47EST). Rootwritesreviewedonly.

# Run68 actual75 preparednativeJIT + genuineupdater; preserve25523

REVALIDATE PID25523/install1FBCBFC7-895D-4127-A67B-A6FB54A336C5.75signed/
installed sameisolatedLab, actualnormalLLDBattachdyld/prepare_debuggerBP,
newRX120MiB/7680pagewrites6.46s/allACK, ownofferpublished, BPdeleted andnormal
detach. Actualhealth5/phase7/21guests/activation1/212652translatedblocks/
159610segments/124989800codebytes, pool4frames/0errors. ActualgenuineSteam
updaterExtracting, NOTLibrary/BPM/game proof. Keep session, NOrepeatlaunch/
install; wait normal42/drain/restart andinspectactualUI thenONEknowninput.
Fixed120MiB codecache nearlyfullalready; no raise orperformanceinference.
Own prepared-region75receipt validatescodepreparation ONLY; laterhealth proves
selfcheck+faultinstall/actualELF. Private workspace/observe75-private.py NEWtags
writesrun68. No presumedliveLLDBsession (64358normaldetach+quitcomplete).
FullgoalACTIVE/bridge125NOTgame, game/return/stabilityFALSE/noSTABLE_SUCCESS.
NormalMadeira/main/apps/accounts/games/saves preserved. CLIonlyNEVERMacunlock/
credentialGuardtrust/security/FEX/Valve/vendor/CodexDBchanges. Source OWNdirty
weekdaycommitpushCLOSED(last21:27EST), sourceHEAD971cea. Rootwritesrequire
reviewedescalation, no bypass. Next actualLibrary/BPM/stability discrimination
before any further runtime patch.

# Run68 fullBuild75/finalcalls PASS; signing pending, no75deviceproof

Preserve exactAir/currentapps; actualownpaused25506 ended via debugger BEFORE
anyLinux/Steam. Revalidatefreshprocesses; iOS can prewarm newPID withoutargs.
Actual74 alias expectedRX wasRonly (SBMemoryRegionInfo Xfalse), onecode-page
debuggerwrite didNOTgrantX. Fresh native debuggerRX16KiB stayedRX afterwrite,
then freed. No codeexecution inthatcontrol. Wholeoldregion script REFUSED
BEFOREwrites onmissingX; no relaxedguard orknownfault replay.
NewDEFAULT-OFF--debugger-prepared-jit sourceimplemented. Classicdisabled; own
single-use nativeoffer magic/PID/exact120MiB/alignment/pagecount validated.
Copiedjit.c accepts genuineRXrange, normalRWalias/postXcheck/original42test,
existingreadypublication. NoTXM BRK/PCskip/FEX/Valve/vendoredits. HOST12contract
ASanUBSanPASS/backendOSfixtureboundaries explicit. Runtime26units/fullXcode75/
actualMachOcalls/classicdisabled/pool/hash/advicePASS. Signing75 active;
harvest beforedeployment. Private workspace/qualify-sign75-private.py.
Next exactLab-onlyupgrade signed75, NEWstoppedPID +standardinteractiveLLDB.
Set/resolve breakpoint ideck_lab_native_jit_prepare_debugger BEFOREcontinue.
Workspace prepare_linux_jit_offer.py allocatesONLYfreshown120MiB RX, validates
noimageoverlap, prepares per16KiB via developer API, publishes ownfixedoffer
LAST afterall7680writes. Config prepared-region75-config-private.json must
match NEWPID/actual75MachOUUID; nonewrittenyet. No external credentials/PCskip.
Then removeownBP andnormaldetach; check actualselfcheck/result/counters +
genuineSteamUI. All75device/JIT/UI/gameproofFALSEcurrently. OriginalgoalACTIVE,
bridge125NOTgame/noSTABLE_SUCCESS/unload. Main/apps/auth/games/saves preserved.
CLIonlyNEVERMacunlock/trustGuardcredentialautomation/security/CodexDBchanges.
Rootwrites stillrequire reviewed escalation; no approval bypass. Commitpush
weekdayCLOSED(last21:14EST).

# Run67 actual74 classic self-check protection fault; no Linux/JIT success

74installed in isolated existing com.kuschqin.ideck.freshtest, installUUID
1BF10146-010D-453D-B0CF-8BFFA23351CE. NO assumedlivePID: actual25477 dead on
freshinventory. OS20:41:21 SIGBUS/KERN_PROTECTION_FAILURE0x117bf8000 generated
selfcheck ->jit_ios_acquire ->ownprepareclassic ->startFrontend. Native
receiptkernel-25477-1120666-168517000.log health1phase0/0guests/0frames/JIT0.
Actualinteractive standardLLDB attached dyldSIGSTOP then detached. Classic
mprotect passed but generated code was not executable; NOTLinux/CEFfailure.
DO NOTrepeatclassic onthisAir. Needgateknownfailure, thenONEminimal own-region
authorizeddebugger-preparation experiment. OfficialStikJIT1.9.0INTEGRATION.md
andSources/ScriptRunner.swift reviewed: attachalone insufficient underTXM;
per16KiBdebugger-preparation required. No newTXM/adoption code yet.
Earlierprewarm25406 hadNOretainedarg/noLinux; failedlocalCLI launch64 was
argumentordering, notdevicecrash. Correctfreshlaunch25477 hadactualargs.
Rawcrash/LLDB/privatecontrols in workspace/2026-11-17/raise-cybersecurity-concern;
runtime74/fullXcode/finalcalls/deepstrict/matchingAirprofiles/textPASS. Host
realJIT+16syscalls/8health/pinnedDarwinfaultcontrolsPASS, notdeviceUI.
Rootwrites require reviewed escalation; quotaerror earlierresolved, no bypass.
CLIonlyNEVERMacunlock/credentialsGuardtrust/security/FEX/Valve/vendor/CodexDB
edits. Allworkingapps/main/auth/games/saves preserved. FullgoalACTIVE,bridge125
NOTgame/noSTABLE_SUCCESS/unload. CommitpushweekdayCLOSED(last20:44EST).

# Run67 Build74 signed; guarded Lab-only deployment pending

Harvest deployment observer before any repeat. Private command in workspace/
deploy74-private.py; runtime74/fullXcode/final classicfalse->OSacquire then
faultinstall + pool/hash/originaladvice/deepstrict/matchingAirprofiles/textPASS.
73 NEVERinstalled/superseded on fault-installer review. HOST repeated sameELF
+16syscall checks +8healthconfigs +pinned Darwin fault/chaining/failstopPASS.
Current72same25112/install302802A3... freshhealth1768/frame1703/CLI2/noPlay;
screenshot STILLgenuine0x3000 error, no newuser test. Guard preserves changes.
74 launches STOPPED explicitly; exact newPID/install must come from receipt.
Next standard authorized LLDB device attach/detach to NEWPID, then explicit
linux-steam-native-jit-classic tries ONLYclassic OS path BEFORELinux. NoTXM/
BRKscript/entitlement/lock/securitychanges. Refusal=interpreter, handlerfailure
stops beforeguest. Positivehealthtranslations not aloneinteractiveUIproof.
NoFEX/Valve/vendor/CodexDB/auth/Guard/trustautomation; preserveworkingapps/main/
games/saves. CLIonlyNEVERMacunlock. Rootwrite nowneeds reviewed escalation,
temporaryquotaerrorresolved, no bypass. GoalACTIVE/bridge125NOTgame/noSUCCESS.
JITsignal lifecycle/handoff toWine not qualified. CommitpushweekdayCLOSED.

# Run67 optional emitter HOST qualification; actual72 transport error

Preserve72native25112/install302802A3-CFEF-4D64-A4AB-EADBBDE083D9; REVALIDATE.
ActualLibraryblack then genuineSteam0x3000 recoverydialog visuallyverified.
GuestCEFhelper276 Chrome_ChildIOT CrashHungProcess; no primary nativehashfault.
ONE DownACK2; NO Enter/restartoptionactivation, don't infer recovery.
Latesthealth124/56guests/588436992B/pool1703frames0errors/hashfail0/noPlay.
GuardpathNOTexercisedonAir. FullgoalACTIVE/bridge125NOTgame/noSTABLE_SUCCESS.
Run67DEFAULT-OFF--native-jit builder only; completeHOSTengine qualification
being built, NOTiOSactivation orCEFfix. InitialrequiredvDSOlinkerPATHfailure
recorded; v2existingtool-bin/ld.lld. Harvest11934 beforehostcontrol. Keepall
main/apps/auth/games/saves; noFEX/Valve/vendor/security/CodexDB/lockchanges,
CLIonlyNEVERMacunlock/credentialsGuardtrustautomation. CommitpushCLOSEDweekday.

# Run66 actual72 installed/launched; initialphase0, preserve25112

ActualPID25112/install302802A3-CFEF-4D64-A4AB-EADBBDE083D9 mustrevalidate.
Receiptkernel-25112-1102162-361476000.log/build72, firsthealth1/phase0/pool0/
newfiber_hash_growth_failures0. NOLinux/UIproofyet; initialstartupobservation
only. ObserveSAMEsessionwithrun66/observe72-private.py NEWtags, don'trepeat
install/launch. Strictguardmatchedoldinert24805 andstale71receipt24602; only
thatLabnormallyended+samecontainerupgrade, accounts/games/savesunchanged.
Full72Xcode/finalhashcallocNULLbranch/actualflushguard/pool/originaladvice/
deepstrict/exactAirprofiles/signedtextPASS. HostoriginalNULLrepro/guardrollback
+fullengineactualARM64failure1/flush1/exit0 +7healthconfigsPASS. Initialengine/
otherallocsoutofscope, noCEFfix/stabilityclaim. CLIonlyneverMacunlock/security/
credentialGuardtrust/FEX/Valve/vendor/CodexDBedits. Main/allworkingappsuntouched.
Ownsource/docsdirtyweekdaycommitpushCLOSED. FullgoalACTIVE/bridge125NOTgame,
noSTABLE_SUCCESS/unload/goalcomplete.

# Run66 signing72PASS; guarded deployment96584 active

Harvest96584 beforeanyrepeat. FullXcode/finalactualhashNULLguard+pool+original
advice/deepstrict/matchingAirprofiles/signedtext preservationPASS. Freshold71
receiptSTILLdead24602/health38/frame234/noinput/noPlay; current24805sameinstall
03D2128C freshlymatchedbyguard, no newLinuxsessionobserved. Normalendonlythat
oldLab+samecontainerupgrade72inprogress. NOT72device/UIproofyet. Rawrun66
signing/deployreceiptsprivate. No workingapps/auth/games/saves/mainmodified.
One-hypothesishashgrowthcallocfailurepreservesoldtable/existingflush;initial
engine/otherallocsoutofscope. Hostactualfunctions+completeengineELF failure1/
existingflush1/guestexit0+7healthconfigsPASS. CLIonlyneverMacunlock/credentials
Guardtrust/security/FEX/Valve/vendor/CodexDBedits. Ownsource/docsdirtyoutside
commitpushwindow. FullgoalACTIVE/bridge125NOTgame/noSTABLE_SUCCESS/unload.

# Run66 fullXcode72/finalNULLguardPASS; signing active, no72deviceproof

Runtime25units/fullXcode72PASS. FinalactualcallocNULL/oldhash/oldsizebranch +
linkedcounterADRPaddress/flush BEFOREoldlistmutation andinsertflushgating
verified. Existingpool/originaladvicecallsretained. Verifier-onlyglobalsymbol
annotationassumptioncorrectedusingnmaddress onSAMEbinary, no rebuild.
SigningonlydisposablecopyexistingexactAirprofiles; harvestobserver15988before
deploy. Private run66/qualify-sign72-private.py. Candidate72NOTinstalledyet.
Freshcurrent24805same03D2128C install; receiptSTILLdead24602/health38/frame234/
noinput/noPlay observedbefore72; preserveunknownnewsession andstrictguard.
HostcontrolledoriginalNULLfails, guardedrollback+completeengineELF/actualflush
PASS. NoCEF/rootcapacityfixclaim; INITIALengine/otherallocsoutofscope.
CLIonlyneverMacunlock/credentialsGuardtrust/security/FEX/Valve/vendor/CodexDB
changes; main/allworkingapps/accounts/games/saves preserved. Ownsource/docs
dirtyweekdaycommitpushCLOSED. FullgoalACTIVE/bridge125NOTgame/noSTABLE_SUCCESS.

# Run66 runtime72PASS/fullXcodeactive59848, preserve new24805

ActualhostoriginalNULLfailure reproduced; actualguardedresize+insert rollback/
retryboundPASS; COMPLETEengine ARM64ELF injection1/guard1/existingflush1/exit0
PASS. DefaultOFFhashgrowthguardonly; INITIALengine/otherallocsremainoutofscope.
Runtime72compiled25units. FullXcodeobserver59848 ACTIVE; harvestbeforefinal/
sign/deploy. Same71memory/RFB/CASPt lbsourcebytes, kernelarchivehashdifferent
(recompiledmetadata), noarchiveidentityclaim. SourceOWNdirtycommitwindowCLOSED.
Fresh14:54device24805same03D2128C installation preserved, receiptSTILLdead24602/
health38. Readbefore72unchanged. Don'ttarget24602/restartunknownnewusertest.
Private run66/verify-link72-private.py, qualify-sign72-private.py preparednotrun.
FullgoalACTIVE/bridge125NOTgame; noSTABLE_SUCCESS. CLIonlyneverMacunlock/
credentialsGuardtrust/security/FEX/Valve/vendor/CodexDBchanges. Preserveall
workingapps/main/accounts/games/saves.

# Run66 actualHOSThashfailure+engineflushPASS; runtime72building30924

Harvest30924beforeAppbuild. NewDEFAULT-OFF--fiber-hash-growth-guard copied
asbestos.c ONLY. ExistinggrowthcallocNULL preservesoldhash/requestsordinary
flush; no repeatedgrowthwhilepending. INITIALengine/otherallocationsoutofscope.
ActualextractedoriginalfailsNULLlist, guardedrollback/rehashPASS; COMPLETEHOST
engine ownARM64indirectbranchELF injected1growthNULL/guard1/actualflush1/exit0.
SevenhealthconfigsPASS inclnumericcounter. NoFEX/Valve/vendoredit/capraise.
Initialfullfixturezeroactualgrowthfailedgate, correctedindirectbranches(v2PASS).
Private run66 commands/evidence. Build72runtimeaddingonlyflagto71config.
Actual71native24602deadOSreport; new24805sameinstall03D2128C observedfresh14:54
andUNTOUCHED. Receiptold24602, noassumednewLinuxsession; revalidatebeforeany
upgrade. Main/allworkingapps/accounts/games/saves preserved. CLIonlyneverMac
unlock/credentialsGuardtrust/security/CodexDBchanges. CommitpushweekdayCLOSED.
FullgoalACTIVE/bridge125NOTgame/noSTABLE_SUCCESS/unload.

# Run65 terminal71 nativehashgrowthSIGSEGV; Run66 guard next

Actual71PID24602 DEAD10:35:29.9256EST exactOSreport build71/UUID2b509159...,
SIGSEGV0x200000 list_null->list_init_add->fiber_resize_hash->fiber_insert.
Lasthealth38/pool234NOerrorsSTale. Original-adviceA/BINCONCLUSIVE, no71Library/
BPMinputs. New24805sameinstall03D2128C-8695-49F7-B774-79EA7A7539F7 observed
anduntouched; fresh14:54inventorySTILL24805, receiptold24602. NoLinuxsession
assumed/no kill/restart. ActualcurrentCEF218132264B/fullSHA891d85...matches
historical. Rawrun65crash/hash/logsEVIDENCE.
NextONEcopiedenginegrowthcallocfailureguard; preserveoldhash/requestexisting
flush/avoidretryuntilflush. Firstcontrolledactualoriginal-vs-patchedhelper
HOSTfailureinjection, sourceguard/defaultOFF; nofalseCEF/capacityfixclaim.
Initialengineandotherallocfailuresremainoutofscope. CLIonlyneverMacunlock/
credentialsGuardtrust/security/FEX/Valve/vendor/CodexDBchanges. Preservemain/
allapps/auth/games/saves. Ownsource/docsdirty;weekday14:54commitpushCLOSED.
FullgoalACTIVE/bridge125NOTgame/noSTABLE_SUCCESS/unload/complete.

# Run65 actual71 installed/launched; updater ongoing, preserve24602

Actual71nativePID24602/install03D2128C-8695-49F7-B774-79EA7A7539F7 (revalidate),
receiptkernel-24602-1083937-527073000.log. Initialhealth6/pool1prepare4buffers/
5frames/0errors/peak2; physicalofficialSteamupdaterExtracting, NOTLibrary/BPM
proof. DoNOTrepeatinstall/restart.71all70flagsEXCEPTexclusive-discardOFF,
finaloriginalsysmadvise+pool/deepstrict/matchingAirprofiles/signedtextPASS.
Old70whiteblankfreshguardmatched24250/frame359/ACK3/noPlay, normallyendedONLY
Lab thenSAMEcontainerupgrade; auth/games/saves preserved.
Private run65/observe71-private.py NEWtags; awaitnormalupdater42/drain/restart
thenknownLibrary/BPMsameboundedinputs. StrongerHOSTpure-spin metadata7checks
PASS/narrownegative; hostinterruptsallowed, notCEF/deviceclearance. Earlier63
sameCEFfaultpredatesdiscard;71onlycurrentcontributiontest, neverrootcauseproof.
Main/allworkingapps untouched; noFEX/Valve/vendor/security/auth/CodexDBedits.
CLIonlyneverMacunlock. OWNdirtysource/docs/windowCLOSED. FullgoalACTIVE,bridge
125NOTgame/noSTABLE_SUCCESS/unload/goalcomplete.

# Run65 signed71 PASS; guarded SAMEcontainerupgrade active

Harvestdeployobserver14319 beforeanyrepeat. FullXcode/finaloriginalsysmadvise+pool/
exactAirprofiles/deepstrict/textpreservation71PASS. Fresh70physicalWHITEblank/
health256/frame359/CLIseq3/noPlay at10:26; identity24250/install1C100DD2 matched
byguard. NormallyendONLYfailed70 +sameLabcontainerupgrade71 inprogress. No71
UIproofyet. Private run65/deploy71-private.py andair71 receipts.
Hostmetadata7checks andstrongerpure-spin7checksPASS (1exclusive/16brokeralloc+
release/15advice/live0; no guestwaitsyscalls, hostinterruptsstillallowed). No
CEFcorruptionrepro/rootfixclaim. Same63faultpredatesdiscard, so71onlycurrent
contributionA/B. Keepallotherflags/pool/kernelmemorysourceidentical70.
CLIonlyneverMacunlock/security/credentialGuardtrust/FEX/Valve/vendor/CodexDB
changes. Preservemain/allworkingapps/auth/games/saves. WeekdaycommitpushCLOSED;
OWNsource/docsdirty. FullgoalACTIVE/bridge125NOTgame/noSTABLE_SUCCESS.

# Run65 71fullXcode/finaloriginal-advice+poolPASS; signing observer pending

CurrentAir70historicalPID24250/install1C100DD2..., revalidate; Libraryactual
responded, BPMblackthenwhiteblank; ONEEscapeACK3/no recovery. Pool359frames0
errors/peak3; nativehealth142advanced, no newuserPlay. SourceOWNdirtywindowCLOSED.
Hostmetadata/payloadactualARM647checksPASS/12replacement/16alloc+release/15advice,
narrownegative only. Historical63SAMECEFfaultBEFOREdiscard/broker (coarserCoW),
so71iscontributioncomparisonCURRENTconfig, neversolecauseproof. Runtime71
25units/fullXcode/final_sys_madvise->_ideck_original_madvise andpoolcallsPASS.
SAMEallflagsEXCEPT --exclusive-private-discard removed. No71deviceproofyet.
Signingonlydisposable71copy usingmatchingexistingprofiles/cert; harvestexact
observerbeforesafeguardedupgrade. Private run65/qualify-sign71-private.py,
observe71-private.py NEWtags, deploy71-private.py requiresold70sameidentity/
healthpool359/CLIseq3/noPlay; refusals preserveunknownorchangedsession.
CLIonlyneverMacunlock/credentialGuardtrust/security/FEX/Valve/vendor/CodexDB
changes; keepallworkingapps/main/accounts/games/saves. FullgoalACTIVE, bridge
125NOTgame, neverSTABLE_SUCCESS/unload/goalcomplete.

# Run65 metadataHOST7checksPASS; runtime71 original-advice A/B building

Keepcurrent70native24250/install1C100DD2 aliveuntilqualifiedcandidate/freshstate.
ActualLibraryworked; BPMtransitionblackthenWHITEblank, notverifiedGamepadUI.
ONEEscapeACK3, health142/pool359unchanged, no recovery. Pool0errors/peak3 still.
ActualguestCEFfault272SIG11 classifiedreadonly, originunknown. Metadata/payload
HOSTactualARM64sevenchecksPASS,12exclusive replacements/16brokeralloc+release/
15nativeadvice/live0; narrowreproNOTobserved, NOTCEF/deviceclearance.
NextONEcomparison71keep70pool/broker/allflagsEXCEPTremoveexclusive-private-
discard ->originalpinnedmadvise. Runtime71inprogress; harvestbeforeAppbuild.
Private run65/runtime71-command-private.json/log. Noclaimedfix/newdeviceaction.
Userall-safeauthorizationpersists, neverMacunlock/credentials/Guard/trust/
security/FEX/Valve/vendor/CodexDBedits; preservemain/allapps/auth/games/saves.
WeekdaycommitpushCLOSED, OWNdirtyworkpreserved. FullgoalACTIVE,bridge125NOTgame.

# Run64 actual70 Library input works; BPMblack withguestCEF fault; preserve

Currenthistorical native24250/install1C100DD2-F194-4C55-99C3-B6D86803509E must
revalidate.70samecontainerinstalled; savedlogin andLibraryactualgamelist/covers
responded toONEknownclick. ONEBPMclick ->black. Health90/mono1082131385 pool359
frames/0allocfail/0invalid/0exhaustion/358releases/peak3; nativealive, noRFBerror.
Supportedboundedpoolhypothesis, NOTUIstability. ActualguestCEF272 SIGSEGV
E7FB2CF0 invalidpointer6f005200740061. Exact9codewords matchhistoricalofficialCEF
uniquelyfile5e52ce0/ELFfault5e62cf0/biasE2150000. FAULT_MAPoffsetwrong3000:
pinneddiagnosticomitsmapping_offset; nevernearestexport/offsetblindattribution.
PublicChromium126RawFree/FreeInSlotSpanpatterninference, corruptionoriginUNKNOWN.
NoValve/FEX/vendor/security/CodexDB/credentialedits; CLIonlyneverMacunlock.
NextONEminimalhostactualARM64metadata/payload/guardCoW+advicecoherencecontrol,
keepAir70alive, noinputretry oroverlappingdeviceexperiment. Ownchangesdirty
weekdaycommitpushCLOSED. FullgoalACTIVE/bridge125NOTgame/noSTABLE_SUCCESS.

# Run64 actual70 installed/launched; preserve live24250/updater

ActualBuild70PID24250/install1C100DD2-F194-4C55-99C3-B6D86803509E (revalidate),
receiptkernel-24250-1081241-365212000.log; initialhealth2 confirms poolprepared1/
4buffers16,384,000B,3frames/0invalid/0exhaustion/2released/peak2. Physicalscreen
genuineSteamupdaterExtractingpackage, NOTLibrary/login/BPM/gameproof. No
reinstall/restartwhileactive. Expectedexisting one-timeupdaterexit42 handling
retained. Private run64/observe70-private.py NEWtags capturesreceipt/health/screen.
FinalMachO/deepstrict/exactAirprofilecert/textpreservationPASS, signed70immutable.
Oldfailed69exact23891 normallyended thenSAMEcontainerupgraded; auth/games/saves
untouched. FullgoalACTIVE/bridge125NOTgame. AwaitactualframesandknownsafeSteam
Library/BPMnavigation aftergenuineUI appears. RawprivatehashesEVIDENCE. CLIonly
neverMacunlock/credentialsGuardtrust/security/FEX/Valve/vendoredits. Main/all
otherapps/worktrees preserved. WeekdaycommitpushwindowCLOSED; OWNdirtychanges
leftuncommitted. NeverSTABLE_SUCCESS/unload/goalcompletewithoutfullrepeats.

# Run64 fullXcode70/finalMachO PASS; signing7267 active

Samepreparedsource build initiallysandbox-refused workspaceinfo.plist; normal
Xcodeaccess samecommandPASS. Finalactualdecoder->poolselector,init->malloc,
snapshot->memcpy+immutableNoCopy,startup->prepare verified. Signingonlydisposable
70copy existingAirprofiles/cert; observer7267 ACTIVE, owncodesign36715 U at
lastcheck. DoNOTretry/kill/duplicate. Qualifiedartifactnotyetinstalled. Fresh
old69screen09:40stilldisplayallocationfailure, health3636same309calls/1failure/
0navigation; identity23891/installDAD4225A. Safealloperationsauthorization
permitsendONLYthisfailedLab +samecontainerupgrade aftersignpass/freshguard.
Private run64/deploy70-private.py validatesstrictidentity/state andsignedhash.
FullgoalACTIVE/noSTABLE_SUCCESS;25nativeunits/6health/hostpool+decoderPASS.
Main/workingapps/auth/games/saves untouched; noFEX/Valve/vendor/securityedits.
CLIonlyneverMacunlock. WeekdaycommitwindowCLOSED; leaveOWNchangesdirty.

# Run64 HOSTpool+actualdecoder+healthPASS; fullXcode70 active69541

Readactual69failurebelow. FreshAir69native23891/installDAD4225A alive but
displaycheckedmallocFAILED; noinputtest/restartduringhostwork. OneNEWdefaultOFF
--frame-snapshot-pool4slots1280x800 preparedbeforeLinux, immutablelastconsumer
release reuse/lifetime. HOSTASanUBSan/Werror +actualgenerateddecoderfull/partial/
lateallocatorNULL/exhaustion/no callback/cleanup PASS;6healthconfigsPASS;25iOS
unitsPASS. Guestmemoryidentical69/defaultRFBidentical68. Private run64 outputs.
FullXcode70 observer69541 ACTIVE, harvestbeforefinalverify/sign/install. No70
deviceproofyet. Newfiles+docs OWNdirty; weekday09xx closedcommitpushwindow.
DoNOTeditFEX/Valve/vendor/main/security/auth/CodexDBs. CLIonlyneverMacunlock.
SafetestLabupgradeauthorized; revalidatefailed69/anynewusertestbeforeaction.
FullgoalACTIVE,bridge125NOTgame; noSTABLE_SUCCESS/unload/complete.

# Run63 actual69 alive, display FAILED explicitly; new pool experiment next

FreshNov17 09:28 exactAir native23891/installDAD4225A revalidated.69installed/
launched, startup3snapshots0fail, latesthealth3565=309calls/1allocfailure/307
releases/1retainedframe. Actualscreen native Displayerror snapshotallocation
failed;Linuxsessionpreserved over real signed-in SteamStore. Failurecontained,
NOTinteractiveLibrary/BPM. DoNOTrepeatblindinput orclaimUIsuccess/nativeabort.
Rawprivate run63 hashesEVIDENCE. Safeoperations authorized; preserveapps/auth/
games/saves, noFEX/Valve/vendor/security/Codexedits, CLIonlyneverMacunlock.
NextONEdefaultOFF preallocated4slot1280x800 immutableframepool; validate lifetime/
exactpixels/NULL/exhaustion/concurrency thenbuild/link/device. At09:28weekday
commit/pushwindowCLOSED; leaveownedchangesuncommitted. FullgoalACTIVE,bridge125
NOTgame; neverSTABLE_SUCCESS/unload. Oldnotesbelowarehistorical.

# Run63 signing69 PASS; isolated deployment1572 inprogress

ExactAirprofilecert/deepstrict/signtextpreservation actualPASS. Existing26442
completed, notlive. Private run63/sign69-evidence-private.json. InitialnoLab
installguard REFUSED new23816 (retainednegative). ReadcurrentprocesssameoldURI,
receiptSTILLcrashed23696/health34unchanged, no newLinuxstartup. Saferevalidated
exactinert23816 normallyendonly thenSAMEcontainerLab69upgradeobserver1572 now
running. No69runtimeproof; harvestbeforeanyrepeat. Userall-safeauthorization
persists; no workingapps/main/auth/securitychanged. NoMacunlockrequests.

# Run63 aabdb23 pushed; signing69 VERIFIED LIVE, not finished

Sourceimplementation/tests/fullXcode69/finalMachOcalls checkpointaabdb23 pushed.
OwnnormalCLI signingobserver26442 ACTIVE; lastactualps64840 codesign STAT U,
0.3%CPU/elapsed2:53 at23:29EST, waitingdiskI/O; noCodeResourcesseal/receipt yet.
Parent64646/privatequalify-sign69, child64831resign-app,64840codesign onlyTHIS
Lab69disposablecopy. DoNOTkills/retry/rebuild/sign/installfromtimeout. Re-poll
samehandle26442 orrevalidateexactprocessandprivate sign69-evidence receipt.
Keepauthorization/constraints unchanged; not genuineuseractiongate/goalblocked.
No69install/runtimeproofyet. deploy69-private.py preparedrefuseanyoldLabprocess,
runONLYafteractualsignreceipt/deepstrict/textpass andfreshAirsessioncheck.

Useful63done: actualgeneratedRFBfull/partialdecoder withretainedimmutableframes,
forcedmallocNULL/no callback/errorreturn, hostrealFoundationmaxdims512concurrent
snapshots/all515released,5healthconfigs,25iOSunits/fullXcode/finalupdate->helper
andMachOnative_malloc/___memcpy_chk/NoCopyinit bindingPASS. DefaultgeneratedRFB
identical68; guestmemoryidentical68. NoattemptedtinyFoundationinfallibility/
ObjCexceptioncatch/assertionbypass. Existingauth/games/saves/main preserved.
FullgenuineSteamLibrary/BPM +licensedMadeiragame/return/repeatsgoalACTIVE;
bridge125NOTgame. NoSTABLE_SUCCESS/unload/goalcomplete. CLIonlyneverMacunlock/
credentialsGuardtrust/security/FEX/Valve/vendor edits. Rawprivate run63.

--- Prior63 ---

# Run63 signing69 observer26442 live — harvest before deployment

FullXcode69PASS, finalRFBupdate->snapshothelpercall and MachOsymbolizednative
malloc/memcpy_chk/NSDataNoCopyinit verified on SAMEbinary. Unusedmarkerdeadstrip/
genericdisassemblerunsymbolizedCstub verifiernegatives corrected, no rebuild.
Kernelmemoryidentical68. HOSThelper andrealgeneratedRFBdecoder/5healthconfigs
PASS. ExistingAirprofilecert checks signingonlydisposablecopy. Private run63/
qualify-sign69-private.py. Observer26442 active; doNOTduplicate. deploy69-private.py
prepared, refuses ANYoldLabprocess atfreshcheck; runONLYafterdeepstrict/signtext
pass. observe69-private.py NEWtags. No69install/runtimeproofyet. FullgoalACTIVE,
bridge125NOTgame; noSTABLE_SUCCESS/unload. CLIonlyneverMacunlock/credentials/
Guard/trust/security/FEX/Valve/vendor/main/workingapp edits. Data preserved.

# Run63 69 XcodePASS/finalRFBcallPASS; signing49984 inprogress

Harvestobserver49984 beforeanydeploy/signretry. FullXcode69exit0, realfinal
LRRFBClientupdate->checked_snapshot BLverified, nohostallocationinjection;
kernelmemorysourceidentical68. Private run63/final69-linkevidence +signed69
copyinprogress. HOSTsnapshothelper+actualgeneratedRFBdecoder+5healthconfigs
PASS; allnegativesretained. No69install/deviceproofyet. Airfreshinventoryat
runstartNO Labprocess; revalidatebeforeinstall, preserveanynewusertest.
Existingprofilematch/cert/signtext/deepstrict required. NoFEX/Valve/vendor/
main/security/authchanges. FullgoalACTIVE/bridge125NOTgame/neverSTABLE_SUCCESS.

# Run63 checked immutable frame snapshot — HOSTpass/runtime69 building

Sourceparent3b292fd pushed/cleanbeforeown63. Previousgoalturnprogress: exact68
nativeRFBcopyabort established plusactualrendererwaitcaptured. NOcurrentLab
process on freshNov16check. No69deviceactionsyet. Ownsource/tests/docsdirty.

SINGLEnewdefaultOFF --checked-frame-snapshot replaces ONLYgeneratedRFB
_pixels.copy with helpercheckedmalloc+memcpy+NSDataadopt/deallocator (no large
Foundationcopy). Independent immutablepixels; noalias/reuse, lastretainerfrees.
NULLpixelallocreturnsnil->existingfail/NO displaystop, Linuxpreserved. Tiny
Foundationobjectallocation notmadeinfallible; no exceptioncatch/assertionsuppress
orFAKEblankframe/Steam/FEX/vendor change. Other decoder resize/raw/patchallocs
unchanged. ThisdoesNOTpromiseRAMcapacity/CEFwait/gamefix.

HOSTFoundationASanUBSan/Werror maxdimensions+5refusals+retainer/immutability+
8threads512frames PASS snapshot-host-v2 (v1nullabilitycompileerrorretained/fixed).
515nativeownedbuffers released exactly, live0. DefaultgeneratedRFBsourcebyte
identical68. Health5config/postcap test +runtime69 nowobserver86113; harvest
beforeAppbuild. Private run63/runtime69-command-private.json +buildlog. No69
sign/install/UIproof. NEXT finishruntime/fullXcode/finalRFBupdate->helpercall,
exactAirprofiles/cert/signtext thenfreshsessioncheck/safeLabupgradeonly. Bounded
statscalls/failures/livebytes/release health distinguishes actualeffect. No
Macunlock/credentialsGuardtrust/securitysettings. Preservemain/allapps/data.
FulllicensedSteamPlay->Madeiragame/return/repeats ACTIVE; bridge125NOTgame.
NeverSTABLE_SUCCESS/unload/complete. Commit-s/pushonlyexperimentperAGENTShours.

--- Prior62 ---

# Run62 TERMINAL68 nativeRFBcopy allocation — no live Lab now

Source466c021 +actualcallerevidence6ee2eac pushed. Freshinventory NO Labprocess.
Exactnative23696 crash23:10:25.0041EST EXC_CRASH/SIGABRT NSAllocateMemoryPages->
NSData copy->LRRFBClientupdate+2464/appoffset10602620. Privatecrash68-native.ips
hashEVIDENCE. Health34wasstale; laterLibraryeventafterexitprovidesNOinput/UIproof.
Don'ttargetstale23696/restartjustforretry. No69candidateyet. SameisolatedLab68
installed/accountroot preserved. Checkdevicefreshbeforeanynewqualifiedtest.

Usefulprogress: actual namefree8main/4ABIframeprobe emitted12windows, allunique
inEXACTonAirCEF+glibc; renderer270cond_wait/CEFWaitManyinference. Maincycles
advanced, no deadlock/lostwakecauseproven. Source/default/gates/tests documented.
NEXT separate defaultOFF RFBfullframesnapshot allocation experiment toaddress
repeated63/64/67/68nativeabort. Usecheckedgenuineownedmemory/snapshot, preserve
pixelbytes/immutability/asyncMetal+RFBdrains/input; testerror/dimensions/lifetime/
coalescing; no catch-all/assertion suppression/fakeframes/Valve/FEXpatch.
Independentguestwaitdiagnostics unchanged. NeedactualLibrary/BPM/Play->licensed
Madeiragame/return/repeats; bridge125NOTgame. NeverSTABLE_SUCCESS/unload/complete.
CLIonlyneverMacunlock/credentialsGuardtrust/securitysettings. Allsafepermission
persists; preservemain/otherworktrees/workingapps/auth/games/saves. Commit-s/
pushonlyexpinhours. Rawprivate run62; nooverlappingobserversactive.

--- Earlier62 (historical) ---

# LIVE68 Run62: admission capture succeeded; Library request pending

HEAD466c021 pushed; newactual evidence docsdirty. Native23696/installDAB59580-
8BD2-4466-928E-50B7988614DE, kernel23696-1042878-945412000.log. Revalidate.
Private run62/observe68-private.py NEWtag. Normalupdater42/restart observed;
health34/153guests footprint2124208624/4970brokerslots/allerrors0. ONE fixed
Libraryevent justsent input68-library; don'trepeat/restartbeforefreshstate.

Actualname-free max8mainwaitsampler captures4frames for180/188/renderer270!
Privatekernel68-renderer945403B zeroFAULTinthatwindow,12dedupinstructionwindows
ALLunique inEXACTcurrentCEF+glibc. SHA/currentmodulepaths/EVIDENCE.run62.actual68.
Renderer270 untimed393 expected0/allbits ffff4390: libc82c4c/85648->CEF630fab4
(pthread_cond_wait@PLT)->6338580. Exactsource+disassembly infers WaitManyImpl,
notnearestcef_get_xdisplaysymbol. Cyclesadvancingaroundwait; NOpersistentdeadlock/
lostwake/rootcauseproof. Bound4framesdoesn'tgivehighercaller. NativeRFBcopy
abortseparateknownrisk. No68game/return/stability; bridge125NOTgame.

NEXT actualLibraryresult/samecurrentnativefaults andwaitercorrelation before
anotherpatch. Keep68live; no69prepared. FullgenuineSteam+licensedMadeiragame/
return/repeatsgoalACTIVE, neverSTABLE_SUCCESS/unload/complete. CLIonlyneverMac
unlock/passwordsGuardtrust/security; noFEX/Valve/vendor/main/otherapps changes.
Allsafepermission persists; scope/check hours beforecommit-s/pushonlyexperiment.

--- Prior62 ---

# LIVE68 Run62: updater actual; preserve new session

Actual68PID23696/installDAB59580-8BD2-4466-928E-50B7988614DE; receiptkernel-
23696-1042878-945412000.log. Revalidate. Private run62/observe68-private.py NEWtag,
air68-launch-private.json. SameLabupgrade/deepstrict/profilecert/signtextPASS;
physicalupdaterextracting. Firsthealthphase0 racedstartup; doNOTrestartfromthat.
No68caller/UI/game/returnproofyet. Oldinert22456 normallyended, noappdata/auth
change. NEXT observe normalupdater42/restart thenboundednativecallerrows +UI.
Keepcurrent68alive; no parallelobserver/reinstall. Name-free mainwaitscope8/
fixedABI/codehelper4 testedrealARM64withgenericname, no sync/watchdog change.
Symbolizergolden2uniquematches/loadbias0 andduplicateELF2ambiguouscandidatesPASS.
NoSTABLE_SUCCESS/unload/goalcomplete. Fulllicensedgame/returngoalACTIVE. Allsafe
permission persists; CLIonlyneverMacunlock/credentialsGuardtrust/securityedits.
NoFEX/Valve/vendor/main/otherworktree/workingapp changes. Commit-s/pushonlyexp.

--- Prior62 ---

# Run62 68 signed; deployment47348 running — harvest first

Build68deepstrict/exactAirprofilecert/textpreservation PASS, private
run62/sign68-evidence-private.json. Normalisolatedupgrade observer47348 now
freshchecksoldLab22456/URI thenendsONLYthat inertprocess and installs68/launch.
No68runtimeproofyet; harvestbeforeanyrepeat. NoMacunlock/password/Guard/trust/
security changes. Existingall-safeauthorization persists; data retained.

# Run62 LIVE signing68 — do not duplicate

Nov16 23:01EST resumed samewriter. Mount/origin/main/worktrees verified. Build68
runtime24units/fullXcodePASS/finalsampler->helpercall +MAIN_SCOPE_V2markerPASS;
broker memorysourceidentical67. ExistingAirprofiles/certmatched. Ownsigning
observer56587 preparingdisposablecopy signed68; harvestbeforedeployment.
Private run62/qualify-sign68-private.py/sign68-evidence-private.json expected.
No68installedyet. FreshcurrentAir22456 sameoldinstall2468CC7D phase0/noLinux,
receiptstillold kernel22456/904972. Noactivetest. Revalidatefreshbeforeactions.

run62/deploy68-private.py prepared exact22456 oldURI guard; ONLYrunaftersignpass.
observe68-private.py prepared NEWtags. No68runtimeproof. Code-symbolizergolden
2actualARM64matches/loadbias0 PASS. Allpendingown62source/docs retained. Full
scope/CLIonly/noFEXValvevendorsecuritymainauth edits. NeverSTABLE_SUCCESS/unload.

--- Prior62 ---

# Run62:67 ended by nativeRFB allocation abort;68 admission repair HOSTpass

Parent/source e7b39e7 PUSHED; ownRun62tinyobserver/tests/docsdirty. Native67old
22266 ACTUAL08:46EST SIGABRT NSAllocateMemoryPages->NSData copy->LRRFBClient
update+2464, exactOSreport/image5f4af0fa-87c9-36bb-93f0-a1d35faafd65. Notjetsam/
timeout/probeproof. Complete2,280,974B log zero callerrows evenmain266untimed393
present; controlledhostCrRendererMainname didnotqualifyactualthreadname. Two
sameguest271hungSIGTRAP reports, zero recordednativeENOMEM/MMAP_FAILURE.

Current12:11ESTactualscreenshotHOME, sameinstall2468CC7D-AA69-4C11-B21E-
16F80228C6DB newnative22456 receiptkernel-22456-904972-764429000.log phase0/
guest0/foot4.9MiB. NOactiveLinuxsession. Revalidatebeforeactions; don'ttarget
stale22266 orkillanunknownuser session. No68built/signed/launchedyet.

NewdefaultOFF observeradmissionremovesunverifiedtaskname, caps8MAINuntimed
waiters per sample. Existinghelper4ABIframes/GROWSDOWN/readablefileEXECwords/
trylock/statechecks unchanged; noarbitrarybuffers/strings, sync/timeout/mapping/
watchdog/policy/FEX/Valve/vendor/security change. HOSTactualARM64 ProbeMain
fixture name-independent-ELF-v1 PASS withnormalwake/exit0. NEXT build68same67
stackonlyadmissionchange, finalcode/profiles/signtext gates; freshinertLab
identitythen safeupgradeperall-safeauthorization. Boundedserialobservercollect
newcallers BEFOREwatchdog/nativeRFBexit; no overlappingexperiments. KeepRFB
allocationfailure separatefuturefeatureflag; no exception/assertion suppression.

TaskfulllicensedSteamPlay->Madeiragame/return/repeatedstability ACTIVE,
bridge125NOTgame. NeverSTABLE_SUCCESS/unload/complete. CLIonlyneverMacunlock/
credentialsGuardtrust/locksecurity edits. Main/otherworktrees/apps/auth/games/
saves intact. Rawartifactsprivate run61/run62. Commit-s/pushonlyexperimenthours.

--- Prior Run61 ---

# LIVE67 Run61: updater running; preserve actual session

Actual67installed/launched PID22266/install2468CC7D-AA69-4C11-B21E-16F80228C6DB,
nativekernel-22266-904309-209912000.log. Revalidatebeforeactions. Private
run61/air67-run-config-private.json and observe67-private.py <NEWtag>. Noobserver/
debuggercurrentlyactive. Warmhealth15 mono904449217/phase7 footprint894028648,
23guestentries,141broker slots/2chunks/errors0. Actualscreenshotupdaterextracting;
NOTLibrary/BPM/waiterdiagproof. Keepnormalupdater42/restart/session, norelaunch.

24nativeunits/fullXcode67/finalsampler->helpercall+markers/identical66broker
memorysource/exactAirprofilescert/deepstrict/signtext allPASS. Newexplicit
--blocked-wait-callers defaultOFF; HOST14PTE/busy/bounds/permission controls +
REALARM64ELF2validatedcallers/normalwake/exit0 anddefaultELFcontrolPASS. Own67
source/tests/docsdirty from7a8acc8pushed. Scopedcommit-s/pushonlyexperimentperhours.

NEXT afternormalupdater: boundednewnative log plusphysicalscreen. Inspect
LINUX_WAIT_CALLERS status/count and LINUX_WAIT_CALLER9codewords; onlyeligible
mainCrRendererMain untimedwait, existingGROWSDOWN ABIlinks/filebackedexecwords,
nonblockingmemorylock/statechecks. Noarbitrarygueststrings/buffers, nomapping/
sync/timeout/watchdog/origin/auth modifications. Byteverifyagainstexactcurrent
CEF andglibc; no nearest-export or manualhexguess. Prior66hungcaller351was
provenCrashHungProcess; LATERbadIPC213distinct, notcauseestablished. Needhigher
mainwaitcallertodiscriminate, notspeculativesemanticpatch. Goalrealinteractive
Library/BPM/Play->licensedMadeiragame/return/repeatsACTIVE, bridge125NOTgame.
NeverSTABLE_SUCCESS/unload/goalcomplete. Userall-safeauthorization persists,
CLIonly/neverMacunlock/credentialsGuardtrustlock/securitychanges. Preserveall
main/worktrees/otherapps/auth/games/saves. NoFEX/Valve/vendor changes.

--- Run61 qualification ---

# Run61 qualified67 deployment in progress; harvest3696 before more actions

FullXcode67/finalreal sampler->helper call/markers PASS. Broker/kernelmemory
sourcebyteidentical66. ExistingexactAirprofileappdevicecert/deepstrict andsigned
textpreservationPASS. Private run61/signed67/Madeira.app immutable/sign67evidence.
Fresh66receipt22068/health202/CLI2 andphysicalscreenstillblackStore verified,
no newusertest. Ownboundeddeployment3696 now normallyends ONLYfreshmatched66,
upgrade SAMEisolatedLabID andretainedlaunch perstandingall-safeauthorization.
No67devicecallerproofyet. Harvestlaunchreceipt beforeanyretry; norepeated
permission/unlock/credentials/trust/Guard/security actions. Keepallappdata/main.

# Run61 waiter-callers qualification — full67 building, preserve66

HEAD/pushed7a8acc8; newownRun61source dirty. CurrentAir66PID22068/install
D03CEFF5-7E05-4963-B71A-60595C51EEF5 preserved, revalidatebeforeactions. Native
66capped log confirms selectedmapreduction butnotUI. ReadRun60actual failure:
CrashHungProcess exactcallee/rodata351; laterorigin213 distinct. No solecause.

New defaultOFF --blocked-wait-callers, onlyblocked UNTImED mainCrRendererMain
futex0/9. Holds existinggeneral_lock mm lifetime; nonblocking tryreadmem, atmost4
frames, existing readable writable anonGROWSDOWN nonexecmainstack ABIlinksONLY;
file-backed readableEXEC code9words each, BL/BLR returncheck. No arbitrary
buffers/strings, nofaultmaterialization/PTEgeneration/accounting/sync/timeout/
watchdog change. RevalidatePC/cycles/FP/blocking; stale discards status5. Status
busy/unavailable/badchain explicit; BESTEFFORT, no rootcauseclaimfromabsence.
NoFEX/Valve/vendor/security/auth/main modifications.

HOST14actualPTE helperASanUBSan/Werror PASS wait-callers-host-v2; firstv1missing
realnative-loglinker symbol retained, correctedharness only. REALARM64ELF test
wait-callers-ELF-v2 exports2validatedcallerframes thennormalwake/exit0; firstv1
signedcyclecompareWerror fixedexplicitcast, notruntimefailure. DefaultELF-v2
passes, firstdefaultshell Bash3.2emptyarraynounset negative retained/corrected.
Allsource/test raw artifacts private run61. Runtime67 24nativeunits PASS;
fullApp67 BUILD runningobserver63151, app67-build-private.log, don'tduplicate.
No67sign/install/devicecallerproofyet. No reauthentication/Guard/JIT needed.

NEXT harvestfull67; finalactual sampler->helper call+marker; exactexistingAir
profile/device/cert/deepstrict/signtext gates. ONLYthen freshidentity/screensame
boundedowned66test andsafeisolatedLabupgrade67 underpersistentall-safepermission.
No repeatedapproval/unlockrequests. Observebeforewatchdog actualcallerrows,
byteverify againstexactonAirCEF SHA891d85f... andactualglibc, don'tnearest-export
label. Onehypothesisdiagnostic only, notfutexsemanticfix. FulllicensedPlay->
Madeiragame/return/repeats ACTIVE, bridge125NOTgame. NeverSTABLE_SUCCESS/unload.

--- Run60 ---

# LIVE66 Run60 failure checkpoint; next bounded waiter-callers discriminator

Source d12799d PUSHED; main2ac39 untouched. Actual66PID22068/installD03CEFF5-
7E05-4963-B71A-60595C51EEF5 preserved, revalidate. Newbroker actuallyworks for
selectedCoW mappingcounts but NOTUI: savedauthdesktopchrome; LibraryACK1 and
BPMACK2 stillblackcontent, lateremptyStoredata-page. Health75 guest147/
foot2000378136,5031slots/40chunks/80MiBreserved; brokerallerrors0. Capped4,194,282B
native66checkpoint hasZEROrecordedENOMEM/MMAP_FAILURE/probe, TWO same273SIGTRAP
reports only; absencelimitedtowindow, no capacity/stabilityclaim.

ExactonAirCEF SHA891d85f97231fcafa5763b7140039c5d3cbbb99f2a42ede08de5991abcbc3cdb,
unique36B→PCe83d1504/file6271504/ELFVA6281504/biasE2150000. Programmatically
correctsavedcallerELFVA99a6800/BL99a67fc→fatalhelper; rodata+EXACTfetchedChromium
126source proves child_thread_impl.cc351 CrashHungProcess/Crashingbecausehung.
Earliermanualhexcaller-rangeoff10000 correctedprivate; no falsefunc/canaryclaim.
Main268 priorfutex393 expected0/allbits/untimed ffff38d0 libcPCe134f22c/LR
e13428b8 cycles1559325936 unchanged, underlyingcauseUNKNOWN. LATERfreshprocess372
13:09:53 badIPC213==INVALID_INITIATOR_ORIGIN perexact126source; don'tattribute
thislaterrefusalas firsttrapcause. No policy/watchdog/Valve/assertion suppression.

NEXT Run61 defaultOFF nonblocking bounded existingmainstack ABI/code-only
waitcallers metadata toidentifyhigherwaitercaller; HOSTtests first. No new67
source/buildyet. DoNOT restart66 forguessing; usequalifiedconcretesuccessor under
all-safeauthorization. CLIonly/neverMacunlock/credentials/Guard/trust/security/
lockchanges. No FEX/vendor/Valve/main/otherworktree/appdata edits. Fulllicensed
SteamPlay->Madeiragame/return/repeats ACTIVE; bridge125NOTgame. NeverSTABLE_SUCCESS/
unload/goalcomplete. Private run60 allrawdiagnostics/source/artifacts outsideGit.

--- Earlier Run60 ---

# LIVE66 Run60: preserve new Air session, broker ACTUALLY active

Actual66 installed/launched, PID22068/installD03CEFF5-7E05-4963-B71A-60595C51EEF5;
receiptkernel-22068-902262-337296000.log. Revalidatebeforeactions. Private
run60/observe66-private.py <NEWtag>. No activeobserver/debugger now. ONEactual
startuphealthseq2 mono902272344 footprint461228520: brokeralloc290/release149,
live141slots/2chunks/4MiBreserved/2183168logical, mapattempts2/failures0/all
ownership/unmap/overlap/cap/adviceerrors0. Actualscreenshot Steamupdaterextracting,
NOTLibrary/BPMsuccess. Keepnormalupdaterautorestart/session; norelaunch/reinstall.
Signedmain865b8909d60790eacf6ab3c345fc12fc34fb881f07fb10402fb372a916f538a3,
text101aff116539910a564109cae993f8d742a504c0f498c8c0712a3b44bcfdeae4.

65wasfreshidentityverified thennormalended underall-safeauthorization; sameLab
upgradepreservedprivateprefix/auth/games/saves. No workingapp/main/phone changes.
NEXT boundedhealth/screenshot andnativeoriginalfailure/counterreadout. Never
inferUIfromupdater/process/counters. Goallicensedgame/return/repeats ACTIVE,
bridge125NOTgame. DoNOTSTABLE_SUCCESS/unload/complete. CLIonlyneverMacunlock/
credentialsGuardtrust/security/lockbypass. NoFEX/Valve/vendor edits.

--- Qualification chronology ---

# Run60 deployment66 in progress — harvest before touching device again

Actual finalMachO CoW->ownedallocate/data_release->ownedrelease/sys_madvise->
existingdiscard calls verified, hostinjection absent/defaultsource identical65.
Deepstrict/exactAirappdevicecertprofile and signed__TEXT preservation PASS.
Private run60/sign66-evidence-private.json, signed66/Madeira.app immutable.
Own deployment observer82652 nowends ONLY freshlyidentitymatched65/21759,
installsameisolatedLabID preserving data, launchesretainedfrontend. HARVEST
before repeating launch/install. No66runtime/UIproofyet. No overlappingtests.
All safeauthorization persists; no workingapp/main/FEX/Valve/securitychanges.

# Run60: owned CoW broker qualification; preserve65 until candidate ready

Active writer unchanged. HEAD14432ce pushed; own Run60 source/tests now dirty.
Volume/remote/worktrees verified. Actual65 receipt still21759/installF0183973-
5915-427B-A6E7-8646A52B46F1; latest health295 mono901701034 footprint2106677648,
guest139 CLI6/filepolicy0 diagnostic125/gamefalse. Actual07:52EST physicalscreen
WHITE nativeLab content, keyboard/restart-disabled/spinner visible; this is NOT
current interactive Home proof. EarlierHome/screensaver-wake remainshistorical.
Don't infer native death from blankguest; no stop/install/auth/security changeyet.

New DEFAULT-OFF --cow-backing-broker routes ONLY compatible private anonymous
CoW groups(originalspan1) into genuinelyowned dynamic128nativepagechunks.
Exactlast-dataref releases slots; finalchunkrelease realmunmap; partialfreedslot
publicMADV_FREE advisory only, zero before reuse. Nativealignment isolates slot
protection. No fixedaddress/softgrant/coarsercopies/file/shared/FEX/Valve/vendor
change/capraise/assertionsuppression.128slots*4096chunks bounded; sparseobjects
can retain MUCH more virtualcapacity. No claimphysicalRAMreclaimed/capacityfix.

Hoststandalone13 ASanUBSan/Werrorcontrols PASS run60/broker-host-v2 (v1tenwithout
advice retained). Real memory-unit12 boundary/rollback/concurrency/dense/sparse
controls PASS cow-broker-integration-v2: dense64logicalbackings->1native2MiBmap,
sparse32->1native2MiBvsoriginal512KiBrounded; unchangedguestbytes/refcounts.
Composedcurrentlazy/checkedfork/discard/broker72checks PASS composed-broker-v1
includingrealARM64ELF/SVC. Healthgate0/1/postcapstats4configurationsPASS.
Runtime66 23iOSunitscompiled. Fullapp66 nowXcodePASS withcorrectCLI/toolchain; finalcalls/defaultsourcePASS; signinginprogress, private
run60/app66-command-private.json/app66-build-private.log; harvestbeforeanysign.
No66install/UI/Steam/bridge/game/returnproofyet. Native65 staysunchanged.

NEXT qualifyfinalMachO calls+defaultgeneratedsource unchanged, exactAirprofiles/
cert/text/deepstrict, then freshidentity andnormal isolatedLabupgrade perexisting
all-safeauthorization. One hypothesis only: nativeCoWmappingcount reduction,
measure actualbroker stats+originalENOMEM/UI/input. DoNOTmixinputdurationfix.
Preserveauth/games/saves/allworkingapps/main. CLIonly/neverMacunlock/credentials/
Guard/trust/lockbypass. Fulllicensedgame/return/repeatedstability goalACTIVE,
bridge125NOTgame; neverSTABLE_SUCCESS/unload/goalcomplete frombuild/UIalone.

--- Prior Run59 ---

# LIVE65 Run59 checkpoint: preserve actual session, partial effect not stable

Actual65PID21759/installF0183973-5915-427B-A6E7-8646A52B46F1, private run59/
air65-run-config-private.json, nativekernel-21759-898761-18690000.log. Revalidate
beforeactions. No observer/debuggeractive. Genuine savedauthdesktopLibrary and
BPMHOME/menu/DownLibraryhighlight worked. EnterACK5 didn'testablishLibrary;
coverartLittleNightmares->Ori/avatarAway =realSteam screensaver, NOTgame/hang
proof. ONEpointerclick allowedLibraryactiononblankAway ACK6 wokeHome menu.
Current65functionalpartial; don'trestartuntil concretequalifiedsuccessor.

Actualdiscard3749calls/461864960guestbytes; NOTRAMreclaimed. Complete capped
4,194,242B log includesONE native4.55MiB sharedfileENOMEM12->-12 tid270/group267.
Boundedprobe16KiBsharedRWsuccess/released,fullsharedRO/privateRW/anonRW allENOMEM12,
allreleased/originalpreserved. Adjacentfoot2239289864/avail766977528/regions56857
NOTatomic/exactcap. ZeroGUEST_FAULT in cappedwindow; no nativeRFBabortobserved
inthiswindow, notuniversalabsence. Health99 guest140/CLI6/filepolicy0/gamefalse.
BPM Library/game/bridge/return/repeatedstability unproven. NeverSTABLE_SUCCESS.

Sourceparent4735700 pushed, own59flag/72checks/docs dirty; qualifiedfull65/
finalcalls/Airprofiles/deepstrict/signedtextPASS, signedmainSHA
7eec54c15831d81fd8ee74b25d87a0465111cef93d16c40f1d5698b6e1752ba1.
Review/commit-s/pushonlyexperimentperhours; preserveallmain/worktrees/apps/data.
Latestall-safeauthorization persists, no oldpendingpermissionquestions. CLIonly/
neverMacunlock/credentialsGuardtrustlockbypass. NoFEX/Valve/vendor/securityedit.

NEXT ONEhypothesis: bounded genuinelyowned DYNAMIC smallprivatebacking broker
can reduce native mmapcount WITHOUTcoarserCoWmaterialization. Inventory actual
pt_map_nothing/CoW/data_release andPrivateDiscardrollback contracts FIRST, then
isolated dense/sparse/ownership/refcount/concurrency/failure/cleanup/coherence
tests, defaultOFF. No nativefixedaddresses/softgrants/sharedfile/caps/mprotect/
assertionsuppression. No66sourceorbuildyet. InputheldEnter/Screensaver remains
unproven; don'tmixnewinputpatchwithmemoryexperiment. DeviceHubtoolunavailable,
no pymobiledevice3; no other tool/password/privateRFBsecret extraction attempted.
FulllicensedSteamPlay->existingMadeiragame/return/repeats stillobjective,
bridge125NOTgame. Keepcurrent65 whileindependentwork; newcandidateonlyaftermilestone
gates. NoSTABLE_SUCCESS/unload/goalcomplete.

--- Run59 earlier chronology ---

# LIVE65 Run59:actual Library visible; oneBPM event justsent, preserve session

Actual65PID21759/installF0183973-5915-427B-A6E7-8646A52B46F1, NativeDiagnostics/
kernel-21759-898761-18690000.log. REVALIDATEbeforeactions. Private run59/air65-run-
config-private.json andobserve65-private.py. No activeobserver/debugger now.
Genuineupdater/normalretainedautorestart/savedauthdesktop/Library visible07:09EST,
LibraryACK1. OneBPM fixedevent sent input65-big-picture; resultPENDING, don't
repeat/restart. ActualSteamdiscard1717calls/38649856guestbytes observed, NOT
physicalRAMreclaimed. Health40 footprint2168199592/guest146/filepolicy0/gamefalse.
No stableBPM/game/return success. Neverclaimfromprocess/splash/counteronly.

HOSTv5 now72checks inclrealSVC233 reachesreplacement1/65536; full65Xcode23units/
finalcall/marker/counters/nohostinjection/span2absence/deepstrict/exactAirprofile
cert/textpreservationPASS. Signedmain7eec54c15831d81fd8ee74b25d87a0465111cef93d16c40f1d5698b6e1752ba1.
Verifieroffset65mistakecorrected64 onSAME signedapp READONLY, norebuild/resign.
Parent4735700 pushed/main2ac39unchanged, own59flag/tests/docsdirty. Latestuser
heartbeatcontinues currentwriter; no parallelresearcher. Allsafeauthorization
persists; workingapps/main/worktrees/accounts/games/saves untouched. CLIonly/
neverMacunlock/credentialsGuardtrustlockbypass. No66prepared.

NEXT observeBPMactualscreen andboundedfreshfailure/resources/replacementcounts,
thenifusable sameone-step Library/game-details flow. Don'tequate replacements
withphysicalreclamation or singlevisibilitywithstability. Ifsamecapacityfailure
recurs, classifyoriginalguest vsnativeRFBallocation independently, preserve
negative; no blindretry/cap/assertion/mprotect/FEX/Valve patch. Fulllicensed
SteamPlay->Madeiragame/return/repeats stillgoal, bridge125NOTgame. NoSTABLE_SUCCESS/
unload/goalcomplete. Commit-s/pushonlyexperimentperhours.

--- Run59 earlier chronology ---

# LIVE Run59:65 qualified; safe isolated install/launch observer7470

Sameactive writer, no new researcher. Userheartbeat preservesall-safeauthorization.
ReverifiedvolumeUUID/origin/branch/main2ac39/experiment4735700/worktrees. Own59
flag/tests/docs dirty, keep. HOSTv5 72PASS including REALARM64 SVC233 reaches
exclusive replacement1call/65536guestbytes, notphysicalreclaimedmemory. Full65
Xcode23units/finalsys_madvise->discardcall/marker/counters/nohostinjection/span2
pass. Deepstrict/exactAirprofilecert/signedtext PASS on SAME signed65; verifier
initialnsects65 errorcorrected64 READONLY, noresign/rebuild. SignedmainSHA
7eec54c15831d81fd8ee74b25d87a0465111cef93d16c40f1d5698b6e1752ba1.

Fresh Air64 original21278 alreadydead; inertpostexit21469 exactoldLabURI/
receiptstill21278/no newLinux main, normallyended perapproval. ONLYLabupgrade
65currentlyexec7470, harvestreceiptbeforeclaim/repeating. No workingapps/data
changed. Private run59/sign65-evidence-private.json andruntime65/app65commands.
No newauthentication/credentials/Guard/trust/JIT/lock action.

NEXT harvestactual65PID/installUUID andnewreceipt, observegenuineupdaternormal
autorestart->savedauthLibrary/BPM/input. ActualLINUX_PRIVATE_DISCARD counters
mustadvance; noteeligibility/busy/fallback mayyield0. Replaced/requestbytesNOT
RAMreclaimed. Captureboundednativefailures/resources+physicalscreen, don't
claimstabilityfromhost/build/process/splash. NativeRFBcopyfailure remains
unchanged forsinglehypothesis comparison. No66prepared. CLIonly/neverMacunlock.
FulllicensedSteamPlay->Madeiragame/return/repeats goalACTIVE, bridge125NOTgame.
NoSTABLE_SUCCESS/unload/complete. Commit-s/pushonlyexperimentperAGENTShours.

--- Run59 earlier chronology ---

# LIVE Run59: discard65 fullApp building; not installed yet

Parent4735700 pushed/readback, main2ac39 unchanged. New defaultOFF hybrid
--exclusive-private-discard uses unchanged historicalPrivateDiscard.inc only
on copiedmmap + observers, requirescheckedfork/defaultspan1CoW. HOSTcurrent
composition normal22/failsecond22 + realARM64ELF20 + adjacent4 =68PASS v4.
Earlier3 harness failurenegatives preserved/private; readMD/EVIDENCE, notruntime
faults. Defaultgeneratedsource equalsactual64.23nativeunits65compilePASS.
FullXcode65 runningexec26560, doNOTspawnanother. Private run59/hybrid65/source,
app65-command-private.json/runtime65-command-private.json. No65signed/installed
yet. No sourcePrivateDiscard/FEX/Valve/vendor/security/lock changes.

64alreadyactualnativeSIGABRT sameRFBallocationslot,21278gone. No new65session
started; revalidatefreshdevice/currentLabidentitybeforeupgrade, keepdata.
Userall-safeauthorization persists/no repeatedpermissionquestions. CLIonly/
neverMacunlock/credentialsGuardtrustlockbypass. ExistingAirprofilesexpireNov20,
useexactmatch/cert checks and disposablecopy. Final65 sys_madvise->discard
callsite/marker/counts linked andnohostinjection/spantwo, signedtextsame required.

NEXT finishbuild/sign65 thenactualAir single experiment: eligible replacement
countermustactuallyadvance; replacement/requestbytes NOTphysicalreclaimedRAM.
Compare genuineLibrary/BPM/input andsame nativeallocation failures. Prototype
canfallbackunsupported/busy/allocationfailure; no effect is validnegative.
DoNOTclaimfix fromhost/build/processpresence. NativeRFBgracefulfailure separate
futurehypothesis; don'tmixwith65. FulllicensedSteamPlay->Madeiragame/return/
repeats stillgoal, bridge125NOTgame. NoSTABLE_SUCCESS/unload/goalcomplete.

--- Run58 and earlier ---

# CURRENT Run58 FINAL:64 default-span ALSO native RFB allocation SIGABRT

ReadRun58 MD/EVIDENCE FIRST.64originalspan1 actuallyrendered savedauthdesktop,
LibraryACK1 but UIHome/noLibrarycompletion/BPM/game. ExactPID21278 absent, OSreport
03:38:38EST EXC_CRASH/SIGABRT NSAllocateMemoryPages/NSData-copy/RFBupdate appoffset
a1c240, same63nativefailure. Original2MiB sharedfilemmap nativeENOMEM12 at
guest203/group178;16hostfailure rows. Actualprobe16KiBsharedRW succeeds/released;
2MiBsharedRO/privateRW/anonymousRW allENOMEM12,allreleased/originalpreserved.
Adjacentfoot2134366680/available871900712/regions49095 NOTatomic/exactcap. No
GUEST_FAULT in complete64log, doesn'texclude63coarsecontributiontopointerfault.
No liveuserLinuxsession found after64exit; revalidatebeforefutureupgrade.

Sourcecheckpointcd63898 pushed; current58 ownadjacentELFfixture/docsdirty. Both
span1/2real ARM64fork/CLONE_VM adjacentread4checksPASS; nanosleepwaitnotpure
no-syscallTLBproof. Main/vendor/FEX/Valve/security/lock/accountdata untouched.
No activeobserver/debugger; no65built. Rawrun58 private, evidencehashes public.
FullgoalstillACTIVE, bridge125NOTgame. Latestall-safeauthorizationpersists.

NEXT onehypothesis: audit/revalidate historical exclusivewholebacking private
DONTNEED replacement fromRun18 on CURRENTlazy/fork/CoW stack, source
PrivateDiscard.inc/build-madvise-stats.py. NeverAir-qualified, currenthybrid
hardcodesPRIVATE_DISCARD=0. Ifhostbarrier/rollback/ARMELF controls pass, addnew
explicitdefaultOFF hybridflag andcompare actual65 eligibilitycounts, resource
behavior andrealUI, notrequests=reclaimedRAM. No speculativecap/mprotect/soft
backing/assertion suppression. NativeRFBgracefulfailure canbe separate later
fix; don'tmix hypotheses. StaticMachOsegments don'texplain475GBcoldvirtual,
sourceguestsetrlimit doesn'tforwardhostAS/DATA. Nativeallocationcauseunknown.

Preserveallapps/main/worktrees/auth/games/saves. CLIonly/neverMacunlockrequests/
credentialsGuardtrustlockbypass. Commit-s/pushonlyexperimentperhours. NoSTABLE
SUCCESS/unload/complete withoutfullrepeatedAirSteamUI/licensedgame/return.

--- Run58 live chronology and earlier ---

# LIVE Run58: baseline64 actualAir updater; do not interrupt

Parentcd63898 checkpoint pushed/readback. Current original-span64 sameotherflags
fullXcode/23units/finalcall/span2absence/sign/Airprofilecert pass, sameLab upgraded
preservingallauth/games/save. ActualPID21278/installEF1FE8B8-2071-4EA1-9316-AE5B08538BC5;
REVALIDATE beforeactions. Nativekernel-21278-886169-545242000.log. Interpreter.
Currentgenuineupdater underway, no Library/BPM64 proofyet. Noobserver/debuggerlive.
Private run58/air64-run-config-private.json andobserve64-private.py. Initial
phase7/20sec/22guests/553MB observed; notCEFsuccess. Continue bounded observations.

New own ARM64 adjacent-reader/CoW/fork test4checks PASS eachspan1/2host combined
stacks. Waits cancrosssyscalls; notexclusion ofCEFpointercorruption. Noenginepatch.
Runtime64 is controlonly, no newfix. ReadRun57originalCEFfault/nativeRFBabort
below. Native63originalPID20893 wasOSaborted, notjetsam. New21122 recognized
sameURI/no newreceiptLinux; stoppednormally forapprovedsafe64upgrade. Main/
otherapps/data untouched. Latestbroad safe-operationauthorization persists,
NEVERrepeatoldpermissionquestions. CLIonly/neverMacunlock/credentialsGuardtrust.

NEXT finishsameflowLibrary/BPM64, getfreshoriginalfailure/nativecapacityprobe/
OSreport ifany; distinguishchanged/intermittent failures, don'tclaimssolecause.
Source58tests/docs currentlydirty; no65prepared. Historic exclusivewholebacking
MADV_DONTNEED prototype fromRun18HOSTtested butNEVERdevicequalified; current
hybridbuildexplicitlyPRIVATE_DISCARD=0. Ifcapacityrecurs, revisitactualeligible
reclamation onlyaftercurrentcontrol; don'tblindlyturnon oldcandidate orassume
requestedbytes=reclaimedmemory. FulllicensedMadeiragame/return stillgoal,
bridge125NOTgame. NoSTABLE_SUCCESS/unload/complete.

--- Run57 and earlier ---

# CURRENT Run57 FINAL:63 Library worked; BPM failed, native RFB allocation abort

Read Run57 MD/EVIDENCE FIRST. User explicitly allows safe isolated upgrades;
old approval questions superseded. Sourceparent7ca5490; current scoped span2
feature/test/docs changes await checkpoint. Default1; vendor/FEX/Valve untouched.
Host24 actualmemory ASanUBSan controls: dense64->32backings/both1MiB; sparse32
both/512KiB->1MiB. Full63/23units/finalcalls/doubleinstruction/deepstrict/exactAir
profiles/signedtext pass; real spanmarker configured8/copied2 observed.

Actual63 sameLab installed, auth preserved, genuine saved-auth Library/inputACK1
works. BPMACK2 black/header only. First guest269 SIGSEGV PCe7fb2cf0 /unmapped
0x110005f007d /LDRw8[x8+18], actualCEFdiskSHA891d85f97231fcafa5763b7140039c5d3cbbb99f2a42ede08de5991abcbc3cdb
unique36B ->file5e52cf0/ELFVA5e62cf0/bias e2150000. Reporter+3000offset wrong.
Later guest415 BRK PCe733b270/ELFVA51eb270, recent prot0 anonymous8.06MiB
mmap-12; NOT Run56sharedfile failure, no sharedprobe rows. No solecauseclaim.
Native63PID20893 actuallySIGABRT03:20:20EST: OSreport NSAllocateMemoryPages/
NSData copy -> LRRFBClient update+2464, appoffseta1c240. Notjetsam/timeout.
Actual63signed mainSHA3d43820c0f37e9bd2bf39553eb4dd3e90fc31f41164323a5b0f7a58eb5f39084,
install25570A03-E897-4B09-8225-286DC854001A.20893gone; NEW21122 sameURI listed,
receipt still20893/no newLinux evidence. Revalidate beforeactions, preserveuser
session. No observer/debugger active. Private run57 evidence only hashespublic.

NEXT samehypothesis baseline span1 actualAir control, allotherflags same. Combined ARM64ELF20 hostregression nowPASS on lazy+checkedfork+span2 stack. No64built
yet. NativeRFBallocation and firstCEFpointerfault are separate layers; no blind
fallback/assertion suppression. Bridge125stillNOTgame, fulllicensedgame/return
objective active. NeverSTABLE_SUCCESS/unload/complete without repeated actualgoal.
CLIonly/neverMacunlock/credentialsGuardtrustlocksecurity changes. Main/other
worktrees/accounts/games/saves untouched. Commit-s/pushonlyexperiment perhours.

--- Historical Run56 and earlier ---

# CURRENT Run56 FINAL:62 UI eventuallywhite; real native capacity probe observed

Latest explicit safe-operationapproval persists; oldquestions below superseded.
Current62 PID20594/install590D1B80-44C2-433B-BE8D-0A734A25A5CC, revalidate before
actions. Actual Library/BPMhome/Back-menu/Down-Library worked, butActivate restored
DDLCdetail background only ->white02:40EST, no Install/Play. Nativehealth132/
guest141/CLIseq5/filepolicy0/gamefalse. Not game execution or stableUI. Preserve
allauth/game/save data; experimentalLab safe upgrades approved, no newquestions.

Capped/stopped native4MiB log copiedONCE successfully (livecopy7000 was transient
observer failure, notdeath). ACTUAL probe sixrows: tid163/group140 original
sharedRW/offset0/4767744B ENOMEM12->-12;16KiB samefile sharedRW succeeds/released;
full4767744 sharedRO/privateRW/anonymousRW allENOMEM12. attempted4/allreleased1,
originalresultpreserved. Finalmmap importlibSystem, notdefinedWine/FEX override.
Closest periodicfootprint2236537304/available769730088/regions57043/virtual
483073245184 non-atomic. Supports size-sensitive native processwide allocation/
placement/capacity issue, NOTsolefilepermissions or provenregioncap/RAMcause.
Differentrequest/group from61tid379/9.08MiB. Firstappvirtual475568488448 already
at5MBfootprint, doNOTattribute allVA toLinux or allVA tophysicalmemory.

Source62: FileMmapProbe.inc/generator/buildflag defaultOFF,HOST30exactfunction
ASanUBSanWerror + nativeunlinkedownfile, ownershipregression/defaultsourceequal,
23native/fullXcode/FINALcallsite/textsame/deepstrict/Airprofiles PASS. Actual
probe nowexecuted, butNOTfix. No activeobserver/debugger left. Private run56
artifacts/sourcehashes inEVIDENCE; repo ownchanges currentlyuncommitted. Publish
reviewedcheckpoint onlyexperiment perAGENTShours; main/otherworktrees untouched.

NEXT onehypothesis: coarser compatible anonymousCoW groups could reduce native
mapping pressure. FIRST extend real-kernel dense/sparse/backing/rounding/bytes/
flag-boundary/accounting/rollback controls; quantifyextra materialization. Then
defaultOFF boundedparameter ifsupported, no file/shared/protection crossing,
no cap/assertion/mprotect/FEX/Valve/security/lock changes, actualAir compare.
Stillcontinue genuineSteamPlay/customtool->licensednativeMadeira game/fullreturn/
repeats. Bridge125NOTgame. NoSTABLE_SUCCESS/unload/goalcomplete. CLIonly/neverMac
unlock; no credentials/Guard/trust automation or accountdata transfer. Permission
is NOTthe blocker. Do not repeatstatusonlyresearch; implement thenactualtest.

--- Detailed prior Run56 chronology, superseded by final state above ---

# LIVE Run56: genuine62 BPM/input works; safe-operation approval persists

READ Run56 MD/EVIDENCE FIRST. Sourceparentb512255, own62patches/docs currently
uncommitted; don't overwrite. All safe recovery/normal isolated upgrades are
EXPLICITLYapproved by latestuser; NEVER repeat old61/Ctrl-C approval questions.
Still no lock bypass/Macunlockrequests, credentials/Guard/trust automation,
FEX/Valve/security/Codexstate edits, workingapp/account/game/save changes.

Old debugger gone, same60 health4972->4996 recovered, no newinterrupt. ExactAir
UUID/migration/origin/branch/remote/worktrees verified. Fresh Air4/iPad13,1 OS27.2/
24B119 RAM4056186880. Only com.kuschqin.ideck.freshtest remains Labidentity.
61installed/actualLibrary input succeeded, BPMwhitefailed with same-thread379/
group270 host sharedfilemmap9,523,200B ENOMEM12 -> Linux-12 -> libcefBRK/group5.
Native appnotdead. Adjacent available675898896B/region56728 notatomic/solecause.
OldNov12/14CEF CHECK/badIPC213 NOTcurrenterror. Main/otherworktrees preserved.

Critical61Cefbytecorrection: actualELF SHA891d85f97231fcafa5763b7140039c5d3cbbb99f2a42ede08de5991abcbc3cdb.
RuntimeFAULT_MAP literalfileoffset0x6351060 WRONG fordiskBRK; unique36B pattern
at0x634e050 givesBRKfile0x634e060, ELFVA0x635e060, candidatebias0xe2150000.
Reportedoffset+0x3000 samplebias likelynativealignment; reporterNOTfixed/proven.
No nearestexportedfunctionlabels, disassembly/binaryprivate only.

NEW FileMmapProbe.inc + explicit --file-mmap-failure-probe composedwith existing
file-map-cleanup into COPIEDreal.c. Defaultsourcebyte-identical61. Firstmatching
sharedRW/offset0/ENOMEM regularfile1nativepage..16MiB only:4different controlmaps
sharedpageRW/sharedfullRO/privatefullRW/anonymousfullRW, immediateunmap/no
contents/PTEwrites/originalretry/fallback. Stopreleasefailure, preserveoriginal
result/errno. Oncepernative lifetime. HOST30 ASanUBSanWerror exactfunction +
realunlinkedownfile, existingownershipregression PASS.23adapters/fullXcode62/
FINALrealfs->probeCALL/deepstrict/exactAirprofiles/cert/textpreservation PASS.
Signed62mainSHAe354566eae9a0628589818c134266f4fa1e1060bc24e5632ff951f5c33a01db8.
Private immutable run56/signed62/Madeira.app installed SAMEID/no uninstall/data
transfer, old61normallyterminated afterfreshidentity.62 ACTUALPID20594,
install590D1B80-44C2-433B-BE8D-0A734A25A5CC; revalidate beforeactions. Config
run56/air62-run-config-private.json has exactdevice/URI/currentreceipt. Native
kernel-20594-881693-786674000.log. Interpreter; no newJIT/debuggerrequired.

Actual62 genuine desktopLibrary thenBPMHOME rendered. Screensprivate contain
account/friends, no publication. Back opensMainMenu, Down visuallyLibraryselected,
lastoneActivate sent to thatverifiedLibrary item: RESULT STILLTOOBSERVE.
NativeCLIactions totalexpected5 (Library,BPM,Back,Down,Activate); oldackonlyseq2
was earlier. Do NOT doubleActivate blindly. Current62 remains live; preserve.
No SteamPlay/download/game/return proof. Defaultsteamappsno appmanifests; shared
steamappslistCoreDeviceActionError3 (possiblynotcreatedyet), not installedgame
proof or root corruption. Need legitimate smallowned/free Windowsgame+custom
compattool choice/sharedinstall and actualbridge->nativeDock auth/JIT/launch.

Firstcomplete62 boundedobserver samplehealth71 no probe rows. Nextlive native
copy CoreDevice7000 (healthcopy succeeded) -> observer33852 TERMINAL, stopped.
Notappcrash/no rootfix claim. Other4early file_backend220MB failures have
native_errno0, outside sharedhostENOMEM gate. Never conflate. Can collectsmall
health/window/screenshot independently; ifneedlog use strictlyserial bounded
identityverified stop/copy/finallySIGCONT with verifiedresume, NEVER newLLDBSB
poll duringattach. Do not stopfunctional62 merelytoforce failure; keepactualgoal.

NEXT capture actualLibrary result frompendingActivate, navigate safelybyone
verifiedstep atatime. RequestArrow/EnteronlygenuineUI, no credentials orhidden
execcontract. Ifmappingfailure recurs, completeprobe/originalcontext then
minimalbackedmemoryfix. StableinteractiveLibrary/BPM->realSteamPlay/licensed
Madeiragame/fullteardown/reliableSteamreturn/repeats remain objective. Bridge125
NOTgame. NoSTABLE_SUCCESS/unload/goalcomplete/newresearcher/cadencechanges.
Commit-s/pushonlyexperimentAGENTShours afterreview; currentSundayallows.

--- Historical Run55; pending approvals below are SUPERSEDED ---

# URGENT Run55 V4: debugger cleanup pending, NOT currently verified detached

Read latest Run55 MD/EVIDENCE before ANY action. V3 snapshot/resume below was
successful, but later V4 LLDB session38994 is still open/hung on async attach/SB
state query. Optional callercollector NEVERexecuted. Same Air60/PID19384/
installationB55DD703-F281-4556-9A49-09550951953B was freshly verified beforeV4.
Two duringV4 health copies bothsequence3638/mono864840006; apppossiblypaused.
No actualstop event/ready state/capture/detach confirmation. Official process
`detach --keep-stopped false` QUEUED, notexecuted/confirmed. No debuggerkill.

Ctrl-C ONCE requested but AUTO-REVIEW REJECTED: may leave pendingattach/native
pause unverified. No workaround/retry. Userquestion PENDING specifically allows
oneCtrl-C hungquery interruption then officialdetach/resume + healthverification.
Wait actualreply; no inferencefromelapsedtime/genericcontinue. No newdebugger/
experiment/input/install/restart/quit/kill/security/lockchange. Keep currentTTY.
Resolve cleanup FIRST; update evidence before saying sessionrecovered. NoMacunlock.

Restricted-executor CoreDevice initialization timeout was CONTEXT-only: outside
restrictedcontext exactAir19384 verified promptly. Do not call Air unavailable
or infer Linuxcrash fromthaterror. Python SB statepoll during attach canblock;
futureobservers should waitactualnative stopEVENT beforecollectorimport. Source
warns, optionalcaller path remainshost-only. Preserve61permissionpending/auth/
game/save/main/otherworktrees. No STABLE_SUCCESS/scheduler/APIstatuschanges.

--- Earlier V3-only observations; NOT current detach status ---

# LIVE Run55: actual Air PC snapshot/resume; white UI unresolved

Read MD/EVIDENCE.run55 FIRST. Parente68a668; volumeUUID/origin/branch/remotes/
main/worktrees verified, initiallyclean. No other researcher/hostruntime active.
Actual Air60/PID19384/installationB55DD703-F281-4556-9A49-09550951953B still
current on last successful preflight; REVALIDATE before any next attachment.
Current142 guests; old wave1 updater42/DORMANT is NOT current shutdown.
Fresh physical white screen/nativeoverlay observed; no usableLibrary recovery.

NEW official Xcode LLDB device backend works despite older profiler21 failure.
Exact60 Mach-O UUID/profile/device/PID/URI gate, frame0 nativePC only,16 of149;
actualStop5 -> capture150ms -> Detach(False) success/state9. Collector-through-
detach158ms AFTER stopped; outercommand/statewait16.260s NOT exactpause duration.
No locals/arguments/objectpayload/expressions/targetwrites/restart. Actual60main
SHA3f1603b74ad6c041763123c67366391e85224e7835f66c55b155bfd23fd75350.
SamePID health3565->3574/90s afterdetach;142guests/footprint2103007800B. CPUdelta
115.726367s/90s (aggregate128.585%singlecore), notUIresponsiveness/FPS.

Offline app offset0xaf3f84 = gadget_scvtf_int_vec/math.S6019. Other14 PCs at
kernel0x70dc candidate __psynch_mutexwait+8; mainthread0xcd4 mach_msg2_trap+8.
Systemcache model/OS matches, but runtime systemUUID not captured. Singleinstant
sparsePCs cannot name guestowner/lockowner/rootcause. _pc=x28 sourcecomment is
NOT actualguestELFPC proof: gadget consumes translated parameterstream. No
arbitraryregister/CPUobject dumps or gadget-fix assumptions.

IMPORTANT async LLDB correction: device-select and attach canreturnStarted5 or
Connected2 beforeactualstop. Earlier prematurecollector trieddetach/error3,
keptdebuggeropen; afteractualSIGSTOP official processdetach --keep-stopped false
succeeded/state9 and health3518->3537 advanced. Its2ms NOTpause duration. Third
attempt waits5 beforeimport and9 beforequit; that V3 debugger fullyexited (V4 later pending above). NEVER
unconditionallyquit/kill ontimeout or issueprocesskill. Toolfinally resumes/
detaches onlymatchingPID; foreignPID preserved. Configpreflight remains external.

Final opt-in PCcollector +11 fakeSB hostcontrols pass. Optional atmost2threads/
3callerPC each is HOST-only (unwinder mayread return-address slots, no payload).
Attempted next freshprocess preflight FAILED CoreDevice code1 serviceinitialize
TIMEOUT. That was restricted CLI context; later authorizedCLI succeeded and V4 attempted
attach but is now pending cleanup as above. No reset/restart/inferredappcrash.
Private run55 has report/screen/health/transcript/hostcontrols; hashes inJSON.
No app/runtime/vendor/FEX/Valve/profile/auth/game/save/security/lock changes.

NEXT resolve V4 cleanup as above; no further optionalcaller test now. Keep current60 session; signed61 run52/signed61 unchanged,
NOTinstalled, specific61 choice stillpending (old60approval used already).
On explicit61 choice orauthoritative naturalend, revalidate andnormalLab-only
sameIDupgrade, preserveauth/games/saves/no uninstall/transfer. CapturefreshX11
windowstate+actualgoodLibrary/BPM/input, then targetedfix and genuineSteamPlay->
licensedMadeira game->qualifiedallruntime/display/storageteardown/return/repeats.
Bridge125NOTgame. Prior only-upgrade-can-add-evidence claim superseded byactual
LLDBpath. ExistinggoalAPIblocked unchanged; noSTABLE_SUCCESS/unload/cadencechange.
CLIonly; NEVERMacunlock/credential/Guard/trust automation. Pushsignedoffscoped
checkpointonlyexperiment duringAGENTShours. Fullobjective remains incomplete.

--- HISTORICAL; header supersedes older current-state claims ---

# LIVE Run54: exact watch ELF hostPASS; current60 live, specific61 choice needed

Read latest MD/EVIDENCE.run54 FIRST. Parent8233c3e branch/origin/remotes/main
2ac39be/worktrees/volumeUUID verified. No unrelated/FEX/Valve/vendor/app/auth/
game/save/security/lock changes. CLIonly. Fresh Air60/19384 installationUUID
B55DD703-F281-4556-9A49-09550951953B stillpresent; no input/stop/install. Last
physicalwhite isRun53, no fresh screenshot thisrun. Do NOT infer crash/end.

NEW real HOST control executes EXACT signed61 watch ELF SHA9fca248acfe0180079a157b7de152bc7a312127554d1d0114d3c5fb6767f9e60.
Newunauthedroot only, no Steam/VNC/device. 2rows30008msapart/36.465s hostwall:
ownwindowa hide/focusb accurately observed. Own guestchild24 intentionally
SIGTERM0 thenreaped1/status15; hostobserver56818terminal0/PID26723ended.
Expected synthetic control outcome, NOTCEFcrash orfullruntime/device teardown.
Default ownfixture optimizedARM64IR exactlyequivalent toHEAD(exceptfilename
metadata). Optional runner watch mode only; app/observer sourceunchanged.
Analyzer realstreamnewrow+time advance true, allsession/UI/game qualifiersfalse.
Private run54, signed61main+watchhashesstillunchanged, no rebuild/resign/install.

BOUNDARY AUDIT: same specific61 choice pending3goalturns (Run52asked after
signedartifactready; Run53/54noactualanswer). Latestrepeatgoal forbidsactive
restart, NOTconsent; original60upgradealreadydone. Independentpreparation now
complete atcomponent scopes. NextdecisiveAirtest needs current60end/61install;
more hostcontrols cannot substitute. Aftercheckpoint markthreadgoalblocked on
thisuser-onlyboundary. Never markcomplete/writeSTABLE_SUCCESS/unloadLaunchAgent
or change research cadence. Preserve app/root/artifacts; no repeatedquestions.

NEXT after actual specificupgradechoice orauthoritative sessionstate change:
revalidate exactcurrentPID/URI/profile/device, normal authorizedLab-onlysameID
upgrade/no uninstall/authtransfer. Collectfresh61 own complete state rows with
independentnative identity + physicalgoodLibrary/BPMvsblank, discriminate
mapping/focus/render. Then actualSteamPlay->licensedMadeira game->qualified
Linux/Wine/display/storage teardown->reliableSteamreturn/repeatedstability.
Bridge125NOTgame. Goalunchanged; no Mac-unlock/password/Guard/trust automation.
Pushsignedoffsource/redactedevidenceonlyexperimentallowedhours.

--- HISTORICAL; header supersedes earlier current-state claims ---

# LIVE Run53: Air60 stillwhite, signed61 unchanged; pending specific upgrade choice

Read latest MD/EVIDENCE.run53 FIRST. Parent4e7b105, branch/origin/remote/main
2ac39be/worktrees/volumeUUID verified; initiallyclean. No unrelated/vendor/
FEX/Valve/runtime/app/account/game/save/security/lock changes. CLIonly.
Fresh exactAir60/19384 installationUUIDB55DD703-F281-4556-9A49-09550951953B
process present; physical16:21EST screenwhite. No input/stop/restart/install.
Specific61 choice fromRun52 STILLpending. Repeatedgoal/no-restartinstruction
is NOT that approval. Do not ask repeatedquestions or infer elapsed consent.

Independent HOST artifact analyzer analyze-x11-state.py + testscript:32controls
PASS including4 existing realLinux/Xvfb receiptcases fromRun52. No newruntime
execution. Boundedcomplete numeric rows only, exactappendprefix/partialbyte/
cap/time advancement/error flags. Duplicates/clockstalls/failed samples notfresh.
Root-child rectangle/stack/focus metadata only; extra focuseddescendant has
UNKNOWN coordinateparent. Lost attrdefault0 notknownunmapped. No pixels/WM/
render/Steam qualification. Native-session-bound,cause,UI,game_return always
FALSE; must independently bind nativePID/build and physicalUI. Private run53.

SIGNED61 run52/signed61/Madeira.app stillUNCHANGED main+watchSHAverified.
No newbuild/sign/install. Prior full61 Xcode/finalMachO/resource/deepstrict/
matchingAir/app/cert/profiles valid; profileexpiryNov20. Do NOT overwrite or
resign while pending; interpreter needsnoJIT. Details and exacthashes Run52.

NEXT only after actual61 upgradechoice: revalidate current60 identity, normal
Lab-only stop/sameID upgrade preservingauth/games/saves, no uninstall/transfer.
Capturecompletefresh own /data/tmp/ideck-x11-state.jsonl before/after with exact
native-session and physical goodLibrary/BPMvsblank evidence. Useanalyzerwithout
claiming fromstale/unboundmetadata. Then narrow mapping/focus vs renderingfix,
realSteamPlay->licensedMadeiraGame->fullteardown/reliableSteamreturn. Bridge125
NOTgame; noSTABLE_SUCCESS/unload/complete. Commit-s/pushonlyexperiment during
allowedhours. Never main/forcepush/upstream messages. User-onlygate recorded;
continue independent useful work wherefeasible, not repeatedstatus-onlyturns.

--- HISTORICAL; header supersedes current-state claims below ---

# LIVE Run52: signed61 ready, active60 preserved; specific upgrade choice pending

Read latest MD/EVIDENCE.run52 FIRST. Sourceparent5720f81 Run51 pushed. Same
experiment branch/origin/main2ac39be preserved. Private artifacts run52.
Fresh exactAir current60/19384 UUIDB55DD703-F281-4556-9A49-09550951953B
STILLPRESENT. No input/stop/install. Last physicalwhite, metadataScreensaver
continues; no current browser-unresponsive message, old4events historical.
CLIonly,noMacunlock/auth/Guard/trust/security/Valve/FEX changes.

New --x11-window-state defaultOFF, signedbundle-copy/PID1-VFS/nooverwrite.
Oneguest <=120numericJSONLrecords/30sdelays/20sdeadline/stopfirsterror. Dedicated
/data/tmp/ideck-x11-state.jsonl survivesnativecap. Lastpartial/staleness and
non-atomic nature explicit; no title/property/pixel/input/WM/clientmutation.
HOST21 ASanUBSan protocol+watch,8realVFSinstaller modes,5actualcompilegates,
17negative+9eventnavigation regressionPASS. CurrentARM64LinuxRunner/Xvfb/Xlib
own-window4cases0/46.695shostwall underbuildIO, NOTdevice/performanceproof.
23iOSunits/currenthashes match. FULL61 Xcode72673terminal0, actualfinalparent
configure+nativeinitinstallcalls/linkedwatchcommand/ARM64ELFresources verified.

DISPOSABLESIGNED61: run52/signed61/Madeira.app. Sign20551terminal0,
validation95643terminal0; deepstrict/existingAir+IDs+cert+profiles/entitlements/
unchangedcode+resourcesPASS. ProfileexpiriesNov20. No profile/account/keychain
setting changed. Unsigned61original+live60/root untouched. WatchELFSHA
9fca248acfe0180079a157b7de152bc7a312127554d1d0114d3c5fb6767f9e60.
SignedexeSHAb96aa2ae2a9e2d6713f809ee9ea2178094d0c3b1379264c6879bbbf2277e8a90.
TextSHA81446f26cc7af400a5357b4442ce1c1a7b59be0c28a637fe7f5dc3a93718af0e.
NOTinstalled/Air-tested. No binarydistributionlicenseclearance.

USERQUESTIONPENDING after concrete signed61 ready: allow endCURRENT60+upgrade61
or preserve. Origin: user no-active-session-restart rule. Old60 upgrade consent
alreadycompleted, not61 approval. No elapsed-time consent. Revalidate reply/
actualidentity BEFORE normal Lab-only stop/install. SameID preserveauth/games/
saves, no uninstall/accounttransfer. Ordinary retainedlaunch, interpreter noJIT
required. Need fresh complete JSONLsamples + physicalgoodLibrary/BPMvsblank
viewability/focus before causalpatch, then actual licensedWindowsPlay/game/
fullteardown/reliableSteamreturn. Bridge125 NOTgame, noSTABLE_SUCCESS/unload.
Commit-s/pushonlyexperimentallowedhours; never main/forcepush/upstreammessages.

--- HISTORICAL; header supersedes old current-build claims ---

# LIVE Run51: Build60 actual Library/BPM/input, blank after screensaver; preserve

Read latest MD/EVIDENCE.run51 FIRST. Parentbb3ac02, UUID/origin/worktrees/main
verified. User explicitly approved ending CURRENT59 and upgrading60; DONE.
Actual sameID install/launch0, current60PID19384 installationUUID
B55DD703-F281-4556-9A49-09550951953B. Revalidate before actions, never stale59.
No uninstall/auth transfer/working-app or phone changes. CLIonly,noMacunlock.

Real desktopLibrary + BPMhome/menu + BPMall40/installed0 Library physically
confirmed. Saved auth restored, no credentials/Guard/EULA automation. Fivegrid
keys did not prove exact target; no activate/download. Sequence12/action7 means
native dispatch only. Screensaver visible16:41:59UTC; one pointer wake logs
WasHidden1at16:43:30, but content black. Oneback no menu. Later shared read-only
RFB and later physicalframe whiteblank; no causal/nativeMetal claim. Bothowned
observers terminal0, no input/pairing records. Owntransportsecret private.

CPU sampler cannot-find-pid21 is NOT crash: subsequent exactPID/UUID live and
health115 advances:140entries/2218465752bytes; captrue; bridge0/gamefalse.
Winegeneration0/UNKNOWN; legacyphase8 NOT stop. Preserve60; no samplerretry or
new device experiment. Host ps review could not complete due usage limit; NOT
executed, no unsafe determination/bypass/retry. Independent work continues.

Finalhealth1511/142entries/2093537680bytes, bridge0/nav12. Current webhelper
Screensaver lifecycle advances through20:41UTC despitewhite; ALL4 cumulative
unresponsive-kill lines historicalNov9/10/12, NOTcurrent60. No browserdeath or
renderinghealth claim. No deviceinput/restart during finalreads.

Independent new x11-window-state.c: fixed :99 read-only window/focus/geometry
metadata, no pixel/property/input/auth. HOST19 ASanUBSan protocol cases pass,
actual staticARM64ELF SHA850282bb7d1683de241b2892db81d84c1ed4b3e22ea3ef45f43d81300832e1d7.
Private run51/x11-state-v4. NOT bundled/Air-run, no new Xcode build. Actual HOST LinuxRunner+Xvfb+Xlib
control4casesPASS0/2.859s: map/unmap/remap/focus/destroy, negative geometry and
no-WM mask. Ownobserver87492terminal0. FreshunauthedCoWroot/privateartifacts;
no Steam/VNC/device write. Basic no-WM X11 semantics work; CEF-specific/pressure
and Air behavior unresolved. Current60/19384 revalidated15:36EST, stillwhite.
Quota reset passed and normal read-only checks worked; no bypass. Root
status/validity/race/cap/deadline explicit. Testscript test-x11-state.py.

NEXT discriminator: integrate the qualified read-only state ELF behind an
explicit Lab build gate, capture goodLibrary vs blank mapping/focus before
causal WM patch. Do not overwrite live60/root. No Android graphics copy/FEX/
Valve/security edits. Need genuine Windows download/toolPlay->qualifiedLinux
shutdown->nativeDocklegitimateauth/JIT/game->fullteardown/return. Bridge125
notgame; repeatedfullstability incomplete. NoSTABLE_SUCCESS/schedulerunload.
Rawrun51 private; scopedsource/redactedrecords only experiment permittedhours.

--- HISTORICAL; header supersedes old pending-user/current59 claims ---

# LIVE Run50: one approvedEscape sent, no UI exit; signed60 ready, userchoice pending

Read latest MD/EVIDENCE.run50 FIRST. Parentc47252c, volumeUUID/origin/branch/
worktrees/remotes verified, main2ac39be unchanged. Exactcurrent59/19056 URI UUID
CED6F4B3-5948-4663-A9BE-FFE0ED4677D9+receiptmatch. Preserve apps/auth/games/saves.

User replied“允许” to ONEEscape question. Exactlyone backnotificationposted0.
Physicalinitial+settledscreens STILLSteamScreensaver; NOTdelivery/UI success.
No repeat/alternate input.59logcapped, no new numericack onthisinstalledbuild;
admission/RFB/Steam stage unknown. Health1808/143guests/1629084072bytes/bridge0.
No termsacceptance, restart, upgrade or debugger. Do NOTclaimfrozenapp/rootcause.

NEW asyncchoicepending: user permits endCURRENTLab+upgrade60 OR preservesession
and personally lighttouchscreensaver. NOanswer yet; consumedEscape consent is
NOTthischoice. Keepcurrent59 untilactualreply; no repeatedbuttons/lockrequests.
CLIonly,noMacunlock/security/auth/Guard/trustautomation.

Independentfull60 nowDISPOSABLESIGNED: run50/signed60/Madeira.app. Existing59
main/helperprofiles exactAirUDID/app/cert/expiryNov20 verified; no newprofiles.
Signobserver23224terminal0,validation59116terminal0;deepstrict/entitlements/
unsigned-signedcodeidentityPASS. SignedSHA
3f1603b74ad6c041763123c67366391e85224e7835f66c55b155bfd23fd75350.
TextSHA23a336df6bc5e389b35b4f3d1ef19760dca6959ac8b189b0466b6901a46cd18f.
Codesign '-' output formatparse failed; read-only ':-' XMLfixed, notsignfailure.
Originalunsigned60andlive59untouched. NOTinstalled/devicevalidated. No public
binarylicenseclearance. Rawlogs/screens/profiles/privatepayloads outsideGit.

Afteractualchoice revalidate exactcurrentidentitybeforeend/install. Ownnormal
retainedCLI launchmode perpreviouslaunchreceipt, no credentials or accountcache
transfer. Verify numericnavigation ack/physicalUI, genuineinstall/Windowsdepot/
customtoolPlaycapture, then qualifiedLinuxshutdown/nativeDockauth/JIT/game and
fullteardown/return. Bridge125notgame, no stablecycle. FullgoalACTIVE; noSTABLE_
SUCCESS/unload/merge. Signed-offsource/redactedevidenceonlyexperimentallowedhours.

--- HISTORICAL states below; currentheader supersedes liveclaims ---

# LIVE Run49: actual59 Screensaver preserved; Escape approval pending; unsigned60 ready

Read MD/EVIDENCE.run49 FIRST. Parent3c839d0 branch/origin/worktrees/remotes verified;
main2ac39be unchanged. VolumeUUID580CADCD-33F5-4D78-9530-2287615873CA mounted.
Exact live59PID19056 URI UUIDCED6F4B3-5948-4663-A9BE-FFE0ED4677D9+receipt match.
No install/restart/debugger/deviceinput thisrun. CLIonly,noMacunlock/security/
auth/Guard/trust changes. Preserve account/games/saves/workingapps/allworktrees.

Realwebhelper proves Screensaver_uid2 created11:39:11/visible11:39:14. Changing
full-screen gameart is NOTgame. Health1577/143guests/1620482496bytes/bridge0;
legacyphase8 NOTstop. Longintervalhealth CPUavg2.282cores incl idle, not UI/
interaction/stability/game proof. ActualLibrary/BPM/navigation remainsRun48.

ONE Escape request rejected by auto-review (possiblependingEULA/manualtest).
NOTexecuted; no workaround/retry/alternateinput. Separate read-onlylogs passed.
Async specificapproval questionpending, prior RatatanEULA personalchoicealso
no reply. DO NOT acceptterms or sendEscape untilactualrequiredanswer. Continue
independentcode; preservepossibleuserlive59. No repeatedlock/unlock requests.

New ownLab Winebodyresult provenance: UNKNOWN vs normal-return vs longjmp,
fulluint32code, actualinitialpthreadonly/once/pergeneration, invalid/foreign/
duplicate refused. PrivatecopiedWineProcessBridgeonly; noordinary/FEX/vendor/
Valvechange. One small atomicnumericreceipt surviveslogcap with explicitfalse
allWineworkers/gameexit qualification. Initialjoin/result NOT fullteardown.
HOSTrealpthread/heldTLS/abnormal0xc0000005/knownnormal0/unknown/generation/
create+observerEAGAIN ASanUBSanPASS;3actualiOSunitsWerrorPASS;22runtimeunitsPASS.
Fullunsigned60 normalreviewbuild37034 TERMINAL0 afterdefault-sandbox65failure.
Finalactual2bodycalls+originalmain+guards+delegatewrite+packageverified; SHA
773445334c3fe7c4fd1340bb1879a5c48973e4892a2c909c7bd4b50f6ca4d0e1.
PRIVATE run49/hybrid60 andruntime60; NOT signed/installed/devicevalidated.
Do NOT upgrade current59 whileuser/inputchoicepending. Preserve currentapp.

Next permitteddeviceaction: awakenverifiedUI afterexplicitinputapproval, inspect
install/Windowsmanifest/PE and genuine customtoolselection/Playcapture, then
qualifiedLinuxshutdown/nativelegitimateauth/JIT/game. Bridge125 notgame; no
repeatedgame/return/fullstability. FullgoalACTIVE,noSTABLE_SUCCESS/unload.
Combinedbinarylicensegateunresolved; scopedsource/redactedevidencecommit/push
onlyexperimentduringallowedhours. Keeprawlogs/screens/binaries/profilesprivate.

--- HISTORICAL states below; header supersedes currentstateclaims ---

# LIVE Run48: actual Air Library/BPM/input; unexpected UI change, preserve user test

Read latest MD/EVIDENCE.run48 FIRST. Source checkpoint1db7fcb signed-off/pushed
experiment only, remote verified; main2ac39be unchanged. Current59PID19056 same
UUIDCED6F4B3-5948-4663-A9BE-FFE0ED4677D9; revalidate before mutation. NO new
install/restart/debugger this continuation. Preserve session/prefix/auth/games.

ACTUAL screenshots: Store ->Library list/artwork ->BigPicture home ->right
changes selected game ->Enter opens Ratatan details. Genuine LinuxSteam, no
fakeUI/credentials. Fresh compat_log registers ideck-madeira-lab+manifest+prefix.
Not physicaltouch/Bluetooth/repeatedstability/SteamPlay/game/return success.
BPM initialblack eventuallyrendered; no permanentfreeze/causalfix claim.

Official install dialog1.68GB/free4.46GB, shared /mnt/ideck/SteamLibrary chosen.
Ratatan online-service EULA was observed06:39; agent didNOT accept.06:44screen
changed to othergameartwork withNOagentinput. Usertextreplystillpending; cause/
manualactivityunknown. PRESERVE possibleliveusertest; no input/restart/upgrade
or assumedacceptance/gameproof. After freshuserchoice/state inspectrealWindows
manifest; choose realregisteredtool ifneeded and testactualPlaycapture. Bridge
still125, nativeDock/JIT/auth/worker/signal/storage/return gatesnotqualified.

Latesthealth163:59/19056,140guests,1602148728bytes, logcap4MiBreached. Retainedphase8
NOTstop.1029samples,maxsample2425035272bytes,11memorywarnings; nottruepeak/cause.
Private run47/screen59-* and logs; hashes EVIDENCE48, no rawpayloads inGit.

New ownLab numeric CLIack sequence/action inatomic health afterdispatch;cap
retained,no text/coordinates/accountdata/perkeyfilewrite. ActualhostASan/UBSan
8writers4001events/gates0/1/refusals/postcap and4iOSunitsWerrorpass. NOT full
linked/deployed, running59unchanged. Exact17negative/9pairedhandler regression
passeswithUI/RFBstubs. Keepcurrent usertest alive; noinstalljustforthispatch.
CLIonly,noMacunlock/lock/security/auth/trustautomation. FullgoalACTIVE,noSTABLE_
SUCCESS/unload/complete. Combinedbinarylicensegateunresolved,sourceonlypublish.

--- HISTORICAL states below; currentheader supersedes liveclaims ---

# LIVE Run47: actual59/19056 Linux startup+CLI registration; preserve session

Read latest MD/EVIDENCE.run47 FIRST. Parent/remoteexperimentbe0de64, main2ac39be
unchanged. Source43..47 DIRTY; permittedSaturday hours, scoped checkpoint due.
Verifiedvolume580CADCD-33F5-4D78-9530-2287615873CA. Allmain/worktrees/working
apps/accounts/games/saves preserved; CLIonly noMacunlock/auth/trust automation.

Original59 build62216 andsign5008 TERMINAL0. Startup markers actuallylinked,
deepstrict/profile/codeequality pass. Signed59SHA
533647a310420f5dbfb7d2cc18f32d5f910be511a80d1d4efbcc9f9b8d6cb7a7.
Same-ID install+normal-launch81782 TERMINAL0, actual59PID19056 new installedUUID
CED6F4B3-5948-4663-A9BE-FFE0ED4677D9. Do NOT reuse58/19052/19041/18911.

First actual59 native receipts kernel-19056-809681-609389000.log, healthseq21
phase8/92guests/~734MB. Legacyphase8 does NOT mean noLinux; retainedworldlive.
Withoutdebugger actual logs retained_argument1/cold0, scene_connect, frontend
selected, viewDidLoad, Metalready, CLIregister step andregistered1. Initial
physicalscreen X11root/cursor NOT SteamUI/login/Library/BPM. Observer20530
TERMINAL0. Preserve live59, no restart/reinstall/newbinary whiletestactive.
Next observe realauthenticated SteamUI; only then ONE bounded event + actual
ack + physicalscreenresponse. NoCLIevent posted yet. Physicaltouch/controller
still unqualified, host243coordinatepoints notdeviceproof.

58 nativeforeground stayedphase0/noregistration. Combinedterminate/start10004
notLinuxcrashproof. Ordinary19041 stillphase0; debugger didnotreturnstopped
startupvalues, later noSuchProcess, mightperturblifetime. AllLLDBsessionsclosed;
NO debuggerattach on59. Do notclaimmissingarguments/causalfix. New59 onlyfixed
route markers/readablemodeguard; modechecksunchanged. Unexpected19052guard
abortedfirstinstall, identitycheckedLab58; no matching newstartupreceipt and
screenHOME/oldNativeidle. Only exactpre-runtime19052 normallyterminated under
userpriorauthorization, then same-ID59install preservedcontainer. MacAllocator
untouched. Approvalusagefailedinitial46launchNOTexecuted, laternormalreview
resumedafterreset; no bypass.

Prior53actualsaved-loginStore/Friends observed, finalhealth142/144guests/2.245GB
andcappedlog, endreasonunknown. NOT repeatedLibrary/BPM/input/game/return proof.
OneWineinitialpthreadjoin observer NOT allWineworker/signal/storagequiescence;
no autoLinuxrestore, bridge125 notgame execution. Full goalACTIVE, no STABLE_
SUCCESS/unload/completion. Keep rawscreens/logs/Valve/profiles/privatepayloads
outsideGit; unresolvedcombinedbinarydistributiongate. Source-only/redacted
scoped signed-off checkpoint + push only thisexperiment, no mainmerge/forcepush.

--- HISTORICAL states below; currentheader supersedes live PID/build claims ---

# CURRENT Run47: signed59 startup trace; install/launch81782 NOT YET COLLECTED

Read latest MD/EVIDENCE.run47 FIRST. Parent/remoteexperimentbe0de64, main2ac39be
unchanged; volume580CADCD-33F5-4D78-9530-2287615873CA verified. Source43..47DIRTY,
Saturday local allows scoped signed-off checkpoint/push; review/check stilldue.

COMPLETED46 full58/59681, finalcallsite+signature+unchangedtext verified, same-ID
install58exit0. SignedSHA8d21ad7aa4a59b5e0970bad4f942ff1247cbf4ca8a78238fddf5af79af574b67.
Initial launch was NOT executed: automatic review usage limit, not unsafe verdict.
No bypass. After suggestedreset passed, normalreview resumed05:34EST.

Actual58/18911 native receipt, foregroundscene+timer but phase0/guest0/no CLI
registration/Winegeneration0. Blacknativeview, NOT Linuxfailure/UI proof.
Fresh-mode combinedcommand10004 terminated prior instance with no newreceipt;
ordinary afterverifiedabsence launched19041, stillphase0/noregistration.
Debugger never suppliedstopped startupvalues, later noSuchProcess; mightperturb
lifetime. NO debugger on next test. All LLDBsessions CLOSED; no password/rawargv
read. Do notattribute cause toprewarming/trust/Linux/assertions.

Unexpected same-name19052 aborted planned install, exactURI verified Lab58
6A88B111-AF15-4A48-93CD-1287040B1F1F (MacAllocator untouched). ScreenHOME,
no matching newreceipt (old19041phase0/guest0/Wine0); only exactpre-runtimeLab
19052 normallyterminated afteridentitycheck underexistinguserauthorization.

New59 only fixed stage markers+readable missing-mode label, NO guard relaxation.
Main retained_argument bool/cold_selection; scene route; frontend entry/Metal
beforeafter/CLIregistration. No rawargv/account/authlogs. Actual mainiOScold0/1
Werror+22frontendunits pass. Full59/62216 TERMINAL0; final actualstartupcalls
verified. Disposable signing5008 TERMINAL0/deepstrict/profiles/codeequalityPASS.
Signed59SHA533647a310420f5dbfb7d2cc18f32d5f910be511a80d1d4efbcc9f9b8d6cb7a7.
Private run47/hybrid59+signed59; existingAirprofilesexpireNov20, no newprofile/
security/account/keychain changes. Samecom.kuschqin.ideck.freshtest, no datareset.

CURRENT install+normal-launch observer81782: endedknownidle19052, installation
started; result NOT YET COLLECTED. Poll SAME81782/read install59-final-observer/
launch59-final-observer. NO reinstall/restart or duplicate experiment. Once OS
launch succeeds verify actualfresh59PID/receipt/stage markers+screen, no debugger.
If unexpected liveuser session preserveit. Identity ALWAYS path+PID, sameMadeira
name is insufficient. No Macunlock request or credential/Guard/trust automation.

53 historical genuineStore/Friends/savedlogin valid, not repeatedLibrary/BPM/
input/game/return/stability proof. NoCLI events ever posted to58 because listener
notregistered. InitialWinejoin notfullworker/signal/storage teardown, bridge125.
Full goalACTIVE, no STABLE_SUCCESS/unload/complete. Publishonlysource/redacted
receipts, allrawimages/logs/Valve/profiles/private payloads outsideGit. Keepmain/
allotherworktrees/apps/accounts/games/saves; no FEX/Valve edits or upstreammsgs.

--- HISTORICAL states below; currentheader supersedes livebuild/PID claims ---

# CURRENT Run46: idle newer53/18539;58 BUILD ACTIVE59681; real Store seen45

Read latest MD/EVIDENCE.run46 FIRST. Parent/remote experimentbe0de64, main2ac39be
unchanged; volume580CADCD-33F5-4D78-9530-2287615873CA verified. Source changes
43..46 DIRTY, now Saturday local allows commit/push after actual scoped review.

DO NOT reuse old18355. It genuinely rendered saved-login Store+Friends on Air,
not Library/BPM/input/game success. Final health142 still144guests/~2.245GB;
append log capped4MiB, no end reason. Logged max~2293.65MiB/1127samples;4memory
warnings. Current actual debugger list contains NEW53PID18539 same installed
UUID AEE12339-C654-431C-AAFE-1863B8240CB6. ScreenHOME, nativehealthphase0/guest0/
sequence1/~5MB. New process cause unknown. Preserve/revalidate before actions.
No new install/restart this run yet. Old manual Library question no reply; no
input success assumed. Account preserved, no credential/Guard automation.

Source adds OFF-by-default --cli-input-controls (9 fixed notifications, existing
RFB, no text) and tools/post-lab-navigation.py. Host actual handler17negative/
9paired/throttle ASan/UBSan pass,22iOS units compile. No53listener, do NOT send
notifications to53 or call transport success inputproof. Pinned Metal fullquad
fillsdrawable but old touch usedaspectfit: actual baselinehostAirLibraryY6
expected46. Own guestRect nowbounds+finitecheck; exact methods243points+negative
ASan/UBSan pass. No vendor/production change. Physical touch still unqualified.

Full57 original34128 TERMINAL0/package app+helperIDs pass, UNSIGNED/UNINSTALLED,
SUPERSEDED by newly reproduced touch offset. Never deploy57. New current full58
59681 ACTIVE (snapshot copies may precede prepare receipt); runtime private
run46/cli-input-touch-ios22units pass. Poll SAME59681/read build-result/log,
never rebuild on observer timeout. Once terminal success verify final linked
notifyregistration, sender, touchbounds and package identities before signing.
56/55/54 also completed private only;53 currently installed.

Existing Air main/helperfreshtest profiles expireNov20 match samecertificate;
common identity verified available in existing login keychain. No new profiles/
account/security/entitlement operation. Follow manual-resign skill disposable
copy; source --lab-bundle-identifier accepts only .linuxlab or knownfreshtest,
final app+helperexpectedIDs checked. Revalidate nativecurrentidle before user-
authorized oldLab-only terminate/upgrade; preserveallaccounts/games/saves.
No phone/main/MacAllocator edits. CLIonly NEVER askMacunlock or autoauth/trust.

Next actual Library/BPM/control on58, captured SteamPlay->native authorizedDock
game->proper full cleanup/return/repeatedstability. One Wineinitialpthreadjoin
observer NOT allWineworker/signal/storage readiness, no autoLinuxrestore.
Bridge125, goal ACTIVE, no STABLE_SUCCESS/unload/completion. Raw images/logs/
ValveELF/profiles/private roots NEVER Git, unresolved binarylicensing gate.

--- HISTORICAL headers below; current header supersedes live PID/build claims ---

# LIVE Run45: actual53 Steam update on Air18355; old trust gate superseded

Read latest MD/EVIDENCE.run45 FIRST. Preserve CURRENT actual53PID18355,
installedUUID AEE12339-C654-431C-AAFE-1863B8240CB6; revalidate before actions.
New actual native receipt53/18355 kernel-18355-770279-621974000.log. DO NOT
restart/reinstall/upgrade56 or alter active prefix while this test runs.

Previous18113 CoreDevice record contradicted Instruments/actual LLDB process
lookup. CLI screen read showed home, then normal foreground black launch shell;
no current OS prompt. Persistent official debugger reported no such process and
real list noLab; closed own debugger. User already authorized ending oldLab.
ONE terminate-existing Lab-only restart succeeded new18355, same53/container.
No install/trust/profile/credentials/Guard/security/lock/FEX/Valve action. CLIonly.
Old pending trust/system-prompt assumption superseded by actual successful start.

Fresh physical screen genuine Steam extracting; new actual bootstrap log
stable_linuxarm64 manifest1792618285 update00:21:36, complete00:24:41UTC,
verify00:24:42; steamrtarm64/steam -nobigpicture -cef-disable-gpu. LaterX11cursor
NOT Library/login/BPMsuccess. Five40s actual numeric samples sequence14..18,
footprint324..939MiB, ~1.75nativeCPUcores; not true peak or stability proof.
Bounded observer56011 TERMINAL0. Current post-update health/native/screen
observer90435 was launched; re-poll same handle/read actual artifacts. No new
experiment until current actual status read. Private run45 holds raw screenshots/
logs, NEVER Git. Next user credentials/Guard only if genuine login visible.

Prior unsigned56 actual full/final link PASS (34110 terminal0) and55/54 completed
local only, do not rebuild. Source parentbe0de64; remoteexperimentbe0de64/main
2ac39be last verified. Run43+44 code+45evidence DIRTY outsideFriday22-08, preserve.
Native request/entry and initial pthread join observer implemented but no actual
licensed game handoff/return. One initial join NEVER all Wine workers/signals/
storage readiness; no automatic Linux restore or fake bridge result125success.
Full genuine Library/BPM/input + licensed game/return repeatedly stable goal
ACTIVE, no STABLE_SUCCESS/unload/complete. Main/allotherworktrees/apps/accounts/
games/saves preserved; no Macunlock request or auth/trust automation.

--- HISTORICAL states below; current header supersedes old gate/live PID claims ---

# CURRENT Run44: full56 initial Wine pthread observation; NO device/game success

Read latest MD/EVIDENCE.run44 FIRST. Isolated experiment HEAD/remotebe0de64,
main2ac39be unchanged; volume580CADCD-33F5-4D78-9530-2287615873CA verified.
All Run43+44 code/tests/docs DIRTY UNCOMMITTED/UNPUSHED outsideFriday22-08.
Preserve all source and main/worktrees/installations/accounts/games/saves.

Exact Air read-only current53PID18113 pathUUID AEE12339-C654-431C-AAFE-1863B8240CB6;
last-native receipt STILL52PID17126. No new53start/Steam/crash/trust/lock proof.
User OS-prompt reply PENDING. No launch/kill/install/sign/credential/security
operation this turn; don't repeat gate request or retry refusal. NEVER ask
Mac unlock. Revalidate identity/session before any future mutation.

Original full56 observer34110 TERMINAL0, no wait/rebuild. FinalSHA
2a24d1dbaf8fe31491756e5a0c53a7fa1343ac7088c6fd85677cd35b617938a4.
Private run44/hybrid56 final-initial-join-evidence + bounded disassembly:
actual Wine start calls early-idle+join-observer create; no initial detach;
actual health snapshot and native setup factory calls. Package/platform pass.
56 UNSIGNED/UNINSTALLED;55/54 also completed local only,53 installed unchanged.
Earlier file-name search20616 and remote/check93277 also completed, no live jobs.

DefaultOFF --observe-wine-initial-join requires --madeira-setup. Only disposable
WineProcessBridge initial create/detach adapted; original entry/attributes same.
Observer joins actual initial pthread including TLS; early refusal before prefix/
socket mutation. Failed observer creation preserves real started thread and
records ambiguity. Numeric health all_Wine_workers_qualified=0. Actual host held
TLS-destructor + create/observer EAGAIN + nextgeneration controls ASan/UBSan pass.
Current native source supports further starts subject to checks/optional once
flag; old unconditional single-session characterization superseded. Still NO
full Wine child/worker/signal/global/storage cleanup proof, no automatic Linux
restore. Initial join NEVER game-return permission.

Next physical experiment remains already installed53 Library/input/CoW memory
once user gives fresh official OS-prompt result. Next actual hybrid launch uses
normal native user sign-in/JIT/Valve Dock authorization; no credential transfer
or directEXE. Need measured remaining Wine shutdown and real game->return loop.
Bridge diagnostic125, stable goal ACTIVE; no STABLE_SUCCESS/unload/complete.
Continue meaningful independent work at user-only boundary, preserve earlier
request/option/native entry/Metal/backend drain safeguards. No FEX/Valve edits.

--- HISTORICAL earlier results; current header supersedes state/phase claims ---

# CURRENT Run43: full55 complete; native setup entry HOST/link qualified only

READ current MD/EVIDENCE.run43 FIRST. HEAD+remote experiment be0de64e1e3ce9a2db41b9150418c675000f07e0;
main remote2ac39be unchanged. Volume580CADCD-33F5-4D78-9530-2287615873CA verified.
All Run43 source/tests/docs DIRTY UNCOMMITTED/UNPUSHED outside Friday22-08.
Do not reset, restart builds, re-wait completed handles or overwrite source.

Completed full54 original51811 AND full55 original80444 terminal0. No active
build observer. Final55SHA ed5700c94f946bff145e72ed7f0c95c1dc460c8b499469e5ed237fd5d17ea6f5.
Full Swift/UI source typecheck+link/package/platformIOS pass; final disassembly
verifies native factory/pending-sequence/callback calls.55 unsigned/uninstalled.

DefaultOFF --native-setup-transition requires stage/capture/Dockstorage/Metal
drain and private full --madeira-setup. Actual normal0/DORMANT captured request
stages one native slot; explicit button checks current state/counts0/drain/
window/sequence, disables Linux restart and presents existing native setup.
Native user login/JIT/Play unchanged. Private Linux-arg auto-start excluded;
ordinary source untouched. Delegate bounded16/readiness callback route wired.
Exact method18negative/single/duplicate HOST controls + callbacks ASan/UBSan,
actual C->Swift model/option/sequence regression and22iOS units pass. Host UI/
runtime services stubbed; no real UI/auth/JIT/game/return proof. Receipts private
run43/native-setup-ios-v3,hybrid55,native-entry-controls,native-callback-reproducible.

Installed53UUID AEE12339-C654-431C-AAFE-1863B8240CB6 untouched; last read-only
currentPID18113, native receipt STILL52PID17126 (do NOT reuse PIDs blindly).
Pre-Linux system refusal not a Linux crash. User manual-open/system-prompt reply
PENDING; no new install/launch/kill/trust/security/lock/auth action or repeated
request. CLIonly, NEVER request Mac unlock. First actual device discriminator
remains53 genuine Library/input/CoW memory once OS permits. Check fresh reply/
identity before any action; don't interrupt unknown active user session.

Next actual hybrid handoff must qualify measured Linux/backend/viewer/storage
ownership and native supported licensed Dock launch. No directEXE or token
conversion. Initial Wine pthread detached, wineserverstop joins server only;
DO NOT auto-restore Linux from game-exit/running flags. Clean return remains
unimplemented/unverified; bridge diagnostic125, repeated stability incomplete.
No STABLE_SUCCESS/unload/goalcomplete. Preserve full goal, all installations/
accounts/games/saves/main/vendor source. Private combined binary not distributable.

--- HISTORICAL notes below; current header supersedes completed/live/phase claims ---

# LIVE full54 integration build51811; do NOT repeat or install at pending53gate

One private unsigned54 local compile job ACTIVE, source snapshot complete.
run43/hybrid54/prepare-evidence includes real Swiftrequest/slot, C headers and
actual private native ContentView option hook.22stage-ios units already PASS.
Xcode resource packaging, no errors observed yet. Poll SAME51811/read actual
build-result+xcode.log; timeout not terminal. If passes verify final exported
receiver/realcontroller call and native launchOption method/package. No signed/
installed54 or actual UI/game proof. Installed53/userOSprompt remains untouched.

Return path source recheck initial Wine pthread detached, server stop joins
server only; not all Wine worker/global teardown proof. No automatic Linux
restore from game-exit flags. Full goal ACTIVE, game/return/stability incomplete.
Source Run43 DIRTY UNCOMMITTED/UNPUSHED outside Friday22-08; preserve changes.
No main/FEX/Valve/account/trust/lock/security edits. Next actual53device test
requires user officialOSprompt resolution; don't retry system refusal.

# UPDATE Run43: private native Dock option hook implemented, actual game NOT run

All Run43 edits UNCOMMITTED/UNPUSHED outside weekday22-08 (Friday18:29+).
HEAD/remote be0de64 main2ac39be unchanged. Preserve dirty source. New exact
private ContentView.startDock option block calls LabDockPending.launchOption:
no capture keeps ordinarychosen/default untouched; captured request requires
real manifest/model+native product options, errors BEFORE prepareDock/authfile.
All original login/JIT/cloud/session/installers/ValveLaunchApp downstream source
preserved; no directEXE route. HOST dispatch fallback19/realindex11/3negative
cases and existing CABI/concurrency15/7/49 pass. Actual adaptedFULLContentView
parsed only (not typechecked); new Swift method+Cmapper iOSdylib linked, export
verified. No54fullbuild/install or automatic native UI transition yet.

Read-only Air current18113 installed53UUID AEE12339-C654-431C-AAFE-1863B8240CB6;
last-native-log STILL52PID17126. No fresh53start/Steam proof; no crash/lock/trust
inference. No start/stop/install/security action. User OS prompt still pending,
preserve current instance. Once permitted qualify installed53 Library/input/
memory first. Next native UI/game handoff+runtime/storage ownership and Wine
exit/Steamrestore still need implementation+deviceproof. Bridge125, no stable
marker/unload/goalcomplete. See latestMD/EVIDENCE.run43 for receipts/hashes.

# UPDATE Run43: real capturedRequest->Swift metadata slot wired, defaultOFF

ALL Run43source UNCOMMITTED/UNPUSHED, Friday18:23+ outside22-08; HEADbe0de64/
main2ac39be. Preserve11scoped dirtyfiles. No53device retry/prompt reply yet.
New --stage-dock-request needs capture/Dockstorage/Metaldrain and private
full --madeira-setup. Actual UIKit owner after normal0/DORMANT+prefixbound
calls public CABI receiver, stages owned request in one native Swift slot.
No Wine or original pending-capture consumption. Duplicate/stale/busy/discard
and8writers accept1 HOST via actual C->Swift ABI, prior15/7/49 controls pass.
22iOS units compile; actualcontrollerreference and independent iOS linked
publicexport verified. First INTERNAL cdecl stripped, made PUBLIC+reverified.
No new full54 final app link/deploy, licensed game/return still unimplemented.

Next user53officialOSprompt -> installed53 actualLibrary/input/memory.
Independent nextcoordinator uses stagedrequest realmanifest+Valveoption then
normal native sign-in/JIT/Dock LaunchApp, after measured storage/runtime
ownership. No directEXE or metadata-as-license. Bridge125; no STABLE_SUCCESS/
unload/goalcomplete. CLIonly, no Macunlock/security/auth/Guard/FEX/Valve edits.

# UPDATE Run43: real8216byteIPC->Cmapper->ownedSwiftrequest->Dock model verified

Run43 ALL edits still UNCOMMITTED/UNPUSHED outside weekday22-08 (Friday18:19+);
HEAD/remote be0de64/main2ac39be unchanged. Preserve7scoped dirty files.
New LabDockRequest uses actual C validator/map, aligned immutable request copy
then Swift strings/argv; no borrowed guest pointers/raw logs. HOST valid frame
plus3malformed/mutation isolation+prior15/7/49controls PASS. C/Swift UBSan.
Actual iOS Swift+C mapper dylib links, unresolvedmapper absent; corrected
inheritedmacOSsysroot warning with explicit iphoneos/SDKROOT/syslibroot, vtool
IOS/min17/sdk27 checked. No full new app/device runtime test. Future PRIVATE
--madeira-setup includes adapter and C headers in copied bridging header ONLY.
Installed53 untouched; userOSprompt still PENDING, no install/launch/trust retry.

NEXT once user resolves official Air gate test53 actualLibrary/input/memory.
Independent next coordinator dispatch must retain existing Dock sign-in/JIT/
ValveLaunchApp and true Linux/Wine storage/runtime handoff; no directEXE or
metadata-as-license. Bridge125 remains; game/return/stability incomplete.
No STABLE_SUCCESS/unload/completion. Read latest MD/EVIDENCE.run43 first.

# UPDATE Run43: install+Valve launch-option matcher qualified, source UNCOMMITTED

Run43 dirty source NOT pushed: Friday18:15+ outside22-08. Remote/HEADbe0de64,
main2ac39be verified. Preserve all6 scoped files/edits, no reset or mainmerge.
LabDockSelection now resolves exactly one real config.launch key with same
AppID/path/cwd/Windows-style argv. Actual production option parse tested: sparse
index7 selected,7 contradictory sets rejected,49 argument quoting roundtrips
pass; existing15install-record negatives pass. iOSARM64 symbol/object PASS.
No fallback0/arrayoffset/directEXE, license inference or actual dispatch.
Initial own Swift precondition-throw test error fixed; no product regression.

Air53 system-prompt question STILL PENDING, no new device action. Keep53
installed and its saved state; no rebuild54/launch retry/trust/lock/credential
automation. Once user resolves official OS gate, test53 actual Library/input/
memory. Independently next integrate typed capture to real Dock coordinator
with legitimate native sign-in/Valve LaunchApp and measured Linux/Wine writer/
lifecycle handoff. Full game/return/stability incomplete; bridge125 remains.
No STABLE_SUCCESS/unload/goal complete. Read EVIDENCE.run43/latestMD first.

# CURRENT Run43:53OS prompt pending; native Dock selection component qualified

Source parent be0de64 pushed/readback, isolated branch. User question about
Air53 manual-open/system prompt still PENDING, no approval inferred. No new
device launch/install/security/trust/lock/account action. Keep installed53
unchanged; future CoW-device result still unverified.

Independent source LabDockSelection.swift matches captured AppID/install to
exactly one real installed shared-library DockGame and preserves argv/working/
exe/customExecutables. HOST actual production parser/model+15 contradictions
PASS; iOSARM64 object/symbol PASS, full app link not done. Own harness duplicate
method extraction fixed. Only future explicit private cold Lab source package
includes it; production unchanged. No actual dispatch/game/auth/runtime/lease
permission; bridge125. Extra argv still needs real Valve launch-option matching.

NEXT read fresh Air OS prompt; once allowed test already installed53 Library/
input/memory. Future coordinator MUST use ContentView.startDock normal native
sign-in/Valve LaunchApp rather than direct EXE, and qualify Linux/Wine ownership
and return. No new54 build/install until53 device outcome. Current changes
pending signed-off allowed-window checkpoint. No stable marker/unload/complete.

--- Earlier history; above supersedes outdated source/phase notes ---

# CURRENT Run42:53 installed; OS launch refused pre-Linux; user prompt pending

Original sign70342 terminal0, full/deep/mainhelper/package pass. SignedSHA
02d583e1b51c6629b7b475d8a5ba1d82777cf49eb1e79a90dd44139baa40be88.
Idle17126 revalidated phase0/guest0, ordinary SIGTERM+absence then samecontainer
install53exit0; appsversion53 confirmed. UUID AEE12339-C654-431C-AAFE-1863B8240CB6.
NO actual53 Linux/Steam execution: one launch CoreDevice10002/FBS Security3
refused for generic signature/entitlement/profiletrust reason. Local actual
signer/profile/Air/expiry/gettask/appID/team audit passes. Sole trust cause NOT
proven. User asked to manually open Lab on Air, report actual prompt and do
any official developer trust/verification themselves; question PENDING. Don't
repeat installs/launches/refusal/Macunlock asks or bypass security/locks/auth.

Independent HOST actual ARM64 ELF20checks PASS on combined lazy/fork/group
stack (cow-arm64-guest-v2). Initial harness lacked private log initialization
and correctly refused idle-5 before guest; corrected runner starts own sink.
11native CoW/concurrency/rollback controls and7log/16ELF regressions also pass;
NOT device UI/memory/stability proof. Source c24ac82 pushed. New runner/docs
pending scoped signed-off checkpoint. Full goal ACTIVE, bridge125, licensed
Madeira game/return unimplemented. No stable marker/unload/completion.

Next read fresh user reply and actual Air state. Once OS allows execution,
one controlled installed53 same-prefix run to Library/input/memory metrics.
No old profile gate (current main/helper valid Nov20, old47 expired irrelevant).

--- Earlier history; above supersedes old signing/process/build state ---

# SIGNATURE WAIT VERIFIED: original70342, actual codesign13616 MAIN53

Do not repeat/restart signing. Source b100272 pushed/readback. Extra HOST
four-concurrent-writer control passes;11cases now pass, helper/runtime53
unchanged. New tests/evidence pending commit. Signer13616 exact target is
run42/hybrid53-air-sign/Madeira.app; another unrelated codesign rollback153
exists and is untouched. This is verified ongoing signing, not a new
credential/lock gate. No device upgrade/53UI proof yet.

# UPDATE Run42: full53+final Mach-O PASS; signature live70342, not installed

Actual helper/caller/error branch/invalidate/release inspected; HOST injection
absent. Package resources pass. Build66631 completed0, do NOT rerun. Signature
70342 uses already-existing current Xcode profiles matchingAir/Lab/helper/cert,
expire Nov20 04:42:34/36Z. Old embedded47 expired but not current gate. No
account/security/profile changes. Re-poll70342 then revalidate current17126
identity/health before upgrade. No actual53 device benefit/test yet.

# CURRENT Run42: HOST CoW grouping10pass, full53 live build observer66631

Read latest MD/EVIDENCE.run42 FIRST. Parent checkpoint e1a6005 pushed/readback.
New defaultOFF --cow-native-group qualifies compatible PRIVATE ANON same-backed
flags/offsets inside native-page group only; original file/shared/ptrace paths
unchanged. HOST64writes16backings256KiBrounded vs baseline64backings1MiB.
10controls memory-unitASan/UBSan incl both-side writes, partialunmap, boundaries,
filemetadata fallback and injectedfailrollback PASS. Existing7log/16ELF pass;
22iOS compile. No device benefit/RSS/exactregionlimit/solecause claim.

Actual full unsigned53 building private run42/hybrid53, live exec session66631.
Re-poll same handle/read build-result+xcode.log; DON'T restart due timeout.
Not signed/installed/final artifact verified yet. Profile main expires
2026-11-13T04:43:44Z, helper+2sec; revalidate before every signing/use.

Air fresh current17126 same52 installedpath, own native receipt now exists,
healthphase0/sequence1/guest0. No action taken, preserve/revalidate before any
upgrade. Actual52test17010 died RFB NSAllocateMemoryPages/NSData abort after
native mmapENOMEM; NOT50 forkNULL. No stableUI/game/return; bridge125.

CLIonly/no Macunlock/security/auth/Guard/trust/FEX/Valve/vendor/Codex edits.
Main2ac39be unchanged. Run42 source pending scoped signed-off allowed-window
checkpoint; no STABLE_SUCCESS/unload/completion. Finish full53/final marker
then actual Air discriminator when signing/connectivity permit.

--- Earlier history; above supersedes stale build/process fields ---

# CURRENT Run41: actual52 RFB allocation abort; qualify CoW granularity next

52 full build/final linked branch inspection/deep matchingAir sign/install and
actual17010 updater verified. Later exact52 crash SIGABRT NSAllocateMemoryPages
->NSData->LRRFBClient update; NOT50 fork NULL store. Repeated native file mmap
ENOMEM persists. No capacity/stableUI/game/return proof. Exact receipts/hashes
in EVIDENCE.run41.actual52. Native historical sequence54/phase8 is NOTlive state.
New unexpected17126 same installed52 path exists, Air Home. Preserve/revalidate
identity/current receipt before any stop/upgrade; no blind restart.

New HOST actual pinned CoW measurement:64 adjacent4KiB writes ->64backings;
16KiB host rounding yields1MiB for256KiBguest (ratio4). Parent/child bytes and
accounting PASS. test-cow-backing.py + private cow-backing-reproducible. Not
RSS/exactVMregions/solecause proof. NEXT qualify privateCoW compatible-native
page grouping and rollback on HOST before iOS runtime changes. No grouping
patch yet. PureLinux51 parked/neverinstalled. Fork52 avoids tested NULL crash
onHOST25 but device failure-path execution not proven.

Keep full hybrid objective active, bridge125/game/return incomplete. CLI ONLY,
no Macunlock/security/credentials/Guard/trust/FEX/Valve/vendor/Codex changes.
Profiles expire2026-11-13T04:43:44Z main/helper+2sec, check fresh everyuse.
Do not bypass or claim signature refusal is Linux crash. User oldLab upgrade
consent resolved; preserve all unrelated work/apps/accounts/games/saves.
Main2ac39be unchanged; scope Run40+41 source pending reviewed signed-off
checkpoint in current weekday22-08 window. No STABLE_SUCCESS/unload/completion.

--- Historical details; above supersedes old process/build state ---

# CURRENT Run41: actual50 SIGSEGV in fork PTE copy; host fix qualified,52 building

Read latest MD/EVIDENCE.run41 FIRST. Actual50PID16772 CRASHED, exact device
SIGSEGV/KERN_INVALID_ADDRESS0 pt_copy_on_write+232 -> mm_copy -> clone. UUID
and final disassembly match NULL child PTE store. NOT47 RFB NSData abort.
Final trace18mapping failures/max sampled67,702regions; root native pressure
cause/region limit unproved. Numeric futex diagnostics observed, not cause proof.

Unexpected16901 same installed50 executable exists; last-native-log copied now
STILL dead16772. Inspect receipt/scene/state BEFORE stopping/upgrading. Never
blindly target stale PIDs. User permits old Lab termination/upgrades; preserve
unexpected actual user tests, all auth/root/game/save/apps/production/phone.

New defaultOFF --fork-map-failure: checked fork-only tables, allocation before
ref transfer, partial anonymous accounting, reservation errors -> mm_copy cleanup
-> clone ENOMEM. HOST exact baseline memory.c722 fault reproduced;25 fixed
actual kernel copy/clone controls ASan/UBSan PASS. Private fork-map-control-v4.
No iOS failure injection, cap/clock/watchdog/FEX/Valve/vendor changes. Other
unchecked engine/ordinary-map allocations remain. Full52 not yet built/installed;
fork-ios components building. Pure Linux51 PARKED, never installed.

CLI ONLY; no Mac unlock/security/credential/Guard/trust/Codex changes/subagents.
BranchHEAD/remote b12d781, main2ac39be untouched. All scoped Run40+41 DIRTY
UNCOMMITTED/UNPUSHED outside weekdays22-08. Existing profile main expires
2026-11-13T04:43:44Z, recheck before signing/use. Bridge125; licensed Madeira
game/return/stable loop unimplemented. No STABLE_SUCCESS/unload/goal complete.

--- Earlier history below; above supersedes stale active process state ---

# LIVE Run41: actual50 PID16772 running, preserve active Library navigation test

Read latest MD/EVIDENCE.run41 FIRST.50 full Xcode/finalscene+resources/futex
marker/deep matching Air signing PASS. Actual same-container install50 exit0,
app list50. Signed MachO a474144def1982630d980407d1ab663b43d1b8828a8fff61c76a42c43034cad6.
Unexpected postinstall16757 at Home had stale49 receipt (NOT current health);
first guard refused BEFORE launching. Own source Linux starts only after
didFinish/scene. Controlled fresh --terminate-existing -> actual50 PID16772,
new current native receipt, real updater screenshot. Prewarm hypothesis only.

Current16772 native file kernel-16772-664772-554414000.log, session auto42->wave2
RUNNING. Actual real Steam Store/chrome rendered after initial black. One Library
click opens white menu; Library first-row follow-up observer underway/recent:
read private run41/rfb50-library-home-click before/after. Do NOT restart/install
over this live test or infer UI success from ACK/PID. Current bounded log had no
MMAP_FAILURE/signal5 yet. Numeric futex metadata really appears; decode actual
hung renderer thread only after failure, no arbitrary memory dereference.

Separate PRIVATE Linux-only CONTROL51 prepared, not signed/installed, same
qualified kernel/engine/frontend/archive hashes as50, no Windows runtime linked.
Purpose only to isolate combined-link/initializer side effects IF50 fails. It
is NOT a replacement architecture/game bridge success. Generator
build-linux-frontend-control.py; actual symbols/bytes inspected. First link missed
CoreGraphics, corrected v2 passes. No runtime changes to make it link.
Do not install this control over a recovered or active user50 session.

49 prior renderer267/272 CrashHungProcess FATAL captured, not original ENOMEM.
Its21min final health still guest165, no usableUI; owned failed49 ended SIGTERM
(no forced kill), absence verified before50. Known file-map failure leak patched
defaultOFF and provenhost; no claim original capacity solved. No clock/budget/
watchdog/FEX/Valve/vendor/security/Codex changes. CLI only, no Mac unlock asks,
credentials/Guard/trust automation or subagents. Main2ac39be unchanged, source
dirty UNCOMMITTED/UNPUSHED outside weekday22-08 (HEAD/remote b12d781).
Profiles expire2026-11-13T04:43:44Z; recheck at sign/use. Shared auth/root/games
preserved, bridge125, actual licensed Madeira game/return/stability unqualified.
No STABLE_SUCCESS/scheduler unload/goal completion. Full objective ACTIVE.

--- Earlier details/history below; above supersedes stale live state ---

# LIVE Run41: actual49 PID16532, automatic update->retained wave2 verified; renderer hung

Read latest MD/EVIDENCE.run41 FIRST. 49 actual signed/installed same .freshtest
container; PID16532 (REVALIDATE) active. Official updater42 completed, real
backend/RFB/Metal drains then ONE automatic restart -> RUNNING wave2 SAMEPID.
DO NOT restart/install over it blindly. No root reimport/auth transfer.

Wave2 partial desktop chrome -> black X11 cursor, not usable Library/BPM. Actual
renderer267/thread272 emits Chromium126 child_thread_impl.cc351 CrashHungProcess
Crashing because hung -> wait5; public exact source fetched. Main267 blocked
futex98 with small/unchanged cycles. Bounded current log MMAP_FAILURE count0,
not proof original memory cause fixed. Pretrap footprint2313361424/available
692905968/regions52593. Repeated official update version1792618285 installed0
also observed47, not proven cause; pinned DroidDeck installer/session inspected,
no Android/sandbox/repair copied. No watchdog/assertion suppression or blindretry.

DefaultOFF --file-map-cleanup proven host baseline3 failed-transfer leaks/fixed3
releases+3 successful transfers; actual full host copied backend7 logging+16ELF
regressions pass.22iOS/full49/finalmarkers/deep signing passed, narrow scope.
New own task snapshot blocked-futex numeric metadata source added (op/expected/
bitset/timed/caller addresses only, no memory read); existing controls running.
Next finish actual-futex host fixture then build50 diagnostic WITHOUT altering
wait/wake/clocks/budget/watchdog. Don't claim diagnosis from a sent input or PID.

CLI only, no Mac-unlock/security/credentials/Guard/trust/FEX/Valve/vendor/Codex
changes or subagents. User old Lab upgrade consent RESOLVED, preserve unrelated
user tests/apps/data. Existing profile expiry2026-11-13T04:43:44Z. Dirty Run40+41
UNCOMMITTED/UNPUSHED in daytime (HEAD/remote b12d781), main2ac39be unchanged.
Bridge125; real licensed Madeira game/return/stable loop still unimplemented.
No STABLE_SUCCESS, scheduler unload or goal completion.

--- Earlier detail retained below; above supersedes stale live/candidate fields ---

# LIVE Run41: genuine Store -> transport0x3000 -> actual47 native allocation abort

Read latest MD/EVIDENCE.run41. Current47 PID16203 died SIGABRT: exact crash
NSAllocateMemoryPages -> NSData -> RFB update. Unexpected new47 idlePID16392
observed Home/phase0/guest0, inspected but not stopped. Revalidate identity and
active state before next upgrade. One Exit radio selected, confirmation never
connected; NOT normal exit/game return. No other local writer found.

Store really rendered; ordinary Library click visibly affected menu/content,
but explicit0x3000 and black content, NOT usable Library/BPM. Native first2MiB
shared mmapENOMEM then networkservice100 signal9; later utilities exit127 with
libcef map-segment errors. Original cause still unqualified. New defaultOFF
--file-map-cleanup fixes separately proven pt_map metadata-failure mapping leak
in copied realfs.c; baseline3 leaks/fixed3 releases +3 success ownership controls
ASan/UBSan/Mach coverage pass,22iOS units pass, vendor/base unchanged. Do not
increase caps/retry/suppress assertions or call this original-root fix.

Full48 update-exit policy/package/link PASS, NOT signed/installed. Full49 building
with cleanup + public self VM region/internal/external/compressed accounting.
Next inspect49 receipts, exact current Air/profile/idle instance before isolated
sign/install/test; preserve auth/games/root and all other apps. Signed47 still
installed. Profile expiry2026-11-13T04:43:44Z. No Mac unlock/security/credentials/
Guard/trust/FEX/Valve/vendor/Codex changes or subagents. No stable marker or goal
completion. Bridge125; licensed native game and return still unimplemented.
Dirty source/docs UNCOMMITTED/UNPUSHED outside weekday22-08, main unchanged.

--- Earlier continuity below; latest live state above supersedes it ---

# LIVE Run41: real47 updater complete; post-update Steam PID16203 active

Read latest MD/EVIDENCE.run41 FIRST. Actual47 installed, initial16191 real updater
completed42 (wait10752)/native0/DORMANT4/reaped1, guests/workers0 and RFB/Metal
drain marker. Empty probe dirs3/no files removed; library registration0/changed1.
UI incorrectly labels successful42 cleanup as failed. Same47 fresh post-update
PID16203 now shows saved-login splash -> actual desktop chrome/black content.
REVALIDATE identity; preserve this live session, no blind new install/restart.
New source handles exact42 Linux-only restart, automatic max1 after all real
drains and no captured game; all65536 wait statuses ASan/UBSan pass. NOT installed
or device-validated yet. No Wine/game permission, bridge125. Build48 pending.
No Library interaction/BPM/current game/return/stability result. Main unchanged;
dirty Run40+41 UNCOMMITTED/UNPUSHED outside weekday22-08. User upgrade consent
resolved; CLI only, no Mac-unlock/security/credentials/Guard/trust/FEX/Valve/vendor
or Codex edits, no subagents. Never copy account secrets. Full goal ACTIVE.

--- Previous detail/history follows; live state above takes precedence ---

# Latest Run41 update: real45 cold UI verified; Linux mount empty-probe fix building47

User authorized old Lab end/upgrade; no pending consent gate. Read EVIDENCE.run41
and latest MD Run41 first. Keep Run40+41 edits UNCOMMITTED outside weekday22-08;
HEAD/remote b12d781, main2ac39be unchanged. CLI only, no Mac unlock/security/
credentials/Guard/trust/FEX/Valve/vendor/Codex changes or subagents.

Real missing scene manifest caused44 UIKit SIGTRAP, exact UUID confirmed. Fixed45
full build/sign/install completed AFTER installer observer175s timeout; actual
placeholderLoading meant pending, not Linux failure. No duplicate install.
First45 PID16132 stayed black/idle; LLDB batch only connected, never stopped,
expressions failed; later health sequence advanced8->31, no stale suspended state.
Do NOT claim inspected window state/JIT success. SAME45 controlled fresh launch
--terminate-existing + madeira-linux-lab-setup produced PID16153, actual native
setup screenshot and cold receipt prefix_bound1/Linux idle1/game_started0.
Extra UISceneClassName proposal46 is REJECTED as necessary fix, built but NEVER
installed; only own proposal source/log edits removed, main.m matches actual45.
Keep the REAL scene-manifest fix in private generator/final package checker.
Fresh-launch receipt is not proof args reached an existing process; require a
verified fresh own test and actual current receipt/window. Native UI's Windows
Steam32 VA warning was not lowered/bypassed; no Wine/game ran.

Then actual45 fresh linux-steam-retained-frontend PID16155 failed BEFORE guest
exec: native -39 ENOTEMPTY, no Steam UI success. Actual bounded app-directory
inventory confirms old fakefs mountpoint contains ONLY empty
steamapps/common/Control from old owned compatibility diagnostics. No files.
New --retire-empty-probe defaultOFF requires registration+Dock flags. Linux VFS
validates exact empty chain, rmdir only those empty dirs BEFORE native mount;
any file/other name/symlink refuses, old empty-mount guard remains. No raw host
rmdir behind meta.db, no game/account/data migration or deletion. Categorical
retired-directory count/files_deleted0 log only. No runtime-lifetime reset.

Host actual fakefs/realfs sanitizer controls7 pass: OFF refusal preserved, ON
full/partial/empty okay, file/other-dir retained/refused. Actual ARM64 ELF read
through cleanup->shared mount->registration passes fresh+merge; interrupted0
means preservation/no guest. iOS retire-ios + full47 next; read receipts first.
Current device remains owned failed45 PID16155 (REVALIDATE) until verified47 ready.
No overlapping runtime/overwrite. Native profile expiry2026-11-13T04:43:44Z.
Next47 launch Linux frontend FRESH, verify actual dirs_retired3, registration,
real Steam UI/saved auth/input/storage, not just PID/Frame/BrowserReady. Bridge
still125, no real game/return/stability. No combined binary distribution clearance,
STABLE_SUCCESS, scheduler unload or goal completion.

--- Older Run41 detail follows; live state above takes precedence ---

# Run41: user explicitly authorized ending old Lab and upgrading

The user NOW says “允许结束旧 Lab 并升级”. Prior pending-choice gate is RESOLVED;
do not ask again or treat it as pending. Same isolated Lab/iteration authorization,
CLI only; preserve unrelated apps/main/accounts/games/saves. No Mac-unlock asks,
credentials/Guard/trust automation, settings/lock/security/FEX/Valve/Codex edits.
Read MD Run41/EVIDENCE.run41 and actual newest private receipts FIRST.

Run40 uncommitted source/docs preserved. HEAD/remote b12d781, main2ac39be. Current
weekday daytime means NO commit/push, do not drop these edits. Volume UUID verified.
Old Lab23 PID4952 got SIGTERM; immediate query still present but later exact query
absent, so NO SIGKILL was sent. This is not clean frontend/game teardown proof.
Verified matching unexpired Air main/helper profiles/cert, upgraded SAME .freshtest
container to actual44, no uninstall/data erase; before/after Linux root marker
matches. No auth/save transfer. First CLI launch64 was argument-order harness
error corrected; actual launch44 PID16066 immediately exited back Home.

Actual specific .ips UUID matches the final44 Mach-O. UIKitCore top symbol
UIApplicationEvaluateRuntimeIssueForNoSceneLifecycleAdoption, EXC_BREAKPOINT.
Final44 Info has NO UIApplicationSceneManifest; standalone working Lab DOES.
last-native-log still23, no fresh cold setup result, process absent. These are
actual startup failure evidence, not Steam/CEF or entitlement refusal.

Smallest fix: private generator copies EXACT standalone Lab UIScene manifest
(LinuxLabSceneDelegate), new final package gate requires it. Actual old44 fails
new gate. Full fresh45 Xcode passes; sign/install/device test IN PROGRESS, read
actual private run41 newest receipts/status first. Do not overwrite/restart a live
new45 blindly. Existing profile expiry2026-11-13T04:43:44Z, recheck at actual use.
Native CoreDevice screenshot command works: no DeviceHub GUI/Mac unlock needed.

NEXT actual45 cold native setup should show real UI, write new build receipt
with Linux idle. Then actual Linux frontend retained mode with preserved saved
login + registered shared library, normal real input/Storage/windows depots.
Native game bridge still125 and no real game/return. No Valve acceptance/stability/
full teardown/license distribution clearance/STABLE_SUCCESS or goal completion.

--- Earlier continuity retained as history; pending-choice text below is obsolete ---

# Latest Run40: opt-in Linux shared install-library registration

Read MD Run40 + EVIDENCE.run40 FIRST. Source parent b12d781, main2ac39be retained.
Recheck actual status/remote/time; Run40 source/docs are UNCOMMITTED/UNPUSHED:
validation finished after08:00 weekday. HEAD/remote b12d781. Do not drop edits or
commit/push before a fresh allowed-window check. Preserve every unrelated worktree and app/state.
CLI only, no Mac-unlock requests, cybersecurity/settings/auth/Guard/trust/FEX/
Valve/vendor/Codex edits or subagents. Full goal ACTIVE; no completion claim.

New qualified builder --register-shared-library requires explicit Dock/shared/
capture/Metal flags. Native initial PID1 registrar BEFORE first Steam guest,
not on retained restart/cold native setup. Caller owns private root exclusively;
PID1 alone is not writer admission. Bounded256KiB KV span plan appends one unused
numeric entry; keeps original bytes/comments/unknown fields/other libraries.
Fresh config has primary /Steam + /mnt/ideck/SteamLibrary. Exact backup and
original mode retained, O_EXCL stage verified + old content rechecked + rename.
Existing interrupted stage/backup retained; error is not automatic cleanup/retry.
Only categorical V1 numeric result, never raw file/account data. No migration.

Actual HOST fresh/merge each run a real ARM64 ELF via Linux syscalls reading the
new fakefs config + shared realfs. Own wrappers ASan/UBSan; deps not rebuilt with
sanitizers. Both native guest0, repeat byte-identical, old metadata/mode retained.
Interrupted fixture harness0 verifies original/stage retention, NO guest started.
Exact existing native KV reader sees default/old/shared entries, NOT Valve proof.
Initial test header AT_PWD corrected only in own harness. Final test receipt
run40/library-registration4. Final22 namespaced iOS units pass; actual optionOFF
Runtime.o no registrar reference, ON has it. Full App44 PASSES; actual register/plan/controller calls + distinct Linux TLS/
Wine global + processed rootfs/resources/callback verified. Unsigned SHA
9f1fdeb6...ccfaa39. Private signed44/deep strict0/embedded main+helper Air coverage
and post-sign package checks pass; signed SHA07dbcc4e...4f4605a. NOT installed.
See final44-linked.json and sign44-verified.json for exact hashes.

ONE Air query still exact old Lab23 PID4952/installB265FEBE; revalidate before
any action. No device input/stop/install/restart/auth. Existing old-session end +
isolated upgrade/iteration question remains pending, do not repeat/infer consent.
Signed43 retained; corrected signed44 includes registration and has finished
actual final package/link + own matching-profile checks. No silent
install/substitution. Existing profile expiry2026-11-13T04:43:44Z; never assume
validity later or work around expired/missing authorization.

NEXT after valid old-session choice: isolate-only upgrade; first real native
setup/Linux idle/JIT/auth, then real Steam storage/library UI and Windows depot
download to fixed shared library. Don't borrow/copy Linux or production auth.
Actual Steam Play -> license-checked Madeira -> full teardown -> Linux restore
still absent, response125. No stable repeated Air game-return/Bluetooth/perf proof,
combined binary license clearance, STABLE_SUCCESS or scheduler unload.

--- Earlier continuity retained below ---

# Latest Run39: cold Madeira setup prerequisite; use corrected App43

Read MD Run39 + EVIDENCE.run39 FIRST. Source parent4f57a965; next source checkpoint
may now be newer, verify Git/remote/status/time. Main2ac39be and all unrelated
worktrees/production/phone/account/game/save state preserved. Full goal ACTIVE.
No cybersecurity/lock/settings/auth/Guard/FEX/Valve/vendor/Codex changes, no
Mac-unlock requests or subagents. Required volume UUID verified.

New --madeira-setup PRIVATE full target, explicit madeira-linux-lab-setup ONLY;
reject mixed Linux/other Madeira args before existing retained-Linux guard.
Linux stage must stay idle; prepare pinned root/known binding then actual
ContentView/bootstrap/controller/hardware/JIT URL handlers. No automatic Linux
initialization, credential entry, runtime/session reset or game handoff. Exact
old auto-start rule excludes madeiraprefix arg. Initial last-cold-setup.json is
NOT continuing status. Queued URL cap16, no raw URLs/auth logged.

Real HOST exact installer method rejected Run38 logical Documents/wine alias.
App41 compiled but not a qualified native setup candidate. New LabMadeiraPrefix
resolves ONLY known binding -> physical MadeiraPrefix; unrelated paths unchanged.
Builder wraps two exact native root expressions in PRIVATE MadeiraDock and
SteamUIExperiment copies; normal source and all installer/PE/path checks retained.
Exact production destination method now passes physical prefix, old alias still
fails. This is NOT full installer/network/registry/Wine/auth/device success.

Inherited callback could return to working-app madeira-steamui after resign ID.
App43 now ONLY registers ideck-linux-lab; exact production callback selector and
FINAL processed Info verified. App42 is pre callback correction. Preserve old
intermediate outputs, do not install them just because they built.

Final corrected full unsigned43 passes; SHA6f32f08a...c283382a, actual C/Swift/
prefix calls and separate Linux TLS/Wine current verified. FeatureOFF actual ObjC
entry has no cold symbols. ASan/UBSan C chooser + exact Swift auto-start/callback
and real filesystem/prefix destination controls pass. See private run39 receipts.
Rootfs input/pin/resources remain required and no Valve/rootfs/auth bundled.
Disposable .freshtest43 signed/deep strict0, post-sign package checks + actual
embedded main/helper Air coverage verified. NOT installed. Existing profiles
expire2026-11-13T04:43:44Z; recheck at use, no account/profile workaround. See
EVIDENCE.run39.signing; signing is never installation/runtime success.

ONE read-only Air query: exact old Lab23 PID4952/installB265FEBE still present.
REVALIDATE before actions. No device input/stop/upgrade/restart/auth. Existing
old-session termination + isolated upgrade/subsequent iteration question still
pending; no repetition/inferred consent from continue/time/heartbeat. Current
candidate43 supersedes35–42, explain this if permission arrives. CLI only.

NEXT after existing user choice: revalidate actual app/profile/device, upgrade
ONLY isolated .freshtest Lab preserving container, launch cold setup explicitly,
verify real native UI and Linux idle, then normal user auth/JIT/runtime setup.
Never automate credentials/Guard/trust or borrow production/Linux auth. Then
Steam Play -> clean Linux/exclusive writer -> real native Madeira launch ->
full Wine teardown/Linux restore. Bridge still125, NO Windows execution or
repeated Air game/return proof. Converter/component license scope unresolved:
NO combined binary distribution, STABLE_SUCCESS, scheduler unload or completion.

--- Earlier continuity retained below ---

# CRITICAL Run38 packaging correction: use candidate40, NOT combined35-39

Source18f1aef733d1831bdad73217dad5a3b5ca5feb00 signed-off/pushed/read back;
remote main unchanged. Subsequent correction may be a newer commit: check actual
Git state/remote and fresh allowed-hours clock. Read MD Run38 final-package
correction and EVIDENCE.run38 first. Full goal still ACTIVE.

FINAL App39 (and earlier combined generator) omitted RootFS Info pin and three
LabCompatibility resources. Earlier build/sign/link claims were narrow only;
DO NOT INSTALL old signed35 as a functional frontend. Old user Air23 untouched.
Fixed PRIVATE build generator derives pin from compiled flags, compiles own
ARM64 helper + exact VDFs, adds actual main resource phase and validates FINAL
Info/hashes/ELF. Fresh generated full40 passes; real39 fails new artifact gate.
verify-hybrid-package.py can check post-build/re-sign candidate independently.
No Valve/rootfs/auth payload in bundle/Git; private rootfs input still required.
Actual unsigned40 SHA6cd4ea83...e294516; matching-profile signed40/deep strict0
and post-sign package verification PASS. Signed40 NOT installed. Read final40/
sign40 receipts for exact hashes; no device/UI/game inference.
Preserve old immutable artifacts as evidence. Candidate40 supersedes35-39; pending
old-session upgrade choice remains, no silent install/substitution or inference.

# Latest Run38: physical drive_c shared storage + Windows mapping/native Dock discovery; App39

Read MD Run38 and EVIDENCE.run38 FIRST. Source parent815ddc5; origin main2ac39be
unchanged. Run34-38 source may now be published after22:00EST; verify actual Git/
remote receipt and fresh clock EACH commit/push, never assume publication from
this note. Preserve all other worktrees/changes. Full goal ACTIVE/incomplete.
CLI only; no cybersecurity/settings/lock/credentials/Guard/trust/FEX/Valve/vendor/
Codex-state changes, Mac-unlock requests, second researcher or concurrent runtime.

Actual Dock.games rejects external drive_c symlinks. New --dock-storage requires
capture/shared/Metal and uses Lab-root/MadeiraPrefix/drive_c/SteamLibrary, mounted
at same guest /mnt/ideck/SteamLibrary. Refuses old outer SharedSteamLibrary, no
migration; old layout default unchanged. WindowsLaunchMap maps only shared paths,
retains NUL argv boundaries, no shell/MADEIRA_ARGS/permission/auth claim.

Native prefix binding Documents/wine -> dedicated MadeiraPrefix; fresh Windows
libraryfolders metadata only if absent, pinned client root read from actual
SteamRuntimeFiles. Existing settings and other prefix/save retained. Controller
post-frontend successful/DORMANT path maps/binds, NOT starts Wine/writer/auth.

Actual HOST ARM64 device IPC/capture with physical C layout + mapped argv passes;
old-layout regression passes. Two native requests/own PE fixture only, never
Windows execution/license proof. HOST Foundation binding/idempotence/settings/
existing-save retention passes normal execution; sandbox atomic fixture update
Cocoa513 is environment, no system setting fix. EXACT selected real Dock discovery
methods + actual parser find synthetic C-contained manifest, not Valve acceptance.
Read-only prefix-template138 names have no shared/config collision, not Wine init.

Full App39 + FINAL mapper/binder calls and separate current identities verified.
Immutable private run38/hybrid39-unsigned/Madeira.app SHAed727d64...e6049ef,
UNSIGNED/UNINSTALLED. Signed35/immutable35-38 preserved. New flagOFF iOS controller
compiles with mapper/binder refs absent. Protocol remains125, NO game started.

ONE Air query still old Lab23/4952/installB265FEBE (REVALIDATE). Existing combined35
+ subsequent same-Lab-iteration choice unanswered, no repeat/continue/time consent
or silent substitution39. No device input/stop/install/auth/signing this run;
production/phone/Mac Allocator/auth/games/saves preserved. No active runtime tests.

NEXT explicit COLD native Madeira setup/auth/JIT mode in SAME isolated app, no
Linux initialization/concurrency or one-session reset; use existing supported
ContentView lifecycle/input/URL handling, no auth/cache transfer. Then actual
Steam Play -> clean Linux/exclusive-writer handoff -> genuine Windows LaunchApp.
Runtime setup, Wine execution/teardown/Linux return/repeated game cycles remain
incomplete. Linux library registration and old-library migration NOT supplied.
Actual Air upgrade still waits existing choice. No STABLE_SUCCESS/task unload/
completion/combined binary distribution before license scope is resolved.

--- Earlier Run37 continuity ---

# Latest Run37: real ARM64 IPC -> native shared request capture; final App38 receiver present

Read MD Run37 and EVIDENCE.run37 FIRST. Published/source parent815ddc5,
remote main2ac39be unchanged. Run34-37 dirty UNCOMMITTED/UNPUSHED outside
weekday22-08 (last16:25EST). Preserve all edits/worktrees. Full goal ACTIVE.
CLI-only, no cybersecurity/settings/lock/account/credential/Guard/trust operations,
Mac-unlock requests, FEX/Valve/vendor/Codex-state edits or subagents.

Fixed actual shared-source mismatch: native preparation BEFORE Linux init,
explicit separate shared fd registration, GameFiles_from_roots; from_data keeps
legacy/default mapping. One bounded owned8216-byte request reserved under mutex
before file inspection; concurrent requests cannot overwrite/in-flight-repopulate.
Native peek/discard APIs, NOT execution/license/storage/Wine permission. No raw
argument/frame serialization/logging. ProtocolV1 response125 remains NOT launched.
--capture-launch requires --shared-library AND --metal-drain, default flags0.

Actual ARM64 ELF via real /dev/ideck-madeira in LinuxLabRuntime -> native separate
shared-file inspection -> owned request peek. Busy/decline/next and two native
concurrent callers/join controls pass. Capture OFF actual IPC also passes with
no pending request. Ordinary/default file routes pass. ASan/UBSan own wrappers,
static deps not instrumented; archive hashes before/after unchanged. New own
Windows PE fixture ExitProcess7 INSPECTED ONLY, NEVER executed; no Steam license.
Native EAGAIN test corrected -11->-EAGAIN(Darwin35), not production workaround.
Real fakefs/shared I/O regression two serial native processes0/0, NOT app restart.

First full App38's final nm missed pending getter due no product caller. Added
ACTUAL retained-owner post-frontend peek + categorical seq/AppID/not-started
private result/status, rebuilt. Final full App38 now actual receiver+registration+
bridge-inspect calls and separate current identities verified. Immutable private
run37/hybrid38-unsigned/Madeira.app SHAfd4f26d0...d466824, UNSIGNED/UNINSTALLED.
Default iOS controller flags0 compiles with new receiver refs absent. Final
auditor tool handle missing after completed receipt; no restart/crash inference.

ONE readonly Air query still Lab23/4952/installB265FEBE (REVALIDATE). Own last
native-log receipt read-only confirms23/4952, no usable health path, no health/
CPU/UI claim. No Steam/account data extraction or device input/stop/install/auth.
Pending combined35 + subsequent same-Lab-iteration choice unanswered; don't repeat,
infer from continue/time or silently substitute38. Signed35/immutable35-37 and
production/phone/Mac Allocator/auth/games preserved. No active runtime tests left.

NEXT real native path mapping/shared writer handoff, isolated Windows prefix/
Steam-library metadata and existing Madeira JIT/full-init/genuine Dock login/
LaunchApp. Do NOT equate Linux auth/PE/AppID/capture/DORMANT to permission.
Native discard currently source/host only. No Windows execution/teardown/Linux
return/repeated game-cycle proof. No fakeUI/DRM/auth bypass/reset. Combined
binary exception unresolved; no distribution. No STABLE_SUCCESS/task unload.
Actual Air upgrade still waits existing user choice; advance independent work.

--- Earlier Run36 continuity ---

# Latest Run36: separate shared library, real ARM64 I/O PASS, full App37; NOT Air/game proof

Read MD Run36 and EVIDENCE.run36 FIRST. Published/source parent815ddc5,
remote main2ac39be unchanged. Run34-36 dirty UNCOMMITTED/UNPUSHED, weekday
13:45EST outside22-08 window. Preserve all edits/worktrees. Goal ACTIVE/incomplete.
CLI only, no cybersecurity/settings/lock/account operation, Mac unlock request,
credential/Guard/trust automation, FEX/Valve/vendor edit or subagents.

New SharedSteamLibrary mounts native Lab-root/SharedSteamLibrary as realfs at
/mnt/ideck/SteamLibrary, outside fakefs data. Empty guest placeholder only; no
native-lifetime remount or existing-file hiding. Initial native owner, no reset.
Opt-in --shared-library / IDECK_LAB_SHARED_LIBRARY(default0), Linux adapters only.
Default /Steam/auth/games/prefix untouched. NOT exclusive-writer permission.

Actual ARM64 ELF f0ff60e5...e5c7d9, scratch fakefs-root -> realfs library reads
native seed, writes/fsync/closes/renames, real fork-child writes/wait4, native
verifies bytes. TWO serial native processes repeat over same files. SAME ELF
also TWO actual LinuxLabRuntime-entry processes over realfs root; original
repeat-start-16 retained. Both ASan/UBSan wrappers nonrecovering, static deps not
instrumented; before/after archive hashes unchanged. NOT same-app restart/Wine/
Steam depot/ownership/device/game/return proof. No active tests left running.

Namespaced iOS adapters/full App37 PASS. FINAL actual mount->do_mount and unique
Linux TLS/Wine global + GPU methods verified. Immutable private
run36/hybrid37-unsigned/Madeira.app SHA7cafbe42...d528a4, UNSIGNED/UNINSTALLED,
source .linuxlab, label iDeck Linux Lab. Signed35 and immutable35/36 preserved.
Default actual iOS runtime object compiles with shared-mount reference ABSENT.

Steam library NOT yet registered in real Steam or wired into GameFilePolicy.
Existing GameFiles_from_data addresses fakefs data, NOT new native shared source;
use explicit shared common-directory capability for eventual bridge. Dock's
Windows client login/LaunchApp is separate from Linux Steam auth. Never copy/
convert tokens or treat AppID/fixture/executable as ownership. Normal ContentView
JIT/full-init contract must be preserved; bridge remains diagnostic125.

ONE readonly current Air query still Lab23/4952/installB265FEBE (REVALIDATE).
Pending concrete combined35 + subsequent same-Lab-iteration choice unanswered;
no repeat, time/continue inference or silent substitution37. No Air input/stop/
restart/install/auth/signing this run. User live session/apps/accounts/games
preserved. Independent storage work advanced; no mere blocker restatement.

NEXT shared native capability/path mapping + actual writer/runtime handoff and
legitimate Madeira init/JIT/license flow. On actual permission, choose qualified
signed Lab artifact and run actual Air UI/close/restart, then genuine Play/game/
return. No combined binary distribution until exception scope resolved. No
STABLE_SUCCESS/scheduler unload/goal complete. Earlier notes are historical.

--- Earlier Run35 continuity ---

# Latest Run35: FULL combined app35/36; old Air session preserved; game bridge still125

Read MD Run35 and EVIDENCE.run35 FIRST. Published815ddc5, remote main2ac39be
unchanged. Run34/35 UNCOMMITTED/UNPUSHED outside weekday22-08 EST window;
check clock EACH commit/push, preserve all edits. Full Air game/return goal ACTIVE.
CLI-only normal app development; no cybersecurity/settings/lock/account operations.
Never ask Mac unlock or automate credentials/Guard/trust. No subagents/overlap.

Full actual App35 links namespaced Linux + real Wine/FEX/DXMT, separate TLS/global
current identities, CASP translation-before-mutex verified in FINAL Mach-O.
FEX/Wine sources/vendor untouched, prepared component inputs read-only. Reused
compiled payload provenance not rebuilt merely by pinned source HEAD. Initial
missing .m/uninitialized deps/global helper LDFLAGS failures corrected and logged.

Immutable run35/hybrid35-unsigned/Madeira.app SHA7a459f77...9419f. Disposable
hybrid35-air-sign copy explicitly uses SAME existing com.kuschqin.ideck.freshtest
and .JITHelper, display iDeck Linux Lab. Existing profiles cover Air/debug,
expire Nov13 UTC, exact identity matched. Signed/deep strict normal environment0,
SHA5b41400c...8410f2. NOT installed. Sandbox verify NOT_TRUSTED is environment
boundary, NOT device/Linux failure; no trust change. Profile recheck before install.

New shared LabMetalDrain + generated PINNED view tracks REAL command/main bodies;
close rejects new submissions, no completion-before-accounting, no reentrant
reopen, subsequent actual GPU wave passes. REAL HOST Metal blit/readback+3commands+
2subscribers bounded natural0/PASS; NOT Air/driver-global/storage/Wine permission.
Opt-in --metal-drain (source IDECK_LAB_METAL_DRAIN default0), Linux-only flags.
Controller RFB actual tasks -> Metal real completion -> retained boundary.
Full App36 + actual final drain methods/TLS identities verified, immutable
run35/hybrid36-unsigned/Madeira.app SHAde7db5ce...a7acaf, UNSIGNED/UNINSTALLED.
Default controller separately compiles; no full default build35 claim.

ONE readonly Air35 query still old Lab23 PID4952/installB265FEBE (REVALIDATE).
Old selected25 question superseded by materially changed pending combined35+
subsequent same-Lab iteration choice. Await actual YES to end old Lab/preserve
its data/upgrade. No reply yet: no repeated question/time/continue inference,
no silent selected-artifact substitution. No device stop/input/install/auth this
run; phone/production/Mac Allocator unchanged. Don't target stale host test PIDs.

Next on approval: recheck exact current identity/profile, choose qualified signed
Lab artifact transparently, exercise Air genuine Steam/input/normal close/restart.
Then explicit shared-game filesystem writer and actual Madeira init/JIT/legitimate
license contract; bridge remains diagnostic125. No game/return/Stability proof,
no global reset/secret transfer/FEX/Valve edit, no combined binary distribution
until converter/component exception resolved. No STABLE_SUCCESS or scheduler stop.

--- Previous Run34 continuity (historical) ---

# Latest Run34: real CASP/CoW fix + TWO HOST Steam/embedded-RFB cycles, NOT Air/game success

Read EVIDENCE.run34 and MD Run34 FIRST. Parent/last published815ddc555d7a1c3e10fdc067bf0ebf395ca0fdf7.
Run34 source UNCOMMITTED/UNPUSHED outside weekday22–08 local window; check current
clock before EACH later commit/push. Preserve these edits and all other worktrees.
Main2ac39be/vendor d141978 pristine. User additionally forbids cybersecurity work;
normal app compatibility/build/runtime only. CLI only; no Mac-unlock/security/
lock/credentials/Guard/trust automation. Full Air game/return goal ACTIVE/incomplete.

Original-engine embedded RFB test black562s: TWO actual native samples show
CASP mutex owner in CoW MM-writer wait, other CASP waiters hold MM readers.
Not the prior pre-Steam AF_UNIX ACK issue (still a separate unfixed limitation).
Minimal extracted actual helper + modeled native locks reproduces; strict v2
ASan/UBSan model passes candidate (initial recovering-UBSan shim result rejected).
REAL static ARM64 CASPAL64/fork/CLONE_VM/128-page CoW ELF also reproduces baseline
lock cycle; own bounded termination -15, not crash/cleanup. SAME ELF candidate
naturally0/0.813s with real CoW isolation/worker wait4 PASS. Host-only, not Air.

Shared casp_order_patch.py moves ONLY writable translation before global CASP
mutex; exact model/production helper byte equality checked. Copied engine archive,
original/vendor/FEX/Valve unchanged. CASP/STXP mix + existing CASP32 misalignment/
cross-page remain unqualified, no broad atomic correctness claim. Explicit
LINUX_LAB_CASP_ORDER=1 requires frontend/native logs, default0 unchanged.

Actual candidate real embedded RFB same hostPID38304/root/owner TWO visually
inspected genuine LOGIN windows -> actual RFB close -> actual decode/input group
completion BEFORE signal restore -> backend0/guest0/DORMANT/reaped7 EACH -> owner
joined -> NATURAL process0/453.777s total incl operator delay. No auth submitted.
90/240s native samples lack original cycle. ALL host tests TERMINAL; no stalePID.
First candidate observer went missing/PID35003 absent/no receipt: UNKNOWN cause,
not crash/fix proof; detached bounded later observer preserved actual final result.

Full unsigned iOS feature34/default34 builds + FINAL actual instruction order
and marker/hidden methods verified. Feature SHA87480606...b4a9 immutable private
run34/feature34-unsigned/LinuxLab.app; UNSIGNED/UNINSTALLED, source .linuxlab ID.
Default excludes marker/retained UI and preserves old engine order. Gate3 refuses
before writes. No new profiles/device action. Never claim build proves Air/game.

NEXT advance qualified components into correctly namespaced COMBINED Linux+
Madeira target and explicit GPU/storage/runtime boundaries; genuine game handoff/
return remains diagnostic125, NOT executed. No permission inferred from DORMANT,
no global/consumed/counter reset or auth-secret copying. Kernel/root retained,
4096 cumulative handle capacity/profiling-off remain. Resolve converter/component
license scope before binary distribution. No Bluetooth/Metal/game stability proof.

ONE Air readonly query still23/4952/B265FEBE. Preserve live user session and
console29282; revalidate identity before touching it. Pending SELECTED25 upgrade
choice unanswered: no repeat/inferred consent/substitution34. No Air restart/
install/input/login or phone data changes. No STABLE_SUCCESS/scheduler unload.

--- Earlier Run33 context ---

# Latest Run33: retained-owner integration built; final transport Steam cycle NOT verified

Read EVIDENCE.run33 and MD Run33 FIRST; parent3d56582, actual publication via Git.
Source/default app/main/other worktrees/vendor/FEX/Valve preserved. CLI ONLY;
never Mac-unlock/credentials/Guard/trust/lock automation. Full Air goal incomplete.

Before mandatory embedded transport callback, actual dedicated-pthread C backend
TWO genuine login render/normal-close/restart cycles NATURAL0, both reaped8;
734.527s includes manual delays, NOT startup performance. Exact OLD source snapshot
run33/pre-transport-boundary-source/hashes.json. Does NOT validate current API.

CURRENT API binds same owner/root/transport. Requires actual child/native joins/
reap then embedded RFB completion BEFORE signal restore. Failure poisons; original
one-shot consumed/stage NOT reset. App process-lifetime NSThread/NSCondition mailbox,
wave-guarded display, restart only DORMANT+drained. Profiling refused;4096 cumulative
child capacity; no owner rebinding. GPU/Metal/storage full barrier UNVERIFIED;
never infer Wine permission from this boundary. Bridge still125/no game.

Current host test900s bootstrap stall, Steam/callback NOT reached. x11vnc native
sys_connect waits managed peer ack; no later Xvfb thread in sample, PID6 exits0
~23.873s but exact cause/role not proved. Minimal real ARM64 ELF confirms early
accept+roundtrip0, late accept cannot get beyond connect5s; intentional own kill.
No socket runtime patch. Peer refs/SCM_RIGHTS/credentials require a real ownership
solution, not deleting ACK. Native path root-length theory unsupported by source.
Second current binary observer session expired: original PID absent, NO terminal
receipt. Never call a crash/clean close. Copied old Steam/x11vnc logs predate start,
excluded in run33/owner-boundary-observed/reconciliation.json. All run33 host tests
now terminal/identity absent; no stale PID target or live host test assumed.

Full current feature33/default33 Xcode + final markers/resource11/syntax pass.
Feature bceaf5ce...cdbbd6 immutable run33/feature33-boundary-unsigned/LinuxLab.app,
UNSIGNED/UNINSTALLED. Generic Xcode output DEFAULT. No current Air UI/game proof.

NEXT discriminate actual Xvfb process termination/pre-accept lifetime; minimal
pending-connect/SCM_RIGHTS/credentials/cancellation controls before copied patch.
Then complete CURRENT callback+embedded viewer cycle, verified namespaced
Linux/Madeira combined linkage and real licensed game/return. Do not restart
completed audit or call old source success current validation.

ONE Air query observed23/4952/B265FEBE. Preserve live session/console29282, revalidate
identity before any action. Pending SELECTED25 upgrade choice still unanswered;
no inferred consent/substitution33. No Air input/stop/restart/install/auth. No
STABLE_SUCCESS/scheduler unload. Publish -s scoped experiment only in allowed hours.

--- Earlier Run32 context ---

# Latest Run32: opt-in native RFB completion integrated/final-linked App, NOT Air tested

Read EVIDENCE.run32 and MD Run32 first; parentf6c1bcdb1bd4d405cccac360027112e6f8b65f2f.
Current git gives published revision/status. Main2ac39be/vendor d141978 pristine,
origin kuscholar/iDeck/experiment/linux-steam-madeira-ipad only.

Prior31 HOST TWO genuine Steam login render/normal-close/restart cycles NATURAL0
verified, no auth/game/device success.32 adds missing native viewer boundary:
explicit LINUX_LAB_RFB_LIFETIME=1 generated pinned-source copy, recursive admission
lock + actual GCD decoder/input group. Stop closes starts/input then main-queue
completion after task bodies/callbacks return. Default includes original source.
Feature controller closes input/frame admission at guest return, refuses late
client start, drops queued frames/clears CPU frame after completion. GPU in-flight
UNVERIFIED explicitly; not Linux/Wine/game quiescence. No App restart enabled.

Four actual host socket/callback-held controls ASan/UBSan PASS, default RFB
instructions identical. Full feature32 FINAL methods+GPUmarker verified, SHA
1945259685fb50f4d932bc3b7e581f60f621804cab1166fd2193ea04b15a08b2, immutable
private run32/feature32-unsigned/LinuxLab.app. Full default32 excludes new methods/
marker/resources; current generic run32/xcode products DEFAULT.32 UNSIGNED/
UNINSTALLED/device UI untested. Backend archives reused29, so run31 joined waves
NOT included. No full Metal/GPU/storage/captured-object lifetime guarantee.

NEXT real App integration: dedicated serial native session owner retains root,
actual child/native joins+signal leases per31, coordinates native RFB completion
and GPU/storage boundary. Do not reset consumed/global/counters or start Wine
from task counts. Then namespaced exact Linux adapters + verified Madeira link
and genuine Steam Play/owned game/return. Bridge125 still diagnostic.

ONE current readonly Air23/4952/B265FEBE still alive. Preserve live session/
console29282 noCtrlC, pending25 choice unresolved; no repeat/infer/substitute32.
No device input/stop/upgrade/restart/login. CLI only, no Macunlock/lock/security/
credential/Guard/Valve/FEX modifications. No stable sentinel/unload; full Air
Library/BPM/input + licensed Madeira game/return/repeated stability goal ACTIVE.

--- Earlier Run31 context ---

# Latest Run31: TWO genuine HOST Steam login render/close/restart cycles pass

Read EVIDENCE.run31 and MD Run31 first. Baseline35ff61c + exact run30/31 dirty
source snapshots; check Git for current revision. Branch experiment/linux-steam-
madeira-ipad/origin kuscholar/iDeck, main2ac39be/vendor d141978 preserved.

Actual same native PID/root/kernel first login window -> close -> real all
tracked joins -> reap8/0left -> signals restored -> explicit reacquisition ->
new init child -> second REAL login window -> close -> joins -> reap7/0left ->
signals restored -> NATURAL native0,239.934s total incl observations/manualclose.
No credentials/Guard/submit. Private run31 QR/screenshots/logs stay out of Git.
Initial black frames resolved; cannot call them a hang/causal failure. First
sandbox attempt Xvfb bind/connect EPERM pre-Steam, native5; authorized SAME
binary displays both. Both old owned host children TERMINAL, no stale PID use.

--worker-waves requires --join-workers; owner can recreate reaper ONLY after
actual finish joins, sealed/zeroactive/noerror. No history/generation/error reset
or provider-global revival. DefaultENOTSUP. Profiler OFF and remains lifetime-
closed.20 real worker/reaper waves + all10 old regressions ASan/UBSan PASS.
iOS object compile only, NOT new App/sign/install/Air/Wine/game evidence.
Run30 FOUR real ELF waves also pass, one-shot runtime API remains EBUSY.

NEXT explicit isolated App retained-frontend lifecycle: native viewer close,
storage-writer/signal ownership then correctly namespaced Linux adapters and
verified Madeira linkage. Actual Steam Play -> licensed game -> return still
absent, bridge125. No reset consumed/counters/remount/kernel blanket workaround.
Cumulative4096 child handles and timer-create semantics remain limitations.
No authenticated Library/BPM repeat/stability/game/Bluetooth qualification.

ONE readonly Air still23/4952/B265FEBE. Preserve live session/console29282 no
CtrlC; pending selected25 choice unresolved, don't repeat/infer/substitute newer
candidate. No Air input/stop/upgrade/restart/account action. CLI only, no Macunlock
requests/locks/security/trust/password/Guard/Valve/FEX edits. Preserve all main/
other worktrees/data. Goal ACTIVE, no STABLE_SUCCESS/scheduler unload. Publish
only scoped signed-off checkpoints in local allowed hours; git gives publication.

--- Earlier Run30 context ---

# Latest Run30: retained-root FOUR real ELF waves HOST verified, no Steam/device cycle

Read EVIDENCE.run30 and latest MD first. Parent35ff61c0ec5f59f1fe8d6299a5694af7452ff92b
actually pushed earlier; new30 edits UNCOMMITTED outside weekday22–08 at20:01EST
Nov10. Main2ac39be/origin kuscholar/iDeck/experiment branch verified, vendor
d141978 pristine; preserve all unrelated worktrees/installations/data.

Explicit --guest-waves requires --join-guests. Owner-only reopen after sealed/
actual full joins, no error/join underway, no counter/handle reset. Default
ENOTSUP; cumulative4096 capacity remains (2-slot unit exhausts ENOSPC). Real
TLS/body-complete-but-unjoined refuses; foreign owner refuses. Not a full Linux
restart/handoff certificate. No App target enabled.

Actual HOST same root/init/mm FOUR ARM64 ELF waves,16 separate PASS rows each,
status0, child slots/joins2/4/6/8, complete PID2+ reap each. Original runtime
one-shot API STILL EBUSY. ASan/UBSan own controls and all4 prior guest-join
regressions pass; iOS registry object compile only. No actual Steam/CEF or
Madeira game/return/device validation, no memory-reclamation claim. New helper
keeps native init/root rather than reinitializing/remounting/resetting consumed.
Private run30 has exact source/binary/regression/per-wave hashes.

NEXT actual genuine Steam close then new frontend child in retained private
fakefs root. Must address auxiliary-worker restart/epochs, native signal owner
reacquisition, stale sockets/viewer and SQLite/storage writers before game.
Profiler off first discriminator (run28 profile-on setup stalled). No blindly
reopening/resetting resource registries or starting Wine from zero counters.

ONE readonly Air check still4952/B265FEBE. Preserve Lab23, pending selected25
choice/console29282 noCtrlC; no input/stop/install/restart/account actions. CLI
only, no Macunlock/security/trust/credentials/Guard automation. No completion
sentinel/unload; full genuine Air Steam -> licensed Madeira game -> reliable
return/repeat remains required, diagnostic bridge still125, no game.

--- Earlier Run29 context ---

# Latest Run29: actual kernel/Wine symbol collision isolated; no new App/device test

Read EVIDENCE.run29, MD Run28/29 and private run28/29 FIRST. Baseline parent
f962015e551bd95fedb60bcf284270f3c6445a47 already pushed; use fresh Git/remote
state for current checkpoint. Branch experiment/linux-steam-madeira-ipad,
origin kuscholar/iDeck, main2ac39be unchanged, vendor d141978 pristine.

Run28 genuine HOST Steam login visually confirmed, normal close only (2 mouse
packets, NO authentication), real guest/native joins, init wait4 reaped7/0left,
signal restoration, NATURAL native0. Both old own host PIDs TERMINAL, don't reuse.
Profile-on setup stalled in VNC connect; no-profile reached Steam, one A/B pair
not sole-cause proof. Residual footprint248202320/resident706707456, pages0/
blocks0/tables1; NOT complete reclamation/reset. Native init retained mm source-
consistent; actual run28 didn't record per-mm identity. Raw QR/logs private.

Run29 actual ordinary iOS kernel+prepared wineserver -r pair fails duplicate
_current. New opt-in assembler label isolates Linux TLS _ideck_linux_current.
NO token macro/ObjC selector/Wine/FEX/Valve/default target edits. All Linux task
consumers require same forced header; Linux-only audit rejects forgotten adapter.
Actual fresh host-v4+iOS-v5 archives,16 real ARM64 ELF checks/two TLS threads/
regular-global fixture/ObjC selector pass. ASan/UBSan own harness/adapters only.
Actual namespaced pair -r passes distinct globals; engine/system refs unresolved,
NOT final App/Wine runtime/device. Twelve prepared native archives no observed
overlap; pairing archive nm incomplete, not comprehensive. Wine source pin clean
9129e968 matches, prepared archive provenance still not rebuilt/verified.
Configure platforms SEQUENTIALLY: pinned BSD mktemp probe's fixed /tmp names
collide under parallel setup; ios-v4 failure preserved, fresh ios-v5 passed.
Initial assembler/asm-label/dirfd setup errors documented, not counted success.

ONE fresh readonly Air check still identifies Lab23 PID4952/executableB265FEBE.
No Air input/stop/install/restart/auth, no new App candidate deployed. Prior
selected25 retirement choice PENDING; don't repeat, infer consent or substitute.
Preserve console29282 noCtrlC. Old capped logs/updater4942 not current exit proof.
CLI only, no Macunlock requests/security/trust/password/Guard automation.

NEXT real implementation: qualify native retained-root frontend lifecycle,
viewer/storage/mapping/signal ownership and exact Linux-only adapter archive
linked with verified Madeira resources in isolated app. Potential dormant-kernel
new-init-child restart is only a hypothesis; don't reset consumed/counters or
reinitialize root from zero entries. Registry epochs and return not implemented.
Do not enable joined prototypes by compilation alone. Bridge125 still NO GAME.
Full genuine Air Library/BPM/input -> licensed Madeira game -> reliable return/
repeat ACTIVE. No STABLE_SUCCESS/unload/goal completion; preserve all worktrees,
working apps/accounts/games/saves. Raw packages/Valve/profiles/log/auth stay out
of Git. Publish scoped signed-off checkpoints only during allowed local hours.

--- Earlier Run27 context (historical) ---

# Latest Run27: real profiler stop/join/buffer release HOST verified, not app linked

Read EVIDENCE.run27/latest MD/private run27/profile-controls FIRST. Baseline
source5cfce802f932f7fad6fc43e1d25efaa28552bafc and documentation
208e65441a97696173b6fdcc0342887816a5b57e are actually pushed/read back.
Parent208e654 is test-time source parent; use git for current revision/status.

Builder --stop-profile requires --join-workers. Native owner only, actual
guest-exited + child joins + sealed worker admission before stop; profiler
checks outside locks, final dump then returns. Release requires actual full
tracked worker/reaper joins and no TLB producers BEFORE disable/free. No new
cancel/reset/revival/default/FEX/Valve change or Wine permission.

Actual3 ASan/UBSan host cases PASS: enabled133samples/0dropped, disabled ordinary16,
producer-leak cleanup EBUSY until explicit unregister. Real joins completed,
file stable, logical retained allocations6291456->0 (NOT physical RSS/iPad).
Wrong-owner/early/open-admission refused, idempotent release/no init revival.
Default4 generated sources/counter text identical Run26, old feature29 MachO
1693d0... unchanged/no new APIs. iOS arm64 ARCHIVE compile/symbols only, NOT
new final app linkage/sign/install/device execution. Raw profiles/PCs private.

NEXT implement/qualify actual genuine unauthenticated Steam/CEF graceful exit
with joined guests/native workers and profile release, then real signal/root/
memory/storage boundaries toward Madeira. No actual licensed game/return;
bridge125. Child registry still4096 cumulative, no restart epochs, failed pre-
exec cleanup lacks returned-call receipt: don't call phase6 safe. No complete
Linux teardown or STABLE_SUCCESS/unload. Full Air UI+game+return goal ACTIVE.

One fresh readonly Air old23/4952+B265FEBE alive; no device input/stop/install/
restart/auth. Prior one-time25 retirement choice PENDING; don't repeat/infer
continue/time consent or substitute29. Preserve console29282 noCtrlC, native
viewer and all auth/games/saves. Capped kernel/updater4942 status not current
exit proof. Lab29 unsigned, host-qualified v3 trace only;28 tracer obsolete.
CLI only/no Macunlock/security/credentials/Guard/Valve/FEX changes. Main2ac39be
and all other worktrees/installations preserved.

--- Historical Run26 publication context ---

# Current published source checkpoint: 5cfce802f932f7fad6fc43e1d25efaa28552bafc

Source/docs checkpoint signed off and remote-readback verified22:02EST Nov9.
Branch experiment/linux-steam-madeira-ipad, origin kuscholar/iDeck. Main still
2ac39beff91251d36f3ad6331d3f8402b3c10e18. Per-run parent82b7861+dirty fields below
refer to exact test-time snapshots; use git status/rev-parse for current state.
No binary/auth/rootfs/profile/Valve payload published, no Air installation or
restart. Read Run26 evidence next. NEXT real implementation is explicit
cooperative profiler stop and actual provider join/resource cleanup; preserve
the unanswered25 retirement choice and active Air session. Full genuine Air
Library/BPM/input, licensed Madeira game/return and repeated stability remain
required. No STABLE_SUCCESS/unload or goal completion.

--- Run26 test-time evidence before publication ---

# Latest Run26: native auxiliary join/TLS ownership verified on HOST, not app linked

Read EVIDENCE.run26/latest MD and private run26/full-controls-v2 FIRST. Previous
turn PROGRESS: genuine host Steam login and fixed input/erase, not Air/game.
New NativeWorkerJoins.c/h + builder --join-workers: managed joinable timer/
profile/TTY via owned reaper, forwarders retain original join owner captured
before join. Slots reused ONLY after actual pthread_join including TLS; seal
closes starts, finish joins reaper, sticky errors cannot certify completion.
No new cancel/detach/reset. One native owner/lifetime, not runtime permission.

10 ASan/UBSan controls PASS: held TLS with counter0 (including actual pinned
timer), original native-forwarder owner/return37 through real ARM64 ELF,8slots
reused10008joins/4producers,1000 creation-fail rollback, failed-join no false
quiescence, real timer/TTY/ordinary16. TTY calls source's EXISTING private-pipe
cleanup cancel; no user-terminal/device input.7 old default regressions pass.
Default4 provider sources byte-identical and counter text identical/no registry
reference. New iOS arm64 OBJECT compile only; NOT app/Xcode-linked, installed,
Air-tested, complete Linux stop or game. Feature29 actual MachO1693d0... intact,
registry symbols absent. Full source/hashes/builds/tests private run26.
Three actual TSan TLS/owner/concurrent-reuse controls also pass; specific HOST-
injection iOS compile refusal verified. Not blanket LinuxRunner race coverage.

IMPORTANT next gate: actual old profiler test STILL shows sampler1 after guest
end; source loop infinite. Implement explicit cooperative profiler stop in
copied archive then real provider test; don't fake quiescence or call counts
TLS completion. Child-guest join prototype separately still4096 cumulative
identities/unlinked. Native worker active slots now reuse; no frontend epoch/
reset/resume API. Timer original ignores create failure; qualify before app
enablement. Need real guest shutdown, signals/storage/global cleanup, legitimate
Madeira linkage/auth/game/return. Bridge125 NO GAME, no success sentinel/unload.

One fresh readonly Air query old23/4952+B265FEBE alive. No device input/stop/
install/restart/auth. Prior one-time25 retirement question PENDING, don't repeat
or infer continue/time approval/substitute29; console29282 noCtrlC. Old caplog/
updater4942 status not current exit. Safe session end/explicit reply before
selected25 health/discard, then separately selected v3 window trace if needed.
Lab29 unsigned, host-qualified probe only;28 probe obsolete after actual v2
loader defect (not earlier Air white root cause). Preserve raw QR/screenshots.
HEAD82b7861/experiment branch, origin kuscholar/iDeck, main2ac39be/other worktrees
preserved. Source uncommitted outside weekday22–08. CLI only, no Macunlock/
credentials/Guard/security/FEX/Valve changes. Goal ACTIVE/full UI+game+return.

--- Historical Run25 context ---

# Latest Run25: real HOST Steam login/input confirmed; diagnostic v3, Lab29 unsigned

Read EVIDENCE.run25/latest MD and private interactive-host/evidence.json FIRST.
Prior28 build success was NOT Steam proof. Actual v2 host Steam ended125; real
RTLD_LOCAL plugin control distinguishes plain0/traced125, global0/0. This is a
PROBE defect, NOT earlier Air white-screen root cause. Do NOT deploy28 tracer.
V3 uses RTLD_NEXT then fixed-soname NOW|NOLOAD|LOCAL existing libX11 reference;
no new DSO/global promotion/Valve/FEX/GPU/assertion changes. One handle retained
changes Xlib unload lifetime; not transparent all-loader/unload qualification.
Numeric phase2 routes1/2 or fatal-125, same bounded partial stderr coverage.

All4 scope cases now0 with local plugin visibility preserved; real Xlib normal/
fork/cap plain-v-traced reports/pixels match. Actual VFS8modes/23checks pass.
ELF SHA b24c76df23870634a81e29ef893f4359d71234f3fc86b2db4600d44bb1a6b432.
Genuine HOST Steam login visibly rendered twice; SECOND held-live session shows
fixed ideck-test insertion then Backspace-clear, each22packets and separately
inspected screenshot. No real account/password/Guard/submit. Raw QR screenshots
are PRIVATE, never publish.60 parsed actual Steam/webhelper rows/4guestPIDs;
zero OBSERVED false attributes, not complete coverage/no-fault proof.

First observer ended220s, then native/port absent; initial zero-packet input
probe INVALID as Steam input failure, disappearance cause unproven. New owned
parent-held observer keeps runtime alive for UI, then intentionally stops ONLY
its own child on stop-request. Second host44845 ended by owner SIGTERM at242.386s,
not crash/clean-teardown/Wine-handoff proof. No current HOST test remains.

Source29 explicit flag+launch argument uses path/markerV3. Full feature/default
iOS builds and FINAL linked symbols/resource hashes pass; current generic xcode
products DEFAULT29, immutable feature run25/lab29-unsigned. Feature MachO1693d0...
Lab29 NOT SIGNED/INSTALLED/DEVICE TESTED. No ordinary baseline delta. Full evidence
source/artifact hashes private run25; source uncommitted outside weekday22–08.

ONE Air readonly query confirms old23/4952+B265FEBE; preserve current session.
No Air input/stop/upgrade/account action. Prior one-time25 retirement question
PENDING; don't repeat/infer continue/time consent or substitute29. Console29282
noCtrlC. Capped kernel/updater4942 status not current exit. After actual end/
explicit approval qualify selected25 health/discard A/B; v3 trace only separately
selected next. JoinableGuests still unlinked partial child prototype, not full
native stop/TLS/auxiliary-worker/signal/storage reset. Need legitimate Madeira
linkage/auth/game/return; bridge125 NO GAME. No STABLE_SUCCESS or scheduler unload.
CLI only, no Macunlock/security/credentials/Valve/FEX changes, goal ACTIVE.
Main/other worktrees/accounts/games/saves preserved; origin kuscholar/iDeck
branch experiment/linux-steam-madeira-ipad HEAD82b7861, remote main2ac39be.

--- Historical Run24 context ---

# Latest Run24: explicit Xlib diagnostic Lab28 signed, NOT installed

Read EVIDENCE.run24 and latest MD first. Full feature/default Xcode, actual
VFS8modes/23checks, resource11cases, ordinary byte-identical launcher and host
ARM64/protocol regressions pass. Diagnostic build flag AND explicit argument
linux-steam-window-trace required. Ordinary frontend is unchanged even in the
capable build. Preboot trusted bundle ELF -> /ideck-diagnostics, no live injection.
Actual Steam namespace/trace activation is UNVERIFIED. Final linked/source/sign
hashes in run24; signed28 immutable run6/signed-lab28. Current xcode products
DEFAULT28, do not mistake them for feature candidate. Discard/gameFile off in28.

Run22 diagnostic stub collided with preexisting glibc-start.S; restored original
EXACT HEAD, new xlib-glibc-start.S; three rebuilt controls byte-identical run23.
No runtime/helper rewrite or historical artifact modification.

Air23/4952+B265FEBE preserved and last readonly identity still alive. Current
white-screen/root cause/stability unresolved. Prior one-time retirement25 async
question PENDING, don't repeat or infer consent/substitute28. No console29282
CtrlC. Capped old log/updater4942 status not current exit proof. Next independent
step: real unauthenticated host Steam loading/trace, then safe selected Air
experiment only after actual end/absence or explicit reply. Bridge125 NO GAME;
full native stop/storage/signals/legitimate Madeira execution/return still open.
CLI only, preserve all auth/games/saves/main/vendor/FEX/Valve; no Macunlock.
HEAD82b7861, origin kuscholar/iDeck; outside weekday22–08 UNCOMMITTED/UNPUSHED.
Goal ACTIVE, no STABLE_SUCCESS/unload.

--- Historical Run23 context ---

# Latest Run23: v2 numeric Xlib lifetime tracer host-verified, NOT app integrated

READ EVIDENCE.run23/latestMD FIRST. Prior22 PROGRESS: real wire+libX11 pixels
matched; Air23 stillWHITE after one F1 menu key. No visible UI response/focus
proof. No current-session stop/restart/upgrade/auth action. Exact23/4952 B265FEBE
was reverified22 and again18:06EST23; no stop/upgrade. Current library/game/stability remain unverified/failed.

Own ARM64 .so wraps ONLY XGetWindowAttributes/XDestroyWindow, real argument/
output/return forwarding and errno save/restore by source. No XError handler,
assertion/mapping/GPU/Valve/FEX patch, credentials or new native thread. V2 logs
fixed numeric PID/TID/call/window/op/phase/result/time to existing PRIVATE stderr;
no owned fd/lock. Explicit512KiB budget/omission marker; forkcopies/CLONEVMshares,
so cap/short/interleaved/absent rows never prove completeness or no failure.
RTLD_NEXT/LD_PRELOAD propagation in real Steam NOT yet established; missing real
symbol exits diagnostic125, never fabricates Xlib success. Not for live injection.

Four actual HOST ARM64/distro-glibc/libX11/Xvfb controls PASS: normal/stress plain
versus traced complete reports/pixels EXACTLY match. Warmup root query BEFORE
fork then independent clients. Normal130/128 rows;33/32 get-success,16 expected
get-failure and16 destroy each. Stress adds4000 successful queries EACH, caps
parent524122/child523976 numeric bytes, then completes same pixels/counts.
FNV hashes4133264837/658546117. Build script reproduces exact3 artifact hashes.
V2so SHA333057792adbb13e10a88219b09d422a2e5fa356ef860b35f2e88a4a74d56c19.
Private run23/compiled-v2-source,v2-controls/evidence.json,repro-build. Own source
only. V1 passed tests but file-handle ownership design superseded BEFORE appuse;
old sources/artifacts preserved, NOT actual Steam failure. run22 old5 sourcefiles
reconstructed aftertests, verified against ALL recorded hashes, snapshot private.

NOT in project/app/Steam launcher/signed25–27/device root; no new iOS build or
install this run. NEXT actual implementation: explicit defaultOFF build+runtime
opt-in, signed-bundle ELF payload, guarded preboot VFS installer, fixed Steamchild
LD_PRELOAD environment. Prove final linkage/resource/defaultabsence, then actual
selected Steam processes/events (not just load markers). Keep ordinary path and
all auth/game/save/production state intact; no blanket injection into live23.

Prior one-time retirement25 question remains PENDING. Don't repeat or infer
consent from continue/time. Preserve current23/CLIconsole29282 noCtrlC; capped
kernel/old updater4942 status not current exit. After real end/absence/explicit
approval, qualify chosen25 health/discard A/B first; don't silently substitute.
Then native policy27/actual SteamPlay, complete native stop/storage/signals and
legitimate Madeira game/return. JoinableGuests21 only unlinked childprototype,
not full teardown/reset. Bridge125 NO GAME. No success or scheduler unload.

HEAD82b7861, origin kuscholar/iDeck experimental worktree; main/other worktrees/
apps/account/games/saves/vendor preserved. Outside weekday22–08, edits uncommitted.
CLI only, no Macunlock/security/credentials/Guard or Valve/FEX modifications.
Goal ACTIVE, no GO/completion. Raw ELF/distro/Valve/log/profile/auth stays private.

--- Historical Run22 context ---

# Latest Run22: raw X11 AND real Xlib window/pixel controls PASS; Air still WHITE

READ EVIDENCE.run22/latestMD FIRST. Prior21 was PROGRESS (joins/TLS + white frame).
Exact Air23/4952+B265FEBE reverified before test. One F1 menu press/release after
host controls ended,2 packets written; actual native screenshot remains WHITE.
No visible UI response/focus qualification. Legacy nav utility's hardcoded
visually-verified scope is WRONG for this run; ignore it, use screenshots.
No exit/restart/install/auth/Guard/data-transfer or active-session termination.

New real ARM64 diagnostics: raw core-X11 wire versus distro libX11/glibc through
own glibc-start.S, two process/client connections each16 windows on own Xvfb:97.
Both PASS with identical counts and per-client FNV pixel hashes4133264837 /
658546117: each control32 windows,64 live attributes,32 expected destroyed-window
BadWindow errors,32 images/65,536 pixel comparisons. Host durations2.994/3.622s,
NOT iPad performance. NEW private unauthenticated root clones, VFS-installed own
ELFs, no Steam/auth launch or host SQL metadata fabrication. Original root/Air
unchanged. First sandboxed server bind failed/setup placeholder+ENOENT; fresh
normal socket access in a NEW root passed. Do NOT call initial failure Air fault.

Rejects broad basic-X11/live-window/Xlib/pixel failure as sufficient HOST cause,
NOT Chrome ownership race/copied-archive pressure/sharedmem/GPU/common decoder/
Air-specific causes. Steam's logged XGetWindowAttributes failure may be stale
window or another failure; no root-cause/fix claim. Diagnostics NOT in app, no
new app build/install. Exact source/ELF/lib/package/log/screenshot hashes private
run22 and EVIDENCE. Source only; no Valve/game/auth/profile binary in Git.

Prior retirement25 question still pending; do not repeat or infer permission from
continue/time. Current23 kernel log capped, updater4942 status not current.
Preserve CLIconsole29282 noCtrlC. After genuine end/absence/explicit approval,
bounded25 health/discard A/B then actual SteamPlay policy27; don't silently
substitute27 for pending25 choice. Signed25/26/27 unchanged/uninstalled.

21 JoinableGuests remains UNLINKED prototype, only child pthreads/TLS and4096
cumulative nonrecycled slots. Auxiliary workers, signal/global/mount cleanup,
storage lease and legitimate Madeira/Windows Steam auth remain open. No Wine
permission/reset certificate from zero counts/joined children. Bridge125 NO GAME.
No stable Library/BPM, licensed game/return, full app/control qualification yet.

Branch experiment/linux-steam-madeira-ipad HEAD82b7861; primary/main and other
worktrees/apps preserved. Vendor d1419782 pristine. Source UNCOMMITTED outside
weekday22–08. CLI only, no Macunlock/security/FEX/Valve/credentials changes.
Goal ACTIVE; no STABLE_SUCCESS/unload. Next concrete work: narrow Xlib lifetime
instrumentation/current long-session pressure discriminator and complete native
handoff; keep full UI+game/return goal, not passing test subsets as completion.

--- Historical Run21 context ---

# Latest Run21: actual Air white-screen; child-native join prototype verified on HOST

READ EVIDENCE.run21, white-screen-evidence.json private summary and latestMD FIRST.
Previous turn PROGRESS (file policy/feature-default27/signed candidates). Current
Air23/4952+B265FEBE exact identity reverified17:19EST. Fresh native screenshot AND
independent passive shared RFB frame are WHITE with cursor. Steam logs continue
updating; exact source XGetWindowAttributes failed for window at21:23. Not proven
original cause/death; may be stale windows/commondecoder/server/rendering. Broad
crash word counts are INVALID as crash events, rejected. No input/auth/Guard,
stop/upgrade/restart; viewer preserved, no pairing operation. Private run21.

UNLINKED JoinableGuests.c/h plus --join-guests copied task-archive option:
tracked JOINABLE child pthreads, seal creations under mutex, native owner and
actual joins include TLS completion. Four ASan/UBSan HOST controls PASS: actual
TLS held after entry return/join waits;1000 native creation failures no handle
leak; ordinary ARM64 ELF16 with2registered/2joined; real orphan join waits2011ms,
late marker then exists,1registered/1joined. Child ended naturally, no signal.
Default generated task.c byte-identical prior default;3 existing lifetime modes
PASS, ordinary16 included. iOS arm64 OBJECT compiles only; not an app/device test.

NOT full Linux teardown: timer/profile/TTY/forwarder TLS/ownership, mappings,
global mounts/signals, writers/storage lease still open. Registry cumulative4096
slots not recycled, so NOT ready for long Steam lifetimes. No cancellation,
detach/reset, timeout workaround or Wine permission. Source27 app snapshot
predates this UNLINKED generator option. Signed27 unchanged/uninstalled, as25/26.

Pending prior ONE async question: may retire only live23 and install25? No reply.
Don't repeat or infer approval from continue/time. Capped kernel/old updater4942
status doNOT prove current exit; CLIconsole29282 noCtrlC. After actual end/absence
or explicit approval, qualify25 health/discard A/B first. Pending choice is25,
don't silently substitute27. Then actual SteamPlay native policy request27 and
full lifecycle/storage/legitimate Madeira launch/return. Bridge125 still no game.

Remote main2ac39be/experiment82b7861 reverified17:23EST. Vendor d1419782 pristine,
primary/other worktrees/apps/accounts/games/saves unchanged. Source UNCOMMITTED
outside local weekday22–08. CLI only, no Macunlock/security/credential/Valve/FEX
change. Goal ACTIVE; no STABLE_SUCCESS/scheduler unload. Independent next work:
auxiliary native worker joins/stop ownership and current X11 failure discriminator,
not more repeated build-only claims or assertion suppression.

--- Historical Run20 context ---

# Latest Run20: signed27 ready; native file policy host-verified; live23 preserved

READ EVIDENCE.run20 and latestMD FIRST. Prior turn was PROGRESS (health25, real
library-path parser). This run adds native file capability/policy integration,
48 ASan/UBSan controls,3 actual host ARM64 helper/bridge+health controls,7 logging
modes/ordinary16/protocol and6 resource-phase cases PASS. Diagnostic125 still
NO GAME. No actual Steam Play, ownership/Wine/game/return/stability proof.

One read-only CoreDevice query revalidates exactAir23/4952 executable B265FEBE-
DE84-4F31-AB6A-235C8BF6F8F8. No device input/stop/upgrade/restart/data/auth action.
Prior async question to end only this experiment and install signed25 PENDING.
Do not repeat or infer consent from continue/time. Current cappedlog and updater
4942's status are not fresh exit evidence. Preserve CLIconsole29282, noCtrlC.

27 has explicit LINUX_LAB_GAME_FILE_POLICY=1 (requires compat/frontend/nativeLog).
Registers trusted native LinuxSteamRootFS/data fd before guest, follows only two
fixed common roots, refuses native symlinks/nonregular/aliases/unsupportedPE.
Files are read-only, metadata/path revalidation NOT an atomic freeze/license.
Only counts/AppID/errno/library/machine in atomic health; game_launched=false.
No shell/Wine launch, arbitraryroot, credentials/args/path logging. Still one
native lifetime; full stop/writer lease/signals/TLS and Madeira auth needed.

Default26 resource audit FAILED despite compiled default success: helper was
always copied. Fixed Xcode phase now explicit-opt-in; removes only3 generated
files on reuse, preserves unknown files. Source bumped27; full default27 excludes
all experimental policy/health/discard symbols/markers AND tool resource. Full
feature27 linked marker/symbol/resource hashes and exact Air/profile deep-sign
PASS. Signed27 SHA c4336e4ff9c08bd25215d4624a4e2d0333c59fd7c0e7742f467887896e549cde.
Private run20/compiled27-source, lab27-unsigned, final-linked27.json; disposable
run6/signed-lab27/LinuxLab.app. 25/26 preserved; NONE newly installed. Current
xcode output FEATURE27. Pending user choice concerns25, don't silently substitute27.

Actual UI baseline remains genuine user-auth LinuxBPM/Library40 in16/17, with
severe latency/memory pressure. Air policy/discard/health25–27 untested. Native
file parser is conservative ASCII/.exe/singlylinked; no full PE verification or
Steamworks licensing. Linux login is not Windows Dock login; never transfersecrets.

HEAD/remoteexperiment82b7861, remotemain2ac39be reverified unchanged; source edits
UNCOMMITTED outside local weekday22–08 window. Vendor/LinuxRunner d1419782 pristine,
no FEX/Valve/primary/security/lock changes or Macunlock request. Goal ACTIVE, no
STABLE_SUCCESS/unload. Next after genuine23 end/approved retirement: bounded25
health/discard memory+UI A/B, then actual SteamPlay policy request27, then full
native shutdown/storage lease and legitimate Madeira game/return. Continue
independent safe implementation while current user session is preserved.

--- Historical Run19 context ---

# Latest Run19: signed25 ready, active-session approval PENDING; source26 parser prepared

READ EVIDENCE.run19 and latestMD FIRST. Exact Air23/4952/executable B265FEBE-
DE84-4F31-AB6A-235C8BF6F8F8 verified09:46EST, screen genuineAway. Kernel log is
CAPPED; old result10752/zero entries belongs updater4942. No current normal exit
proof. Preserve this live session/auth/games/saves. CLIconsole29282, noCtrlC.

ASKED ONCE via async question: may end this specific active experimental session
and install concrete signedLab25, because user prohibits restarting active tests.
Reply PENDING. Do not repeat or infer approval from time. If user approves, verify
current exact identity first; only that Lab process may end. No other app, logout,
erasure, security/lock operation or Macunlock request. If current actually ends,
fresh authoritative absence/completion can allow already-authorized isolated
upgrade; never use stale updater result, capped absence or observer timeout.

25 adds current session-specific atomic health JSON in NativeDiagnostics,
health_file in receipt. Updates every10s even after append4MiB cap; PID/build/
native_log+sequence/time+phase+limited counts+self CPU/footprint. Schema2 result
reports now carry identity too. Counts0/initial-returned doNOT grant full cleanup/
Wine permission; missing/stale health is not death. Seven host modes incl cap/
collisions/symlinks/fork/atomicreader PASS; ordinary16 and task progress controls
PASS, affected unitsASan/UBSan only. Full feature/default25 builds, finalsymbols/
markers/defaultabsence and exactprofile deep-sign PASS. NoAir25 validation yet.

Candidate: private run6/signed-lab25/LinuxLab.app, signedSHA
ba05a3b0ca88943ec002dc2329a3dbf8cce877219afae2c61820e30ba108c9c0.
Immutable source/artifacts run19/compiled25-source, final-linked25.json.
Do NOT install current xcode output (it is DEFAULT25). Signed24 also preserved.

After25build, sourceCFBundleVersion bumped26: actualAir library metadata ONLY
/Steam, while old bridge fixture only/mnt/ideck/SteamLibrary. Host syntax parser
now accepts exactly both fixed/common roots, preserving per-install containment,
hostileprefix/traversal/arg checks. ASan/UBSan protocol tests PASS. This fix is
NOT in signed25, no26Xcodebuild. Guesthelper/VDF unchanged, diagnostic125 only.
No real SteamPlay/ownership/Wine/game/return or repeated stable operation.

HEAD82b7861, remote main2ac39be unchanged. Scoped editsUNCOMMITTED outside local
weekday22-08 window. Keep everyotherworktree/app/account/save/privateartifact.
No FEX/Valve/vendor edits, no auth transfer, JIT activation or combined release.
GoalACTIVE; no STABLE_SUCCESS/unload. Next actualAir25 A/B after safe session end;
independently native path capability/launch lifecycle toward real Madeira.

--- Historical Run18 context ---

# Latest09:41EST Nov9: preserve live23;24 compiled/linked/signed, NOT installed

Actual4952/executable B265FEBE-DE84-4F31-AB6A-235C8BF6F8F8 reverified on exactAir.
Real saved-authBPM home, Ratatan details, Steam menu and full Library40 verified,
but severe delay/incomplete areas and pressure FAIL stable operation. No Play/
Install or account action. Steam Power focus+Return has NOT established exit;
lastscreen genuine Away/screensaver. No user test forcibly stopped/reinstalled.

IMPORTANT current23 kernel log reached4MiB CAP after last1560s resource sample.
Repeat identical2383rows/820warnings is HISTORICAL capped data, NOT fresh health,
no-fault, exit or quiescence. Old last-runtime-session10752/zero workers is4942's
updater result, NEVER use it for4952. CLIconsole29282 remains alive, don'tCtrlC.
Do not install over this live session merely because candidate ready. Native
process presence also does not prove guest Steam responsive or still running.

24 full experiment build SUCCESS, final actual sys_madvise callsite+symbols/
markers inspected. Savedimmutable run17/lab24-unsigned, final-linked24.json,
compiled24-source. Existing exact Air/profile disposable signed+deepstrict:
run6/signed-lab24/LinuxLab.app, signedSHA eac5fd463bccdbe437dbd9280626ab75cc22b19de45a5005d2178d0f4f321fc9.
Full default24 build/final absence of discard markers also PASS; missingflag
combination refuses beforebuild. 80hostchecks pass (22normal/22failure/20lazy/
16ordinary); samealigned host grouped64MiB discard releases66699336bytes vs0
baseline, eagerpartial0deliberately. NO Air24 reclamation/UI/effect validation.

Read EVIDENCE.run17/run18+latestMD. BranchHEAD82b7861, source editsUNCOMMITTED
outside weekday22-08 window. Keep main/everyotherworktree/app/auth/games/saves.
No FEX/Valve/vendor/security/JIT/cap edit, credentials/Guard/lock automation or
combined binary distribution. CLI only, never requestMacunlock. GoalACTIVE,
bridge125 remains diagnostic/no game/no return/no STABLE_SUCCESS/unload.

NEXT discriminate actual normal Steam session completion/absence and preserve
if still active. Then only isolatedLab24 upgrade and actual Air memory/request/
replacement/UI A/B. Do not count successful build/host/scripted packets as device
success. Future long sessions need an independent current identity/health receipt
because bounded kernel log saturation removes later exit/resource evidence.

--- Prior run18 context ---

# Run18: real Air Library/BPM works slowly; conservative discard candidate24 building

Read EVIDENCE.run17/run18 and latestMD FIRST. Main/pins unchanged; branchHEAD
82b7861, scoped edits UNCOMMITTED outside allowed weekday22-08 window. Preserve.

CURRENT actualAir23/4952 (revalidate; console29282), same freshtest app/prefix.
Saved-authSuccess14:10:01UTC without credentials/Guard. Genuine BPM home,
Ratatan selection/details, full Steam menu, and actual Library AllGames40 /
Installed0 visually verified. Input/render delay MINUTES and at947s~2.62GBpeak/
820warnings: NOT stable. KeyboardRFB packets != actual response; await frame.
No Install/Play/account actions; bridge125 still diagnostic, no Wine/game/return.
Testing Steam's visible normal ExitSteam route to end this bounded UI session.
Do NOT native-kill/reinstall just because candidate ready or observer timesout.

Host prototype PrivateDiscard.inc replaces ONLY whole exclusively owned private
anonymous backing; bounded64MiB/try-write-lock, allocateALL beforecommit, exact
refcounts/offsets, nofile/shared/COW/exec. Preserve flags/reservations/logical
account, invalidate code/generation, releaseold. Busy/unsupported/failure falls
back to original. NoMAP_FIXED/mprotect/cap/FEX/Valve/vendor/security edits.
Normal+second-allocationfailure controls22each, realARM64lazy20/ordinary16 PASS;
concurrency100cycles and busy-lock refusal covered. ChangedunitsASan/UBSan,
rest not fully. Earlier fixture/null-exefile/Bash3/double-read failures retained
and corrected; first tight-reader timeout prompted nonblocking optimization.
Same aligned64MiB host test: baseline0 reclaimed both; prototypegrouped lazy
66699336bytes released, eagerpartial deliberately0. HOST, not Air fix proof.

DEFAULT OFF LINUX_LAB_PRIVATE_DISCARD=1 requiresstats1/lazy1;24 runtime marker+
numeric replaced calls/guestbytes. Host-only option still refusesiOS; separate
explicitexperimental option supports candidate. Full24 build firstfailedmissing
CMAKE, now rerunning with preparedCMake. NOT installed. Current23 unchanged.
Before any new build use CMAKE=$privateparent/bin/cmake (see buildflags/docs).
Snapshot actual compiledsource/finalsymbols/hashes, sign with exact existing
Air/app/cert/profile only; do not infer linked/signed/app effect from source.

Continue CLI ONLY; never ask Mac unlock, automate credentials/Guard/trust, or
modify security/locks. No success sentinel/unload; actual licensed game+return,
physical touch/Bluetooth and repeated stability remain open. Preserve every
other app/account/game/save/worktree. Candidate24 may deploy only after current
actual Steam completion/absence is verified, not a stale updater result.

--- Historical run17 context ---

# Run17: Lab23 installed; genuine Air22 Big Picture home verified once

Read EVIDENCE.run16/run17 and latest MD FIRST. Branch parent82b7861; main/pins
unchanged. Real22/4057 saved-authSuccess02:19UTC + own Big Picture icon click and
scripted Return onboarding => actual full genuine Big Picture HOME screenshot
run16/after-finish-guide.png. No credentials/Guard/security action.1325s sample
peak2.8877GB/483warnings/~1.975CPUcores: NOT repeated stable Library/navigation,
physical touch/Bluetooth, game or return. Bridge125 still diagnostic.

Nov9 old4057 absent, cause unknown. New4320 foregrounded without termination,
actual completed ordinary16/status0 screen/current receipt. Identity-verified
completed4320 retired, absence confirmed, then ONLY isolated Lab23 upgraded with
existing exact Air/app/cert/profile/expiry/deep-strict checks. Auth/root/games/
saves and every other app intact. CLI only, NEVER request Mac unlock.

23 observation-only default-off LINUX_LAB_MADVISE_STATS requires NativeLog1.
Copied pristine mmap unit wraps original syscall unchanged, counts numeric
requests/bytes. Host64MiB DONTNEED zeros contents but reclaims0bytes (eager/lazy),
munmap releases; not proven sole Steam cause. Five log+ordinary16 and counted/
no-discard host controls pass; affected units ASan/UBSan, rest not fully.
Full feature23/final Mach-O markers/deep-sign PASS. Full default23 Xcode and
final absence of experimental symbols/markers also PASS (authorized build; initial
sandbox build stalled and only that own xcodebuild was stopped).

CURRENT actual23 post-update Steam PID4952 (REVALIDATE), console29282,
private run17/active-session23-postupdate.json/collect-native.py. Own4942 updater
initial tid2 exit10752/currentresult guest0+worker0 verified before retirement;
afterabsence freshSteam. Saved authSuccess14:10:01UTC, desktop header rendered,
black maincontent. At181s footprint2.362GB/0warnings,2725DONTNEED calls/
1021263872requestedbytes (not unique/reclaimed). Fixed Big Picture icon click
through shared app-local USB RFB underway; don't infer UI success from packets.
No credential/Guard/account/security action. Preserve this live session; never
reuse updater result or CtrlC console.

Run17 source+evidence uncommitted outside weekday local22-08 window; leave so.
No FEX/Valve/vendor/main/security edits or combined binary distribution.
No actual game/return/stability, no STABLE_SUCCESS/scheduler unload.

--- Historical run16 context ---

# Run16: Lab22 installed, fresh launch pending;21 GPU1 black not fixed

Read latest EVIDENCE.run15/run16 FIRST. Main/pins unchanged, parenta395868.
Actual20/3845 SIGKILL with~2.989GB/26warnings. Only after absence installed21.
Actual21/3992 updater exits42/counters0, rechecked before retirement. Fresh
21/4025 helper really gets --disable-gpu/--disable-gpu-compositing.650s sample
~853MB/peak994MB/0warnings/0.215CPUcores but BLACK guest/cursor, no UI success.

IMPORTANT failed debugger caveat: no actual stack. SB select returnedStarted;
hyphenated script refused. Standard CLI still state2Attaching/0threads, detach
false; immediately later noLab + SIGKILL9. Confounded by debugger attempt, NOT
spontaneous Linux/pressure crash evidence. No further attach attempts. No
credential/Guard/security/lock action. Use in-app numeric sampler instead.

Lab22 only adds LINUX_LAB_NATIVE_LOG opted-in bounded nonblocking task sampling
every10s (1024IDs/128rows, skipbusy/truncated explicit). Numeric IDs/wait flag/
lastsyscall/progress counters; no names/argv/registers/addresses/payload. Writes
after unlocking; snapshots best-effort, last syscall can be stale. Default stub
empty.5host log modes+real ARM64 live wait/touch/unmap/contended-lock checks PASS,
wrapper/log/task hooks sanitized, rest not. Initial test scanned unrelated kernel
address lines; corrected new-row scope, NEW run PASS. Full22 feature/default
build/final payload checks, signed/deep-strict PASS.

22 installed ONLY after exact4025 absence, same isolated freshtest/auth/root/
games/saves. Fresh launch CLI console14583, private run16/launch22-steam.json
and steam22-console.log. ACTUAL new PID4056/build22 receipt verified;11 real numeric task samples
on Air and screenshot shows legitimate updater extracting package.110s resource
window, no warnings, peak991791880bytes. This is NOT CEF/Library/login success.
FIRST collect current completion/progress before touching4056. Source noarg can
launch diagnostics: don't infer mode from requested args. If genuine updater42,
verify completion/current identity before retirement, then after absence fresh
Steam. NEVER reuse stale updater result, PID or overwrite live test.

Full Library/BPM/input/Play->licensed Madeira game->return/repeated stability
remain absent; bridge125 diagnostic. No FEX/Valve/vendor/JIT/cap changes, no
Mac unlock request, no auth transfer/automation or combined-binary release.
Keep task active, no STABLE_SUCCESS/unload. Private raw artifacts excluded.

--- Historical run14/prior context ---

# Run14: real20 CPU/classes active;21 CEF GPU A/B prepared, NOT installed

Read current EVIDENCE.run14 and latest investigation FIRST. Primary/main/pins
unchanged; branch source parent9c69a1b. Actual19 Steam3640 endedSIGKILL9 after
443.001s, ~2.9847GB footprint/21.55MB available/15warnings. Genuine saved login
Success-OK00:59:02 and account header verified, contents black; no Library/input
success. Fixed Library/View clicks only move pointer; no passwords/Guard.
ActivityMonitor ended0.988s disconnected/onlykernel, no app CPU metrics.

20 adds ONLY private public self CPU + existing independent atomic Linux counters.
Full feature20 build/final markers/sign/install;5 logging host modes+16 real
controls and default-off iOS unit Werror PASS. First3801 was actually completed
ordinary16, NOT Steam. Verified completed+retired it. Fresh3836 Steam updater
returned42/counters0; verified completed+retired it before post-update launch.

CURRENT actual20 Steam PID3845, install9BB06401-21A9-40BF-A202-C0ACE2F64FA8.
REVALIDATE; console18291; native kernel-3845-341595-865524000.log. Private
run14/active-session20-postupdate.json. At229s CPU647.19s=2.826native cores,
footprint2.271GB/peak2.406GB,3warnings. Logical anon582571pages, codewords105.9MB,
13 tables,17cap/12pressure flushes. Noncoherent logical counters != footprint,
codewords exclude metadata/disconnected blocks, no sole-root-cause claim.

NEXT preserve this active test and collect complete real UI/resources/exit.
Prepared21 adds default-off LINUX_LAB_CEF_DISABLE_GPU=1 -> official Steam
-cef-disable-gpu ONLY (current actual GPU uses ANGLE/Mesa llvmpipe). Full21
build/final launch+policy/CPU markers verified, shell command on/off syntax checks
PASS, signed/deep-strict copy ready, NOT installed/device-qualified. Existing
working target/root/auth/games preserved. Do not install/restart while3845 active
or call compilation an effective GPU-path/content fix. After genuine end, test
actual helper switch + real Library/input/memory/CPU before further changes.

Noarg still diagnostic: actual launch mode must be observed, not assumed from
CLI request. Old updater42 file belongs3836, not3845 result. Saved20 immutable
unsigned and21 candidate private run14; reconstructed20 source is explicitly
reconstructed, not build-time snapshot. No private entitlements/JIT claim, no
Valve/FEX edits or credential/Guard/Mac-unlock automation. Bridge125 remains
diagnostic, no game/return/repeat stability. Keep schedule active; no success
sentinel/unload. Preserve every unrelated worktree, main, app and private data.

--- Historical run13 and prior context ---

# Run13: Lab19 grouping deployed; updater42 completes, fresh Steam active

Read latest EVIDENCE.run13 and investigation FIRST. Source parent ca8216c, main
unchanged. LINUX_LAB_LAZY_PAGES=1 copied memory.c co-materializes absent neighbors
within same native-page group AND SAME reservation under existing lock; existing
data refcount ownership, COW/shared/JIT/logical cap preserved. Default off.
Host64MiB lazy delta68517936 vs eager67158064 (1.02025x vs old4.0324x). Actual
ARM64 base/grouped20 lazy contract + base/grouped16 ordinary controls PASS,
wrapper/grouped memory unit sanitized; remaining archive not fully sanitized.
Full feature19 build/final linked lazy+log+scene markers/sign/deep-strict/install
PASS. Full default19 build/final absent lazy/log bridge PASS.

Exact same Air/app/profile/certificate checked before upgrade, prior3600 visible
completed16/status0. Actual19 PID3625 completed official Steam extraction/update,
returned raw10752(exit42)/guest0/worker0, peak1018481440/0warnings during217s.
This does not prove whole-Steam stability; update state differs from18. Only
AFTER exact completion verified, combined terminate/relaunch refused10004 and
no new PID/receipt. Plain launch AFTER verified absence succeeds fresh3640.

CURRENT active19 Steam PID3640, executable install UUID
CFAF156B-6A09-41F4-AF18-0899415498BC (REVALIDATE). Console handle37953; native
file kernel-3640-340467-766994000.log; private run13 active-session19-postupdate.json.
At78 samples footprint2.103GB/available903MB and0warnings, black guest/cursor.
Memory still growing: no stable-memory/Library/login/BPM/input success. Preserve
this actual current test; no overlapping experiment or kill for timeout. Old
last-runtime-session10752 belongs3625, NOT3640 completion evidence.

NEXT current real UI/resources/exit diagnosis. If grows to limit again isolate
next allocating layer; don't claim first fix sole root cause or raise limits.
Auth data/games/root remain intact. No credentials/Guard/Mac-unlock automation
or new login request absent genuine login screen. Bridge125 still diagnostic;
no actual game, return or repeat-stability proof. No STABLE_SUCCESS/unload.
CLI only and all older isolation/licensing/private-artifact boundaries remain.

--- Historical run12 and prior context ---

# Run12: Lab18 actual SIGKILL preceded by memory-limit pressure

Read EVIDENCE.run12 and latest investigation FIRST. Main/pins unchanged. Private
run12 real-launch18-steam.json PID3571 is TERMINAL SIGKILL9:111 samples, footprint
3004584152/available1683240 and4 memory warnings. This supports memory pressure,
not exact allocating-layer or formal jetsam cause. App scene lifecycle unlogged;
no background exclusion. Later PID3600 is a DIFFERENT unclassified instance;
revalidate/preserve before install/launch. Do not reuse stale PIDs or console IDs.

Host unsanitized actual interpreter page control reproduces4.0324x footprint
for same64MiB writes:128MiB eager67174472 vs512MiB lazy270876888 bytes. Native16KiB
vs guest4KiB independent lazy-page mmap. No runtime allocator fix yet. NEXT add
opted-in copied-memory.c native-page-group co-materialization bounded by same
reservation and absent contiguous pages, using existing refcounts. Test edges,
protection, COW and unmap before Air. No memory-limit increase, FEX/Valve edits,
blind retries or assertion suppression. Original guest cap remains.

Lab17/18 built/final linked/signed/installed in SAME isolated freshtest container;
Air17 real diagnostic PASS0/request1/guest0/worker0. Lab18 resource metrics proven
on Air, not successful Library. Default full build/bridge-absent check PASS,
5 logging controls plus ordinary regressions PASS. Source noarg still launches
diagnostics, not automatic Steam. Activity Monitor capture missed the actual
process window; NO app CPU/ledger results. Real pending human force-close question
from run11 remains unanswered; don't repeat login absent actual login screen.

Auth/games/saves preserved. Full product goal remains unachieved; bridge125
is only a diagnostic, no game or return. Keep scheduled research active, no
STABLE_SUCCESS/unload. CLI only, NEVER request Mac unlock. Preserve other
worktrees/apps/main and all private rootfs/auth/log/profile artifacts.

--- Historical run11 and prior context ---

# Run11 8eaf7b6: Lab16 installed, Air diagnostic PASS; Steam process ended

FIRST current state supersedes old Lab13 auth-wait notes: PID2676 is gone. The
new Lab13 PID3054 was activated without termination; actual screen showed a
COMPLETED ordinary16 diagnostic/status0. Only then signed Lab16 was installed
into SAME isolated freshtest container with exact existing Air profile/certificate.
No working app/root/auth/games/saves erased. Actual Lab16 compatibility PID3186
completed status0/request1/guest_entries0/worker_entries0, guest helper PASS.
This is synthetic AppID480 + diagnostic125, not licensed game or Steam Play.

Completed diagnostic was identity-verified before explicit fresh Steam PID3190.
New shared USB display observer actually works and captures genuine account
startup splash1280x800; no key/pointer/auth action. It is NOT interactive Library
or successful authentication evidence. A later observer failed and authoritative
CoreDevice then listed NO Lab process:3190 really ended. Cause UNKNOWN. Current
crash/jetsam listing has no new matching report; runtime result absent, guest log
no fatal/assertion. User question PENDING: manually force-closed or spontaneous?
Do not assume OOM, successful login, stability or an active old PID. No blind
restart. Preserve same root/account state; no new login request without UI evidence.

Worker flag LINUX_LAB_NATIVE_WORKERS=1 requires guest lifetime opt-in. Copied
archive reserves before native pthread_create and retires after original body/
nested cleanup or failed start across4 providers. Host7 modes PASS incl actual
timer/free, private-pipe real TTY, guest->harmless native handler2 forwarders,
optional profiler1 surviving guest count0, roles/underflow/EAGAIN. Actual iOS
failure-injection guard refuses compile. Full Lab16 feature/default builds and
final Mach-O markers/query + native-handler object inspected. Runtime query is
LOCAL symbol; nm -gU falsely missed it, full nm confirms link. Signal lease NOT
linked; no restart/stop/Wine permission. Original vendor/base/primary unchanged.

IMPORTANT CORRECTION: iOS Apple native-handler forwarding is real, not a stub.
Only posix_spawn is macOS-only. Older run10 inference was wrong and corrected.
Current counters exclude UIKit/RFB/TLS/VM/Mach/future starts; zero not full cleanup.
NEXT collect delayed termination evidence and wire a private native log sink:
pinned kernel LOG_HANDLER_DPRINTF writes fd666, but Lab never connects it. Keep
native log private, input tracing disabled, no credential/Guard automation.
Full genuine Library/BPM/input -> licensed Madeira game -> reliable return and
repeat stability remain required. No success sentinel/goal completion.

--- Historical run10/prior context ---

# Run10 9348bb8: unlinked native signal lease; Air13 auth pending

Fresh actual15:27 physical Air screenshot remains genuine empty Steam login/
expired QR; same native Lab13 process/executable alive. Preserve it. No install,
restart, input, credentials, Guard, auth copy or LLDB attach. Human login/input
question remains pending; do not repeat trust/Mac unlock/login questions.

New NativeSignalLease.c/.h is NOT linked into the Lab target. It is an isolated
native signal-resource component, not permission for Wine or runtime restart.
It captures original actions before Linux initialization, records exact expected
USR1/PIPE ownership, requires one native owner thread plus serialized other
signal owners, and refuses unknown/incomplete native cleanup. Foreign pointer,
mask or flag changes poison it without restoring either signal. Real OS component
fixture tests5 modes pass ASan/UBSan; standalone iOS object compiles. This is not
an iOS app build/link/device success. No actual new signed app exists from run10.

Actual real ARM64 standard16 host control + recorded Linux ownership PASS;
other_native_workers=-1 correctly refuses release/EAGAIN with both actual Linux
handlers preserved. The lease stays owned until this one host test process exits.
Current Lab CANNOT supply a measured complete worker certificate. Full native
cleanup, lease integration, Wine/game/return and repeated stability remain open.

Pin review identifies native timer, optional profiler, real TTY and Apple native-handler
forwarding pthread providers beyond guest entries. NEXT independent
work: authoritative worker lifetime accounting or explicit exclusion per provider
before enabling signal restore. Do not invent zero from the task counter. No
atomic sigaction CAS exists: native owners must serialize; syscall-failure paths
are poisoned but not fault-injected. Existing runtime reentry guard stays intact.
Active Air13 and saved unsigned Lab15 unchanged; bridge remains diagnostic125.

--- Prior run9 and historical evidence ---

# Run9 6fb631d: native signal ownership persists; active Air13 unchanged

Read run9 actual host evidence before designing handoff. Standard ARM6416-control
guest finishes0, all guest table entries and native lifetime reservations drain,
but native SIGUSR1 STILL points to LinuxRunner and SIGPIPE remains SIG_IGN.
Prior sentinel actions/masks are NOT restored. A separate HOST ONLY child-start
EAGAIN case has the same ownership leak after actual guest wait256/exit1. The
first negative harness mistakenly expected old orphan-probe512; corrected and
rerun into NEW output. Both final controls pass8 checks, no runtime fix claimed.
Native restart remains refused-16. No FEX/vendor/Valve edits or signal reset.

Next independent experiment is a serialized opt-in native ownership lease with
capture-before-init, full quiescence, foreign-owner refusal and exact restore;
not an assumption that counter0 means Wine may run. Do not restore handlers in
the active Air app or remove the one-lifetime guard. Current Lab15 is still only
a saved unsigned build; no new app/runtime build or install required for run9.

Fresh CoreDevice verifies same Lab13 process/executable alive. User Steam login/
Guard/input reply STILL PENDING. No restart, upgrade, key/pointer/credential action
or LLDB attach. Preserve current app, account/game/save isolation. Prior run8
remains authoritative for tool125 and failed second-viewer policy. No authenticated
Library/BPM/game/return/repeated stability; no success sentinel or goal completion.

--- Prior run8 and historical context ---

# Run8 checkpoint e61ed82; preserve Air13 genuine login

FIRST preserve the SAME active installed Lab13 session (run6 d865032); fresh
CoreDevice and actual15:15 physical screenshot show genuine empty Steam login,
expired QR, no authenticated Library. User auth/input question STILL PENDING.
No new installation, restart, input, passwords or Guard action this run. Do not
repeat trust/Mac unlock/login requests. Never copy this root/auth to another app.

New optional LINUX_LAB_COMPAT_TOOL=1 installs OUR signed-bundle ARM64 helper and
VDFs through real fakefs before guest execution into fixed versioned
/Steam/compatibilitytools.d/ideck-madeira-lab-v1. Matching files reused; unknown
conflicts/stale stages preserved; init-only and bounded validation. Host24 checks
pass. ACTUAL installed helper executes with synthetic AppID480, returns125;
native_bridge_requests1 and outer diagnostic shell0. This is NOT real Steam Play,
license ownership, game execution, discovery or game-return success.

Unsigned Lab15 full feature build and final Mach-O/resource inspection pass;
all-flags-off iOS build and ordinary16/protocol/package/Python34 regressions pass.
Saved run8-lab15-unsigned; NOT signed/installed/on-Air qualified. Optional
LINUX_LAB_SHARED_DISPLAY=1 adds x11vnc -shared only to this experimental frontend.
Current13 rejects second ordinary AND shared developer viewers, leaving original
viewer alive. Do NOT keep retrying or alter that active server live. New public
usbmuxd observer uses only exact-device ListDevices/Connect to app5993, ephemeral
Mac loopback, bounded time/bytes, no pairing records/trust/security/credentials.
Actual observer delivered no frame or input. Private display password is NOT a
Steam account credential; never publish either. Host-only wire fixture confirms
shared bit1, not device success. No LLDB attach/expression was performed.

A separate unauthenticated host Steam discovery observer was bounded/terminated;
no tool-discovery/UI proof. No competing host experiment remains from that run.
After user login/input/Library qualification, preserve that auth; only after live
user session ends, sign/upgrade Lab15 if needed, run explicit
linux-steam-compatibility-diagnostics then fresh frontend lifetime. Collect
last-compatibility-control.json and guest tmp/ideck-compatibility-results.txt.
Actual Steam discovery/Play must be measured separately. Preserve one-lifetime
Wine/runtime guard and finish full Linux cleanup before real Madeira handoff.
Bridge125 is still diagnostic; all full product/stability gates remain open.

--- Previous run7 and historical context follow ---

# Run7 source/build progress (09d2347); preserve active Air Lab13 login

FIRST respect the human auth boundary below. Fresh CoreDevice confirms SAME
Lab13 process alive; no device restart/install/input or account inspection this
run. User login/Guard reply still pending. Never repeat Mac unlock/trust requests.

Independent lifecycle experiment now reproduces guest-exited with a real orphan
still running. Host virtual-namespace SIGTERM stops that controlled orphan; this
is not a production stop API or Wine handoff proof. New optional
LINUX_LAB_GUEST_LIFETIME=1 copied-archive hooks count pending starts before
pthread_create and retire only on create error/outer guest-entry cleanup after
nested TLB cleanup. Native initial embedding reservation included. Default query
is -95 unsupported; invalid tracking fails closed. Original archive/vendor unchanged.
Host actual observe/signal/standard16 and injected-EAGAIN rollback controls pass.
Full tracked/default iOS Lab14 builds pass; final tracked query/hooks/marker
verified after initial unused query was dead-stripped. Raw artifacts/hashes under
run7* in private base; saved tracked app run7-tracked-unsigned/LinuxLab.app.
Lab14 NOT signed/installed/device-tested. DO NOT upgrade the live Lab13 to test
it while the user may be authenticating. No runtime restart guard removal or
actual Madeira launch: bridge125 remains diagnostic, all native/global cleanup
and Wine/FEX coexistence still need measurement. Preserve full user goal.

--- Air user-login boundary and prior evidence ---

# FIRST: live genuine Linux Steam login on Air, human auth pending

Actual13:57 frontend13-later.png visibly confirms Valve's real ARM64 Linux Steam
login window (account/password + official QR). This SUPERSEDES older black-frame
notes below. User was asked via async question to scan using Steam Mobile or
enter credentials/Guard directly and report Library/touch. Preserve active Lab13
session; no rebuild/restart/install/credential automation or repeated login question.
Do not export/copy this root/browser/account state. CLI-only, no Mac unlock ask.
Actual auth/input/Library/BPM/game/return/stability still unverified; no success
sentinel. While awaiting user response, continue independent bridge/lifecycle
source work without touching this active app or auth. Implementation d865032.

# Current active session — Lab13 genuine Steam/CEF (run6)

Read latest run6 evidence before older notes. User trust DONE, no Mac-unlock
requests ever. Actual Air8 TCP17 PASS; actual Air11 complete clean fakefs import
PASS/current image8afdfb2b9dfa76eef305865ec64994451a7cf953fd1bc2eb3a53fd10d066d84a.
Image/root already installed; do not re-copy2GB or replace data. Native X11/RFB/
Metal desktop/cursor is real physical evidence, not Steam UI/login.

Air11 XOpenDisplay failure: borrowed NSString filesystemRepresentation outlived
its autorelease pool. Host ASan reproduces UAF, fixed malloc-owned absolute prefix
passes9 actual socket/cwd/lifetime controls. Air12 advances into InternalAPI_Init.
Exact ARM64 ldd finds libnm.so.0 absent. Air13 explicit fixed normal signed-apt
libnm0=1.52.1-1 install and ldd complete status0/guest-exited. No credentials used.
Completed diagnostic PID was identity-checked/ended; SAME Lab13 fresh normal
linux-steam-desktop session is ACTIVE, recorded private
run6/trust-cleared/launch13-steam.json PID (revalidate; never use stale IDs).

FIRST inspect this active session, don't restart/reinstall while genuine Steam
may still initialize or user interacts. New actual CEF/webhelper65 initialization
progresses, original InternalAPI_Init fatal absent; screenshot at13:55 still black
X11 cursor, no interactive login/Library/BPM. D-Bus/GLib/Vulkan warnings are not
proven root causes; don't add blind flags/patches. Read fresh bounded
LinuxSteamRootFS/data/tmp/ideck-steam.log and Steam/logs/{steamwebhelper.log,cef_log.txt,
steamui_html.txt} through private app container, plus screenshot. Preserve session.
If actual login appears, user-only credentials/Guard, no native credential automation.

Run6 implementation checkpoint `d8650325a90534452317e0b13d0c40a41e626e38`; signed off. Actual CEF logs have
BrowserReady65536 and PopupHTMLWindow/BrowserReady131073 by18:56:06, but collected
frame does not yet prove a visible interactive login.
Private run6 EVIDENCE hashes include final signed Lab13/debugging receipts. Scope:
ordinary host16 ELF + diagnostic125 bridge and protocol/package regressions pass;
Python24, socket9, header7 and actual Air TCP17 pass. Rootfs UTF8 locale workaround
was REJECTED on actual iOS; final image uses per-entry PAX BINARY preserving known
UTF8 bytes. Don't reintroduce unavailable locale or copy old browser state.

No controller/Library/BPM/game/return/repeated stability evidence. Bridge125 is
still diagnostic, not Madeira execution. Continue actual full goal, no success
sentinel or scheduler unload. Preserve original apps/account/games/main and all
unrelated worktrees; never FEX/Valve/security/auth edits.

--- Previous step-by-step context follows ---

# Latest: run6 — user trust completed, actual Air controls passed

Read the run6 section and EVIDENCE.json before older notes below. User repeatedly
confirmed developer trust; do not ask again or ask for Mac unlock. CLI only.
Air iPad13,1/iPadOS27.2(24B119); exact private device selection unchanged.
Lab8 actual17 TCP controls exit0 with real visible results. Lab6 failure was
native UIKit Scene adoption (SIGTRAP), now corrected, not a Linux crash.

Lab10 is installed in the existing isolated com.kuschqin.ideck.freshtest container
and launched with linux-steam-desktop. Revalidate its recorded PID from private
run6/trust-cleared/launch10-frontend.json; never use stale PID. Preserve live user
sessions; don't restart/reinstall while import/frontend/user login is active.
Original working iDeck, Mac Allocator, accounts/games/saves unchanged.

The clean2GB image is already staged at Documents/LinuxLabInput/steam-rootfs.tar.gz;
SHA07676e4c820a7cca7c9db46df80e681de6a294260e37273a9f1a8e0c479921ea.
No auth/cache transfer. Lab8 verified hash but failed import; Lab9 exact failure
archive79 at copied fakefs.c251 (header iterator), native cwd restored. Same pinned
no-iconv host libarchive reproduces UTF-8 PAX warning in C locale. Lab10 attempted a thread-scoped UTF-8 locale, but actual iOS creation fails;
no guest started. That approach is removed. Seven pinned-library native header
checks now prove per-entry PAX hdrcharset=BINARY preserves validated filename
bytes in C locale; global-only header is insufficient. A new image is being
repacked from the original verified clean image with only this header change.
FIRST finish/inspect new image receipt before building/deploying the next Lab; collect Library/Application Support/iDeckLinuxLab/last-root-import.json
and screenshot. Complete root import is not yet recorded. No JIT needed for interpreter.
If import succeeds, root is LinuxSteamRootFS; inspect data/tmp/ideck-{steam,xvfb,x11vnc}.log
without publishing raw state/QR/account text. A black frame/process is not UI.

Prior relative native socket prefix was wrong: pinned FIFO changes native cwd.
Absolute prefix with same-inode /var alias budget check now passes real8-test
contract. Exact clean embedded host run advances beyond X11 but Steam then reports
InternalAPI_Init failure; exact-env ldd finds missing ARM64 libnm.so.0. No sole
cause claim or assertion suppression. Isolate this dependency through signed normal
guest packages if the physical run corroborates it. Do not restore old host browser
state to make it work. Original host warm root's real login proof remains host-only.

New frontend build gates: LINUX_LAB_PACKET_PIPES=1 LINUX_LAB_TCP_VIEW=1
LINUX_LAB_STEAM_FRONTEND=1 LINUX_LAB_ROOTFS_SHA256=<actual verified pin>, plus pinned
static libarchive via tools/build-ios-archive.sh. Default frontend off. Current
root importer/source/Metal/RFB/input are experimental; no on-Air interactive Steam
or controller/Library/BPM/auth/game/return stability evidence yet. Bridge remains125.
Continue actual goal; no STABLE_SUCCESS.json or scheduler unload justified.

---

# Linux Steam + Madeira iPad continuation

User requested every305 minutes until repeatedly stable on **iPad Air4/iPad13,1**.
As of run4, user LaunchAgent com.kusch.ideck-linux-steam-ipad-305m is loaded,
interval18300seconds. Fresh readback runs2/last0 and this continuation prompt
actually entered research work. The official CLI daemon/queue serializes the
existing thread. This is a macOS task, not a native app Scheduled-UI task; future
sleep/storage outages can delay it. Do not create another overlapping job.

## Required context and constraints

Work in `/Volumes/easystore/GitHub/FunProjects/iDeck-linux-steam-ipad`, branch
`experiment/linux-steam-madeira-ipad`, origin kuscholar/iDeck. Read migration status
and verify volume UUID580CADCD-33F5-4D78-9530-2287615873CA before writes. Read
AGENTS/CONTRIBUTING, LINUX_STEAM_MADEIRA.md and its EVIDENCE.json FIRST. Inspect
current branch/remote/uncommitted work and active processes. Preserve all other
worktrees, apps, accounts/games/saves. No main merge, reset/force push or FEX edit.
Check the user's commit/push window immediately before each operation and sign off.
Do not restart completed audits or overwrite an active experiment's executable.

**User requires command-line operation and explicitly prohibits any further Mac
unlock requests.** Do not operate around locks, alter security settings or extract
credentials. Normal authorized CLI tools are allowed. Never automate Steam login,
Guard or user trust approval. Continue independent verifiable work at real human
authorization gates; do not repeat unchanged prompts or assume unsupported paths.

Implementation checkpoint: `fef1bb73214e223f4e5d641422236f29198ede4c` (signed-off run5 isolated branch; host login/input, not Air success).

## Latest resume: run5 (supersedes run4 host UI result)

Genuine ARM64 Linux Steam login is now VISIBLY INTERACTIVE ON THE MAC HOST only.
Two CEF WebUI/client WebSockets previously403 now101. Native pinned RFB click,
fixed public test text insertion and Ctrl-A/backspace deletion actually appear
in private frames. NO login submitted, no auth/cache transfer, no Library/BPM.
Raw frames contain transient QR login material; never publish them.

Actual discriminator: Valve GetIPCConnectionDetails invokes real lsof. Initially
missing ->127; install normal Debian lsof4.99.4+dfsg-2 ->1 because LinuxRunner
lacked TCP tables/socket inode identity. Optional app/LinuxProcTCP.c plus
build-tcp-view.py overlay only copied archives: real guest FD ownership/inodes,
native TCP state, proc/net/tcp{,6} and per-PID net. NO Steam/FEX/vendor patch or
security-check bypass. Partial ABI: guest-visible FD-backed sockets only, no
orphan sockets, queue counters/network namespaces/UDP completeness. IPv6 header
must say remote_address; real lsof tests caught and corrected that distinction.

Reproducible test-tcp-view.sh now passes base-negative1 (13 expected failures),
positive17, real Debian lsof19 IPv4/IPv6 including actual owner PID. Changed units
ASan/UBSan, not whole runtime. Ordinary16 with correct embedded adapter and bridge
fixture125/repeatEBUSY plus protocol sanitizers pass;15 Python tests pass.
An earlier CLI ordinary run lacks embedded urandom/bridge and fails those fixture
requirements, not proof of a TCP regression. Sanitized Steam run also stalls in
CEF and shows inherited proc task-list alignment diagnostic; no causal claim.
Unsanitized same-source Steam run captures login/input and ends0 after366.673s.

Unsigned Lab5 rebuilt with both LINUX_LAB_PACKET_PIPES=1 LINUX_LAB_TCP_VIEW=1.
Final Mach-O TCP_V1/packetV3/dirfdV3 and linux-tcp-diagnostics markers verified;
embedded tcp ELF checked. NOT signed/installed/on-Air. linux-tcp-diagnostics
uses TCPRootFS and last-tcp-probe.txt. Air still has old Lab1; pending user trust
confirmation unchanged (run5 single probe-file read missing). No repeated trust/
unlock requests or device launches. Native Mac stack sample timed out, no stack
artifact; no success or fault inferred. One attempted resource sample found the
observer had already ended; no memory/CPU measurement exists.

NEXT: carry genuine rootfs/X11/RFB/Metal/input into isolated iOS frontend and
qualify Air controls after human trust. Keep guest Steam state app-private and
never copy account secrets from any existing app or host. Current root run2/
steam-fakefs-v3 is UNAUTHENTICATED but has private transient QR/browser/log state;
prepare clean installation state rather than transporting that session. Inspect
fakefs metadata/symlinks/hardlinks before exporting a portable root. Bridge still
only diagnostic125; licensed Madeira game/return remains wholly unverified.

CEF debug is explicit --cef-debug, unauthenticated only. Steam endpoint [::1]:8080
was identity-verified; unrelated Docker owns IPv4:8080, leave it alone. Safe CDP
returns numeric ports/boolean key presence and101/403 metadata only; never save
raw headers/frames/auth. Observer refuses stale X99 state. Normal cleanup passes;
if forced termination left old display artifacts, verify no runtime before any
explicit private-root-only recovery. Never copy/delete live metadata or overwrite
an active artifact. All host runs ended; no assumed live PID. See run5 private
receipts and EVIDENCE hashes before a new experiment.

## Historical resume: run4


Air4/iPad13,1 is freshly connected, iPadOS27.2(24B119). Read-only last-probe check
still missing; trust confirmation has not arrived. No repeated launch/install or
Mac-unlock request. Preserve installed Lab1/production/Mac Allocator and all state.
Lab4 is prepared UNSIGNED, not installed: explicit linux-packet-pipe-diagnostics
uses separate PacketRootFS, current report and feature-flagged private archive.
No rootfs importer, iOS Steam display or Madeira linkage yet. Verify exact profile,
certificate/device/current availability before any later deployment.

Packet-at-creation is now IMPLEMENTED in app/PacketPipe.c, enabled only via
--packet-pipes / LINUX_LAB_PACKET_PIPES=1; default/base stream code unchanged.
Immutable copied-source/archive receipts and final iOS marker V3 are required.
The corrected probe expects O_DIRECT on WRITER ONLY (Linux source), unlike the
initial test's wrong read flag expectation. Baseline still EINVAL; basic now0.
15 contract cases+complete=16PASS with changed-unit ASan/UBSan: boundaries,4096
splits, short discard/zero, flags, byte counts, EOF/HUP/dup/fork, blocked wakeup,
signal cancel, capacity and EFAULT/partial-EMFILE cleanup. Ordinary16 and diagnostic
compat125 pass. tools/test-packet-pipes.sh reproduces this in a NEW private root.
Packet-to-stream writer conversion and proc writer reopen without DIRECT remain
explicit EOPNOTSUPP, now bounded numeric diagnostics; ordinary stream conversion,
splice/SCM_RIGHTS of these descriptions and full API coverage are not qualified.
Don't claim complete kernel semantics or silently drop flags.

Real Steam advances past controller pipe fatal. Missing genuine helper IBus/NSS/
accessibility/XKB and SDL dependencies were actually identified and installed in
the private guest. Genuine CEF logs and BrowserReady now exist. A300s actual X11
observation gives a screenshot of **Unexpected Transport Error0x3009**, NOT a
working login/Library/BPM. Wrapper0 only means display session ended. The UI test
used packet-v5; final packet-release/iOS also correct full-closed poll masking and
add refusal diagnostics. Exact binaries differ: read hashes/evidence first.
CPUinfo/inotify/D-Bus log errors are NOT a proven root cause; referenced Chromium
code logs cpuinfo failure nonfatally. Do not spoof CPU features or patch checks.

NEXT single discriminator: use final artifact to see whether documented packet
conversion/reopen limits occur, then trace bounded numeric WebUI/client local
transport and socket/FD-pass establishment/close failure causing0x3009. Preserve
fresh unauthenticated root run2/steam-fakefs-v3; no logged-in cache transfer.
Observer --seconds1..600 enables longer observation; no blind retries/timeouts or
Continue Anyway. All bounded runs end before checkout/build mutation; revalidate.
Continue real rootfs/X11/RFB integration as useful in parallel with diagnosis; actual Air testing remains mandatory. Credentials/Guard/
trust are user-only. Game bridge remains diagnostic125 and launches no game.

LaunchAgent readback runs2/last0/18300s; this continuation arrived and performed
real work. Keep schedule active; no STABLE_SUCCESS.json exists. No GO/stability,
physical ELF/UI, Bluetooth, licensed game launch/return or JIT coexistence proof.

## Earlier recorded state (run3; historical, superseded above)

## Current actual status and next gates (run3)

Selected Air4/iPad13,1/iPadOS27.2 is paired and available over CoreDevice. The
fresh lock-state query reports passcodeRequired=false. Device Hub control's
executor failed on the inherited writable-root symlink; do NOT change sandbox/
trust/config or ask Mac unlock. Public devicectl screenshot works and shows the
actual **Untrusted Developer** dialog. One Lab1 launch still returns10002; this
is a user trust boundary, not Linux failure. The async Air trust question is
pending. No further install/launch for this unchanged gate. After user confirmation,
first collect the installed Lab1 control; no device ELF result exists yet.

Default source ID linuxlab has no profile. Air-installed Lab1 uses the previously
absent, already-authorized com.kuschqin.ideck.freshtest; production/Mac Allocator
and phone apps untouched. Validate exact app/profile/device before upgrades.
New unsigned **Lab3** adds explicit linux-distro-diagnostics, fixed prepared
DebianRootFS fakefs control. Final iOS arm64 build/linked v3 and mode markers pass;
not installed/signed yet. Host prepared distro adapter passes6results, wait0 and
repeatEBUSY; ordinary16 controls/ASan/UBSan/packages6 pass. Preserve single lifetime.
Source docs describe app-private root placement and last-distro-probe.txt. No
in-app rootfs importer or Linux Steam iOS display target yet.

LinuxRunner vendor pin d1419782 and optional libarchive fc6563f5 source remain
pristine. Interpreter-only Lab excludes JIT, GUI and Madeira linkage currently.
Host genuine ELF tests cover fs/entropy/shared mmap/clone/wait/socketpair/futex,
invalid openat/faccessat2 and absolute-dirfd plus NULL-path file utimensat; all16 pass. Native
bridge and actual ARM64 compatibility wrapper return diagnostic125, never a game.
Protocol sanitizers/package/archive/scheduler tests pass. No Steam discovery or
native host path/license/symlink/TOCTOU authorization is implemented by syntax-only
IPC. Complete Linux shutdown and Wine's session-once lifecycle remain gates.

Important correction: v1 common-path guard broke touch. v2 moved the guard to
relative openat, allowing full Debian initialization. Full-root real Steam then
still aborted: actual backtrace shows generic_accessat -> sys_faccessat2.
Current v3 checks relative openat AND accessat with explicit non-directory fds;
it preserves absolute-dirfd behavior, file-null utimensat and the original common
normalization/assertion. Generated fs_path.c.o is restored pristine, fs_generic.c.o
replaced, linked marker IDECK_LINUXRUNNER_DIRFD_GUARD_V3 required. Host16 controls
and final unsigned iOS2 marker pass; installed Air1 still has v1, no device fix claim.

All103 pinned Debian base packages verified, assembled and configured IN the
Linux guest, with normal CA setup. ARM64 glibc2.41/curl8.14.1/OpenSSL3.5.7 and genuine
Valve HTTPS download pass on host outside the tool network sandbox. Prior sparse
root http0/DNS errors are not evidence of an intrinsic LinuxRunner network failure.
All17 official stable ARM64/resource packages verified/extracted. Root assembly
is under run2; read latest import/client logs before claiming startup. Codec ../
links resolve to regular same-package targets, escapes/chains rejected. A native
host-only fakefs importer patch accepts only existing SAME regular inode aliases
on case-insensitive storage (PAM/pam doc hardlink), rejects different-inode conflicts.
It is not a guest filesystem/runtime or permission workaround.

Full-root run2/steam-fakefs-v3 now completes the official Steam update naturally
(exit42/268.075s; Valve steam.sh defines42 as restart). Following launch actually
fails steamui.so loading because libGL.so.1 was missing. Signed guest apt refresh
and normal installation supply libGL/minimal X11/VNC. ldd then identified direct
GTK/GLib/PipeWire/PulseAudio/GdkPixbuf/EGL/VA dependencies; their guest apt install
also completes. Keep exact package versions/hashes in private evidence; no GPG or
TLS bypass, Valve patch or host package install. No account data in this root.

Actual Xvfb960x540 plus authenticated loopback VNC works: unchanged pinned RFBClient
captures a true empty desktop/cursor. New tools/rfb-capture.m builds a host-only
private PNG observer (never claim a captured frame proves Steam UI). A second
1280x800 real Steam X11 experiment shows Valve's actual Verifying installation
window. Read run3/steam-x11-control.json and private tmp/ideck-steam-x11.log before
repeating; bound/cleanup are not Steam crash proof. No Library/login/CEF success.
With OpenAL fixed, VGUI loaded but the GLX-disabled control failed glXChooseVisual.
Mesa25.0.7 packages were already present. Enabling XvfbGLX advances beyond this,
then real Steam fatals controllerxinput_linux.cpp31 on negative pipe descriptors.
Numeric discriminator now DONE: separate host pipe observer (base/vendor/iOS
unchanged) logs SteamPID11 pipe2flags0x90000 -> -22/EINVAL; other calls0. ARM64
O_DIRECT=1<<16, so this is packet+CLOEXEC. Pinned pipe.c rejects O_DIRECT.
Freestanding guest/packet-pipe-probe.c reproduces ordinaryPASS, packet-22 and
exit1 (expected FAILURE evidence, not passing semantics). Next design real packet
pipe behavior with isolated boundary/short-read, fork/dup, poll/EOF/cancellation
and fcntl tests; never strip the flag or suppress assertions. No EMFILE/CPU/clone
sole-cause inference. No runtime behavior fix or device pipe execution yet. Exact source
observer and guest script are now committed with four boundary tests. Wrapper
exit0 does not prove Steam success; its bounded private per-run guest logs do.
Do not overwrite host/ish during an active guest. No CEF/login/Library success.

After actual Air ELF controls, bring up complete rootfs and minimal X11/display,
then genuine Valve ARM64 Steam login/Library/BPM. Reuse LinuxRunner RFB client/
Metal framebuffer only after checking dependencies; no fake Steam UI. Only then
validate Steam-discovered compatibility tool and Madeira's real licensed game
launch/return. Keep Wine/FEX/DXMT and ordinary iDeck unchanged; no Proton substitute,
DRM/auth bypass, assumed private entitlements, converter-exception expansion or
unreviewed combined binary publication. Wired controls are not Bluetooth proof.

At every run record exact revisions, experiment hypothesis/discriminator, real
artifact evidence/hashes, regression results/limits and next action in the log.
Private artifacts: `.madeira-install/linux-steam-ipad`, raw device/profile/auth
files excluded from Git. Observe only bounded identity-checked processes. Never
call build/install/process/BrowserReady a working interactive UI.

Stop this scheduled task only after repeated actual Air ELF/interactive genuine
Library+BPM/input, Play->licensed Madeira game->return and stability evidence.
Record evidence-backed STABLE_SUCCESS.json privately, then boot out **only**
`gui/<uid>/com.kusch.ideck-linux-steam-ipad-305m`; do not stop other services.
The task itself does not evaluate milestones; the agent must verify evidence.
