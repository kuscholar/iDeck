# Owned AMD64 data-image execution experiment

Build138 is a hypothesis test, not a proven gameplay fix. Build137's real second
Hot Roads process fails a22.047MiB UnityPlayer executable-pool copy. The canonical
DLL section/query succeeds. Repeated large pool copies consume scarce contiguous
native executable storage. The existing data-image path already runs libcef at
its PE address through FEX; retain all Steam/client/support aliases and test that
same existing route only for UnityPlayer, under explicit isolated layout flags.
No Valve/game bytes, FEX implementation or native reservation guards are changed.

`MADEIRA_CEF64_UNITY_DATA_ONLY=1` adds only the exact UnityPlayer.dll basename to
the existing libcef-only policy. It is off by default and requires the existing
session/owned-layout policy. All outer eligibility still applies: AMD64 PE32+,
not hybrid/ARM64EC, builtin, resource-only or WoW64. Do not generalize this to all
DLLs: historical Steam client alias failures remain a separate contract.

Before genuine gameplay, exercise `MADEIRA_CEF64_IMAGE_DATA_PROBE=1` in a fresh
isolated component diagnostic. It adds only the owned `ideck-x64-image.dll`.
The source-built DLL has24MiB BSS, code exports, writable state, Windows static
TLS and a callback into its caller. The driver executes32calls per round, checks
independent worker-thread TLS and performs two rounds in three child processes.
First round explicitly unloads; the last intentionally leaves the DLL loaded at
child exit. This is an execution/ABI/lifetime check, not just a PE mapping test,
and not proof Steam/game rendering works.

Build with the pinned LLVM-MinGW toolchain, outputting privately outside Git:

```sh
"$LLVM_MINGW/bin/x86_64-w64-mingw32-clang" -O2 -Wall -Wextra -Werror \
  -fno-emulated-tls -shared experiments/cef64/image-execution-dll.c \
  -o /private/build/ideck-x64-image.dll
"$LLVM_MINGW/bin/x86_64-w64-mingw32-clang" -O2 -Wall -Wextra -Werror \
  -municode experiments/cef64/image-execution-probe.c \
  -o /private/build/image-execution-probe.exe
```

Verify AMD64 headers, SizeOfImage and nonempty TLS directory. Stage the DLL at
`C:\iDeckCEF64ImageProbe\ideck-x64-image.dll`. Back up the existing owned component
probe before temporarily staging the driver as `C:\steam64-cef-load-probe.exe`.
Launch `madeira-cef64-component-diagnostics` with the probe flag, using the
preserved isolated prefix. The driver accepts the launcher's exact fixed argument
without loading it. Results go to `C:\madeira-cef64-load-results.txt`. Require
all child exits0, six round PASS records, final result0, and actual native evidence
that the owned DLL used the data-image route. Do not count compilation, a prior
results file or process existence as PASS. Restore and hash-verify the previous
probe executable before regular Steam. Never replace Steam/game executables.

Only after that discriminator, enable the Unity flag in the selected runtime's
`steam64.env.*` local configuration and test actual game/exit/navigation cycles.
Require absence of the Unity JIT copy, successful process lifetime and user/visual
game evidence. Allocation failure elsewhere, alias/dispatch faults or CEF table
OOM are failures, not reasons to suppress checks. Preserve the rollback config.
