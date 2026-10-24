#!/bin/bash
# Build a DXMT dx11 test as x86_64 PE (runs via FEX on iOS), with shaders
# precompiled and embedded. Same plumbing as build.sh but uses the x86_64
# llvm-mingw and skips the `winebuild --builtin` tag (we want FEX to pick
# it up as a guest binary, not Wine's builtin path).
#
# Usage: ./build-x64.sh <test-name>      e.g. ./build-x64.sh cube
set -eu

if [[ $# -lt 1 ]]; then
    echo "usage: $0 <test-name>   (e.g. cube, cbuffer, texquad, ...)"
    exit 1
fi
TEST="$1"

DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$DIR/../.." && pwd)"
MINGW="$REPO_ROOT/toolchains/llvm-mingw-20260421-ucrt-macos-universal/bin"
DXMT_DIRECTX="$REPO_ROOT/dxmt/include/native/directx"
DXMT_TESTS="$REPO_ROOT/dxmt/tests/dx11"
HLSL_COMPILE="$REPO_ROOT/build/d3d11-triangle/hlsl_compile.exe"
WINE=${WINE:-/opt/homebrew/bin/wine}
APP_BUNDLE="$REPO_ROOT/app/Madeira/arm64ec-windows"

CPP_SRC="$DXMT_TESTS/dx11_${TEST}.cpp"
[[ -f "$CPP_SRC" ]] || { echo "no test source: $CPP_SRC"; exit 1; }

HLSL_NAME=$(grep -oE 'L"shader[a-z_]*\.hlsl"' "$CPP_SRC" | head -1 | tr -d 'L"')
HLSL_SRC="$DXMT_TESTS/$HLSL_NAME"
[[ -f "$HLSL_SRC" ]] || { echo "no shader source: $HLSL_SRC"; exit 1; }
[[ -x "$HLSL_COMPILE" ]] || { echo "host-side HLSL compiler not built — run build/d3d11-triangle/build.sh"; exit 1; }

OUT="$DIR/out-x64/$TEST"
mkdir -p "$OUT"

echo "==> compiling shaders for '$TEST'"
for stage in vs ps; do
    profile="${stage}_5_0"
    "$WINE" "$HLSL_COMPILE" "${stage}_main" "$profile" < "$HLSL_SRC" \
        > "$OUT/${stage}.dxbc" 2>"$OUT/${stage}.err"
    [[ -s "$OUT/${stage}.dxbc" ]] || { echo "${stage} compile failed"; cat "$OUT/${stage}.err"; exit 1; }
    head -c 4 "$OUT/${stage}.dxbc" | grep -q DXBC || { echo "${stage} not DXBC"; exit 1; }
    echo "  ${stage}: $(wc -c < "$OUT/${stage}.dxbc") bytes"
done

cat > "$OUT/${TEST}_blobs.c" <<EOF
#include "test_shim.h"
EOF
(cd "$OUT" && xxd -i -n "${TEST}_vs" vs.dxbc >> "${TEST}_blobs.c")
(cd "$OUT" && xxd -i -n "${TEST}_ps" ps.dxbc >> "${TEST}_blobs.c")
cat >> "$OUT/${TEST}_blobs.c" <<EOF

const struct madeira_shader_blob madeira_shader_blobs[] = {
  { "${HLSL_NAME}", "vs_main", "vs_5_0", ${TEST}_vs, sizeof(${TEST}_vs) },
  { "${HLSL_NAME}", "ps_main", "ps_5_0", ${TEST}_ps, sizeof(${TEST}_ps) },
};
const unsigned int madeira_shader_blob_count =
    sizeof(madeira_shader_blobs) / sizeof(madeira_shader_blobs[0]);
EOF

echo "==> building ${TEST}-x64.exe"
CXX="$MINGW/x86_64-w64-mingw32-clang++"
"$CXX" -o "$OUT/${TEST}-x64.exe" \
    -I "$DXMT_DIRECTX" \
    -I "$DIR" \
    -I "$DXMT_TESTS" \
    -include test_shim.h \
    -std=c++17 -O2 \
    -Wno-int-conversion -Wno-null-conversion -Wno-c++11-narrowing \
    -static -static-libgcc -static-libstdc++ \
    "$CPP_SRC" \
    "$OUT/${TEST}_blobs.c" \
    -ld3d11 -ldxgi -luuid -lwinmm

# DO NOT tag as builtin — let it be a normal guest x86_64 PE so Wine loads it
# through FEX (same path as fib-x64.exe, hello-x64.exe, etc.).

file "$OUT/${TEST}-x64.exe"

echo "==> copying to app bundle (arm64ec-windows)"
cp "$OUT/${TEST}-x64.exe" "$APP_BUNDLE/${TEST}-x64.exe"
ls -la "$APP_BUNDLE/${TEST}-x64.exe"

echo "==> $OUT/${TEST}-x64.exe ready"
