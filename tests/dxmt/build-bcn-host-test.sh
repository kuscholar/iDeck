#!/bin/bash
# Madeira: build and run the host-side BCn decoder unit test.
#
# Subject under test:
#   dxmt/src/dxmt/dxmt_bcn.hpp   block decoders + bcn_decode_image
#   dxmt/src/dxmt/dxmt_bcn.cpp   the BC7 block decoder
#
# Runs on the build host, not on device: the decoder is pure
# arithmetic with no Metal, no Wine and no Windows dependency, which is the
# whole reason it can be pinned here instead of guessed at from a screenshot.
#
# Usage: bash tests/dxmt/build-bcn-host-test.sh
# Exit 0 = PASS.
set -eu

DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$DIR/../.." && pwd)"
DXMT="$REPO_ROOT/dxmt/src/dxmt"
OUT="$DIR/out-host"
mkdir -p "$OUT"

CXX="${CXX:-g++}"

echo "=== building bcn-host-test ($CXX) ==="
"$CXX" -std=c++20 -O2 -Wall -Wextra -Wno-unused-parameter \
    -I "$DXMT" \
    -o "$OUT/bcn-host-test" \
    "$DIR/bcn-host-test.cpp" "$DXMT/dxmt_bcn.cpp"

ls -la "$OUT/bcn-host-test"
echo ""
echo "=== running ==="
"$OUT/bcn-host-test"
