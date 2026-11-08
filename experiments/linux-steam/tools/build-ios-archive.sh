#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
# Pinned BSD libarchive for app-private verified root import. No private iOS dylib.
set -euo pipefail
repo=$(cd "$(dirname "$0")/../../.." && pwd)
: "${LINUX_LAB_ARTIFACTS:?Use the verified private external artifact root}"
: "${CMAKE:=cmake}"
: "${NINJA:=ninja}"
case "$LINUX_LAB_ARTIFACTS" in /Volumes/easystore/*) ;; *) exit 2;; esac
source="$repo/vendor/LinuxRunner/deps/libarchive"
[[ $(git -C "$source" rev-parse HEAD) == fc6563f5130d8a7ee1fc27c0e55baef35119f26c ]] || exit 2
[[ -z $(git -C "$source" status --porcelain --untracked-files=no) ]] || exit 2
sdk=$(xcrun --sdk iphoneos --show-sdk-path)
out="$LINUX_LAB_ARTIFACTS/ios-libarchive-v2"
"$CMAKE" -S "$source" -B "$out" -G Ninja -DCMAKE_MAKE_PROGRAM="$(command -v "$NINJA")" \
    -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DCMAKE_SYSTEM_NAME=iOS \
    -DCMAKE_OSX_SYSROOT="$sdk" -DCMAKE_OSX_ARCHITECTURES=arm64 \
    -DCMAKE_OSX_DEPLOYMENT_TARGET=26.0 -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_TRY_COMPILE_TARGET_TYPE=EXECUTABLE \
    -DCMAKE_FIND_ROOT_PATH_MODE_LIBRARY=ONLY -DCMAKE_FIND_ROOT_PATH_MODE_INCLUDE=ONLY \
    -DCMAKE_FIND_ROOT_PATH_MODE_PACKAGE=ONLY -DCMAKE_FIND_ROOT_PATH_MODE_PROGRAM=NEVER \
    -DENABLE_TEST=OFF -DENABLE_TAR=OFF -DENABLE_CPIO=OFF -DENABLE_CAT=OFF -DENABLE_INSTALL=OFF \
    -DENABLE_ZLIB=ON -DZLIB_INCLUDE_DIR="$sdk/usr/include" -DZLIB_LIBRARY="$sdk/usr/lib/libz.tbd" \
    -DENABLE_BZip2=OFF -DENABLE_LZMA=OFF -DENABLE_LZ4=OFF -DENABLE_LZO=OFF \
    -DENABLE_ZSTD=OFF -DENABLE_LIBB2=OFF -DENABLE_OPENSSL=OFF -DENABLE_MBEDTLS=OFF \
    -DENABLE_NETTLE=OFF -DENABLE_CNG=OFF -DENABLE_LIBXML2=OFF -DENABLE_EXPAT=OFF \
    -DENABLE_PCREPOSIX=OFF -DENABLE_ICONV=OFF -DENABLE_ACL=OFF -DENABLE_XATTR=OFF
"$CMAKE" --build "$out" --target archive_static --parallel 4
stage="$out/ideck-root-tools"
mkdir -p "$stage/source/tools"
cp "$repo/vendor/LinuxRunner/tools/fakefs.c" "$stage/source/tools/fakefs.c"
patch --batch -d "$stage/source" -p1 -i "$repo/experiments/linux-steam/patches/linuxrunner-fakefs-case-alias.patch"
for unit in fakefs fchdir; do
    input="$stage/source/tools/fakefs.c"
    [[ "$unit" != fchdir ]] || input="$repo/vendor/LinuxRunner/util/fchdir.c"
    xcrun --sdk iphoneos clang -target arm64-apple-ios26.0 -isysroot "$sdk" -O2 \
        -DGUEST_ARM64=1 -DENGINE_ASBESTOS=1 -I "$repo/vendor/LinuxRunner" -I "$source/libarchive" \
        -c "$input" -o "$stage/$unit.o"
done
xcrun ar rcs "$out/liblabrootfs.a" "$stage/fakefs.o" "$stage/fchdir.o"
python3 - "$out" "$source" <<'PY'
from pathlib import Path
import hashlib,json,subprocess,sys
out,source=map(Path,sys.argv[1:]);archive=out/'libarchive/libarchive.a'
assert archive.is_file()
(out/'ideck-build-evidence.json').write_text(json.dumps(dict(scope='iOS arm64 static dependency build only, not device execution',
    source_revision=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip(),
    archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
    config_sha256=hashlib.sha256((out/'CMakeCache.txt').read_bytes()).hexdigest()),indent=2)+'\n')
PY
