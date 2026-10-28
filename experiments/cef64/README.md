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
python experiments/cef64/prepare.py chromium126
```

The preparation script requires exact upstream HEAD and an unmodified tracked
tree, checks the original allocator-header SHA256, and changes only the two
core-pool constants. No FEX or proprietary binary is patched. It narrows the
root GN target to chrome_elf; use Chromium's pinned GN, LLVM and DEPS inputs.
Do not disable allocator/BRP checks or fabricate reservations on failure.

The focused BUILD.gn overlay omits unrelated test targets and relocates the
unchanged one-header `content/public/common:result_codes` dependency into the
ELF build file. This avoids generating the complete unused Content/UI graph;
production C++ source files remain unchanged except for the two pool constants.
The builder runs the upstream LASTCHANGE hook and verifies its real pinned
commit, rather than inventing version stamps.

The same treatment retains the exact Windows service-resolver/common,
Sandbox common/buildflags and NaCl buildflag target bodies. Their unrelated
integration tests and unused renderer targets are omitted from this component
build. Unsafe-developer mode is explicitly false; production security flags
in the retained targets are unchanged. Windows compilation remains a gate.

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
