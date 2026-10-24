#!/bin/bash
# Build proc-test.exe + child-test.exe (aarch64-windows console PEs) and
# copy them into the app bundle. Launch on device with
# MADEIRA_EXE=proc-test.exe (the "Run Proc Test" button).
set -eu

DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$DIR/../.." && pwd)"
MINGW="$REPO_ROOT/toolchains/llvm-mingw-20260421-ucrt-macos-universal/bin"

"$MINGW/aarch64-w64-mingw32-clang" -O2 -mconsole \
    -o "$DIR/proc-test.exe" "$DIR/proc_parent.c"
"$MINGW/aarch64-w64-mingw32-clang" -O2 -mconsole \
    -o "$DIR/child-test.exe" "$DIR/proc_child.c"

cp "$DIR/proc-test.exe" "$DIR/child-test.exe" "$REPO_ROOT/app/Madeira/aarch64-windows/"
echo "built + copied proc-test.exe child-test.exe"
ls -la "$REPO_ROOT/app/Madeira/aarch64-windows/proc-test.exe" \
       "$REPO_ROOT/app/Madeira/aarch64-windows/child-test.exe"
