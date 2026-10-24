#!/bin/bash
# Download the pinned Wine Mono (pin.sh) for the app bundle and check its hash.
#
# Wine Mono runs .NET Framework programs; Wine's mscoree looks for it at
# C:\windows\mono\mono-2.0, which WineProcessBridge.m links to the bundled copy.
#
#   fetch.sh            wine-mono-<ver>-x86.tar.xz and its unpacked tree wine-mono-<ver>/
#   fetch.sh --source   also wine-mono-<ver>-src.tar.xz, the matching source, for a release
#
# Everything lands in build/wine-mono/ and is git-ignored. bundle.sh copies the tree into the app.
set -euo pipefail

R="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
D="$R/build/wine-mono"
. "$D/pin.sh"
VER="$WINE_MONO_VER"
URL="https://dl.winehq.org/wine/wine-mono/$VER"

WANT="$(sed -n 's/^#define WINE_MONO_VERSION "\(.*\)"/\1/p' "$R/wine/dlls/mscoree/mscoree_private.h" 2>/dev/null || true)"
if [ -n "$WANT" ] && [ "$WANT" != "$VER" ]; then
    echo "warning: Wine's mscoree asks for Wine Mono $WANT; the bundle stays pinned to $VER (build/wine-mono/pin.sh)" >&2
fi

get() {  # get <file> <sha256>
    if [ ! -f "$D/$1" ]; then
        curl -fL --retry 3 -o "$D/$1.part" "$URL/$1"
        mv "$D/$1.part" "$D/$1"
    fi
    echo "$2  $D/$1" | shasum -a 256 -c -
}

get "wine-mono-$VER-x86.tar.xz" "$WINE_MONO_TAR_SHA256"
if [ "${1:-}" = "--source" ]; then
    get "wine-mono-$VER-src.tar.xz" "$WINE_MONO_SRC_SHA256"
fi

rm -rf "$D/wine-mono-$VER"
tar -xJf "$D/wine-mono-$VER-x86.tar.xz" -C "$D"
echo "$WINE_MONO_MSCORLIB_SHA256  $D/wine-mono-$VER/lib/mono/4.5/mscorlib.dll" | shasum -a 256 -c -
echo "Wine Mono $VER ready in build/wine-mono/wine-mono-$VER"
