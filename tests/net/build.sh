#!/bin/bash
# Build winhttp-test.exe (aarch64-windows console PE) and copy it into
# the app bundle. Launch on device with MADEIRA_EXE=winhttp-test.exe.
set -eu

DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$DIR/../.." && pwd)"
MINGW="$REPO_ROOT/toolchains/llvm-mingw-20260421-ucrt-macos-universal/bin"

"$MINGW/aarch64-w64-mingw32-clang" -O2 -mconsole \
    -o "$DIR/winhttp-test.exe" "$DIR/winhttp_get.c" -lwinhttp

cp "$DIR/winhttp-test.exe" "$REPO_ROOT/app/Madeira/aarch64-windows/"
echo "built + copied winhttp-test.exe"
ls -la "$REPO_ROOT/app/Madeira/aarch64-windows/winhttp-test.exe"
