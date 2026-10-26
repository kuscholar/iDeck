# 64-bit-only Steam installation

The original report was selective: Ratatan (2949320) and Monster Hunter Wilds
(2246340) made an Install sound without proceeding, while Tomb Raider (203160)
could download/install. Device appinfo identifies the first two as `osarch=64`.
This is an installation-capability issue, not evidence that the runtime cannot
execute any x86-64 game.

## Discriminating result

The isolated 32-bit probe showed IsWow64Process=true and native system
architecture AMD64, but Valve's unmodified tier0_s.dll `Is64BitOS` returned false.
The DLL first calls IsWow64Process2. For an ARM64 native machine, it looks up
GetMachineTypeAttributes and queries AMD64 execution capability. That export was
missing in the shipped Wine kernel32; the fallback returns false for ARM64.
Wine also accepted AMD64 mappings on ARM64 while omitting AMD64 from its
supported-machines enumeration.

Build 58 adds the missing Wine API and advertises the existing AMD64 capability
only for MADEIRA_STEAM_UI_SESSION=1. Native identity stays ARM64. A same-device
probe now reports GetMachineTypeAttributes(AMD64)=S_OK/UserEnabled,
Valve Is64BitOS=true and AMD64 guest support=true. These are API results;
real Steam installation/download acceptance is recorded separately in
[the evidence](IDECK_64BIT_INSTALL_EVIDENCE.json).

## Source and scope

The API is backported/adapted from Brendan Shanks' LGPL Wine MR10558,
[posted 2026-04-03](https://list.winehq.org/hyperkitty/list/wine-gitlab@list.winehq.org/thread/ZQBFNVIXTGEJCOETMJKKS3AGOCV3B5UT/).
Our older pinned Wine uses class181 rather than class230. AMD64 on ARM64 uses
its root namespace, so the API must not report WoW64Container for AMD64.
The added Wine API implementation/patch remains LGPL-2.1-or-later; existing
Wine notices remain. Valve files and FEX are unmodified. No authentication,
license or game metadata is bypassed.

## Reproduce

1. Build Bison 3+ and use LLVM-Mingw from BUILDING.md. Put Bison on PATH and
   provide BISON_PKGDATADIR if using a non-installed source build.
2. Run `LLVM_MINGW=/toolchain bash build/wine-pe/build-machine-attributes.sh /new/private/work`.
   This exports the pinned Wine commit to a separate directory, applies the
   tracked patch and builds/strips only i386 kernel32 and kernelbase.
3. Back up the prior local `app/Madeira/i386-windows/{kernel32,kernelbase}.dll`,
   then stage the new files from `work/build/dlls/<module>/i386-windows/` there.
   These generated binaries stay out of Git. Keep original rollback copies.
4. Rebuild `bash build/wineserver/build.sh` with the documented Wine generated
   host headers available and llvm-objcopy on PATH. Verify registry_ios is both
   compiled and inserted into the archive. Ordinary sessions retain their list.
5. Compile `tests/steam-ui/platform32-probe.c` with i686-w64-mingw32-clang
   `-O2 -Wall -Wextra -Werror`; stage it as `C:\platform32-probe.exe` in the
   isolated prefix. Build/sign/install the app with matching development profiles.
6. Explicit `madeira-platform-diagnostics` starts only this probe using paired
   JIT; collect `C:\madeira-platform32-results.txt`. It does not install games.
   The probe reads numeric OS/architecture contracts and calls the existing
   official tier0 exports; no account data is read.
7. Start a fresh real Steam session using the same prefix/authentication. Confirm
   Ratatan Install opens the wizard, then verify legitimate download and the
   final installed manifest. Separately recheck another game and input/gameplay.

Host checks: `python3 tests/host/check-machine-attributes.py`,
`python3 tests/host/check-steam-ui-machines.py`, `check-steam-ui.py` and
`check-ideck.py` in the same host-test directory. A build or API probe alone
must not be reported as a successful Steam installation.

## Client migration discovered after the capability fix

On the first real Build58 run, Steam automatically replaced its original i386
steam.exe with an AMD64 executable and selected 64-bit CEF. This is distinct
from the successful architecture probe and did not establish installation
success. The original and migrated executable hashes are recorded in evidence.

Build59 therefore pins only the experimental x86 launch with the bootstrapper's
existing `-nobootstrapperupdate -skipinitialbootstrap` options. The x64 launch
mode retains its prior arguments. This keeps the legacy-client experiment
explicit; it is not a maintained-current-client solution or a security-update
claim. A future migration to current Steam still needs separate CEF work.

Explicit `madeira-steam-client-restore` maintenance imports a staged, complete
legitimate `Documents/Steam32OfficialRepair` tree. It first backs up all public
client files that it replaces under `wine/client-rollbacks/<uuid>`, preserves
config/userdata/steamapps/logs/cache directories, and moves only extra 64-bit CEF
directories absent from the source into the same rollback. It refuses source
symlinks and destination traversal. Normal launches never perform this repair.
No account cache is transferred. The host fixture exercises an AMD64 client
replacement, preserved account sentinel, rollback, quarantine and isolation.
The native repair runs off the UI thread. Reopen the app afterward before
starting paired JIT/Steam: doing large file restoration before creating the JIT
pool in the same process caused an independent address-window allocation failure
in the first Build59 maintenance run. A fresh process then reached saved-login
Success/OK at 2026-10-26 01:38:42 without updating the pinned client.
