# Ratatan WinRT buffer import compatibility

The official Madeira 0.1.3 IPA omits 64-bit `wintypes.dll`. Ratatan's
`GameAssembly.dll` imports `RoGetBufferMarshaler` from
`api-ms-win-core-winrt-robuffer-l1-1-0.dll`. Wine's API-set schema redirects
that name to `wintypes.dll`; the missing target causes `STATUS_DLL_NOT_FOUND`
and Unity's "Failed to load il2cpp" dialog.

This ARM64EC compatibility DLL exports that one function with the SDK's
`HRESULT WINAPI RoGetBufferMarshaler(IMarshal **)` ABI. It returns
`E_NOTIMPL`, clearing the output pointer, or `E_POINTER` for a null output.
It does **not** implement COM buffer marshaling or replace Wine's full
wintypes implementation. Wine's pinned `wintypes.spec` also marks this API
as a stub. If the game actually requires a successful marshaler call, this
patch is insufficient and the implementation must be extended.

Build with the LLVM-MinGW version and SHA-256 in `docs/BUILDING.md`:

```sh
LLVM_MINGW=/path/to/llvm-mingw-20260421-ucrt-macos-universal \
  sh build/wintypes-compat/build.sh
cp build/stub-dlls/wintypes/wintypes.dll app/Madeira/arm64ec-windows/
```

Bundle the result in `Madeira.app/arm64ec-windows/` and re-sign the app.
Madeira's existing prefix setup links it into `system32` and `sysx64`.
An in-place app update preserves the Wine prefix, installed games and saves.
For rollback, reinstall the preserved original signed IPA; remove only the
new wintypes links/file if they were staged directly in the data container.

Validation completed: ARM64EC PE architecture, exact export name, original
game import inspected, and iOS app deep code-signature verification.
Patched Madeira was installed wirelessly in place on Kusch and its library opened
with Ratatan still present. Game startup verification is pending the user
pressing Play and completing the existing JIT flow; the release IPA did not
respond to the newer source tree's `madeira://play` shortcut.

## Device follow-up

A post-update Ratatan launch loaded both `wintypes.dll` and `GameAssembly.dll`,
created Unity job workers and IL2CPP threadpool workers, and initialized DXMT.
The earlier missing-DLL/"Failed to load il2cpp" blocker did not recur in that log.
Later the runtime logged exhausted 512-entry Mach thread registrations,
slot-0 TEB fallback, unhandled Mach exceptions and invalid exception stack
limits. This is consistent with upstream issue #397, although it does not
prove that every failure in this launch has that single cause.

Candidate upstream PR #412 (head 2873c661cb7fc185e1c5448968017f3b5d19e075)
was applied locally to `signal_arm64_ios.c`. Its host ASan/UBSan test passed
4000 sequential thread registrations and 12000 concurrent registrations; its
negative control reproduced exhaustion without reclamation. This native
runtime change is NOT included in the previously installed IPA. Rebuilding
and linking the iOS app requires the missing FEX, DXMT, Wine unix, FFmpeg,
and pairing static libraries and configured Wine build headers described in
`docs/BUILDING.md`.

A later complete source build (bundle version 5) now includes the native
thread-registry repair and fullscreen migration. See
`docs/LOCAL_IPHONE_REPAIR.md` for its build evidence and pending device gate.
