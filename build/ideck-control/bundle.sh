#!/bin/bash
set -euo pipefail
out=${1:?destination PE path required}
root=$(cd "$(dirname "$0")/../.." && pwd)
compiler=${LLVM_MINGW:+$LLVM_MINGW/bin/}x86_64-w64-mingw32-clang
if ! command -v "$compiler" >/dev/null 2>&1; then
  echo "error: iDeck control helper requires LLVM_MINGW or x86_64-w64-mingw32-clang on PATH" >&2
  exit 1
fi
mkdir -p "$(dirname "$out")"
"$compiler" -O2 -Wall -Wextra -Werror -municode -mwindows -Wl,--no-insert-timestamp \
  "$root/build/ideck-control/ideck-control.c" -lshell32 -luser32 -o "$out"
