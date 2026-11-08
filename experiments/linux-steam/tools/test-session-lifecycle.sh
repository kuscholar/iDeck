#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
set -euo pipefail
repo=$(cd "$(dirname "$0")/../../.." && pwd)
: "${LINUX_LAB_ARTIFACTS:?Private prepared external artifacts required}"
: "${LINUX_LAB_LIFECYCLE_OUT:?Use a new private output directory}"
case "$LINUX_LAB_LIFECYCLE_OUT" in /Volumes/easystore/*) ;; *) exit 2;; esac
[[ ! -e "$LINUX_LAB_LIFECYCLE_OUT" ]] || { echo 'Refusing existing test output' >&2;exit 2; }
src="$repo/vendor/LinuxRunner";host="$LINUX_LAB_ARTIFACTS/host";lab="$repo/experiments/linux-steam"
[[ $(git -C "$src" rev-parse HEAD) == d1419782da2e299fe22f1ddb85c70ae3d1e276b1 ]] || exit 2
[[ -z $(git -C "$src" status --porcelain --untracked-files=no) ]] || exit 2
: "${LD_LLD:=ld.lld}"
LD_LLD=$(command -v "$LD_LLD")
library="$host/libish.a"
lifetime_definition=-DIDECK_LAB_GUEST_LIFETIME=0
if [[ ${LINUX_LAB_GUEST_LIFETIME:-0} == 1 ]]; then
    : "${LINUX_LAB_LIFETIME_ARCHIVE:?Provide the copied instrumented archive}"
    library="$LINUX_LAB_LIFETIME_ARCHIVE"
    lifetime_definition=-DIDECK_LAB_GUEST_LIFETIME=1
fi
mkdir "$LINUX_LAB_LIFECYCLE_OUT"
xcrun clang --target=aarch64-linux-gnu --ld-path="$LD_LLD" -nostdlib -static -ffreestanding -fno-builtin -fno-stack-protector -O2 -Wall -Wextra -Werror \
    "$lab/guest/session-lifecycle-probe.c" -Wl,-e,_start -o "$LINUX_LAB_LIFECYCLE_OUT/probe.elf"
xcrun clang "$lifetime_definition" -fsanitize=address,undefined -DGUEST_ARM64=1 -DENGINE_ASBESTOS=1 -DLOG_HANDLER_DPRINTF=1 -DISH_INTERNAL=1 \
    -I "$src" -I "$host" -I "$lab/app" -Wall -Wextra -Werror -Wno-unused-parameter \
    "$lab/app/LinuxLabRuntime.c" "$lab/app/LabDeviceFS.c" "$lab/app/LabBridge.c" "$lab/app/LaunchProtocol.c" "$lab/tools/session-lifecycle-control.c" \
    "$library" -L "$host" -lish_emu -lfakefs -lsqlite3 -o "$LINUX_LAB_LIFECYCLE_OUT/control"
xcrun clang --target=aarch64-linux-gnu --ld-path="$LD_LLD" -nostdlib -static -ffreestanding -fno-builtin -fno-stack-protector -O2 -Wall -Wextra -Werror \
    "$lab/guest/probe.c" "$lab/guest/clone.S" -Wl,-e,_start -o "$LINUX_LAB_LIFECYCLE_OUT/standard.elf"
python3 - "$LINUX_LAB_LIFECYCLE_OUT" <<'PY'
from pathlib import Path
import subprocess,sys,json,hashlib,time,os
out=Path(sys.argv[1]);results=[]
modes=['failure'] if os.environ.get('LINUX_LAB_LIFETIME_NEGATIVE')=='1' else ['observe','signal','standard']
for mode in modes:
 root=out/mode;root.mkdir();(root/'probe').write_bytes((out/('standard.elf' if mode=='standard' else 'probe.elf')).read_bytes());(root/'probe').chmod(0o700)
 start=time.monotonic()
 with (out/(mode+'.log')).open('xb') as log:r=subprocess.run([str(out/'control'),str(root),mode],stdout=log,stderr=log,timeout=15)
 if mode=='standard' and r.returncode==0:
  lines=(root/'probe-results.txt').read_text().splitlines();assert len(lines)==16 and all(x.endswith('=PASS') for x in lines)
 result=dict(mode=mode,status=r.returncode,elapsed_seconds=round(time.monotonic()-start,3),log_sha256=hashlib.sha256((out/(mode+'.log')).read_bytes()).hexdigest());results.append(result)
(out/'evidence.json').write_text(json.dumps(dict(scope='host real ARM64 interpreter; wrapper sanitizers, static dependency not instrumented; no on-Air/Wine quiescence claim',tests=results),indent=2)+'\n')
assert all(x['status']==0 for x in results),results
print(json.dumps(results))
PY
