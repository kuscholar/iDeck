#!/bin/bash
# Build the M1 canary for iOS arm64.
#
# Runs natively on the device, before any app integration: it answers "does the
# iOS converter work in an iOS process" without dragging in bundling, signing or
# Madeira's own startup path. Those are separate questions and deserve separate
# failures.
set -eu
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$DIR/../.." && pwd)"
source "$DIR/deps.sh"

OUT="${OUT:-$REPO_ROOT/build/madeira-d3d12/out-ios}"
mkdir -p "$OUT"
SDK="$(xcrun --sdk iphoneos --show-sdk-path)"

xcrun --sdk iphoneos clang++ -O1 -g -fobjc-arc -Wall \
      -target arm64-apple-ios15.0 -isysroot "$SDK" \
      -DIR_PRIVATE_IMPLEMENTATION -DCANARY_STANDALONE \
      -I"$MSC_INCLUDE" \
      -framework Foundation -framework Metal \
      -o "$OUT/msc_canary" \
      "$REPO_ROOT/madeira-d3d12/tests/native/msc_canary.mm" \
      \
      -Wl,-rpath,@executable_path

# The dylib travels beside the binary; its install name is @rpath-relative.
cp "$MSC_LIB_IOS" "$OUT/libmetalirconverter.dylib"
cp "$REPO_ROOT/madeira-d3d12/shaders/"*.dxil "$OUT/"

echo "built: $OUT/msc_canary"
lipo -archs "$OUT/msc_canary" | sed 's/^/  arch: /'
