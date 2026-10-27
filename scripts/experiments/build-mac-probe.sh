#!/bin/bash
# Builds the published macos-on-ios probe from a user-provided clean MIT source
# checkout. No Valve files, profiles, installation, or credentials are touched.
set -euo pipefail
source_dir=${1:?Pass the path to a clean macos-on-ios-public checkout}
out=${2:?Pass a disposable output directory}
repo=$(cd "$source_dir" && pwd)
test "$(git -C "$repo" rev-parse HEAD)" = c2562a333d4de4c08da4ceb4a4f1485bddb84e04 || {
  echo 'Unexpected source revision; inspect and update the pinned revision before running.' >&2; exit 1;
}
mkdir -p "$out"
# Copy to a disposable directory; do not edit the user's reference checkout.
tmp=$(mktemp -d "${TMPDIR:-/tmp}/ideck-mac-probe.XXXXXX")
trap 'rm -rf "$tmp"' EXIT
cp -R "$repo/probe" "$repo/shim" "$tmp/"
git -C "$repo" show HEAD:probe/build.sh > "$tmp/probe/build.sh"
chmod +x "$tmp/probe/build.sh"
python3 - "$tmp/probe/build.sh" <<'PY'
import pathlib, sys
p = pathlib.Path(sys.argv[1]); s = p.read_text()
old = '-framework UIKit -framework QuartzCore -framework CoreGraphics -framework Foundation ../shim/overrides/AppKit.m'
new = '-framework UIKit -framework QuartzCore -framework CoreGraphics -framework Foundation -framework GameController ../shim/overrides/AppKit.m'
if s.count(old) != 1: raise SystemExit('Reference build script changed; inspect it first')
p.write_text(s.replace(old, new))
PY
(cd "$tmp/probe" && UDID=unused TEAM=unused IDENTITY=unused T="$out" BUNDLE_PREFIX=com.example.ideck.maclab ./build.sh mac shim)
# Inspect a retagged disposable copy without claiming it is signed or runnable.
cp "$out/MacProbe.app/Contents/MacOS/MacProbe" "$out/MacProbe-retagged"
xcrun vtool -set-build-version ios 17.0 27.0 -replace -output "$out/MacProbe-retagged" "$out/MacProbe-retagged"
xcrun install_name_tool \
  -change /System/Library/Frameworks/Cocoa.framework/Versions/A/Cocoa @rpath/CocoaShim.framework/CocoaShim \
  -change /System/Library/Frameworks/AppKit.framework/Versions/C/AppKit @rpath/AppKitShim.framework/AppKitShim \
  -change /System/Library/Frameworks/Metal.framework/Versions/A/Metal /System/Library/Frameworks/Metal.framework/Metal \
  -change /System/Library/Frameworks/QuartzCore.framework/Versions/A/QuartzCore /System/Library/Frameworks/QuartzCore.framework/QuartzCore \
  -change /System/Library/Frameworks/Foundation.framework/Versions/C/Foundation /System/Library/Frameworks/Foundation.framework/Foundation \
  -change /System/Library/Frameworks/CoreFoundation.framework/Versions/A/CoreFoundation /System/Library/Frameworks/CoreFoundation.framework/CoreFoundation \
  -add_rpath @executable_path/Frameworks "$out/MacProbe-retagged"
xcrun vtool -show-build "$out/MacProbe-retagged" | grep -q 'platform IOS'
if xcrun otool -L "$out/MacProbe-retagged" | grep -Eq '/System/Library/Frameworks/(AppKit|Cocoa)\.framework/Versions/'; then
  echo 'macOS-only framework dependency remains' >&2; exit 1
fi
