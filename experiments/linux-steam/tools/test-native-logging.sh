#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
set -euo pipefail
repo=$(cd "$(dirname "$0")/../../.." && pwd)
: "${LINUX_LAB_ARTIFACTS:?Prepared private external artifacts required}"
: "${LINUX_LAB_LOG_OUT:?New private output directory required}"
: "${LINUX_LAB_LOG_ARCHIVE:?Copied log bridge plus guest lifetime archive required}"
: "${LD_LLD:=ld.lld}"
case "$LINUX_LAB_LOG_OUT" in /Volumes/easystore/*) ;; *) exit 2;; esac
[[ ! -e "$LINUX_LAB_LOG_OUT" ]] || exit 2
mkdir -m 700 "$LINUX_LAB_LOG_OUT"
src="$repo/vendor/LinuxRunner";host="$LINUX_LAB_ARTIFACTS/host";lab="$repo/experiments/linux-steam"
[[ $(git -C "$src" rev-parse HEAD) == d1419782da2e299fe22f1ddb85c70ae3d1e276b1 ]] || exit 2
[[ -z $(git -C "$src" status --porcelain --untracked-files=no) ]] || exit 2
xcrun clang -DIDECK_LAB_GUEST_LIFETIME=1 -DIDECK_LAB_NATIVE_LOG=1 -fsanitize=address,undefined -DGUEST_ARM64=1 -DENGINE_ASBESTOS=1 -DLOG_HANDLER_DPRINTF=1 -DISH_INTERNAL=1 \
    -I "$src" -I "$host" -I "$lab/app" -Wall -Wextra -Werror -Wno-unused-parameter \
    "$lab/app/LinuxLabRuntime.c" "$lab/app/LabDeviceFS.c" "$lab/app/LabBridge.c" "$lab/app/LaunchProtocol.c" "$lab/app/NativeKernelLog.c" "$lab/tools/native-log-control.c" \
    "$LINUX_LAB_LOG_ARCHIVE" -L "$host" -lish_emu -lfakefs -lsqlite3 -o "$LINUX_LAB_LOG_OUT/control"
xcrun clang --target=aarch64-linux-gnu --ld-path="$(command -v "$LD_LLD")" -nostdlib -static -ffreestanding -fno-builtin -fno-stack-protector -O2 -Wall -Wextra -Werror \
    "$lab/guest/probe.c" "$lab/guest/clone.S" -Wl,-e,_start -o "$LINUX_LAB_LOG_OUT/probe.elf"
python3 - "$LINUX_LAB_LOG_OUT" <<'PY'
from pathlib import Path
import hashlib,json,subprocess,sys
out=Path(sys.argv[1]);tests=[]
for mode in ('privacy-cap','resources','kernel','health','health-collision','nonprivate','symlink'):
 directory=out/(mode+'-logs')
 if mode=='symlink':
  target=out/'own-link-target';target.mkdir(mode=0o700);directory.symlink_to(target,target_is_directory=True)
 else:
  directory.mkdir(mode=0o755 if mode=='nonprivate' else 0o700)
  directory.chmod(0o755 if mode=='nonprivate' else 0o700) # Explicit fixture, independent of caller umask.
 command=[str(out/'control'),'refuse' if mode in ('nonprivate','symlink') else mode,str(directory)]
 if mode=='kernel':
  root=out/'kernel-root';root.mkdir();(root/'probe').write_bytes((out/'probe.elf').read_bytes());(root/'probe').chmod(0o700);command.append(str(root))
 with (out/(mode+'.log')).open('xb') as log:
  result=subprocess.run(command,stdin=subprocess.DEVNULL,stdout=log,stderr=log,timeout=15)
 if mode=='kernel' and result.returncode==0:
  lines=(root/'probe-results.txt').read_text().splitlines();assert len(lines)==16 and all(x.endswith('=PASS') for x in lines)
 tests.append(dict(mode=mode,status=result.returncode,log_sha256=hashlib.sha256((out/(mode+'.log')).read_bytes()).hexdigest()))
(out/'evidence.json').write_text(json.dumps(dict(scope='private bounded native logging and real host ARM64 kernel controls; no Steam/iPad/crash fix claim',tests=tests),indent=2)+'\n')
assert all(x['status']==0 for x in tests),tests
print(json.dumps(tests))
PY
