#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
set -euo pipefail
repo=$(cd "$(dirname "$0")/../../.." && pwd)
: "${LINUX_LAB_ARTIFACTS:?Prepared private external artifacts required}"
: "${LINUX_LAB_LAZY_OUT:?NEW private external directory required}"
: "${LINUX_LAB_LAZY_ARCHIVE:?Sanitized copied lazy-memory archive required}"
: "${LD_LLD:=ld.lld}"
case "$LINUX_LAB_LAZY_OUT" in /Volumes/easystore/*) ;; *) exit 2;; esac
[[ ! -e "$LINUX_LAB_LAZY_OUT" ]] || exit 2
src="$repo/vendor/LinuxRunner";host="$LINUX_LAB_ARTIFACTS/host";lab="$repo/experiments/linux-steam"
mkdir -m 700 "$LINUX_LAB_LAZY_OUT"
xcrun clang --target=aarch64-linux-gnu --ld-path="$(command -v "$LD_LLD")" -nostdlib -static -ffreestanding -fno-builtin -fno-stack-protector -O2 -Wall -Wextra -Werror \
    "$lab/guest/lazy-pages-probe.c" -Wl,-e,_start -o "$LINUX_LAB_LAZY_OUT/lazy.elf"
xcrun clang --target=aarch64-linux-gnu --ld-path="$(command -v "$LD_LLD")" -nostdlib -static -ffreestanding -fno-builtin -fno-stack-protector -O2 -Wall -Wextra -Werror \
    "$lab/guest/probe.c" "$lab/guest/clone.S" -Wl,-e,_start -o "$LINUX_LAB_LAZY_OUT/standard.elf"
for mode in base grouped;do
    archive="$host/libish.a";flag=0
    if [[ $mode == grouped ]];then archive="$LINUX_LAB_LAZY_ARCHIVE";flag=1;fi
    xcrun clang -DIDECK_LAB_LAZY_PAGES="$flag" -fsanitize=address,undefined -DGUEST_ARM64=1 -DENGINE_ASBESTOS=1 -DLOG_HANDLER_DPRINTF=1 -DISH_INTERNAL=1 \
        -I "$src" -I "$host" -I "$lab/app" -Wall -Wextra -Werror -Wno-unused-parameter \
        "$lab/app/LinuxLabRuntime.c" "$lab/app/LabDeviceFS.c" "$lab/app/LabBridge.c" "$lab/app/LaunchProtocol.c" "$lab/tools/host-embed.c" \
        "$archive" -L "$host" -lish_emu -lfakefs -lsqlite3 -o "$LINUX_LAB_LAZY_OUT/control-$mode"
done
python3 - "$LINUX_LAB_LAZY_OUT" <<'PY'
from pathlib import Path
import hashlib,json,subprocess,sys
out=Path(sys.argv[1]);tests=[]
for mode in ('base','grouped'):
 for guest in ('lazy','standard'):
  root=out/(mode+'-'+guest);root.mkdir();(root/'probe').write_bytes((out/(guest+'.elf')).read_bytes());(root/'probe').chmod(0o700)
  with (out/(mode+'-'+guest+'.log')).open('xb') as log:
   p=subprocess.run([str(out/('control-'+mode)),str(root)],stdout=log,stderr=log,timeout=30)
  report=root/('lazy-results.txt' if guest=='lazy' else 'probe-results.txt')
  lines=report.read_text().splitlines() if report.exists() else []
  tests.append(dict(mode=mode,guest=guest,status=p.returncode,checks=lines))
(out/'evidence.json').write_text(json.dumps(dict(scope='real ARM64 guest semantics on host; grouped copied memory.c plus wrapper sanitized, other dependency units not; no iPad or Steam UI proof',tests=tests),indent=2)+'\n')
assert all(t['status']==0 and len(t['checks'])==(20 if t['guest']=='lazy' else 16) and all(s.endswith('=PASS') for s in t['checks']) for t in tests),tests
print(json.dumps(tests,indent=2))
PY
