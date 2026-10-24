#!/bin/bash
# Build faultrep.dll (ARM64EC) from faultrep.c / faultrep.def and install it
# into the app's DLL farm (app/Madeira/arm64ec-windows, or $DEST), where it is
# committed like every other builtin. Wine's own faultrep lacks WerReportHang;
# games that import faultrep.dll statically (Ghost of Tsushima) stop in the
# loader with STATUS_DLL_NOT_FOUND when the farm has none. The exports are
# checked against faultrep.def before anything is installed.
# Requires the llvm-mingw toolchain (docs/BUILDING.md).
set -eu
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$DIR/../.." && pwd)"
MINGW="$REPO_ROOT/toolchains/llvm-mingw-20260421-ucrt-macos-universal/bin"
OUT="${OUT:-$DIR/out}"
DEST="${DEST:-$REPO_ROOT/app/Madeira/arm64ec-windows}"
mkdir -p "$OUT"

"$MINGW/arm64ec-w64-mingw32-clang" -shared -O2 -Wall \
    -o "$OUT/faultrep.dll" "$DIR/faultrep.c" "$DIR/faultrep.def"

want=$(awk 'f && NF { print $1 } /^EXPORTS/ { f = 1 }' "$DIR/faultrep.def" | sort)
have=$("$MINGW/llvm-readobj" --coff-exports "$OUT/faultrep.dll" | awk '$1 == "Name:" { print $2 }' | sort)
if [ "$want" != "$have" ]; then
    echo "faultrep.dll: the exports do not match faultrep.def" >&2
    diff <(echo "$want") <(echo "$have") >&2 || true
    exit 1
fi

mkdir -p "$DEST"
cp "$OUT/faultrep.dll" "$DEST/faultrep.dll"
echo "faultrep.dll: $(wc -c < "$OUT/faultrep.dll" | tr -d ' ') bytes, $(echo "$have" | wc -l | tr -d ' ') exports -> $DEST"
