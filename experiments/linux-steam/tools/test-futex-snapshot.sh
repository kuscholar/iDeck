#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
set -euo pipefail
repo=$(cd "$(dirname "$0")/../../.." && pwd)
: "${LINUX_LAB_ARTIFACTS:?Prepared host build}"
: "${LINUX_LAB_FUTEX_SNAPSHOT_OUT:?NEW private output}"
: "${LINUX_LAB_LOG_ARCHIVE:?Existing lifetime/log archive}"
: "${LD_LLD:?Explicit ARM64 linker}"
out="$LINUX_LAB_FUTEX_SNAPSHOT_OUT"
case "$out" in /Volumes/easystore/*) ;; *) exit 2;; esac
[[ ! -e "$out" ]] || exit 2
mkdir -m700 "$out"
src="$repo/vendor/LinuxRunner";host="$LINUX_LAB_ARTIFACTS/host";lab="$repo/experiments/linux-steam"
[[ $(git -C "$src" rev-parse HEAD) == d1419782da2e299fe22f1ddb85c70ae3d1e276b1 ]] || exit 2
[[ -z $(git -C "$src" status --porcelain --untracked-files=no) ]] || exit 2
xcrun clang --target=aarch64-linux-gnu --ld-path="$LD_LLD" -nostdlib -static -ffreestanding -fno-builtin -fno-stack-protector -O2 -Wall -Wextra -Werror \
 "$lab/guest/futex-snapshot-probe.c" "$lab/guest/clone.S" -Wl,-e,_start -o "$out/probe.elf"
xcrun clang -DIDECK_LAB_GUEST_LIFETIME=1 -DIDECK_LAB_NATIVE_LOG=1 -fsanitize=address,undefined -DGUEST_ARM64=1 -DENGINE_ASBESTOS=1 -DLOG_HANDLER_DPRINTF=1 -DISH_INTERNAL=1 \
 -I "$src" -I "$host" -I "$lab/app" -Wall -Wextra -Werror -Wno-unused-parameter \
 "$lab/app/LinuxLabRuntime.c" "$lab/app/LabDeviceFS.c" "$lab/app/LabBridge.c" "$lab/app/LaunchProtocol.c" "$lab/app/NativeKernelLog.c" "$lab/tools/futex-snapshot-control.c" \
 "$LINUX_LAB_LOG_ARCHIVE" -L "$host" -lish_emu -lfakefs -lsqlite3 -o "$out/control"
python3 - "$out" "$LINUX_LAB_LOG_ARCHIVE" <<'PY'
from pathlib import Path
import hashlib,json,subprocess,sys
out=Path(sys.argv[1]);root=out/'root';root.mkdir(mode=0o700);logs=out/'logs';logs.mkdir(mode=0o700)
(root/'probe').write_bytes((out/'probe.elf').read_bytes());(root/'probe').chmod(0o700)
with (out/'control.log').open('x') as log:r=subprocess.run([out/'control',root,logs],stdout=log,stderr=subprocess.STDOUT,timeout=25)
receipt={'scope':'HOST real ARM64 futex wait/private/wake, numeric-only nonblocking observer and native guest exit0; wrappers ASan/UBSan. NOT device/CEF diagnosis','exit':r.returncode,'archive_sha256':hashlib.sha256(Path(sys.argv[2]).read_bytes()).hexdigest(),'log_sha256':hashlib.sha256((out/'control.log').read_bytes()).hexdigest(),'probe_sha256':hashlib.sha256((out/'probe.elf').read_bytes()).hexdigest()}
(out/'evidence.json').write_text(json.dumps(receipt,indent=2)+'\n');assert r.returncode==0,receipt
print('HOST actual blocked futex metadata/wake/exit PASS')
PY
