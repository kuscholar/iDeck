#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
set -euo pipefail
repo=$(cd "$(dirname "$0")/../../.." && pwd)
: "${LINUX_LAB_ARTIFACTS:?Prepared private external artifacts required}"
: "${LINUX_LAB_TOOL_OUT:?New private output directory required}"
: "${LD_LLD:=ld.lld}"
case "$LINUX_LAB_TOOL_OUT" in /Volumes/easystore/*) ;; *) exit 2;; esac
[[ ! -e "$LINUX_LAB_TOOL_OUT" ]] || exit 2
mkdir -p "$LINUX_LAB_TOOL_OUT/resources"
src="$repo/vendor/LinuxRunner";host="$LINUX_LAB_ARTIFACTS/host";lab="$repo/experiments/linux-steam"
[[ $(git -C "$src" rev-parse HEAD) == d1419782da2e299fe22f1ddb85c70ae3d1e276b1 ]] || exit 2
[[ -z $(git -C "$src" status --porcelain --untracked-files=no) ]] || exit 2
xcrun clang --target=aarch64-linux-gnu --ld-path="$(command -v "$LD_LLD")" -nostdlib -static -ffreestanding -fno-builtin -fno-stack-protector -O2 -Wall -Wextra -Werror \
 "$lab/guest/compatibility.c" "$lab/guest/compat-start.S" -Wl,-e,_start -o "$LINUX_LAB_TOOL_OUT/resources/ideck-madeira"
cp "$lab/compatibilitytool.vdf" "$lab/toolmanifest.vdf" "$LINUX_LAB_TOOL_OUT/resources/"
xcrun clang -fsanitize=address,undefined -DGUEST_ARM64=1 -DENGINE_ASBESTOS=1 -DISH_INTERNAL=1 \
 -I "$src" -I "$host" -I "$lab/app" -Wall -Wextra -Werror -Wno-unused-parameter \
 "$lab/app/ToolInstall.c" "$lab/app/LabDeviceFS.c" "$lab/tools/tool-install-control.c" \
 -L "$host" -lish -lish_emu -lfakefs -lsqlite3 -o "$LINUX_LAB_TOOL_OUT/control"
python3 - "$LINUX_LAB_TOOL_OUT" <<'PY'
from pathlib import Path
import subprocess,sys,json,hashlib
out=Path(sys.argv[1]);results=[]
for mode in ['positive','conflict','symlink','stale','invalid','noninit']:
 with (out/(mode+'.log')).open('xb') as log:
  r=subprocess.run([str(out/'control'),str(out/mode),str(out/'resources'),mode],stdout=log,stderr=log,timeout=20)
 results.append(dict(mode=mode,status=r.returncode,log_sha256=hashlib.sha256((out/(mode+'.log')).read_bytes()).hexdigest()))
(out/'evidence.json').write_text(json.dumps(dict(scope='actual pinned host fakefs/VFS; no Steam client discovery, device or game execution claim',tests=results,
 helper_sha256=hashlib.sha256((out/'resources/ideck-madeira').read_bytes()).hexdigest()),indent=2)+'\n')
assert all(x['status']==0 for x in results),results
print(json.dumps(results))
PY
