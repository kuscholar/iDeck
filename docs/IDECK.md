# iDeck

User-directed product integration, 2026-10-23. iDeck runs Valve's genuine Windows
Steam Big Picture locally through Madeira/Wine/FEX. It does not install Linux
SteamOS, stream another computer, replace Steam UI, or bypass authentication or
licensing. Madeira's licenses, exception and component attribution still apply.

## User flow

1. Open iDeck. Prepare its runtime/official Steam resources once in the launcher.
2. Configure the existing Madeira device pairing/JIT flow. Credentials, passcodes
   and pairing approval remain the user's responsibility.
3. Choose **Launch Steam Big Picture**. iDeck requests JIT for the current app
   process, then starts Valve's client with `-bigpicture` in its own Wine prefix.
4. Sign in inside genuine Steam. Steam owns its Remember me state; iDeck never
   copies passwords, refresh tokens or another app's authentication cache.
5. Automatic startup is on by default after setup. Disabling it returns future
   launches to the launcher. JIT must still be obtained for each new process.
6. Use an iPhone controller directly, or tap the guest interface at the touch
   position (existing direct-touch mode, rather than relative trackpad mode).
7. The floating menu offers keyboard, virtual Xbox controls, layout editing,
   settings and automatic-start preference. Home / Back+Start opens it through
   the existing controller routing. Menus consume controller input while open.

## Isolation and data

Build30 upgrades the existing `com.kuschqin.madeira.steamui` installation and
changes its display name to iDeck, preserving the prefix, login state, games and
saves. Retaining this identifier avoids a new free-signing slot and destructive
migration. It is separate from the working Madeira app and main checkout.

The product shell defaults on through `IDeckEnabled` in this branch's Info.plist,
requires the existing `.steamui` bundle isolation, and can be disabled with
`env.MADEIRA_IDECK = 0`. Explicit diagnostics never run concurrently with automatic
startup. Incomplete existing prefixes are preserved, not overwritten by setup.
No Valve executable, game, profile, credential or private log is committed.

## Build

Follow BUILDING.md for the pinned submodules and native dependencies. Source
checkouts alone do not include all required runtime assets. For the research
client resource preparation, use tests/steam-ui/README.md and the verified
`tools/fetch-steam-ui-client.py --architecture win32` flow. Stage that complete,
authentication-free official tree as the private generated app resource
`Steam32OfficialClient`, alongside the existing `prefix-template.tar.gz` and
runtime binaries. Setup copies it once to `wine/drive_c/Steam32BundleLab`.
Missing resources produce an actionable setup error, never a fake ready status.
Do not redistribute Valve components without satisfying their terms.

This PoC currently uses the frozen official 32-bit Steam client. Valve ended its
32-bit Windows client support in January2026; a maintained production solution
is not demonstrated. The 64-bit CEF address-space and intermittent Crashpad
failures remain documented separately.

Example local unsigned compile:

```sh
xcodebuild -project app/Madeira.xcodeproj -scheme Madeira -configuration Debug \
  -destination 'generic/platform=iOS' -derivedDataPath /path/to/private/build \
  CODE_SIGNING_ALLOWED=NO CURRENT_PROJECT_VERSION=30 build
python3 tests/host/check-ideck.py
python3 tests/host/check-steam-ui.py
python3 tests/host/check-steam-ui-keyboard.py
```

Use an authorized development identity/profile for the exact app/helper IDs.
Verify the linked Mach-O (Debug uses Madeira.debug.dylib), signature, install,
launch and phone behavior separately. A successful compile is not device proof.

## Evidence and remaining acceptance

Build29 showed real authenticated Big Picture, a Hot Roads details/download page,
Unity splash and the actual game's menu. Official Steam log tracks app1819280's
`hr.exe`; its manifest reports installed state4. User explicitly reports game
execution works. These do not establish return-to-Steam, Bluetooth input, or
reliable repeated startups. Build29's read-only fatal probe did not reproduce the
Build28 failure; no causal stability fix is claimed.

Build30 launcher/setup/full-screen/menu integration has local compile and host
policy evidence. Build30 is installed and an ordinary launch was independently confirmed alive
on2026-10-24. Product UI/device acceptance remains pending manual Mac unlock
for Device Hub control. Test: launcher on normal open; setup preservation;
JIT handoff; true full-screen Big Picture; controller and direct touch navigation;
floating menu keyboard/overlay/settings; licensed game play and return; app
restart with saved login/auto-start. Do not mark the whole product complete from
these source or host checks.

## Build45 controls and account switching

The floating button now defaults to the safe top-right corner. Drag it to move;
its normalized position persists and is clamped inside safe bounds after rotation.
The scrolling menu includes Keyboard, Virtual controller, layout, Steam menu,
Exit game → Steam, auto-start and settings. Controller
up/down/A also chooses menu entries. Account switching asks for confirmation then
opens Valve's own `steam://changeuser` UI; iDeck never enters or copies credentials.

A small GPL Windows control helper is built from `build/ideck-control/` into the
app by the resource phase. Set LLVM_MINGW to the toolchain root or put
`x86_64-w64-mingw32-clang` on PATH. It accepts only three fixed local actions, uses
no network and no arbitrary shell command. Steam menu focuses the real Steam
window and sends Ctrl+1. Exit game sends a normal WM_CLOSE, waits for actual
process exit, then opens Big Picture. It never force-kills a game; confirm any
save prompt in the game. Visible standard `steamapps/common` game windows are
recognized; focus the desired game if more than one is present.

The isolated Steam session now exposes its virtual player1 before enumeration,
even while touch controls are hidden, through generic HID and XInput. Ordinary
Madeira game sessions retain their previous controller defaults. If the saved
layout contains only keyboard controls, enabling Virtual controller loads Xbox
controls. Read `IDECK_CONTROL_EVIDENCE.json` for actual checks and limits.
Build45's Windows helper reports XInput connected and one HID gamepad; UI touch
navigation, menu effects, account chooser and game-return require separate real
interface validation. Do not treat dispatch acknowledgement as UI success.


## Build48 launcher account entry

Sign in / Change Steam account lives in the iDeck launcher. It starts the genuine
client with a fixed steam://changeuser request; no credentials appear in command
arguments. Big Picture uses the same Steam prefix/session. Account choice and
Steam Guard remain Steam UI operations performed by the user. The previous HUD
account action was ineffective and has been removed. The first launch after this
upgrade disables auto-start once so the launcher is reachable; its toggle remains
available afterward. Physical account chooser and selected-account continuity
are pending validation, not established by successful compilation/installation.


## Build50 desktop-login-first experiment

Product launch first opens genuine desktop Steam. The explicit account action
also requests Valve's changeuser UI. A bounded local observer ignores earlier
log entries and waits for a new exact `SetLoginState: Success - OK` transition,
then requests genuine Big Picture from the same Steam instance/prefix. No password
or refresh token is read, copied into another client, or placed in arguments.
The observer reads at most16KiB per poll and publishes only a categorical success
marker. Split/truncated/replaced logs and stale historical success are covered by
host checks. A command acknowledgement is not proof the Big Picture UI appeared.

For an isolated on-device discriminator without signing out, launch with
`madeira-steam-login-desktop-experiment`. It uses existing saved Steam state,
waits for success and never requests changeuser. User enters any required Steam
Guard/credentials directly. This flow's actual authentication/transition is still
pending device validation; it is not an established fix for browser hangs.


## Build51 saved-login startup

Normal Launch Steam Big Picture (and auto-start) again starts direct Big Picture
using Steam's saved login. Desktop-login-first remains the explicit account-entry
flow and diagnostic argument. This avoids repeating the known hanging live
transition on every normal reopen. Build50 fresh Steam authentication succeeded,
but live transition did not complete; its JS persona error is not proven causal.
Build51 also isolates current-process PEB32 queries from sibling startup globals.
On-device UI and longer stability remain separate validation gates.
