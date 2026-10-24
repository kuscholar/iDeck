#!/bin/bash
# Build the WMA decoder self-test, wma-x86.exe.
#
# See tests/x86/wma-x86.c for what it proves and what each exit code
# means.  In short: CoCreateInstance(CLSID_CWMADecMediaObject, IMFTransform) --
# the call FAudio makes for an xWMA/XAudio2 voice -- then a WMA V2 input type,
# a 16-bit PCM output type, one ProcessInput of real WMA packets and
# ProcessOutput until dry, and a check that the PCM is non-silent AND has the
# 440 Hz fundamental the packets were encoded from.  That last check is the
# point: before this port had a decoder, FAudio passed the compressed bytes
# through as PCM, which is loud and is not silence.
#
# Kept separate from build.sh and from the other per-test scripts here, the
# same way those are kept separate from each other: this stage only adds files.
#
# Usage: ./build-wma-test.sh
#
# Produces wma-x86.exe (i386 PE) and copies it into app/Madeira/i386-windows/
# so the IPA build picks it up.  wmadmod/winegstreamer are NOT LoadLibrary'd:
# they are reached the way FAudio reaches them, through CoCreateInstance, so
# the prefix's COM registration is part of what gets tested.  mfplat IS a
# static import, because the media type and sample objects the IMFTransform
# API takes have no other source.
set -e

NAME=wma-x86
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TOOLCHAIN="$REPO_ROOT/toolchains/llvm-mingw-20260421-ucrt-macos-universal/bin"
APP_BUNDLE="$REPO_ROOT/app/Madeira/i386-windows"
CC="$TOOLCHAIN/i686-w64-mingw32-clang"
OBJDUMP="$TOOLCHAIN/i686-w64-mingw32-objdump"

cd "$SCRIPT_DIR"

echo "=== building $NAME.exe (i386 PE, no CRT) ==="
# Flags:
# -nostdlib because the file supplies `start` and its own memset/memcpy, and
# --large-address-aware because the guest window is a full 4 GB and the image
# must not be restricted to the low 2 GB.
# -lwmcodecdspuuid supplies CLSID_CWMADecMediaObject, -lmfuuid the
# IID_IMFTransform / MF_MT_* / MFAudioFormat_* GUIDs, both as data.
"$CC" -O1 -g -nostdlib -ffreestanding \
    -static-libgcc -Wno-unused-command-line-argument \
    -Wl,--entry=_start \
    -Wl,--large-address-aware \
    -o "$NAME.exe" "$NAME.c" \
    -lmfplat -lmfuuid -lwmcodecdspuuid -lole32 -luuid -lkernel32

ls -la "$NAME.exe"

echo ""
echo "=== machine type (file format) ==="
"$OBJDUMP" -f "$NAME.exe"

echo ""
echo "=== asserting the import set ==="
imports=$("$OBJDUMP" -p "$NAME.exe" | sed -n 's/^\s*DLL Name: //p' | tr 'A-Z' 'a-z' | sort -u)
echo "$imports"
unexpected=0
for dll in $imports; do
    case "$dll" in
        kernel32.dll|ole32.dll|mfplat.dll) ;;
        *) echo "UNEXPECTED IMPORT: $dll"; unexpected=1 ;;
    esac
done
if [ "$unexpected" != 0 ]; then
    echo "FAILED: the decoder must be reached through COM, not as a static import."
    exit 1
fi

echo ""
echo "=== asserting the large-address-aware bit is set ==="
if "$OBJDUMP" -p "$NAME.exe" | grep -q "LARGE_ADDRESS_AWARE"; then
    echo "LARGE_ADDRESS_AWARE present"
else
    chars=$("$TOOLCHAIN/llvm-readobj" --file-headers "$NAME.exe" \
            | sed -n 's/.*IMAGE_FILE_LARGE_ADDRESS_AWARE.*/yes/p' | head -1)
    if [ "$chars" = yes ]; then
        echo "LARGE_ADDRESS_AWARE present (readobj)"
    else
        echo "FAILED: LARGE_ADDRESS_AWARE not set."
        exit 1
    fi
fi

echo ""
echo "=== checking the DLLs it needs are in the i386 farm ==="
# wmadmod.dll holds CLSID_CWMADecMediaObject and forwards to
# CLSID_wg_wma_decoder in winegstreamer.dll; mfplat/msdmo are their imports.
missing=0
for dll in wmadmod.dll winegstreamer.dll mfplat.dll msdmo.dll ole32.dll; do
    if [ -f "$APP_BUNDLE/$dll" ]; then
        ls -la "$APP_BUNDLE/$dll"
    else
        echo "WARNING: $APP_BUNDLE/$dll is missing."
        missing=1
    fi
done
if [ "$missing" != 0 ]; then
    echo "  Build them in an i386 Wine tree configured with --enable-winegstreamer (docs/MEDIA.md)."
fi

echo ""
echo "=== copying $NAME.exe to app bundle ($APP_BUNDLE) ==="
mkdir -p "$APP_BUNDLE"
cp "$NAME.exe" "$APP_BUNDLE/$NAME.exe"
ls -la "$APP_BUNDLE/$NAME.exe"

echo ""
echo "Done. Launch it directly with env.MADEIRA_EXE = wma-x86.exe in madeira.cfg"
echo "(it runs from C:\\windows\\syswow64)."
echo "Expected log:"
echo "  [wma] decoder created fmt=wmav2 tag=0x161 44100Hz 2ch block=743 avg=16000B/s bitrate=128000 extradata=10 flags2=0x1 -> pcm s16 ..."
echo "  MADEIRA-WMA: --- stage A 44100 Hz stereo, honest rate ---"
echo "  MADEIRA-WMA: fundamental 44x Hz (expected ~440)"
echo "  MADEIRA-WMA: --- stage B 22050 Hz stereo low bit rate, honest rate ---"
echo "  MADEIRA-WMA: --- stage D 22050 Hz stereo, chunked and misaligned pushes ---"
echo "  MADEIRA-WMA: PASS -- every stage decoded WMA V2 to PCM at ~440 Hz"
echo "Exit code 62 means PASS."
echo "63 means the MFT was created but the decode failed; 64 means the class is"
echo "not registered at all, which is what a missing winegstreamer.dll looks"
echo "like from here; 65 means ten seconds ran out."
