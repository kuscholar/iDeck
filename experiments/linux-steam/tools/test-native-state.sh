#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
set -euo pipefail
repo=$(cd "$(dirname "$0")/../../.." && pwd)
: "${LINUX_LAB_ARTIFACTS:?Prepared private external artifacts required}"
: "${LINUX_LAB_NATIVE_STATE_OUT:?New private output directory required}"
: "${LINUX_LAB_LIFETIME_ARCHIVE:?Copied tracked host archive required}"
: "${LINUX_LAB_NEGATIVE_ARCHIVE:?Explicit HOST ONLY child-start EAGAIN archive required}"
: "${LD_LLD:=ld.lld}"
case "$LINUX_LAB_NATIVE_STATE_OUT" in /Volumes/easystore/*) ;; *) exit 2;; esac
[[ ! -e "$LINUX_LAB_NATIVE_STATE_OUT" ]] || exit 2
src="$repo/vendor/LinuxRunner";host="$LINUX_LAB_ARTIFACTS/host";lab="$repo/experiments/linux-steam"
[[ $(git -C "$src" rev-parse HEAD) == d1419782da2e299fe22f1ddb85c70ae3d1e276b1 ]] || exit 2
[[ -z $(git -C "$src" status --porcelain --untracked-files=no) ]] || exit 2
mkdir "$LINUX_LAB_NATIVE_STATE_OUT"
xcrun clang --target=aarch64-linux-gnu --ld-path="$(command -v "$LD_LLD")" -nostdlib -static -ffreestanding -fno-builtin -fno-stack-protector -O2 -Wall -Wextra -Werror \
    "$lab/guest/probe.c" "$lab/guest/clone.S" -Wl,-e,_start -o "$LINUX_LAB_NATIVE_STATE_OUT/probe.elf"
for mode in normal failure; do
    archive="$LINUX_LAB_LIFETIME_ARCHIVE"
    if [[ "$mode" == failure ]];then archive="$LINUX_LAB_NEGATIVE_ARCHIVE";fi
    xcrun clang -DIDECK_LAB_GUEST_LIFETIME=1 -fsanitize=address,undefined -DGUEST_ARM64=1 -DENGINE_ASBESTOS=1 -DLOG_HANDLER_DPRINTF=1 -DISH_INTERNAL=1 \
        -I "$src" -I "$host" -I "$lab/app" -Wall -Wextra -Werror -Wno-unused-parameter \
        "$lab/app/LinuxLabRuntime.c" "$lab/app/LabDeviceFS.c" "$lab/app/LabBridge.c" "$lab/app/LaunchProtocol.c" "$lab/tools/native-state-control.c" \
        "$archive" -L "$host" -lish_emu -lfakefs -lsqlite3 -o "$LINUX_LAB_NATIVE_STATE_OUT/control-$mode"
done
python3 - "$LINUX_LAB_NATIVE_STATE_OUT" "$LINUX_LAB_LIFETIME_ARCHIVE" "$LINUX_LAB_NEGATIVE_ARCHIVE" <<'PY'
from pathlib import Path
import hashlib,json,subprocess,sys
out=Path(sys.argv[1]);results=[]
for mode,archive in zip(('normal','failure'),sys.argv[2:]):
 root=out/mode;root.mkdir();(root/'probe').write_bytes((out/'probe.elf').read_bytes());(root/'probe').chmod(0o700)
 with (out/(mode+'.log')).open('xb') as log:
  result=subprocess.run([str(out/('control-'+mode)),str(root),mode],stdout=log,stderr=log,timeout=15)
 if mode=='normal' and result.returncode==0:
  lines=(root/'probe-results.txt').read_text().splitlines();assert len(lines)==16 and all(x.endswith('=PASS') for x in lines)
 results.append(dict(mode=mode,status=result.returncode,archive_sha256=hashlib.sha256(Path(archive).read_bytes()).hexdigest(),log_sha256=hashlib.sha256((out/(mode+'.log')).read_bytes()).hexdigest()))
(out/'evidence.json').write_text(json.dumps(dict(scope='real host ARM64 interpreter: signal ownership persists after guest cleanup; not an iPad/Wine validation or runtime fix; wrapper/task hooks sanitized, other dependency units not instrumented',tests=results),indent=2)+'\n')
assert all(x['status']==0 for x in results),results
print(json.dumps(results))
PY
