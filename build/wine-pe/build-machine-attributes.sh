#!/bin/bash
# Source-only backport; never edits the pinned Wine checkout or Valve files.
# Usage: LLVM_MINGW=/toolchain BISON_PKGDATADIR=/bison/data \
#   PATH=/bison/bin:$PATH bash build/wine-pe/build-machine-attributes.sh /new/workdir
# Output: workdir/build/dlls/{kernel32,kernelbase}/i386-windows/*.dll
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
WORK="${1:?Pass a new private work directory}"
[ ! -e "$WORK" ] || { echo 'Refusing to overwrite an existing work directory' >&2; exit 1; }
mkdir -p "$WORK/source" "$WORK/build"
WORK="$(cd "$WORK" && pwd)"
TC="${LLVM_MINGW:-$ROOT/toolchains/llvm-mingw-20260421-ucrt-macos-universal}"
export PATH="$TC/bin:$PATH"
[ -x "$TC/bin/i686-w64-mingw32-clang" ] || { echo 'LLVM-Mingw is required' >&2; exit 1; }
git -C "$ROOT/wine" rev-parse HEAD > "$WORK/WINE_REVISION"
git -C "$ROOT/wine" archive HEAD | tar -xf - -C "$WORK/source"
(cd "$WORK/source" && git apply "$ROOT/build/wine-pe/steam-ui-machine-attributes.patch")
(cd "$WORK/build" && ../source/configure --enable-archs=arm64ec,i386 \
    --without-x --without-freetype --disable-tests --enable-winegstreamer)
(cd "$WORK/build" && make -j"${JOBS:-6}" \
    dlls/kernel32/i386-windows/kernel32.dll dlls/kernelbase/i386-windows/kernelbase.dll)
for module in kernel32 kernelbase; do
    "$TC/bin/i686-w64-mingw32-strip" --strip-debug "$WORK/build/dlls/$module/i386-windows/$module.dll"
done
printf 'Built patched Wine DLLs in %s/build/dlls; review and stage into an isolated iDeck build.\n' "$WORK"
