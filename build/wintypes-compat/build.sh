#!/bin/sh
set -eu
: "${LLVM_MINGW:?Set LLVM_MINGW to the verified LLVM-MinGW toolchain directory}"
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
OUT=${1:-"$ROOT/build/stub-dlls/wintypes"}
mkdir -p "$OUT"
"$LLVM_MINGW/bin/arm64ec-w64-mingw32-clang" -shared -O2 \
  -Wl,/timestamp:0 \
  "$ROOT/build/wintypes-compat/wintypes.c" -o "$OUT/wintypes.dll"
"$LLVM_MINGW/bin/llvm-readobj" --file-headers --coff-imports --coff-exports "$OUT/wintypes.dll"
