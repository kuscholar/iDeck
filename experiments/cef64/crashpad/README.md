# Reporting-preserving standalone CEF64 Crashpad experiment

The genuine Build93 Crashpad child adopts its two independent source-ELF
1GiB pools, then loads official libcef and requests another16GiB pool. That
request and its32GiB fallback fail. The parent reports a broken crash-server
connection and terminates. No interactive full64 Steam result is claimed.

Single hypothesis: CEF's documented `ExternalHandler` avoids loading a second
libcef by starting the genuine standalone Crashpad handler. The handler must
still register the real IPC connection and produce real minidumps. A fake
pipe server, assertion bypass, or disabling crash reporting is not acceptable.

## Exact public sources

- Crashpad `1174aa4fc3196f478b5b4b77fc970d1cb85cb7cf`, as recorded in
  Chromium126's `third_party/crashpad/README.chromium`.
- CEF `a5d51ba9db7ee74a523dc247bd09ec91ba4d7446`, with the **complete eight-file**
  `crashpad_tp_1995.patch`, SHA256
  `e1474ca60831144a5c096e8dcd3f8e0a36307b55ceb1ab63fe45883dcd396d85`.
- The standalone Crashpad DEPS pins mini_chromium
  `a6607b1fd76b740f31c2249fef2c0bec27ffbe52`, zlib
  `fef58692c1d7bec94c4ed3d030a45a1832a9615d`, googletest
  `af29db7ec28d6df1c7f0f745186884091e602e07` and GN
  `5e19d2fb166fbd4f6f32147fbb2f497091a54ad8`.

The build uses `crashpad_dependencies="standalone"`, not Chromium `//base`.
Its resolved handler graph is checked for an accidental full Chromium
base/PartitionAlloc dependency. Complete CEF upload filtering, backoff,
settings-v2, database retention and optional-argument behavior are retained.
The adaptations are build paths, unconditional inclusion of that CEF policy,
include rebasing and a Chromium-equivalent string-pair parser absent from
mini_chromium. Host tests check the actual CEF filter against malformed and
multi-part key maps under ASan/UBSan and reverse the source adaptations to
verify original hashes.

CEF's patched Windows launcher adds `--type=crashpad-handler` even for an
external program. Its own `RunAsCrashpadHandler` removes this role before
calling `HandlerMain`. This program accepts at most that one exact role,
retaining all IPC, reporting, database and monitor arguments. Duplicate or
different Chromium roles fail. It does not discard unknown Crashpad options.

## Build and real Windows test

Use a fresh disposable directory and official Visual Studio2022 C++/Windows
SDK tools. Never use a working Steam or Chromium directory as the source tree.
From the iDeck repository:

```powershell
python -m pip install ninja==1.11.1.1
python experiments/cef64/crashpad/prepare.py crashpad-test --cef-checkout cef-source
python tests/host/check-cef64-crashpad.py --source crashpad-test --source-only
python experiments/cef64/crashpad/build.py crashpad-test
```

The builder generates and compiles the real handler and own smoke program,
checks AMD64 PE output, starts it with the CEF role/options, registers through
the real Crashpad client, requests `DumpWithoutCrash` and requires a real
`MDMP` file from the database. The outer test has a60second timeout. Only this
own test uses an empty upload URL and disables uploads in its own fresh
database; it has no Steam input or production configuration. A categorical
validation receipt is packaged only after the full Windows test passes.
Raw dumps are deliberately excluded from Actions artifacts.

The Windows workflow is
[cef64-crashpad.yml](../../../.github/workflows/cef64-crashpad.yml).
It has not run for this candidate yet. A Mac `--host-compile` build verifies
source/link compatibility only and cannot establish Windows IPC or iOS
behavior. It uses macOS14 deployment and leaves local SDK deprecation
warnings visible instead of treating them as errors; Windows flags are
unchanged. The Mac smoke executable exits77 without claiming a Windows test.

## Local Mac cross build: no publishing required

The GitHub worker is optional. The local LLVM-MinGW toolchain can generate
AMD64 Windows programs directly on a Mac. A clean second source-tree cross
build has completed without a commit, push, or workflow dispatch.

```sh
python experiments/cef64/crashpad/mingw_build.py \
  --source /absolute/prepared-crashpad \
  --output /absolute/new-disposable-cross-build \
  --tools /absolute/llvm-mingw/bin \
  --gn /absolute/pinned-mac-gn
```

Use the same prepared public source, pinned GN above and Ninja1.11.1.1. The
actual local toolchain was llvm-mingw20260421-ucrt-macos-universal. This
experimental GN adapter requires paths without whitespace and a new output
directory. It clones the prepared directory with APFS copy-on-write, leaving
the original untouched. No source upload is involved.

Deploy the separate `out/ideck-mingw/runtime/` programs. The unstripped originals
remain beside that directory for private debugging. `mingw_build.py` removes
DWARF sections from runtime copies only, then verifies every non-debug section's
bytes, RVA, size and flags, executable headers, actual TLS callback, unwind data,
CPADinfo and imports. Madeira copies an entire PE `SizeOfImage`: GNU debug data
made the original handler request about24MiB despite only about1.3MiB of runtime
sections. The compact handler has the same runtime code and failure checks.
`runtime/runtime-integrity.json` records the exact artifacts. Neither this
packaging check nor independent build IDs establish a Windows/iPhone runtime pass.

To repeat the artifact checks (including a mapped-code corruption discriminator):

```sh
python tests/host/check-cef64-crashpad.py --source /absolute/prepared-crashpad \
  --mingw-build /absolute/new-disposable-cross-build/out/ideck-mingw \
  --mingw-tools /absolute/llvm-mingw/bin
```

MinGW platform differences are explicit: standard include-next forwarding,
GNU equivalents of the original TLS and CPADinfo sections, the upstream
assembly via llvm-ml with its one C++ ABI symbol renamed, and missing SDK
minidump declarations taken from the **same upstream Crashpad** with exact
size assertions. Windows UTF16 fields stay16bit; original dynamic
InitializeContext2 lookup/fallback stays intact. No Windows function is
stubbed. Format/sign warnings remain visible; the upstream zero-initializer
and unused-parameter diagnostic policy is retained. Final PE checks require
the actual thread callback in the TLS array, unwind metadata, handler
CPADinfo and no CEF/dynamic C++ runtime import.

This is a separate compiler configuration, not a native Windows/MSVC runtime
pass. The actual iPhone own test now passes thread-exit destruction, real
Crashpad registration and real local minidump creation. A retrieved16774888byte
report also validates its header, stream directory/ranges and actual system,
misc, thread, exception and module streams. The outer native Wine wrapper
reported exit1 after a child exit0; do not claim a clean overall exit0 from
this test. Full genuine Steam CEF/UI is still a separate gate.

## Isolated iPhone tests and actual configuration rewrite

1. Preserve the isolated app identity, auth, games and saves. End any prior
   exact lab process before another experiment; do not act on a stale PID.
2. Stage the verified `crashpad_handler.exe` and `crashpad_smoke.exe` under
   `C:\iDeckCEF64Crashpad`. Build94's explicit
   `madeira-cef64-component-diagnostics` plus
   `MADEIRA_CEF64_CRASHPAD_PROBE=1` creates a fresh own database every run.
   Require real registration and a retrieved valid minidump. It starts no
   Steam and uses no Steam inputs. Own dumps remain private.
3. Back up the actual helper-adjacent `crash_reporter.cfg` privately. Use
   `configure.py --input original.cfg --output candidate.cfg` to add only the
   fixed ExternalHandler line; verify all original bytes are preserved.
4. Actual Build94 full Steam startup **rewrote that candidate back to the
   byte-identical378byte stock config**, deleting ExternalHandler. The real
   external handler was never launched; the old embedded child repeated the
  16/32GiB failure. This is not a failure of the newly tested handler.
5. Build95 adds an opt-in configuration-write discriminator. Compile the own
   `config_guard.c` with the same x64 llvm-mingw C toolchain using
   `-O2 -municode -static -Wall -Wextra -Werror`, and stage `config_guard.exe`
   beside the other own programs. Its fixed target is ONLY the isolated
   `C:\Program Files\Steam\bin\cef\cef.win64\crash_reporter.cfg`.
   It saves the exact original file attributes, requires the exact handler
   line, sets the Windows read-only attribute, and tests OPEN_EXISTING write
   refusal without writing/truncating. A failed contract aborts Steam startup.
   This is file configuration protection, not a VM protection workaround or
   a disabled reporter. All original report URL/keys/policy remain intact.
6. `MADEIRA_CEF64_EXTERNAL_CRASHPAD=1` requires the existing owned source
   layout, isolated AMD64 prefix, and both own AMD64 programs. The batch
   restores a prior attribute marker first, protects the reviewed config,
   launches genuine Steam, then restores attributes on normal return. An
   exact app kill may prevent that last command; cleanup is mandatory.
7. Explicit component diagnostics plus `MADEIRA_CEF64_CONFIG_RESTORE=1`
   restores the recorded attributes without starting Steam or the own dump
   test. A later launch with the experimental flag off also restores the
   pending marker before Steam. Privately restore the original config bytes
   after attributes are restored. Never delete auth/game/report directories.
8. Require actual new external-handler process/module and handshake evidence,
   then evaluate V8 allocation, BrowserReady, UI/controller/game/return. A
   compile, own-handler success, read-only attribute or elapsed timeout does
   not prove these later gates. Native Windows control remains useful but
   is not a prerequisite for a local bounded iPhone own experiment.

Actual95c preserves the candidate config and attempts the genuine external
handler. Its24MiB image cannot fit the measured8.06MiB largest free range in the
effective560MiB main image pool; later DLL loads also fail with STATUS_NO_MEMORY.
Trial96's compact own reporter independently passes actual iPhone TLS destruction,
real registration and local minidump creation again. Full64 integration/UI remains
a separate gate. Work now continues on `experiment/steam64-cef64`; no publication
is required to reproduce these local experiments.

## Licensing and validation boundary

Crashpad retains Apache2.0; CEF and mini_chromium retain their BSD notices;
zlib retains its license. `CHROMIUM-LICENSE` accompanies the parser derived
from Chromium's string-split behavior. New iDeck-authored scripts/tests use
the repository's GPL3-or-later and Madeira Converter Exception for their own
work only. The artifact copies upstream notices and reproducible build
scripts. Preserve the full source/dependency revisions for any distribution.
No Valve binaries, crash dumps, credentials, signing assets or game data are
inputs to or outputs of this public build.
