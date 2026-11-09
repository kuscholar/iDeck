#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
set -euo pipefail
repo=$(cd "$(dirname "$0")/../../.." && pwd)
: "${LINUX_LAB_ARTIFACTS:?Prepared private external artifacts required}"
: "${LINUX_LAB_PAGE_OUT:?NEW private external directory required}"
: "${LD_LLD:=ld.lld}"
case "$LINUX_LAB_PAGE_OUT" in /Volumes/easystore/*) ;; *) exit 2;; esac
[[ ! -e "$LINUX_LAB_PAGE_OUT" ]] || exit 2
src="$repo/vendor/LinuxRunner";host="$LINUX_LAB_ARTIFACTS/host";lab="$repo/experiments/linux-steam"
: "${LINUX_LAB_PAGE_ARCHIVE:=$host/libish.a}"
[[ $(git -C "$src" rev-parse HEAD) == d1419782da2e299fe22f1ddb85c70ae3d1e276b1 ]] || exit 2
[[ -z $(git -C "$src" status --porcelain --untracked-files=no) ]] || exit 2
mkdir -m 700 "$LINUX_LAB_PAGE_OUT"
xcrun clang -DGUEST_ARM64=1 -DENGINE_ASBESTOS=1 -DLOG_HANDLER_DPRINTF=1 -DISH_INTERNAL=1 \
    -I "$src" -I "$host" -I "$lab/app" -Wall -Wextra -Werror -Wno-unused-parameter \
    "$lab/app/LinuxLabRuntime.c" "$lab/app/LabDeviceFS.c" "$lab/app/LabBridge.c" "$lab/app/LaunchProtocol.c" "$lab/tools/page-footprint-control.c" \
    "$LINUX_LAB_PAGE_ARCHIVE" -L "$host" -lish_emu -lfakefs -lsqlite3 -o "$LINUX_LAB_PAGE_OUT/control"
for reserve in 128 512;do
    xcrun clang --target=aarch64-linux-gnu --ld-path="$(command -v "$LD_LLD")" -nostdlib -static -ffreestanding -fno-builtin -fno-stack-protector -O2 -Wall -Wextra -Werror \
        -DRESERVE_MIB="$reserve" "$lab/guest/page-footprint-probe.c" -Wl,-e,_start -o "$LINUX_LAB_PAGE_OUT/probe-$reserve.elf"
done
python3 - "$LINUX_LAB_PAGE_OUT" "$LINUX_LAB_PAGE_ARCHIVE" <<'PY'
from pathlib import Path
import hashlib,json,subprocess,sys
out=Path(sys.argv[1]);results=[]
for reserve in (128,512):
 root=out/str(reserve);root.mkdir(mode=0o700);(root/'probe').write_bytes((out/f'probe-{reserve}.elf').read_bytes());(root/'probe').chmod(0o700)
 with (out/f'{reserve}.stderr').open('xb') as log:
  p=subprocess.run([str(out/'control'),str(root)],stdout=subprocess.PIPE,stderr=log,timeout=60)
 (out/f'{reserve}.stdout').write_bytes(p.stdout)
 assert p.returncode==0,p.returncode
 result=json.loads(p.stdout);assert result['guest_status']==0
 result['reserve_mib']=reserve;results.append(result)
receipt=dict(scope='HOST real unsanitized ARM64 interpreter; public self-task footprint, not iPad/Steam or allocator-fix evidence',archive_sha256=hashlib.sha256(Path(sys.argv[2]).read_bytes()).hexdigest(),results=results)
receipt['lazy_to_eager_touch_delta_ratio']=results[1]['touch_delta_bytes']/results[0]['touch_delta_bytes']
(out/'evidence.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
PY
