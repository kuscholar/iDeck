# Build 135: two game cycles, third-launch capacity failure

This is an experimental source checkpoint on `experiment/steam64-cef64`, not a
release or a general compatibility claim. The physical target is Kusch,
iPhone 15 Pro Max / A17 Pro. Installed Build 135 was read back after reconnection.

The user confirms that the blocking runtime notice is gone and that Hot Roads
can enter and exit normally twice. Steam's game-process log independently records
both game exits as zero. On the third launch the game loader fails and Steam
subsequently becomes unresponsive. Interactive navigation observations are user
reports; no independent Device Hub screen validation was available with Mac locked.

## Presentation fix and remaining 32-bit limit

The child-window observer records a nonmodal notice in iDeck options rather than
opening the global startup-failure alert. True preflight failures still use that
alert. The matching older failures name Valve's `bin/x86launcher.exe`; free native
VA was only 1172/928 MiB, below the actual 4 GiB window requirement. No reservation
guard was weakened. This presentation fix does not repair that child's capacity
or prove that every failed helper is optional. Counterpart executable names and
resource strings do not justify redirecting the helper to `x64launcher.exe`.

## Third-launch evidence

Times below are November 1, 2026, America/New_York (UTC-05:00).

| Observation | Evidence |
| --- | --- |
| First game | Starts 22:13:53; exits 0 at 22:14:10 |
| Second game | Starts 22:14:28; exits 0 at 22:14:47 |
| Third game | Starts 22:15:05; exits `0xc0000135` at 22:15:08 |
| Original third-game failure | `UnityPlayer.dll` section creation/query succeed, AMD64 machine; mapping fails `0xc0000017` |
| Image-space discriminator | Requested `0x1606000` (22.023 MiB); largest gap `0x13f9000` (19.973 MiB), 195 views in image-spill band `0x7160000000..0x717fff0000` |
| Subsequent CEF failure | New `ExternalEntityTable::InitializeTable` V8 OOM at 22:15:20; same-browser table bank has claimed all twelve 512 MiB slots |

The outer DLL-not-found status does not establish a missing or damaged file:
the earlier successful section/query and failed mapping distinguish address
placement failure. Reinstalling the game is not supported by this evidence.

The image-placement failure and the later CEF table refusal are distinct facts.
Current observations do not prove whether retained views are legitimate live
objects, incomplete process cleanup, fragmentation, or another lifetime defect.
Placeholder-preserving frees are not proof that a whole table lease is reusable.
Do not recycle a live/preserved lease or restore overlapping reservations.

One bounded native-log snapshot used suspend/copy/SIGCONT after login; the third
game mapping failure preceded it. The later CEF OOM followed it, so scheduling
effects are not excluded. The 74-record numeric lease snapshot has no partial
tail or exhausted diagnostic budget, but does not claim complete runtime coverage.
The next clean discriminator should collect small files without suspending Steam.

## Validation and publication limits

Build 135 passed its full Xcode build, final linked diagnostic marker, unchanged
private runtime/helper hashes and deep-strict signing before installation. The
popup and two-cycle results above are subsequent actual-device evidence.

Publication review additionally fixes a diagnostic-only read: a failed
`NtCreateSection` must not dereference its output handle. The extracted production
wrapper passes ASan/UBSan failure/success tests. This follow-up was made **after**
the installed Build 135; it is not claimed as part of that device result.

Host checks cover layout/ownership/transfer, bounds, backing, imports, root-store,
lease diagnostics, launch/return, observer/presentation and signing. The CEF glue
test requires a separate pinned Chromium Git checkout and was not run successfully
with the available source fixtures. Host checks do not validate Steam UI.

This checkpoint excludes private FEX experiments, generated runtimes, Valve/game
files, account data, signing material and raw logs. Build 135 used the privately
authorized FEX131 experiment and helper126; the public checkout alone does not
reproduce that exact private FEX component. Original FEX/Wine submodules remain
unchanged. Evidence hashes are in [CEF64_BUILD135_EVIDENCE.json](CEF64_BUILD135_EVIDENCE.json).

## Next discriminating experiments

1. Attribute image-spill views to process owners and compare before/after child
   exit. Use an isolated owned AMD64 image of comparable size; let a child exit
   without explicitly unmapping it. The existing explicit-FreeLibrary probe
   does not test automatic process cleanup.
2. Compare a Steam-only navigation run with game cycles, observing CEF table
   ownership and exact release semantics. Determine whether demand grows without
   games before changing bank capacity or lifetime handling.
3. Change only the demonstrated lifetime/placement contract, then repeat at
   least three game/exit/navigation cycles on Kusch with guards intact.

Stable repeated game return, Bluetooth, other devices and a long-term capacity
solution remain unverified.
