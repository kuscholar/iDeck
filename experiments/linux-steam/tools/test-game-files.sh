#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
set -euo pipefail
repo=$(cd "$(dirname "$0")/../../.." && pwd)
: "${LINUX_LAB_GAME_FILES_OUT:?New private external output directory required}"
case "$LINUX_LAB_GAME_FILES_OUT" in /Volumes/easystore/*) ;; *) exit 2;; esac
[[ ! -e "$LINUX_LAB_GAME_FILES_OUT" ]] || exit 2
mkdir -m 700 "$LINUX_LAB_GAME_FILES_OUT"
lab="$repo/experiments/linux-steam";out="$LINUX_LAB_GAME_FILES_OUT"
xcrun clang -fsanitize=address,undefined -fno-omit-frame-pointer -Wall -Wextra -Werror -I "$lab/app" \
    "$lab/app/GameFiles.c" "$lab/app/GameFilePolicy.c" "$lab/app/LaunchProtocol.c" "$lab/tests/game-files-test.c" -o "$out/control"
python3 - "$out" "$lab" <<'PY'
from pathlib import Path
import hashlib,json,subprocess,sys
out,lab=map(Path,sys.argv[1:]);root=out/'fixture';root.mkdir(mode=0o700)
with (out/'control.log').open('xb') as f:r=subprocess.run([str(out/'control'),str(root)],stdout=f,stderr=f,timeout=30)
checks=[line for line in (out/'control.log').read_text().splitlines() if line.endswith('=PASS') or line.endswith('=FAIL')]
evidence=dict(scope='HOST native directory/file capabilities and synthetic PE identity bytes; no Steam/Madeira/game/device execution',status=r.returncode,checks=checks,
    source_sha256={str(p.relative_to(lab)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [lab/'app/GameFiles.c',lab/'app/GameFiles.h',lab/'app/LaunchProtocol.c',lab/'tests/game-files-test.c']},
    log_sha256=hashlib.sha256((out/'control.log').read_bytes()).hexdigest())
(out/'evidence.json').write_text(json.dumps(evidence,indent=2)+'\n');assert r.returncode==0 and len(checks)>=30 and all(line.endswith('=PASS') for line in checks),evidence
print(json.dumps(evidence))
PY
