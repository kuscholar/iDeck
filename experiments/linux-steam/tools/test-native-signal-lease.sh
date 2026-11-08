#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
set -euo pipefail
repo=$(cd "$(dirname "$0")/../../.." && pwd)
: "${LINUX_LAB_SIGNAL_LEASE_OUT:?New private external output directory required}"
case "$LINUX_LAB_SIGNAL_LEASE_OUT" in /Volumes/easystore/*) ;; *) exit 2;; esac
[[ ! -e "$LINUX_LAB_SIGNAL_LEASE_OUT" ]] || exit 2
mkdir "$LINUX_LAB_SIGNAL_LEASE_OUT"
lab="$repo/experiments/linux-steam"
xcrun clang -fsanitize=address,undefined -Wall -Wextra -Werror -I "$lab/app" \
    "$lab/app/NativeSignalLease.c" "$lab/tests/native-signal-lease-test.c" -o "$LINUX_LAB_SIGNAL_LEASE_OUT/control"
if [[ ${LINUX_LAB_SIGNAL_LEASE_REAL_RUNTIME:-0} == 1 ]];then
    : "${LINUX_LAB_ARTIFACTS:?Prepared private host artifacts required}"
    : "${LINUX_LAB_LIFETIME_ARCHIVE:?Copied tracked host archive required}"
    : "${LD_LLD:=ld.lld}"
    src="$repo/vendor/LinuxRunner";host="$LINUX_LAB_ARTIFACTS/host"
    [[ $(git -C "$src" rev-parse HEAD) == d1419782da2e299fe22f1ddb85c70ae3d1e276b1 ]] || exit 2
    [[ -z $(git -C "$src" status --porcelain --untracked-files=no) ]] || exit 2
    xcrun clang --target=aarch64-linux-gnu --ld-path="$(command -v "$LD_LLD")" -nostdlib -static -ffreestanding -fno-builtin -fno-stack-protector -O2 -Wall -Wextra -Werror \
        "$lab/guest/probe.c" "$lab/guest/clone.S" -Wl,-e,_start -o "$LINUX_LAB_SIGNAL_LEASE_OUT/probe.elf"
    xcrun clang -DIDECK_LAB_GUEST_LIFETIME=1 -DIDECK_TEST_NATIVE_SIGNAL_LEASE=1 -fsanitize=address,undefined -DGUEST_ARM64=1 -DENGINE_ASBESTOS=1 -DLOG_HANDLER_DPRINTF=1 -DISH_INTERNAL=1 \
        -I "$src" -I "$host" -I "$lab/app" -Wall -Wextra -Werror -Wno-unused-parameter \
        "$lab/app/LinuxLabRuntime.c" "$lab/app/LabDeviceFS.c" "$lab/app/LabBridge.c" "$lab/app/LaunchProtocol.c" "$lab/app/NativeSignalLease.c" "$lab/tools/native-state-control.c" \
        "$LINUX_LAB_LIFETIME_ARCHIVE" -L "$host" -lish_emu -lfakefs -lsqlite3 -o "$LINUX_LAB_SIGNAL_LEASE_OUT/real-runtime"
fi
python3 - "$LINUX_LAB_SIGNAL_LEASE_OUT" <<'PY'
from pathlib import Path
import hashlib,json,subprocess,sys
out=Path(sys.argv[1]);tests=[]
for mode in ('normal','claim-conflict','foreign-handler','foreign-mask','foreign-flags'):
 with (out/(mode+'.log')).open('xb') as log:
  result=subprocess.run([str(out/'control'),mode],stdout=log,stderr=log,timeout=10)
 tests.append(dict(mode=mode,status=result.returncode,log_sha256=hashlib.sha256((out/(mode+'.log')).read_bytes()).hexdigest()))
if (out/'real-runtime').exists():
 root=out/'real-root';root.mkdir();(root/'probe').write_bytes((out/'probe.elf').read_bytes());(root/'probe').chmod(0o700)
 with (out/'real-runtime.log').open('xb') as log:
  result=subprocess.run([str(out/'real-runtime'),str(root),'normal'],stdout=log,stderr=log,timeout=15)
 tests.append(dict(mode='real-runtime-unknown-workers-refusal',status=result.returncode,log_sha256=hashlib.sha256((out/'real-runtime.log').read_bytes()).hexdigest()))
 if result.returncode==0:
  lines=(root/'probe-results.txt').read_text().splitlines();assert len(lines)==16 and all(x.endswith('=PASS') for x in lines)
(out/'evidence.json').write_text(json.dumps(dict(scope='native OS component fixture restores only its own signal test policies; optional real Linux control MUST refuse release because other workers unknown. NOT iPad/Wine/full-quiescence success; not integrated into Lab',tests=tests),indent=2)+'\n')
assert all(x['status']==0 for x in tests),tests
print(json.dumps(tests))
PY
