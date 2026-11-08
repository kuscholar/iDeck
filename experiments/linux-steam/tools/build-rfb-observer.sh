#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
# Host-only shared ClientInit: preserve an existing app viewer. No device patch.
set -euo pipefail
repo=$(cd "$(dirname "$0")/../../.." && pwd)
: "${LINUX_LAB_RFB_OBSERVER_OUT:?New private external build directory required}"
case "$LINUX_LAB_RFB_OBSERVER_OUT" in /Volumes/easystore/*) ;; *) exit 2;; esac
[[ ! -e "$LINUX_LAB_RFB_OBSERVER_OUT" ]] || exit 2
vendor="$repo/vendor/LinuxRunner"
[[ $(git -C "$vendor" rev-parse HEAD) == d1419782da2e299fe22f1ddb85c70ae3d1e276b1 ]] || exit 2
[[ -z $(git -C "$vendor" status --porcelain --untracked-files=no) ]] || exit 2
mkdir "$LINUX_LAB_RFB_OBSERVER_OUT"
python3 - "$vendor" "$LINUX_LAB_RFB_OBSERVER_OUT" <<'PY'
from pathlib import Path
import sys,hashlib,json
vendor,out=map(Path,sys.argv[1:]);src=vendor/'app/LinuxRunner/RFBClient.m';body=src.read_text();assert body.count('uint8_t shared=0;')==1
(out/'RFBClient.m').write_text(body.replace('uint8_t shared=0;','uint8_t shared=1;'))
(out/'source-evidence.json').write_text(json.dumps(dict(scope='host observer only; existing iOS app unchanged',source_revision='d1419782da2e299fe22f1ddb85c70ae3d1e276b1',source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),shared_client_init=True),indent=2)+'\n')
PY
headers="$vendor/app/LinuxRunner"
xcrun clang -O2 -I "$headers" -c "$headers/RFBProtocol.c" -o "$LINUX_LAB_RFB_OBSERVER_OUT/protocol.o"
xcrun clang -fobjc-arc -fblocks -O2 -I "$headers" "$repo/experiments/linux-steam/tools/rfb-capture.m" "$LINUX_LAB_RFB_OBSERVER_OUT/RFBClient.m" "$LINUX_LAB_RFB_OBSERVER_OUT/protocol.o" \
 -framework Foundation -framework ImageIO -framework CoreGraphics -o "$LINUX_LAB_RFB_OBSERVER_OUT/rfb-capture"
