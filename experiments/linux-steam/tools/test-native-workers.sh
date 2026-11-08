#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
set -euo pipefail
repo=$(cd "$(dirname "$0")/../../.." && pwd)
: "${LINUX_LAB_ARTIFACTS:?Prepared private external artifacts required}"
: "${LINUX_LAB_WORKERS_OUT:?New private output directory required}"
: "${LINUX_LAB_WORKER_ARCHIVE:?Copied tracked native-worker archive required}"
: "${LINUX_LAB_WORKER_NEGATIVE_ARCHIVE:?Explicit HOST ONLY worker-start EAGAIN archive required}"
: "${LD_LLD:=ld.lld}"
case "$LINUX_LAB_WORKERS_OUT" in /Volumes/easystore/*) ;; *) exit 2;; esac
[[ ! -e "$LINUX_LAB_WORKERS_OUT" ]] || exit 2
mkdir "$LINUX_LAB_WORKERS_OUT"
src="$repo/vendor/LinuxRunner";host="$LINUX_LAB_ARTIFACTS/host";lab="$repo/experiments/linux-steam"
[[ $(git -C "$src" rev-parse HEAD) == d1419782da2e299fe22f1ddb85c70ae3d1e276b1 ]] || exit 2
[[ -z $(git -C "$src" status --porcelain --untracked-files=no) ]] || exit 2
for mode in normal failure;do
    archive="$LINUX_LAB_WORKER_ARCHIVE"
    if [[ "$mode" == failure ]];then archive="$LINUX_LAB_WORKER_NEGATIVE_ARCHIVE";fi
    xcrun clang -DIDECK_LAB_GUEST_LIFETIME=1 -DIDECK_LAB_NATIVE_WORKERS=1 -fsanitize=address,undefined -DGUEST_ARM64=1 -DENGINE_ASBESTOS=1 -DLOG_HANDLER_DPRINTF=1 -DISH_INTERNAL=1 \
        -I "$src" -I "$host" -I "$lab/app" -Wall -Wextra -Werror -Wno-unused-parameter \
        "$lab/app/LinuxLabRuntime.c" "$lab/app/LabDeviceFS.c" "$lab/app/LabBridge.c" "$lab/app/LaunchProtocol.c" "$lab/tools/native-workers-control.c" \
        "$archive" -L "$host" -lish_emu -lfakefs -lsqlite3 -o "$LINUX_LAB_WORKERS_OUT/control-$mode"
done
xcrun clang --target=aarch64-linux-gnu --ld-path="$(command -v "$LD_LLD")" -nostdlib -static -ffreestanding -fno-builtin -fno-stack-protector -O2 -Wall -Wextra -Werror \
    "$lab/guest/probe.c" "$lab/guest/clone.S" -Wl,-e,_start -o "$LINUX_LAB_WORKERS_OUT/standard.elf"
xcrun clang --target=aarch64-linux-gnu --ld-path="$(command -v "$LD_LLD")" -nostdlib -static -ffreestanding -fno-builtin -fno-stack-protector -O2 -Wall -Wextra -Werror \
    "$lab/guest/worker-forward-probe.c" -Wl,-e,_start -o "$LINUX_LAB_WORKERS_OUT/forward.elf"
python3 - "$LINUX_LAB_WORKERS_OUT" "$LINUX_LAB_WORKER_ARCHIVE" "$LINUX_LAB_WORKER_NEGATIVE_ARCHIVE" <<'PY'
from pathlib import Path
import hashlib,json,os,subprocess,sys
out=Path(sys.argv[1]);tests=[]
environment=dict(os.environ);environment.pop('ISH_GUEST_PROFILE',None)
for mode in ('roles','timer','tty','forward','profile','underflow','failure'):
 command=[str(out/('control-failure' if mode=='failure' else 'control-normal')),mode]
 if mode in ('forward','profile'):
  root=out/(mode+'-root');root.mkdir();body=(out/('forward.elf' if mode=='forward' else 'standard.elf')).read_bytes()
  (root/'probe').write_bytes(body);(root/'probe').chmod(0o700)
  if mode=='forward':(root/'worker-control').write_bytes(body);(root/'worker-control').chmod(0o700)
  command.append(str(root))
  if mode=='profile':command.append(str(out/'own-fixture-profile.txt'))
 with (out/(mode+'.log')).open('xb') as log:
  result=subprocess.run(command,stdin=subprocess.DEVNULL,stdout=log,stderr=log,env=environment,timeout=15)
 if mode=='profile' and result.returncode==0:
  lines=(root/'probe-results.txt').read_text().splitlines();assert len(lines)==16 and all(x.endswith('=PASS') for x in lines)
 tests.append(dict(mode=mode,status=result.returncode,log_sha256=hashlib.sha256((out/(mode+'.log')).read_bytes()).hexdigest()))
(out/'evidence.json').write_text(json.dumps(dict(scope='real host native worker providers/ARM64 controls; profiler deliberately remains live until host process exit; no iPad/Wine/full-cleanup or game claim',tests=tests,
 archive_sha256=hashlib.sha256(Path(sys.argv[2]).read_bytes()).hexdigest(),negative_archive_sha256=hashlib.sha256(Path(sys.argv[3]).read_bytes()).hexdigest()),indent=2)+'\n')
assert all(x['status']==0 for x in tests),tests
print(json.dumps(tests))
PY
