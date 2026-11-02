# Source-built 64-bit CEF support component

Latest physical-device checkpoint: [Build 135](../../docs/CEF64_BUILD135_MILESTONE.md)
removes the blocking child notice and records two normal game exits; the third
launch fails image placement and CEF later exhausts its table bank. Repeated
stability remains unresolved. The exact tested private FEX component is excluded
from this public source checkpoint; see the evidence boundaries in that report.

This is an isolated experiment, not a shipped runtime change. The working
AMD64 Steam + official i386 CEF path remains available.

The actual AMD64 startup trace attributes two 16 GiB reservations to
`chrome_elf.dll` and two more to `libcef.dll`, all in the SAME guest process.
Reducing the guest process count therefore cannot remove these four initial
reservations. The upstream precompiled chrome_elf from CEF
126.2.18+g3647d39 / Chromium126.0.6478.183 was downloaded, package-SHA1 checked,
and disassembled. Its initialization also reserves two16GiB pools. It is not
a lower-demand replacement.

Hypothesis: source-building ONLY chrome_elf with1GiB regular/BRP pools reduces
that module's reservation demand from32GiB to2GiB without changing Valve's
libcef, Steam authentication, or allocator failure/refcount checks. Chromium
derives pool masks from these compile-time sizes. Windows and iPhone component
tests now pass; genuine complete Steam CEF/UI compatibility remains a
hypothesis. Smaller capacity can
exhaust; entropy/capacity/security effects require review before distribution.

The complete Valve libcef has custom API exports; replacing it with stock CEF
is not an established ABI-compatible route. In contrast, all15 chrome_elf names
imported by the actual Valve libcef are in upstream Chromium126's x64 export
definition. Export names alone do NOT prove structure/behavior compatibility.
The install-details payload and crash-reporting contracts must also be tested.

## Reproduction

Use a new disposable Chromium checkout on a Windows worker with the official
Visual Studio/Windows SDK tools already installed. Do not put Steam/account
files in this checkout. Never apply this script to a working Chromium tree.

```sh
git clone --depth 1 --filter=blob:none --sparse --branch 126.0.6478.183 \
  https://github.com/chromium/chromium.git chromium126
python experiments/cef64/prepare.py chromium126 --cef-glue
```

The preparation script requires exact upstream HEAD and an unmodified tracked
tree, checks the original allocator-header SHA256, and changes only the two
core-pool constants in the allocator. No FEX or proprietary binary is patched. It narrows the
root GN target to chrome_elf; use Chromium's pinned GN, LLVM and DEPS inputs.
Do not disable allocator/BRP checks or fabricate reservations on failure.

The focused BUILD.gn overlay omits unrelated test targets and relocates the
unchanged one-header `content/public/common:result_codes` dependency into the
ELF build file. This avoids generating the complete unused Content/UI graph;
Allocator C++ source remains unchanged except for the two pool constants.
The builder runs the upstream LASTCHANGE hook and verifies its real pinned
commit, rather than inventing version stamps.

The same treatment retains the exact Windows service-resolver/common,
Sandbox common/buildflags and NaCl buildflag target bodies. Their unrelated
integration tests and unused renderer targets are omitted from this component
build. Unsafe-developer mode is explicitly false; production security flags
in the retained targets are unchanged.

### CEF crash-contract variant

Control build [40632409115](https://github.com/kuscholar/iDeck/actions/runs/40632409115)
successfully compiled the AMD64 DLL. Its actual Windows load test found all15
required exports and two1GiB private pools, with no new16GiB reservation.
This is not Steam or device success. It uses stock Chromium crash integration.
Repeat control build40633251602 also passed the actual payload gate
(size80, version-match1, mode-size192) and reproduced the identical DLL SHA256
`7dee97bd5ea0a363a68304b71ea4f8d9cbdac0647f716db59639f79f51989cab`.

Source inspection confirms that CEF instead uses `CefCrashReporterClient`,
reads its crash configuration, and supplies different handler/optional-argument
contracts. The `--cef-glue` variant applies the complete published
[CEF crashpad patch](https://github.com/chromiumembedded/cef/blob/a5d51ba9db7ee74a523dc247bd09ec91ba4d7446/patch/patches/crashpad_1995.patch)
at exact CEF revisiona5d51ba9db7ee74a523dc247bd09ec91ba4d7446, whose compatibility
file requires this same Chromium tag. All ten patched files, the patch hash
and exact retained CEF/crash target bodies are checked. Official version
generation uses actual Git ancestry; BSD notices remain with upstream code.
No crash check is suppressed. This is a separate compatibility hypothesis,
not an observed explanation for a device failure of the control DLL.

CEF-aware run40638006082 passes the actual Windows browser/renderer load tests.
Its AMD64 DLL SHA256 is
`673584661cd0044b186e40286b3d57a099b45002d3fc50f334ae1d3d14bc7621`.
The same DLL also passed both role-specific component probes on Kusch.
Matching payload/export checks do not establish
Valve's complete runtime contract; genuine helper/CEF/UI tests remain gates.
The focused CEF target also explicitly depends on the original V8 buildflags
generator required by `content_switches.h`; it does not synthesize that header
or build a replacement V8 snapshot. See [the build recipe](../../docs/CEF64_BUILDING.md).

## Actual native layout evidence

Kusch Build83 simultaneously reserved all six proposed disjoint regions,
57GiB+128KiB total, with exact fixed/no-overwrite results and successful
cleanup. Build84 repeated with maximum RW protection and successfully
zero-tested, wrote and read twelve freshly allocated edge data pages, leaving
the BRP guards untouched, then released every mapping. The host fixtures also
check every slot/edge refusal, wrong returned address and cleanup failures.

```sh
python3 tests/host/check-cef64-layout.py
```

These tests do not give Wine ownership of the regions and do not prove
full-range physical backing, executable permission, FEX consumption or CEF/UI
success. Production remains unchanged. Explicit device diagnostic:
`madeira-cef64-layout-diagnostics` plus `MADEIRA_CEF64_LAYOUT_PROBE=1` for
reserve-only, or `backing` for the bounded own-page test. No Steam/JIT/login
is started. Raw results stay private; hashes are in
docs/IDECK_CEF64_SOURCE_EVIDENCE.json.

The build, Windows loader and separate iPhone component tests have now passed.
The next gate is genuine AMD64 Steam/helper/libcef startup, visible interaction,
Big Picture and game launch/return. The matched official CEF directory was
privately backed up before staging only the source support DLL in the isolated
test prefix. Full Steam launch was refused by the native device lock; it has
no runtime result yet. Keep original component hashes and rollback. A successful
DLL load is not Steam UI success. Publish source, exact build inputs and
applicable BSD notices if the experiment reaches binary distribution.

## Opt-in ownership discriminator (Build85)

The six native holds have a separate experimental ownership-transfer path.
Enable `MADEIRA_CEF64_SOURCE_LAYOUT=1` together with an explicit
`madeira-cef64-component-diagnostics` launch argument. The native constructor
requires both; Wine additionally requires Steam UI session1 and the isolated
`wine-steam64` prefix. Ordinary launches keep their existing layout.

Set `MADEIRA_CEF64_OWNED_CONTRACT_PROBE=1` for the first test. Build the own
AMD64 PE from `load-probe.c` and `owned-contract.h`, stage it as
`drive_c/steam64-cef-load-probe.exe` in that prefix, and start a fresh paired
JIT session. The fixed batch writes `drive_c/madeira-cef64-load-results.txt`.
It reserves/queries all five guest regions, commits two data pages per region,
checks zero/write/read, rejects a duplicate, and releases its own views. It
loads no Valve module and does not authenticate or launch Steam. All five
exact addresses and every check must pass. Inspect the native log separately
to confirm that FEX actually consumes the published15GiB arena.

```sh
python3 tests/host/check-cef64-native-owner.py
python3 tests/host/check-cef64-owned-slots.py
python3 tests/host/check-cef64-owned-transfer.py
python3 tests/host/check-steam-ui.py
```

These host checks compile the production native hold/claim code and Wine
adoption function with fixtures, including rollback and a16thread claim race.
Build85 compiled37native units and the full app, passed linked-marker/deep-signing
checks, and installed. After physical unlock, its actual Windows ownership
probe passed all five exact reservations, ten edge-page commit/zero/write/read
checks, duplicate refusal and all five releases. FEX initialized with an
allocation inside the real15GiB arena. Source-DLL browser85 and renderer87
probes both passed payload80/version1/mode192,15exports and two1GiB pools.
Set `MADEIRA_CEF64_PROBE_RENDERER=1` only for the separate renderer component
probe; it is rejected together with the ownership selector. These are actual
device component/API results, not genuine CEF rendering or Steam UI results.

This is not a finished general-purpose broker: claims are single-use for the
native app lifetime; helper restart/reclamation, conflicting legacy arena
options, fixed-address hint semantics, dynamic pool growth and other hardware
remain gates. A failed boot hold refuses this experimental Steam/probe launch;
reopen without the explicit option to use the preserved working layout. Do not
silently grant overlapping ranges or weaken Chromium failure checks.

## Historical split-layout gate (superseded by results below)

Actual88/89 source64 startup adopts the source1GiB pools and original16GiB
CEF pools; it still fails before a usable Steam UI. The89 own Windows test
proves generic4GiB requests cannot replace FEX backing. Optional official
`-cef-disable-breakpad` removes crashpad admission in a bounded trace; it
does not solve V8's additional reservation failures. Existing single-process
policy was already active.

Opt-in90 separates real FEX8GiB from new4GiB and512MiB V8 holds. Native
eight-region backing and actual seven-region Windows ownership tests pass.
Full90 Steam has not launched: a subsequent snapshot lost CoreDevice and its
SIGCONT attempt failed, then fresh availability returned4016. The completed
probe may be suspended; reconcile its actual identity/state on reconnect
before launching anything. Do not reinstall or repeat passing probes.
See [the current recipe](../../docs/CEF64_BUILDING.md) and the evidence JSON
for exact flags, artifact hashes, limitations and remaining UI/game gates.


## Reporting-preserving standalone Crashpad

Actual Build93 proves that two extra1GiB crash-child support pools alone are
insufficient: the real child next requests another16GiB libcef pool and fails.
Its failed bounded session was stopped after identity verification. Full64
Steam UI is not validated. Build92's corrected near-code candidate passed
native/own Windows contracts, but actual V8 acceptance remains a gate.

The [standalone Crashpad experiment](crashpad/README.md) uses CEF's documented
ExternalHandler with the genuine handler and complete public CEF crash policy.
Pinned-source/filter/entry/config checks and the local cross-build pass. Its
actual iPhone registration, TLS thread-exit callback and real own-process
minidump test pass. Compact runtime copies remove only own debug sections,
checking all mapped non-debug sections and retaining private symbol originals.
These tests do not prove the full CEF/reporting lifecycle. The reversible
config attribute guard preserves ExternalHandler during the isolated trial;
original attributes/bytes are restored and checked afterward. A disabled/fake
reporter remains unacceptable.

## Current CEF64 gate: login rendered, connection pending

Build97 on Kusch actually adopts three separate512MiB V8 tables, preserves
their placeholder ownership and displays Valve's genuine AMD64 CEF login
animation. The earlier ExternalEntityTable OOM is absent in that bounded run.
However, Steam remains WaitingForServerResponse after scheduling its public
CM directory request. There is no new authenticated library/Big Picture/game
success. Another task's intervening public Build99 was identified and excluded
from these experimental results. See the evidence JSON and POC results.

The own three-table test passes its specific reservations/read-write checks,
but its child exit status is anomalous; do not label the entire test PASS.
Build100 adds `network-probe.c`: two fresh tagged child exit tests (CRT return
and direct ExitProcess), public HTTP, HTTPS, server time and both directory
URL forms. It logs only numeric outcomes and byte counts, never response
bodies, addresses, credentials or account data. Certificate checks stay enabled.

Compile it with LLVM-MinGW using `-O2 -municode -static -Wall -Wextra -Werror
-Wl,--no-insert-timestamp` and `-lwinhttp`. Place the AMD64 executable at
`C:\\steam64-network-probe.exe` in the isolated prefix. Launch the experimental
app with argument `madeira-cef64-component-diagnostics` and environment
`MADEIRA_CEF64_NETWORK_PROBE=1`. This mode excludes all other component tests,
does not start Steam and writes `C:\\madeira-cef64-network-results.txt`.
Use separate native lifetimes to compare the existing image-data option0/1;
record the option reported by the actual probe and retain a fresh sentinel.
Build100 compilation/final-link/signing alone is not device test success.


Full64 progress after103: an own CryptoAPI/WinHTTP parent/child discriminator
reproduced destructive shared ROOT enumeration; gated immutable per-reader104
passes all12HTTPS requests with125roots in each process, while opt-out fails.
This is not proof it caused every Steam network stall.105/107 display genuine
AMD64 Big Picture home but eventually need more distinct512MiBV8tables.107
continuous trace confirms preserved placeholders remain owned; never recycle
them.108/109 reserve6tables but starve genericguestVA.110 tests disjoint tables
in the old FEX tail with10GiBFEX and explicit gates. See source evidence and
POC results for actual device limits; no full64game/returnGO yet. All source,
trust/auth/reporting and proprietary-binary restrictions above remain.


### Direct3D loader/device probe (prepared, not device-run)

`d3d11-probe.c` is our own AMD64 PE. It loads `d3d11.dll` at runtime and calls
`D3D11CreateDevice`, writing `C:\ideck-d3d11-results.txt`. A load failure and
a device-creation HRESULT are different gates; success proves neither rendering
nor game/controller compatibility. The recorded Win32 error is meaningful for
a failed API call only. No account/authentication/Valve/game input is read.

```sh
"$LLVM_MINGW/bin/x86_64-w64-mingw32-clang" -std=c11 -Wall -Wextra -Werror \
  -O2 -municode -static -Wl,--no-insert-timestamp \
  experiments/cef64/d3d11-probe.c -o /tmp/ideck-d3d11-probe.exe
"$LLVM_MINGW/bin/llvm-readobj" --file-headers --coff-imports \
  /tmp/ideck-d3d11-probe.exe
```

The compiled file must be AMD64 and must not import D3D11statically, so loader
failure is observable. For the Build119game-owner spill experiment, stage only
in a new own diagnostics directory under `steamapps/common/`; do not replace
any installed game files. Invoke manually from the isolated Windows session
after JIT; no automatic launch argument is wired. To claim the fallback runs,
require actual `[cef64-image-spill]` success plus DLL load. A quiet-prefix load
that never reaches the fallback is only a baseline result.
