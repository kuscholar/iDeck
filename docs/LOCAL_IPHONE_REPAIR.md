# Local iPhone runtime and display repair

The installed 0.1.3 IPA first failed to load a Unity game's GameAssembly due
to the missing 64-bit wintypes DLL. The compatibility module and its limits
are documented in `build/wintypes-compat/README.md`. A later device log
confirmed that both DLLs loaded and Unity created IL2CPP workers. That run
then exhausted the 512-entry Mach thread registry and showed wrong-context
exception handling. This is consistent with upstream issue 397, not proof
that every later access violation has the same cause.

## Native runtime

The local source includes upstream PR 412, head
`2873c661cb7fc185e1c5448968017f3b5d19e075`, which safely reuses eligible exited
thread registry entries. Its ASan/UBSan host checks passed 4000 sequential
registrations with at most 40 alive, 12000 concurrent registrations, protected
entry edge cases, and a negative control reproducing the original exhaustion.
The existing lazy-window and 1024-slot trampoline tests also passed.

A clean local iOS build required Wine IDL headers, native FEX, FreeType,
FFmpeg, GnuTLS, the pairing library and iOS LLVM/DXMT. The Wine server script
now bootstraps unchanged source members instead of requiring a private base
archive. The iOS crypto shim enables its actual static GnuTLS implementation
when host configure cannot detect the iOS library. DXMT now generates the
three embedded AIR headers before their consumer is compiled. The Metal 27
public atomic API compatibility change in the DXMT submodule is preserved as
`build/dxmt-ios/xcode27-metal-atomic.patch`.

Native libraries and the app were compiled locally. The optional i386 DLL
resource farm was preserved from the official 0.1.3 IPA; it was not rebuilt.
The Windows ARM64EC DLL farm otherwise comes from the pinned source tree.
The pinned LLVM host and iOS static-library targets succeeded; the optional
all-target build's libLTO dylib is not an app dependency.

## Display

Library entries can opt into landscape lock on phones. The library retains
its normal orientation after the session. This local build performs a one-time
migration for installed Steam app 2949320: it backs up the library and existing
game config with `.pre-display-repair` suffixes, enables landscape lock/Fit,
and appends Unity's fullscreen, borderless, popup and current-resolution flags
through the existing per-game `MADEIRA_CHILD_ARGS` hook. It preserves later
user changes, and Steam authentication/entitlement/launch are unchanged.

## Verification boundary

The final Xcode Debug build succeeded with bundle version 5 and iOS 26 minimum.
The new registry reuse diagnostics, landscape setting and migration log text
were verified in the executable. Existing development profiles were used,
and `codesign --verify --deep --strict` passed for app and extension.

The resulting IPA is in the workspace's `.madeira-install/` staging folder,
with its SHA-256 and build/test/sign/install logs. After wireless connectivity returned, build 5 installed successfully and launched.
Device app inventory confirmed bundle version 5. The startup log confirmed the
fullscreen migration, the persisted library has `landscapeOnly: true`, and the
device game config contains the expected Unity fullscreen and borderless flags.
The user subsequently confirmed the game runs successfully on build 5.
Preserved original and previous patched IPAs provide an in-place rollback.


## Physical controller follow-up (build 6)

The library controller focus list previously excluded all Steam entries in the
Platform grouping. It now follows installed Steam games and the other games,
with a visible Steam card focus ring and stable IDs for newly discovered games.
A selects the details page, A there starts the game, B returns, shoulders switch
tabs, and held directions repeat after 400 ms at 120 ms intervals. Connection
status and button hints appear below the library. The Home button or Back+Start
opens the session menu; ordinary Start continues to reach the game.

The existing physical GameController-to-XInput transport remains the game's
input path, preserving native gamepad detection and game-provided Xbox button
prompts rather than mapping the controller to keyboard keys. A paired controller
now reserves player 1 synchronously before startup enumeration. Touch-only slot
reservation remains opt-in. Foreground/current-controller notifications and a
one-second foreground discovery reconciliation cover delayed wired profiles and
reconnection. Disconnection clears buttons and motors through the existing
snapshot path. Library/menu ownership continues to neutralize guest input.

The host snapshot/query test covers four slots, ranges, packet changes, concurrent
reads, disconnection/reconnection, capabilities and vibration. The frontend test
also covers held direction repeats and Home menu dispatch. Both tests and the
Xcode build passed. Build 6 was signed, verified, installed and launched on Kusch. The device log
confirms `Backbone One PlayStation® Edition` (MFi) connected in XInput slot 0,
and a device screenshot confirms the connected status and library focus ring.
Actual button navigation and gameplay still require physical input validation;
compilation and controller enumeration alone do not prove them. Settings forms, account entry and touch-layout editing
still retain their existing touch interface.


## Windows.Gaming.Input follow-up (build 7)

The user confirmed build 6 navigated the library but the game ignored the pad.
The device log confirms actual physical input published to the guest snapshot,
and Ratatan loading Windows.Gaming.Input / RawGameController and dinput8,
without loading XInput. The previously opt-in WGI host-pad publication was off.

The game controller picker now includes `XInput and Windows.Gaming.Input`.
This exports `MADEIRA_WGI_HOST_PADS=1` and `MADEIRA_INPUT_FOREGROUND=1` for that
session only, using the existing Wine implementations already present in the
bundled DLL and native win32u. The launch environment preserves these choices
and clears them at session end. A one-time backed-up library migration selects
this mode for the existing Ratatan entry; other games keep their own choices.
No keyboard emulation is used. The frontend regression test verifies both
exports and that a later game does not inherit them. Tests and build 7 passed.
Build 6 physical-gameplay validation failed; do not treat snapshot publication
as proof the Windows application has enumerated or read the controller.

Build 7 was signed, installed and launched successfully on Kusch. Device startup
logs confirm version 7, the Ratatan WGI mode migration and Backbone in slot 0.
The user must restart the game to validate Windows-side enumeration and input.


## Loading failure follow-up (build 8)

The build 7 device log confirms WGI published XInput slot 0 and actual physical
input reached the snapshot. It also records the executable pool shrinking from
896 MB to 560 MB because no single hole fits, then `EXHAUSTED` during module
loads. CRI audio (`cri_ware_unity.dll`) failed with STATUS_NO_MEMORY (c0000017),
followed by Unity DllNotFoundException / WinError 0000007e and repeated retries.
This failure was absent from the previous run where CRI loaded successfully.
The user's transient ErrorCode dialog itself was not captured, so its exact code
is not confirmed. Curl certificate errors occurred in the previously running
build too; certificate validation is unchanged.

Build 8 selects the existing `pool-split=1` allocator for Ratatan through its
per-game config, backed up as `.pre-pool-repair`. The WGI controller mode and
fullscreen flags remain. No executable memory is placed over the stack or the
fixed image window. The split pool tests and frontend tests passed, and the
Xcode build and signature verification succeeded. Actual split allocation and
loading completion must be checked on the next device launch.


## Published baseline

The user confirmed build 8 passes Loading and works. This is user-reported
physical-device validation; the earlier device artifacts independently prove
installation, WGI controller enumeration, input publication and configuration
migration. The transient game dialog's exact code remains unconfirmed.

The DXMT Metal compatibility diff is stored in the parent repository and applied
to a staged shader copy by `build/dxmt-ios/build.sh`. The DXMT gitlink stays at its
published upstream SHA; no unpublished submodule commit is needed. The rebuilt
tracked GnuTLS/GMP/Nettle archives and the small wintypes compatibility binary
are included with their source/build instructions. Device provisioning,
credentials, private logs, games, Valve binaries and signed IPAs are excluded.

The user subsequently confirmed build 8 works. The recurring Steam Big Picture
research is specified separately in `BIG_PICTURE_TASK.md`; it must preserve this
baseline and audit current/historical sources before changing runtime code.

## Rebuilding the local baseline

Use `docs/BUILDING.md` for dependency sources and licence notices. This local
build used Xcode 27 plus its downloaded Metal Toolchain, CMake 4.4.4, Ninja
1.13.2, Bison 3.8.2, LLVM-MinGW 20260421 and LLVM 15.0.7 source
`8dfdcc7b7bf66834a761bd8de445840ef68e4d1a`. For LLVM's iOS build, AddLLVM's
Darwin platform handling also needs to include iOS. Required static LLVM targets
built; the unrelated libLTO dylib did not. The native FEX build uses
FEX_IOS_HOST_BUILD=ON and LTO off; do not pass Windows-only FEX_IOS_HOST compiler
defines to the native iOS target. Generate Wine's IDL include headers with the
configured host widl before building the native Wine archives.

Rebuild the GnuTLS stack, FFmpeg, FreeType, native FEX, native Wine archives,
DXMT/LLVM combined archive, pairing library and Dock using their build scripts;
build the wintypes shim as documented above. Stage licences with
`bash build/stage-licenses.sh`. The tracked four crypto archives were rebuilt
from their pinned sources. This is an executed dependency build in a prepared
workspace, not proof of a clean-machine one-command build. The optional i386
farm in the installed app was preserved from the official 0.1.3 IPA and was not
rebuilt. Provisioning profiles, private keys and signed IPAs are not source.

The app build command, from the repository root after dependencies are ready:

```sh
xcodebuild -project app/Madeira.xcodeproj -scheme Madeira \
  -configuration Debug -destination 'generic/platform=iOS' \
  -derivedDataPath build/DerivedData CODE_SIGNING_ALLOWED=NO \
  CURRENT_PROJECT_VERSION=8 IPHONEOS_DEPLOYMENT_TARGET=26.0 build
```

Use your own bundle ID, valid signing identity and matching development profiles
for the app and JIT extension. Sign bundled libraries/frameworks and the extension
before the containing app; verify with `codesign --verify --deep --strict`.
Update the existing app in place to preserve the prefix and saves. The exact
installed bundle's signature and deployment were verified locally; a different
recipient's signing setup must be verified independently.
