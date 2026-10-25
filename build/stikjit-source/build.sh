#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Build a traceable StikJIT framework from pinned source, not its prebuilt archive.
# Usage: build.sh /path/to/StikJIT /path/to/idevice /new/output/directory
set -euo pipefail
STIK_SRC="$(cd "$1" && pwd)"
IDEVICE_SRC="$(cd "$2" && pwd)"
OUT="$3"
RECIPE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$RECIPE/verify-source.py" "$STIK_SRC" 32287268fa5824f9edce4cb359f5833ce0cf7b00
python3 "$RECIPE/verify-source.py" "$IDEVICE_SRC" d32c8189c51c2789496b0768039419c3705498c3
[[ ! -e "$OUT" ]] || { echo 'Output directory must not already exist' >&2; exit 1; }
mkdir -p "$OUT"
OUT="$(cd "$OUT" && pwd)"
export IPHONEOS_DEPLOYMENT_TARGET=17.4
(cd "$IDEVICE_SRC" && cargo build --manifest-path ffi/Cargo.toml --release --locked --target aarch64-apple-ios)
mkdir -p "$OUT/ffi" "$OUT/StikJIT.framework/Modules/StikJIT.swiftmodule" "$OUT/StikJIT.framework/Headers"
cp "$IDEVICE_SRC/ffi/idevice.h" "$OUT/ffi/idevice.h"
cp "$STIK_SRC/idevice/module.modulemap" "$OUT/ffi/module.modulemap"
cp "$IDEVICE_SRC/target/aarch64-apple-ios/release/libidevice_ffi.a" "$OUT/ffi/"
SDK="$(xcrun --sdk iphoneos --show-sdk-path)"
xcrun swiftc -swift-version 5 -O -parse-as-library -enable-library-evolution \
  -module-cache-path "$OUT/module-cache" \
  -target arm64-apple-ios17.4 -sdk "$SDK" -module-name StikJIT \
  -I "$OUT/ffi" -I "$STIK_SRC/iokit" -L "$OUT/ffi" \
  -Xlinker -hidden-lidevice_ffi -Xlinker -dead_strip \
  -Xlinker -install_name -Xlinker '@rpath/StikJIT.framework/StikJIT' \
  -Xlinker -compatibility_version -Xlinker 1.0 -Xlinker -current_version -Xlinker 1.0 \
  -framework JavaScriptCore -framework Network -framework Security \
  -framework CFNetwork -framework SystemConfiguration -framework IOKit \
  -emit-library -emit-module \
  -emit-module-path "$OUT/StikJIT.framework/Modules/StikJIT.swiftmodule/arm64-apple-ios.swiftmodule" \
  -emit-module-interface-path "$OUT/StikJIT.framework/Modules/StikJIT.swiftmodule/arm64-apple-ios.swiftinterface" \
  -emit-objc-header-path "$OUT/StikJIT.framework/Headers/StikJIT-Swift.h" \
  "$STIK_SRC"/Sources/*.swift -o "$OUT/StikJIT.framework/StikJIT"
cp "$STIK_SRC"/Resources/*.js "$OUT/StikJIT.framework/"
python3 - "$OUT/StikJIT.framework/Info.plist" <<'PY'
import plistlib,sys
from pathlib import Path
Path(sys.argv[1]).write_bytes(plistlib.dumps({
    'CFBundleExecutable':'StikJIT', 'CFBundleIdentifier':'com.stik.StikJIT',
    'CFBundleName':'StikJIT', 'CFBundlePackageType':'FMWK',
    'CFBundleInfoDictionaryVersion':'6.0', 'CFBundleShortVersionString':'1.9.0',
    'CFBundleVersion':'10', 'CFBundleSupportedPlatforms':['iPhoneOS'],
    'MinimumOSVersion':'17.4'}))
PY
echo "Built $OUT/StikJIT.framework from pinned Swift and Rust source"
