# Automatic Steam client acquisition

## Scope and current verification

Feature branch: `feature/automatic-steam-client-install`, based on main `e3d845e`.
The native installer downloads the entire legacy Windows client directly from
Valve; it is independent of Dock's three-package bootstrap. No Valve binaries
are included in the repository or IPA. This document distinguishes acquisition
from successful Steam startup and ongoing support.

Pinned version: **1769731672**. Original HTTPS manifest SHA-256:
`4b8aa78d95dd7a1475c7849c3e783b136452d34be67342b53728799d697c4823`.
Bundled public metadata SHA-256:
`d44d58a17bd35d3b1a03b1adfd9a05d537251a4b986f02af43763d6c62ab934b`.

The saved original manifest was parsed again and compared with the historical
inventory. All 19 archives were independently downloaded again and matched
their pinned size/SHA-256. The resulting 6,233 public files matched every saved
file hash. Compressed total **334,243,667 bytes**; unique extracted files
**729,535,453 bytes** (729,690,685 includes identical cross-package duplicates).
All four key executables are i386; the full package set includes the matching
chrome_elf, CEF resources/locales, Steam UI, controllers, codecs and webhelper.

The original manifest signature is **not independently RSA-verified** by this
implementation. Trust derives from the previously captured Valve HTTPS manifest,
its pinned historical hash, reviewed package hashes, independent full re-download
and a compiled SHA-256 pin for the complete public catalog. It never follows the
moving manifest or accepts arbitrary/user-entered download URLs.

## Exact source availability

HEAD checks performed 2026-10-29T02:56:48.576592+00:00. All listed URLs returned 200
with exactly matching Content-Length. Full GET size/hash validation also passed.

| Package | Archive bytes | SHA-256 | Official HTTPS URL |
| --- | ---: | --- | --- |
| tenfoot_images_all | 6582204 | `990676bc29d01736477c6b571b5048258a6156284ef242503112fc68567cbf01` | https://client-update.akamai.steamstatic.com/tenfoot_images_all.zip.86419c7a56c12dd107b5e0d46f50c8a9b121f3cc |
| steamui_websrc_all | 30827928 | `d76eabdb2eb9ceb3dd2a264ad232bdd667bdcb6d18253903ff6edbbe2f8b1f55` | https://client-update.akamai.steamstatic.com/steamui_websrc_all.zip.399ab78a41fd3867bf178d8bcee57db47a9de0bd |
| resources_misc_all | 4317962 | `187e562403c7544af7162e08baf7677d030ad6f60947c2cdc7dcbcbf0a7a7fe6` | https://client-update.akamai.steamstatic.com/resources_misc_all.zip.99ed79ed868d732d8e9e9a45444b8f003191e3dd |
| resources_hidpi_all | 98371 | `5bdb97ec734f035c1d06a59b62980028b1b05b920c544ae3673b1a515d3d507e` | https://client-update.akamai.steamstatic.com/resources_hidpi_all.zip.a110d78e994c028dc1c412951e87a0c4e9c819f7 |
| resources_all | 3493173 | `6679e6b4866758ccd33bcb9cbcbf47a1531c24e67c85a3005e97bddf1acf7c82` | https://client-update.akamai.steamstatic.com/resources_all.zip.c0054b3a54e3b8d249a38022ccc94ba655c55eae |
| strings_en_all | 114040 | `82ccf2caa9b4f8ac58368dd273ef7a98932eec481f65e9f14080938eaa1d2d50` | https://client-update.akamai.steamstatic.com/strings_en_all.zip.8eef428d222948911a09e2ceb6e5e8a7225b3447 |
| strings_all | 3888210 | `25b9af5cf7cbc276cf3562423340923752730dfd032f1a016aa00476499ec4ab` | https://client-update.akamai.steamstatic.com/strings_all.zip.4e1a9efdaf3fd4c9256366152a38a3144e60b493 |
| public_all | 30703832 | `54922e455d8a33785966cff838cb804dfaf99ce4a0db4dd6111c491d503ab43b` | https://client-update.akamai.steamstatic.com/public_all.zip.3772dd7f589901c02941d91713a174ad2912f68e |
| bins_hardware_all | 357981 | `d84634553d62297f07db4d1eade0fa45757dc6e53515221bf86021520aedfbdf` | https://client-update.akamai.steamstatic.com/bins_hardware_all.zip.deecd74fba6e602ef23ec442f2ddce59120e2002 |
| steamui_websrc_sounds_all | 4676203 | `c823bd39d234e7d9a5fdb5ec6605eae3f175e52bb847725e8826ff526a61641c` | https://client-update.akamai.steamstatic.com/steamui_websrc_sounds_all.zip.74727ca40ef88c5012bb631488fd285418dce825 |
| steamui_websrc_movies_all | 9210097 | `aa89de11cb2e8767b044d9f0aa0e37686fce03187d1c8e3eb0a70793bddb3996` | https://client-update.akamai.steamstatic.com/steamui_websrc_movies_all.zip.f556f4b9c7e087e07c0fef2da2b1d9f27f734cff |
| bins_codecs_win32 | 11208316 | `f2e264360d8463b238d5398796d8ad8c757a2d44f10101a8dacec856b31efa5c` | https://client-update.akamai.steamstatic.com/bins_codecs_win32.zip.6b4ae7fefdf9cd893140df9dc4026fbb644a3bf2 |
| bins_misc_win32 | 16502790 | `2c19b6407c1ea23351421642de14e6ab92024b160d05436e6e691978d4b11a78` | https://client-update.akamai.steamstatic.com/bins_misc_win32.zip.cf75dad8eda3f4e85585749c82825240e4922156 |
| bins_hardware_win32 | 7086351 | `3e2687ac8fa49eaef75244316a4739e4262f2533f5e54fe0e2682807540e175b` | https://client-update.akamai.steamstatic.com/bins_hardware_win32.zip.5761afacd4ecada95f3b6c780bd881b46edb2f34 |
| bins_win32 | 59544006 | `8b712b2a3412a9066b7725f4e1c5cef9a7ca5b187b6585a5b92d25d09df0ba62` | https://client-update.akamai.steamstatic.com/bins_win32.zip.23e34a6d4b10596a44561a5100dac5585d2517da |
| steam_win32 | 2307664 | `1369615c795b60de822876b4dc4042186cf58d0dc8f63ea1371167f667e16925` | https://client-update.akamai.steamstatic.com/steam_win32_steamrow.zip.3e96965d109fc2d4cc14206b2fc4ec960a746ed3 |
| bins_win64_win32 | 10509550 | `345f6e4bdc19b27ae53bf752c21e2d894e0e899d94823222fb426e890d1226b5` | https://client-update.akamai.steamstatic.com/bins_win64_win32.zip.f29d67dc38a4be027f1734802697c668621a6da1 |
| bins_cef_win32 | 130079979 | `fee14790d59463f31693ef95e10327824f5bdd95baf0aa8fae3b81aea98e794f` | https://client-update.akamai.steamstatic.com/bins_cef_win32.zip.1c1d9dc1d899e7c8d1cff9cb0fcc11b89e412b98 |
| bins_webhelpers_win32 | 2735010 | `1ab3b3834172a644759860f65d853970ba1d8b65f30190aae774395d69136307` | https://client-update.akamai.steamstatic.com/bins_webhelpers_win32.zip.8a153ec2ee2090c19b25204806ffca2a7ba15bf2 |

## User flow

Prepare runtime → **Download & Install Steam** → wait for verification →
fully close/reopen iDeck → set up/enable JIT → launch Steam. Acquisition needs
no JIT, desktop, manual ZIP or account transfer. The launcher shows real byte
progress, phases, Cancel and Retry. Incomplete/incompatible clients offer repair.
The automatic installer and manual import share the full pinned-file validator.
Complete matching existing installations are retained without another download.

If Valve removes any required package, the availability pass fails closed before
large downloads; the launcher keeps manual import (`Documents/Steam32OfficialRepair`).
Manual source must contain the entire matching client. Cached packages are
re-hashed on retry. An incomplete in-flight archive is discarded, not trusted.
Backgrounding cancels safely; return and retry. This is verified-package caching,
not byte-range resume or an iOS background download service.

## Storage, transaction and recovery

Downloads/extraction/hashing run on a non-main actor. ZIP extraction reads at most
64 KiB of compressed/output stream data at once (central directory capped at8MiB);
file hashing uses1MiB blocks. Archives/PEs are never read wholesale into RAM.
Only pinned regular-file paths/sizes/hashes are accepted, with CRC and PE gates.
ZIP64/encryption/symlinks/traversal/case collisions and excess expansion are rejected.

Space is checked before extraction: archive total + twice unique expanded size +
actual existing replaced-file bytes +256MiB margin. This deliberately overestimates
when verified downloads are cached. For an empty install, allow roughly2.1GB free
in addition to runtime setup. Backups consume more space for an existing client.

Wine, wineserver, a consumed JIT pool and concurrent preparation block installation.
New files stage outside the prefix; all public replacements are backed up before
a durable per-file journal is written. Individual file replacement uses streamed
copy plus same-volume atomic rename. Cancellation/write failure rolls back; process
interruption leaves the journal, blocking launch until repair replays recovery.
Backups remain in `wine/client-rollbacks/`. This is recoverable per-file commit,
not an atomic swap of an entire directory. Low storage can also prevent rollback;
the journal and backups remain and the UI asks the user to free storage and retry.

The installer never enumerates or replaces config, userdata, steamapps, ssfn,
authentication caches, Wine users/saves or settings. Existing extra x64 CEF
directories are quarantined in the public rollback tree. No prefix reset/uninstall.
The Steam step turns green only after full hashes/PE validation; actual launch
still requires a fresh app process. Green does not establish successful login.

## Valve terms and unsupported-client blocker

[Steam Subscriber Agreement](https://store.steampowered.com/subscriber_agreement/)
§2A grants personal noncommercial use; §§2F–G reserve ownership and restrict
redistribution/modification. This implementation is user-initiated, unmodified
direct download from Valve; it does not redistribute Steam, accept agreements
for the user, transfer credentials or grant game ownership. Public CDN reachability
does not itself establish written permission or Valve endorsement of iDeck.
No specific Valve permission for this compatibility product has been obtained;
a public release must not imply such permission or bundle proprietary binaries.

[Valve support notice](https://help.steampowered.com/en/faqs/view/49A1-B944-48B8-FF00)
states 32-bit Windows support ended January1,2026. Continued authentication and
Big Picture usability are not guaranteed. The inherited frozen-x86 launch policy
contains `-nobootstrapperupdate -skipinitialbootstrap`; this feature adds no new
update suppression. That existing experiment is **not a maintained/security-updated
production solution**. If Steam requires a mandatory update, report it as a
blocker; do not bypass it. Current AMD64 CEF remains a separate experiment.

## Reproduce and acceptance gates

```sh
python3 tools/fetch-steam-ui-client.py --manifest /private/steam-client-win32.manifest \
  --architecture win32 --cache /private/new-packages --output /private/new-client
python3 tools/build-steam-client-catalog.py --manifest /private/steam-client-win32.manifest \
  --inventory /private/new-client-inventory.json --output /tmp/catalog.json
cmp /tmp/catalog.json app/Madeira/SteamClientPackages.json
python3 tests/host/check-steam-client-install.py
python3 tests/host/check-steam-client-install.py --real /private/new-packages
```

The generator only writes public metadata; it never updates the compiled trust pin.
Review any pin change. Build the full Xcode target following BUILDING.md; the target
must include SteamClientInstaller.swift and SteamClientPackages.json as a resource.

Host production extractor/transaction tests and full real 19-package extraction pass.
A separate native Swift URLSession run from a brand-new private host directory
downloaded/verified/installed all files, and a second run returned existing/no-op.
Private evidence: `.madeira-install/automatic-steam-install/` (no binaries/logs inGit).

Full iOS Build96 compiled; final validation and device evidence are recorded in
AUTOMATIC_STEAM_INSTALL_EVIDENCE.json. The independent fresh-container iOS button
test and subsequent real Steam login/Big Picture are required release gates,
not replaced by host download, compilation, or a green prerequisite.

### Implementation revision and device gate

Implementation commit: `9d21529` (signed off, allowed weekday Git window).
Full iOS Build96 was made from those exact Swift files; source and linked artifact
hashes are recorded in the evidence JSON. User approved updating only the empty
iPad test installation after the separate-app attempt hit Apple's three-free-app
limit. That update and actual Build96 launch succeeded. iPhone apps/data remain
unchanged. The iPad user-action gate is Prepare runtime → Download & Install Steam
(or Mac unlock for Device Hub); no Steam binaries have been manually transferred.
The source should not be described as release-ready until that acceptance and
fresh-process JIT/login/Big Picture test actually complete.

## Build99 release evidence update (2026-10-29)

The previously pending acquisition test completed on iPad: user tapped the native
action in a container with no Steam; actual log records fully verified completion
at23:34:04, after an earlier failed/retried attempt. No Valve files were copied
from the Mac. iPad launch exposed a genuine iOS26 weak pipe2 crash, fixed in97,
then a17.4GB map limit blocking the32-bit guest window (minimum48GB). That device
cannot be represented as a successful Steam boot.

User explicitly authorized overwriting the iPhone experimental app, preserving
its container. Build99 fixes an actual LDRSW TEB-load emulation omission which
killed a browser thread after home entry; exact-opcode/neighbor regression tests,
full build/sign/install pass. User confirms usable Steam and requests release.
This is an existing-account iPhone result, not a fresh-account iPhone test or
long-session/game compatibility guarantee. The unsupported legacy-client and
inherited update-policy limitations above remain. The release is an alpha.
