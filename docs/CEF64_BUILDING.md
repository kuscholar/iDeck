# Experimental CEF64 component build and validation

This developer recipe builds one open-source support DLL, not Steam, SteamOS
or a replacement libcef. The working hybrid remains available. Current
results and exact hashes are in [the evidence record](IDECK_CEF64_SOURCE_EVIDENCE.json).

## Windows source build

Use a new disposable directory, an official Visual Studio2022 C++ installation,
Windows SDK, Python, Git and CMake. The successful control jobs used
MSVC14.44.35207 and SDK10.0.22621.0. The builder fetches the upstream-pinned
GN, LLVM and hash-checked resource compiler. Ninja is pinned below.

```powershell
$env:DEPOT_TOOLS_WIN_TOOLCHAIN = "0"
$env:PYTHONUTF8 = "1"
python -m pip install ninja==1.11.1.1
git clone --config core.autocrlf=false --config core.longpaths=true --depth 1 --filter=blob:none --sparse --branch 126.0.6478.183 https://github.com/chromium/chromium.git chromium126
python experiments/cef64/prepare.py chromium126 --cef-glue
python experiments/cef64/build.py chromium126
```

Run these from the iDeck checkout. The Chromium directory must not contain
existing work. The preparation script checks the exact Chromium commit and
original source hashes. The optional CEF integration clones its exact public
revision, applies the complete published crash patch, and generates its version
using real history. No Valve files are inputs.

Omit `--cef-glue` only to reproduce the stock-Chromium control. Two control
jobs passed Windows loader/allocation/export tests and produced the identical
DLL. That control is not established as compatible with Steam's CEF.

The workflow [cef64-component.yml](../.github/workflows/cef64-component.yml)
contains the exact source tests and byte-safe original-header extraction.
Do not use a text-mode PowerShell redirect to extract a file for SHA checks.
Temporary patch fixtures explicitly disable auto-CRLF, matching the checkout.

`ideck-elf-build.log` records real command output. Only after successful tests
does `ideck-elf-artifact` contain a DLL, validation receipt, provenance, scripts
and upstream notices. Verify its SHA256 and AMD64 machine against
`validation.json`. A CEF-aware candidate must also report `cef_crash_glue=true`
and `windows_render_child_load=passed`; an old control receipt is insufficient.
Failures stop the builder. Do not substitute a hand-written generated header,
skip BRP checks, or call a compile-only result a runtime pass.

## Isolated iPhone discriminators

The native app build still requires the dependencies and resources described
in [BUILDING.md](BUILDING.md). Build85/86 used this machine's prepared Wine
headers/resources; a new empty-checkout native build is not newly validated by
these experiments. Never treat a pre-existing native archive as the changed
runtime: rebuild it, link the full app, and inspect the final Mach-O.

Use an isolated `.steamui` app identity and its own `wine-steam64` prefix.
Preserve existing accounts, games and saves. Use matching existing signing
profiles with `tools/resign-app.py`, then deep-strict signature verification;
re-signing cannot add an entitlement that the profile does not grant. The
working app must not be uninstalled. Physical unlock and the existing paired
JIT workflow are required, with credentials entered only by the user.
For profile checks, official Xcode renewal and optional same-bundle upgrades,
see [development-signing automation](DEVELOPMENT_SIGNING.md).

1. Build the own AMD64 `load-probe.c` with its adjacent `owned-contract.h`.
   Windows CMake does this in the component builder. The tested Mac cross
   compile uses llvm-mingw's `x86_64-w64-mingw32-clang -O2 -municode -static
   -Wall -Wextra -Werror -Wl,--no-insert-timestamp`.
2. Stage that PE as `drive_c/steam64-cef-load-probe.exe`, and the validated
   component separately as `drive_c/iDeckCEF64SourceProbe/chrome_elf.dll`.
   Do not overwrite a working Steam directory for the load test.
3. Start a fresh app with argument `madeira-cef64-component-diagnostics`,
   `MADEIRA_CEF64_SOURCE_LAYOUT=1` and
   `MADEIRA_CEF64_OWNED_CONTRACT_PROBE=1`. This selects the own Windows API
   reserve/query/commit/zero/write/read/duplicate-refusal/free discriminator.
   It does not need a Valve DLL or login.
4. Collect `drive_c/madeira-cef64-load-results.txt` and the private native log.
   Require every exact region and operation to pass. Separately verify actual
   FEX allocations/consumer evidence for the published arena; publication
   alone is insufficient.
5. After a clean app restart, run the same argument/layout with
   `MADEIRA_CEF64_OWNED_CONTRACT_PROBE=0` to load the separate source DLL and
   exercise its public payload/export/allocation checks. Keep its output
   distinct from the ownership test. One native lifetime cannot recycle claims.
6. After another clean restart, also set `MADEIRA_CEF64_PROBE_RENDERER=1`
   to test the DLL's non-browser initializer with fixed `--type=renderer`.
   The renderer and ownership selectors are mutually exclusive. This tests
   component initialization, not a real Chromium renderer or web page.

The six-region geometry is measured only on Kusch. Build83 capacity and84
bounded backing passed. After physical unlock, Build85's actual Windows
ownership test also passed all five reservations, ten committed edge-page
checks, duplicate refusal and five releases. The source DLL passed the browser
probe in Build85 and renderer probe in Build87 on the same iPhone. Native
snapshots show real backing adoption; FEX initialized with an allocation
inside the published 15 GiB arena. These are bounded component results,
not full-range physical backing, real CEF rendering or Steam UI success.
Build87 includes Build86's isolated skip of the conflicting legacy V8
fixed-zone service. Actual V8 code reach remains a gate.

Only after these discriminators pass should a separate genuine Steam trial
use a matched official client/helper/libcef resource tree, with original public
files backed up and hashes recorded privately. `MADEIRA_STEAM64_DIRECT_CEF32=0`
disables the hybrid redirect for that trial. Existing saved authentication stays
in the same isolated prefix; do not transfer login caches or automate Guard.

The first prepared full trial uses the matched January 22, 2026 client and all
81 official CEF files, backed up before replacing only `chrome_elf.dll` with
the validated CEF-aware build. Original Steam/helper/libcef hashes are in the
evidence record. This snapshot is a compatibility discriminator, not a claim
of current-client security or support. The isolated client has the recognized
`BootStrapperInhibitUpdateOnLaunch=Enable` setting was insufficient: a later
unlocked trial installed an already-pending October update and replaced the
source DLL before it could execute. That trial does not measure source-DLL
compatibility. Build88 additionally passes the recognized
`-nobootstrapperupdate -skipinitialbootstrap` only when the native owned layout
is active and the isolated AMD64 prefix is selected. Restore matched public
packages before retrying, never account/game/cache directories. Verify the
actual helper/libcef/source DLL hashes and allocation trace after launch.
No checksum, login, Steam Guard or license check is disabled. Preserve the
original configuration or record its absence for rollback. Full Steam UI
validation remains pending.

## Latest owned-layout and reporting discriminator (Build93)

The six-, eight-, nine- and eleven-region layouts are distinct experiments,
not release configurations. The former reporter-disabling test in Build89/90
is historical only. Automatic approval review rejected repeating a launch
that reduced crash diagnostics; Build93 removes that source switch. Keep
Crashpad enabled in every new full Steam trial.

Build92 places the separate512MiB code candidate at `0x70a0000000`, inside
the actual70xx module's4GiB reach segment, and keeps a separate512MiB
placeholder table region at `0x7700000000`. Exact pinned V8 code-range
source motivates this placement. Actual native and own Windows API tests
pass; actual V8 acceptance of this code candidate is still unverified.

Build93 adds two independent1GiB source-ELF pools for the exact crashpad child
role. The eleven native backing/22edge tests and own parent/eight-region plus
separate child/two-pool tests pass on Kusch. The genuine full trial also
adopts the child's two pools, then requests an additional16GiB libcef pool;
16/32GiB retries fail and the parent reports crash-server failure. Adding
these two pools alone does not solve full64 CEF startup. This failed bounded
session was identity-verified and stopped; no suspended app remains.

For reproducing this **known failing** startup, the actual environment is:

```json
{
  "MADEIRA_CEF64_SOURCE_LAYOUT": "1",
  "MADEIRA_CEF64_SPLIT_LAYOUT": "1",
  "MADEIRA_CEF64_NEAR_CODE": "1",
  "MADEIRA_CEF64_CRASH_POOLS": "1",
  "MADEIRA_STEAM64_DIRECT_CEF32": "0",
  "MADEIRA_STEAM_UI_STRICT_RESERVATIONS": "1",
  "MADEIRA_JIT_DUMP": "0"
}
```

Use `madeira-steam64-experiment` only after freshly verifying/ending the prior
exact app identity. Sample startup for a bounded interval, collect private
logs, then explicitly resume or terminate an intentionally paused trial.
CoreDevice timeout is not proof of app death, complete copying, or cleanup.
Never leave a retry loop copying multi-gigabyte logs. Leases are single-use
per native lifetime; helper restarts, additional reservations, sustained
FEX/game capacity, controller input and stable full64 UI remain gates.

The next reporting-preserving discriminator is the genuine standalone
Crashpad handler via CEF's documented `ExternalHandler` configuration. See
[the separate build and test recipe](../experiments/cef64/crashpad/README.md).
The local Mac cross-build route now produces AMD64 programs without publishing
source. Its own real handler registration and minidump test has passed on Kusch. No fake pipe server, no silent crash handler,
no stock Chromium base/PartitionAlloc in this separate handler. Native Windows/MSVC control is pending. Actual Steam overwrites the external
configuration on startup; Build95 tests a reversible file-attribute guard.
Genuine full64 CEF/UI validation remains pending.

Require actual AMD64 helper/libcef loading, BrowserReady, interactive UI,
library navigation, controller input, legitimate game launch and return before
claiming the complete path. Keep raw device logs, Valve binaries, accounts,
games, signing assets and crash dumps outside Git and public artifacts.

## Current102 discriminator (2026-10-29, experimental branch)

Use `experiment/steam64-cef64`; do not merge these uncompleted experiments into
the working baseline. Actual97/101 now render the genuine AMD64 CEF login UI.
In101, new Steam login Success/OK and CM logged-on response are artifact-backed,
but the native process subsequently exhausts its8GiB FEX arena at~68.5seconds.
Neither an authenticated desktop nor a stable full64 Big Picture/game loop is
validated. Full results/hashes are in IDECK_CEF64_SOURCE_EVIDENCE.json.

The successful101 login used all prior SOURCE/SPLIT/NEAR/CRASH gates, plus:

```json
{
  "MADEIRA_CEF64_MULTI_TABLES": "1",
  "MADEIRA_CEF64_EXTERNAL_CRASHPAD": "1",
  "MADEIRA_X64_IMAGE_NOCOPY": "1",
  "MADEIRA_CEF64_LIBCEF_DATA_ONLY": "1"
}
```

This retains normal client/support-module aliases while avoiding only the large
pure-AMD64 libcef copy. All normal image eligibility/safety gates still apply.
It is a diagnostic comparison, not a proven general mapping repair. Genuine
standalone Crashpad runtime binaries and the reversible config guard must be
prepared as described in its own recipe. Never disable reporting as a substitute.

Optional102 adds `MADEIRA_CEF64_WIDE_ARENA=1` only after all13-table-layout gates
are active. It changes only native hold3 from7400000000..7600000000 (8GiB) to
6000000000..7000000000 (64GiB), below guest furniture. Other12 real leases remain
identical. The existing versioned arena publication/consumer contract supplies
the exact range to the unchanged emulator. There is no overwrite, soft grant,
new entitlement, FEX edit or relaxed reservation failure. Capacity and actual
consumer behavior still need device tests; do not infer them from host tests.

First launch `madeira-cef64-layout-diagnostics` with
`MADEIRA_CEF64_LAYOUT_PROBE=wide-backing`. Require13 simultaneous real reservations,
26 boundary zero/write/read checks and complete cleanup. This still does not
prove every page committed or that FEX can execute a full session. Then use the
explicit normal/big-picture Steam64 argument with all documented gates, inspect
the actual published/consumed range, login/library/game/return and allocation
failure traces. Do not restore an overlapping15GiB arena or retry a used lease.

For the independent network discriminator, build `experiments/cef64/network-probe.c`
as AMD64 with LLVM-MinGW `-O2 -municode -static -Wall -Wextra -Werror
-Wl,--no-insert-timestamp -lwinhttp`. Stage it as `C:\\steam64-network-probe.exe`.
Use `madeira-cef64-component-diagnostics` and only
`MADEIRA_CEF64_NETWORK_PROBE=1`; this excludes other component diagnostics and
does not start Steam. Compare image-data0/1 in separate native lifetimes.
Preserve fresh result sentinels and record the probe's actual mode.

Build100 actually passes fresh tagged CRT/direct child exit7, HTTP/neutral TLS,
Steam time and versioned public CM directory200 in both modes. An unversioned
alternative returns404: overall result1 is preserved. Steam's shortened log
string is not a captured wire URI; do not claim that404 diagnoses its request.

##103: standalone reporter layout (capacity verified; full UI incomplete)

102's proposed low64GiB arena is rejected by the actual phone, Mach kr3.
Fresh early inventory reports a mapped PROT_NONE64..448GiB system/GPU region;
even64KiB requests there fail. Never overwrite/unmap that region. The inventory
completes despite a launch observer timeout; the timeout is not a Steam result.

103 instead repacks the existing usable high band. Actual101 never adopts the
old embedded-crash support holds9/10 after switching to genuine standalone
Crashpad. Under all preceding source/table gates plus
`MADEIRA_CEF64_EXTERNAL_CRASHPAD=1`, select
`MADEIRA_CEF64_STANDALONE_LAYOUT=1` and leave WIDE_ARENA unset. The two explicit
layouts are mutually exclusive. Missing external reporting fails before mapping.

| Hold |103 interval or role |
| --- | --- |
|0/1 | Source component pools unchanged |
|2 |8GiB cage unchanged,7200000000..7400000000 |
|3 | FEX7500000000..77ffff0000,12GiB minus64KiB |
|4/5 | Actual16GiB CEF pools and guard unchanged |
|6 |4GiB Oilpan7400000000..7500000000 |
|7 | Near-code512MiB unchanged |
|8 | First512MiB table7140000000..7160000000 |
|9/10 | Other tables71c0000000/71e0000000; not legacy crash pools |

The new Native metadata API identifies this geometry; consumers must not infer
legacy crash-pool roles from the presence of hold10. Bounds, alignment, existing
views, exact fixed addresses, one-time claims and rollback remain checked.
The unchanged emulator consumes the actual versioned published range. A generic
historical log label may still say16GB; check numerical published/consumed bounds.

Verify the actual installed build before each test. First Native argument
`madeira-cef64-layout-diagnostics`, environment
`MADEIRA_CEF64_LAYOUT_PROBE=standalone-backing`: require11 simultaneous holds,
22 backing edges and11 cleanup operations. Then stage the current own
`load-probe.c` executable and run the existing owned-contract component mode
with STANDALONE_LAYOUT1 and all preceding layout/reporting gates. The PE now
checks Oilpan7400000000 and first table7140000000. It explicitly omits legacy
embedded-child pools because those do not exist in this geometry: this is not
a passing legacy-child test. Run the genuine standalone Crashpad IPC/TLS-thread
exit/minidump smoke separately, under the same Native layout, before full Steam.

Host production boot/claim/rollback/geometry/role/fixed-address tests and37 native
units/full Xcode103/final linked markers/deep signing pass.103 is prepared but
NOT installed: the device trusted tunnel became unavailable (4016) before the
install. A subsequent capacity request failed at its file copy before launch.
No103 Native capacity, Windows, Crashpad, UI or game result is claimed. Preserve
accounts/games and public99 rollback; resume after physical reconnect.

2026-10-29 supersedes the prepared-only gate above:103 is actually installed.
Native11/22/11 backing and own Windows compact semantics pass, but the own cmd
exit remains incorrect. Genuine own reporter IPC/TLS-thread/localMDMP passes;
clean wrapper exit is not verified. Full AMD64 Steam/CEF logs saved-login
SuccessOK and survives beyond150s without the earlier FEX exhaustion, with
~3.5GiB arena free. Desktop content remains black and replacement webhelper
cannot reclaim the one-lifetime leases. No full64 usable BPM/game claim.
See the latest POC and exact hashed private artifacts before reproducing.

##104: isolate the shared x64 ROOT-store lifetime

Build the own `experiments/cef64/network-concurrency-probe.c` as AMD64 with
LLVM-MinGW `-O2 -municode -static -Wall -Wextra -Werror
-Wl,--no-insert-timestamp -lwinhttp -lcrypt32`. Stage it under the existing
component-network path `C:\steam64-network-probe.exe`. It sends only public
versioned CM-directory requests, logs counts/statuses rather than response data,
uses two children/two worker threads per process, fresh result nonces and bounded
waits. Preserve all three result files before another test. Do not enable verbose
TLS logging around real Steam authentication.

Use the103 standalone layout/reporting gates and explicit network-component
argument as above.104's `MADEIRA_CEF64_ROOT_STORE=1` additionally requires actual
held standalone metadata and Steam UI session1. It selects a non-destructive
x64 ROOT iterator private to each calling thread/PEB; retry-size requests keep
the same certificate and end-of-list resets the cursor. Trust bytes and normal
certificate verification are unchanged. The ordinary/WoW64 paths are unchanged.

Actual103 control:125roots in parent versus5in each child; parentHTTPS200,
children12157.104 with flag1:125roots in all3,12HTTPS200, fresh child exit7 and
parent/cmd0. Actual-source host test `python3 tests/host/check-cef64-root-store.py`
checks64simultaneous readers/retry/reset/owner/gates with ASan/UBSan. This closes
the own WinHTTP reproducer only; full Steam has a different network path and
needs separate login, visible browsing and game-return validation.

##106: fourth independent V8 table (experimental capacity tradeoff)

105 displays actual full64 Big Picture home, but at12:39:11 a fourth512MiB
ExternalEntityTable allocation fails; host/app existence and cached art are not
interactive UI proof. Explicit `MADEIRA_CEF64_FOUR_TABLES=1` after the existing
standalone/reporting gates changes only FEX to11GiB7500000000..77c0000000 and
adds a fourth real512MiB table77c0000000..77e0000000. Existing pool masks and
first3tables remain unchanged; no preserved/live lease is recycled.

Native capacity argument is unchanged, probe mode
`MADEIRA_CEF64_LAYOUT_PROBE=standalone-four-backing`. Require12 simultaneous
holds,24backed edges,12cleanup. Actual106 passes this, then current owned Windows
PE checks three extra independent table leases after the first, placeholders
and duplicate refusal, C result0. Its cmd exit1235017984 is still incorrect,
not silently reclassified. Own reporter106 IPC/TLS-thread/localMDMP passes; no
clean wrapper exit observed. Full runtime and smaller FEX game headroom still
require tests. A fifth isolate remains a capacity/lifetime question.

The read-only105 delay-load probe uses `MADEIRA_CEF64_DELAYLOAD_TRACE=1`, session1
and actual standalone layout. Exact CEF126 headers/code/structure gate only
public DLL/import names/numeric errors. It never handles/suppresses the fault,
logs arbitrary payloads or modifies Valve code.104's delay-load fatal remains
a separate unresolved failure; no matching105 decoder result was captured.


### Optional110 capacity discriminator

The108/109 six-table guest-band experiment failed full Steam startup even
though Native14/28 backing and ownWindows6table contracts passed. Do not use
that geometry as a working default. Existing Steam-only small-stack option
was observed active and did not resolve the failure. Chromium/game stacks
must not be reduced by listing their executables.

110 optionally adds `MADEIRA_CEF64_TABLES_FROM_ARENA=1` to the existing explicit
six-table/standalone/external-reporting experiment. It publishes a10GiB native
FEX arena `[0x7500000000,0x7780000000)` and uses disjoint table holds
`[0x7780000000,0x77a0000000)`, `[0x77a0000000,0x77c0000000)`. This changes no
FEX source, pool masks or guest semantics. The generic image/stack/heap band
is left free. Native capacity mode is `standalone-tail-six-backing`; fourteen
simultaneous holds,28 backed edge checks and14 cleanups must pass before the
same ownWindows6table test and full genuine client are attempted.10GiB may
still constrain browser and game capacity: no stability/game claim follows
from the successful capacity probes.

`MADEIRA_CEF64_LEASE_TRACE=1` now observes all guest-held regions except the
native FEX arena. Preserve/coalesce and complete release remain distinct; the
observer never clears claims. Read-only early native VM backing observations
now emit `contains`. Only `contains=1`, successful non-submap leaves classify
the target. Build109 low-range leaf output was incorrect and is not evidence
that any system mapping is safely reclaimable. Never unmap the GPU/system
carveout on this evidence.


###111 actual navigation;112 prepared eighth-table discriminator

Actual111 seven-table Native15/30/15 and ownWindows7distinct placeholder/commit/
free contracts pass (ownCresult0; cmd1235017984 still not a clean exit claim).
PhysicalDeviceHub virtualDpad changes selectedgame fromDeathtopia toHotRoads;
virtualA opens its actualSteamdetailpage. Inputstatus observed_changes6.
At13:52:07CEFfails the eighth512MiBtable before any newHotRoadsprocess appears.
All22releaseobserverrecords are preserve/coalesce with remainingview1; none is
an actual complete release. NativeFEX still has~2GiBfree. Do not recycle leases.

112prepares `MADEIRA_CEF64_EIGHTH_TABLE=1`, requiring explicitSEVENTH_TABLE1 and
all priorarena-tail/six/standalone/reportinggates. Existingholds retained;
FEX `[0x7500000000,0x7740000000)`9GiB, new8thtable
`[0x7740000000,0x7760000000)`. Mode`standalone-eight-backing` must pass actual
16simultaneousholds/32backededges/16cleanup, then ownWindows8distincttables,
then realSteamnavigation/game/return. Hostlayout/adoption tests cover all
holdfailures,duplicate/fixedidentity/ranges/refusal, gatefailure and16wayclaims.
No device112result follows frombuild. This finite demand experiment is not an
unboundedlongtermcapacitysolution; furtherliveisolate demand and games may
requiremoreaddressspace or source-builtABI-compatibleCEF with reducedcompiled
pool/tableconstants. Never shrink actualValvepool backing while leaving its
compiledmasksunchanged, overlapFEX, recyclepreservedplaceholders, or suppress
allocationfailures.

After111ended, wirelessCoreDeviceandDeviceHub becameunavailable. Restorefirst:
use the private `recover-experiment-baseline.py` with the exact111launchreceipt
when the paireddevice returns; it runsfreshgatedoriginalattribute restoration,
endsitsownidentity and verifiesglobal/CEFconfigbyte-readbacks. Theoldappis
confirmedended; originalreporterattributes/configrestorationisPENDING, not
successfullycompleted. Do not install/run112 before this gate. No logs, configs,
authdata,Valvefiles orsignedartifacts belonginGit.

### Optional compact source-pool discriminator (113)

After112 actually exhausts eight tables,113 tests
`MADEIRA_CEF64_COMPACT_SOURCE_POOLS=1` only with every previous eight-table,
standalone and external-Crashpad flag. It reverses the *source-built*1GiB pool
placement: regular714..718; BRP70ffff0000..714, including its64KiB guard before
710. The first table moves to718..71a and the ninth occupies71a..71c. The9GiB
FEX arena and stock CEF pool sizes/guards stay identical to112. This does not
assume arbitrary compiled masks or recycle a preserved placeholder.

Before a full launch, run the explicit native layout diagnostic with
`MADEIRA_CEF64_LAYOUT_PROBE=standalone-compact-nine-backing`. Require17simultaneous
holds,34backed edge checks and17cleanup records. Recompile the own AMD64 PE
from `load-probe.c`/`owned-contract.h`; the owned mode with the compact flag must
show9distinct tables and C result0. Inspect the outer process status separately
(the observed1235017984 mismatch is unresolved). Then verify the real source
ELF/official CEF consumes the correct intervals and test actual UI/game/return.

Actual-source host regression commands include:

```sh
python3 tests/host/check-cef64-layout.py
python3 tests/host/check-cef64-native-owner.py
python3 tests/host/check-cef64-owned-transfer.py
python3 tests/host/check-cef64-lease-trace.py
```

A ninth finite table is a measured capacity discriminator. It does not establish
long-term capacity, safe recycling, Bluetooth compatibility or full64gameplay.

113 same-binary native-stack discriminator: with the same nine-table flags,
`MADEIRA_THREAD_STACK_SPILL=1` enables the existing real kernel-pick fallback
for kernel/emulator stack requests bounded only by the4GiBfloor. Actual113
records16logged placements and avoids the no-spill run's1MiBemulatorstack failures;
CEF/game stacks retain their8MiBfloor. `tests/host/check-stack-spill.py` covers
exact opt-in and the unchanged floor policy. This does not provide a4GiBWoW
window for Steam's i386 x86launcher or guarantee more V8tables. Actual113still
exhausts a tenth table after a tracked hr.exe launch; no interactive game proof.

For a game returning STATUS_DLL_NOT_FOUND in this lab,114adds the explicit
`MADEIRA_STEAM_UI_MODULE_ERRORS=1` launch-only diagnostic. Under session1 it
selects `-all,err+module`; no trace, relay, process-argument or file-payload
channels are enabled, including with verbose1. Leave it unset for ordinary
runs. `tests/host/check-steam-ui-debug.py` compiles the actual bridge policy and
checks32gate combinations. Collect raw logs privately; publish only the named
public DLL/import and status. This switch does not install a missing library,
prove game compatibility or replace a genuine device test.


## Build117: opt-in native FEX arena placement experiment

The `MADEIRA_CEF64_FEX_PACK=1` flag requires both
`MADEIRA_STEAM_UI_SESSION=1` and `MADEIRA_CEF64_SOURCE_LAYOUT=1`. It changes
only the search direction for an unhinted request spanning the exact already
owned native FEX arena: requests below16MiB search from the top, larger requests
from the bottom. Sizes, alignment, protections, backing, ownership and release
rules stay intact. Narrow/foreign ranges and ordinary sessions keep the original
direction. It neither enlarges the arena nor guarantees sufficient capacity.

Run `python3 tests/host/check-cef64-fex-pack.py` for production policy and Wine
gap-search tests under ASan/UBSan, then the existing ownership/layout/census/
code-reclaim/low-image regressions. Rebuild the native archive before Xcode.
This checkout reuses generated Wine headers from
`../Madeira/wine/build-macos` read-only; do not assume `wine/build-macos` exists.
The private build117script changes only those two build path variables; no
primary checkout source or generated resource is modified.

Inspect `[cef64-fex-pack] full native arena=` in the FINAL signed debug dylib
and in the actual session log. A linked marker is not evidence the branch ran.
Require current identity, actual signed-pool placement and real regionC before
a game request. Compare against the same layout/CPU/image settings with PACK0.
The source-built CEF layout and standalone Crashpad flags remain experimental;
this is not a product default or an entitlement workaround. Gameplay, controller
response, game-return and longer browsing still require actual tests.


## Build118: retain the lower signed code region

`MADEIRA_CEF64_KEEP_LOW_POOL=1` requires the exact session/source-layout gates
above. With `pool-split=1` and the executable window held, it allows the existing
upper A/B pair even when a larger single lower run fits. Ordinary selection
optimizes only A+B and can eliminate C; actual117had upper285/276/297MiB versus
lower611MiB. The opt-in retains all existing size minima, requested budget,
window exclusion, actual debugger mapping and fallback checks.

`python3 tests/host/check-cef64-pool-plan.py` compiles the actual Swift gate and
selection loop against those measured holes. Run existing `check-pool-split.py`,
`check-pool-low.py` and `check-pool-startup-budget.py` too. The final signed
debug dylib and current device log must contain `[cef64-pool-plan]`. Existing
`pool-mid=1` can use a third upper region within the same total requested budget;
C remains separately sized with its low-image margin. Do not add their virtual
span as usable memory: native mappings/holes between A/M/B are excluded.
Actual A/B/M/C capacity, then Steam/game execution remain required.


## Build119: relocatable game DLL image spill

`MADEIRA_CEF64_IMAGE_SPILL=1` requires the isolated owned `wine-steam64` layout
and `MADEIRA_CEF64_SOURCE_LAYOUT=1`. After ordinary PE-image placement returns
`STATUS_NO_MEMORY`, a relocatable64-bitDLL up to64MiB may use the measured
non-compact source-layout gap `[0x7160000000,0x717fff0000)`. Only a current
process under `steamapps/common/` qualifies. Each native hold is checked for
overlap; compact or unknown extra layouts refuse. Explicit caller constraints,
WoW32, fixed-base images, Steam/CEF and ordinary sessions retain existing
behavior. Existing `map_view` validates all live kernel/Wine mappings; nothing
is overwritten, unprotected, reclaimed or synthesized. Later relocation and
signed executable-copy steps must still succeed.

Run `python3 tests/host/check-cef64-image-spill.py`, the fixed-guard/owned
transfer/native-owner regressions, rebuild the native archive and full app.
Verify `[cef64-image-spill] prior=` in final signed Mach-O and actual logs.
Require the mapping's success status, actual D3D11DLL load, then game rendering
and input; a successful memory map alone is not usable-game validation.
This is an opt-in diagnostic, not a promise that total address/physical memory
is sufficient. Preserve account/game/save data when upgrading the isolated app.
