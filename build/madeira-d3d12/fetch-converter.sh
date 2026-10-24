#!/bin/bash
# Stage Apple's Metal Shader Converter from a FRESH extraction of the
# hash-verified installer package, after a converter update: the iOS dynamic
# library into the app bundle source folder (verified against its pinned hash;
# distributed under Apple's agreement, see app/Madeira/d3d12/NOTICE.txt) and the
# Apache-2.0 public headers into madeira-d3d12/third_party/
# metal-shader-converter, whose SHA256SUMS is rewritten, so the library and the
# headers the runtime is compiled against always come from the same package.
# Nothing from an earlier /tmp extraction or an environment-selected directory
# is trusted. Also stages the licence texts the bundle must carry. After a
# converter update, change the pinned hashes here and in deps.sh together.
set -eu
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$DIR/../.." && pwd)"
MSC_PKG="$REPO_ROOT/research/GPTK/Metal Shader Converter 4.0 beta 2.pkg"
MSC_PKG_SHA256="1acc33c87ea663933df89721a998d066106685473020bcbe007cee7a16155734"
MSC_IOS_DYLIB_SHA256="073f903be98e973ff38f4d79f2c48d61ef938754a77b1caedda79c9f05a068c2"
[[ -f "$MSC_PKG" ]] || { echo "fetch-converter: missing $MSC_PKG (supply Apple's installer package)" >&2; exit 1; }
have="$(shasum -a 256 "$MSC_PKG" | cut -d' ' -f1)"
[[ "$have" == "$MSC_PKG_SHA256" ]] || { echo "fetch-converter: package hash mismatch ($have)" >&2; exit 1; }
tmp="$(mktemp -d /private/tmp/madeira-msc-fetch-XXXXXX)"
trap 'rm -rf "$tmp"' EXIT
pkgutil --expand-full "$MSC_PKG" "$tmp/expanded" >/dev/null
SRC="$tmp/expanded/MetalShaderConverter.pkg/Payload/usr/local/lib_iOS/libmetalirconverter.dylib"
[[ -f "$SRC" ]] || { echo "fetch-converter: iOS dylib not in the package payload" >&2; exit 1; }
got="$(shasum -a 256 "$SRC" | cut -d' ' -f1)"
[[ "$got" == "$MSC_IOS_DYLIB_SHA256" ]] || { echo "fetch-converter: extracted iOS dylib hash mismatch ($got)" >&2; exit 1; }
DEST_DIR="$REPO_ROOT/app/Madeira/d3d12"
cp "$SRC" "$DEST_DIR/libmetalirconverter.dylib"
HDR_SRC="$tmp/expanded/MetalShaderConverter.pkg/Payload/usr/local/include"
HDR_DEST="$REPO_ROOT/madeira-d3d12/third_party/metal-shader-converter"
[[ -f "$HDR_SRC/metal_irconverter/metal_irconverter.h" ]] || { echo "fetch-converter: headers not in the package payload" >&2; exit 1; }
rm -rf "$HDR_DEST/include"
mkdir -p "$HDR_DEST"
cp -R "$HDR_SRC" "$HDR_DEST/include"
(cd "$HDR_DEST" && find include -type f | LC_ALL=C sort | xargs shasum -a 256 > SHA256SUMS)
bash "$REPO_ROOT/build/stage-licenses.sh"
echo "staged $(wc -c < "$DEST_DIR/libmetalirconverter.dylib" | tr -d ' ') bytes (sha256 verified) -> $DEST_DIR, headers -> $HDR_DEST"
