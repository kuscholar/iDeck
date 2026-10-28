# Source-built 64-bit CEF support component

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
derives pool masks from these compile-time sizes. This is a hypothesis until
the component builds and passes Windows/device tests. Smaller capacity can
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

The CEF-aware Windows build and browser/renderer load tests must pass before
that variant can be staged. Matching payload/export checks do not establish
Valve's complete runtime contract; genuine helper/CEF/UI tests remain gates.

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

Next build/test gates: resolve focused GN dependencies and Windows toolchain;
build the DLL; verify PE AMD64/imports/exports and changed allocation constants;
run an isolated load/heap/thread probe; then use a separate test directory on
Kusch before touching the preserved working browser files. Keep original
component hashes and rollback. A build or successful DLL load is not Steam UI
success. Publish source, exact build inputs and applicable BSD notices if the
experiment reaches binary distribution.

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
They do not prove actual iOS permissions or Windows API behavior. Build85
compiled37native units and the full app, passed linked-marker/deep-signing
checks, and installed; the first launch was refused because Kusch was locked.
No ownership/FEX-consumption/device CEF result is available yet.

This is not a finished general-purpose broker: claims are single-use for the
native app lifetime; helper restart/reclamation, conflicting legacy arena
options, fixed-address hint semantics, dynamic pool growth and other hardware
remain gates. A failed boot hold refuses this experimental Steam/probe launch;
reopen without the explicit option to use the preserved working layout. Do not
silently grant overlapping ranges or weaken Chromium failure checks.
