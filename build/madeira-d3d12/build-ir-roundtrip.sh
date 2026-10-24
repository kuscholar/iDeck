#!/usr/bin/env bash
# Offline proof that runtime DXIL conversion works, on the host, in seconds.
#
# Runs the same service the device uses over the same argument struct, so a
# broken conversion is caught here rather than by an empty window on a phone.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$DIR/../.." && pwd)"
source "$DIR/deps.sh"
[[ "$MSC_HAVE_PKG" == 1 ]] || { echo "$(basename "$0"): needs the macOS converter library from Apple's installer package (see deps.sh)" >&2; exit 1; }

R="$REPO_ROOT/madeira-d3d12"
OUT="${OUT:-$DIR/out}"
mkdir -p "$OUT"

clang++ -O1 -std=c++20 -fobjc-arc -x objective-c++ -DMADEIRA_IR_HOST_TEST \
    -I"$MSC_INCLUDE" -I"$R/src" -c "$R/src/unix/madeira_ir_unix.mm" -o "$OUT/ir_unix.o"
clang++ -O1 -std=c++20 -x objective-c++ -DMADEIRA_IR_HOST_TEST \
    -I"$R/src" -I"$R/tests/windows" -c "$R/tests/native/ir_roundtrip.mm" -o "$OUT/ir_rt.o"
clang -O1 -std=c11 -c "$R/src/unix/madeira_sc_pack.c" -o "$OUT/sc_pack.o"
clang++ -o "$OUT/ir_roundtrip" "$OUT/ir_unix.o" "$OUT/sc_pack.o" "$OUT/ir_rt.o" -framework Foundation

echo "=== runtime conversion round trip (host) ==="
MADEIRA_MSC_DYLIB="$MSC_LIB_MACOS" "$OUT/ir_roundtrip"
