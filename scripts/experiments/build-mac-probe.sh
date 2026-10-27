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
