#!/bin/bash
# Build and run the M1 native canary on macOS.
#
# macOS first because it is the fast loop: the same converter API and the same
# binding ABI, without an IPA cycle. It does NOT substitute for the in-app iOS
# run, which the design requires separately before any iOS claim.
set -eu
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$DIR/../.." && pwd)"
source "$DIR/deps.sh"
[[ "$MSC_HAVE_PKG" == 1 ]] || { echo "$(basename "$0"): needs the macOS converter library from Apple's installer package (see deps.sh)" >&2; exit 1; }

OUT="${OUT:-$REPO_ROOT/build/madeira-d3d12/out}"
mkdir -p "$OUT"

# IR_PRIVATE_IMPLEMENTATION: the runtime companion header emits its binding
# constants and helper bodies in exactly ONE translation unit that defines this.
# Without it the kIR* bind points link as undefined symbols -- they are
# header-only and the dylib does not export them.
clang++ -O1 -g -fobjc-arc -Wall \
      -DIR_PRIVATE_IMPLEMENTATION -DCANARY_STANDALONE \
      -I"$MSC_INCLUDE" \
      -framework Foundation -framework Metal \
      -o "$OUT/msc_canary" \
      "$REPO_ROOT/madeira-d3d12/tests/native/msc_canary.mm" \
      \
      -Wl,-rpath,"$(dirname "$MSC_LIB_MACOS")"

echo "built: $OUT/msc_canary"
