#!/bin/bash
# Copy the pinned Wine Mono (pin.sh) into the app bundle, with its licence summary, and patch the
# bundled mscorlib (ml1281).
#
# Called by the Xcode build phase "Bundle Wine Mono" as
#   bundle.sh "$CODESIGNING_FOLDER_PATH/wine-mono"
# and runnable by hand with any destination. The source is build/wine-mono/wine-mono-<ver>
# from fetch.sh; without it the destination is removed and the app is built without Mono.
# The source tree is never modified.
set -euo pipefail

R="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
. "$R/build/wine-mono/pin.sh"
VER="$WINE_MONO_VER"
SRC="$R/build/wine-mono/wine-mono-$VER"
DST="${1:?usage: bundle.sh <destination folder>}"

if [ ! -f "$SRC/bin/libmono-2.0-x86.dll" ]; then
    rm -rf "$DST"
    echo "note: no Wine Mono in $SRC (run build/wine-mono/fetch.sh); the app is built without it"
    exit 0
fi

WANT="$(sed -n 's/^#define WINE_MONO_VERSION "\(.*\)"/\1/p' "$R/wine/dlls/mscoree/mscoree_private.h" 2>/dev/null || true)"
if [ -n "$WANT" ] && [ "$WANT" != "$VER" ]; then
    echo "warning: Wine's mscoree asks for Wine Mono $WANT; bundling the pinned $VER (build/wine-mono/pin.sh)"
fi

# The lib/mono/*-api reference assemblies are for compilers only (~107 MB of 233).
rsync -a --delete --exclude '/lib/mono/*-api/' "$SRC/" "$DST/"
cp "$R/build/wine-mono/COPYING" "$DST/COPYING"

# ---------------------------------------------------------------------------------------------
# ml1281 -- DIRTY HACK: a 4-byte binary patch of a prebuilt mscorlib.dll.
#
# What: GC.Collect(gen, GCCollectionMode.Optimized, ...) returns without collecting. Mono's
# corlib computes the mode flags and then ignores them, so every call is a full blocking
# collection; Terraria calls GC.Collect(2, Optimized, false) back to back (one 85-150 ms major
# GC per frame, ~8 FPS). .NET lets an Optimized request be skipped. In GC.Collect(int,
# GCCollectionMode, bool, bool) the `mode == Optimized` branch (ldloc.0; ldc.i4.4; or; stloc.0
# at IL_003c, file offset 0x53b08) becomes ret; nop; nop; nop.
#
# Why it is a hack: it edits IL bytes in a binary built by someone else instead of building the
# fix from source. It is pinned to one exact file (both hashes in pin.sh) and the build stops if
# the file is anything else, so it can never land on the wrong bytes -- but it also ties the app
# to Wine Mono 11.0.0.
#
# TODO(ml1281): replace with an honest build. Either build Wine Mono from its source
# (wine-mono-<ver>-src.tar.xz / gitlab.winehq.org/mono/wine-mono) with the GC.Collect change in
# mcs/class/corlib (System/GC.cs or the referencesource copy it uses), pinned and scripted like
# the other build/ chains; or get the change into Wine Mono upstream (honour
# GCCollectionMode.Optimized) and drop this patch when a release carries it.
# ---------------------------------------------------------------------------------------------
/usr/bin/python3 - "$DST/lib/mono/4.5/mscorlib.dll" "$WINE_MONO_MSCORLIB_SHA256" "$WINE_MONO_MSCORLIB_PATCHED_SHA256" <<'PY'
import hashlib, sys
p, pristine, patched = sys.argv[1:4]
d = bytearray(open(p, "rb").read())
h = hashlib.sha256(d).hexdigest()
if h == patched:
    print("ml1281: mscorlib GC.Collect(Optimized) already patched")
    sys.exit(0)
if h != pristine:
    sys.exit("error: ml1281: %s is not the pinned mscorlib (sha256 %s); see build/wine-mono/pin.sh" % (p, h))
off = 0x53B08
if bytes(d[off - 6:off + 14]) != bytes.fromhex("160A03183304061A600A052C04061E600A042C06"):
    sys.exit("error: ml1281: unexpected bytes at 0x%x in the pinned mscorlib" % off)
d[off:off + 4] = bytes.fromhex("2A000000")
if hashlib.sha256(d).hexdigest() != patched:
    sys.exit("error: ml1281: patched mscorlib does not match the pinned result")
open(p, "wb").write(d)
print("ml1281: mscorlib GC.Collect(Optimized) patched at 0x%x (dirty hack, see bundle.sh TODO)" % off)
PY
