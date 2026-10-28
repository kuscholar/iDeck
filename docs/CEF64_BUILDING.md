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

The six-region geometry is measured only on Kusch. Build83 capacity and84
bounded backing passed; these are not proof of executable permission, guest
ownership, FEX consumption or CEF rendering. Build85 installed but its first
ownership launch was refused by native lock. Build86 is prepared, signed and
not installed over that pending test; it avoids the old V8 fixed-zone service
that collides with this experimental ELF BRP pool. Actual V8 reach remains a gate.

Only after these discriminators pass should a separate genuine Steam trial
use a matched official client/helper/libcef resource tree, with original public
files backed up and hashes recorded privately. `MADEIRA_STEAM64_DIRECT_CEF32=0`
disables the hybrid redirect for that trial. Existing saved authentication stays
in the same isolated prefix; do not transfer login caches or automate Guard.

Require actual AMD64 helper/libcef loading, BrowserReady, an interactive UI,
library navigation, controller input, legitimate game launch and return before
claiming a complete path. Fixed-hint semantics, helper restarts, extra pools,
other hardware and sustained stability remain unverified. This recipe is not
a product release. Keep raw device logs and all Valve/signing/auth payloads out
of Git; publish only redacted evidence. Preserve upstream BSD notices and the
project's existing component licensing requirements.
