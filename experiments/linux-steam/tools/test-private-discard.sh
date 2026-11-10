#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
set -euo pipefail
repo=$(cd "$(dirname "$0")/../../.." && pwd)
: "${LINUX_LAB_ARTIFACTS:?Prepared external host artifacts required}"
: "${LINUX_LAB_DISCARD_OUT:?NEW private external output directory required}"
: "${LD_LLD:=ld.lld}"
case "$LINUX_LAB_DISCARD_OUT" in /Volumes/easystore/*) ;; *) exit 2;; esac
[[ ! -e "$LINUX_LAB_DISCARD_OUT" ]] || exit 2
mkdir -m 700 "$LINUX_LAB_DISCARD_OUT"
src="$repo/vendor/LinuxRunner";host="$LINUX_LAB_ARTIFACTS/host";lab="$repo/experiments/linux-steam";out="$LINUX_LAB_DISCARD_OUT"
flags=(-fsanitize=address,undefined -fno-omit-frame-pointer -DGUEST_ARM64=1 -DENGINE_ASBESTOS=1 -DLOG_HANDLER_DPRINTF=1 -DISH_INTERNAL=1
    -I "$src" -I "$host" -I "$lab/app" -Wall -Wextra -Werror -Wno-unused-parameter)
for mode in normal fail-second;do
    set -- --sanitize --host-private-discard
    [[ $mode != fail-second ]] || set -- "$@" --host-fail-second
    python3 "$lab/tools/build-madvise-stats.py" "$src" "$host" "$host/libish.a" "$out/$mode" "$@" > "$out/$mode-build.log" 2>&1
    python3 "$lab/tools/build-lazy-pages.py" "$src" "$host" "$out/$mode/libish.a" "$out/$mode-grouped" --sanitize >> "$out/$mode-build.log" 2>&1
    xcrun clang "${flags[@]}" "$lab/tools/private-discard-control.c" "$out/$mode-grouped/libish.a" -L "$host" -lish_emu -lfakefs -lsqlite3 -o "$out/control-$mode"
done
xcrun clang "${flags[@]}" -DIDECK_LAB_MADVISE_STATS=1 -DIDECK_LAB_LAZY_PAGES=1 \
    "$lab/app/LinuxLabRuntime.c" "$lab/app/LabDeviceFS.c" "$lab/app/LabBridge.c" "$lab/app/LaunchProtocol.c" "$lab/tools/host-embed.c" \
    "$out/normal-grouped/libish.a" -L "$host" -lish_emu -lfakefs -lsqlite3 -o "$out/guest-control"
for name in lazy-pages-probe probe;do
    set -- "$lab/guest/$name.c"
    [[ $name != probe ]] || set -- "$@" "$lab/guest/clone.S"
    xcrun clang --target=aarch64-linux-gnu --ld-path="$(command -v "$LD_LLD")" -nostdlib -static -ffreestanding -fno-builtin -fno-stack-protector -O2 -Wall -Wextra -Werror \
        "$@" -Wl,-e,_start -o "$out/$name.elf"
done
python3 - "$out" <<'PY'
from pathlib import Path
import hashlib,json,subprocess,sys
out=Path(sys.argv[1]);tests=[]
def execute(name,command,count,report=None):
    log=out/(name+'.log')
    with log.open('xb') as f:r=subprocess.run(command,stdout=f,stderr=f,timeout=45)
    s=(report or log).read_text();checks=[l for l in s.splitlines() if l.endswith('=PASS') or l.endswith('=FAIL')]
    tests.append(dict(name=name,status=r.returncode,checks=checks,expected=count,log_sha256=hashlib.sha256(log.read_bytes()).hexdigest()))
    assert r.returncode==0 and len(checks)==count and all(l.endswith('=PASS') for l in checks),tests[-1]
for mode in ('normal','fail-second'):execute(mode,[str(out/('control-'+mode)),mode],22)
for name,report,count in [('lazy-pages-probe','lazy-results.txt',20),('probe','probe-results.txt',16)]:
    root=out/(name+'-root');root.mkdir();(root/'probe').write_bytes((out/(name+'.elf')).read_bytes());(root/'probe').chmod(0o700)
    execute(name,[str(out/'guest-control'),str(root)],count,root/report)
evidence=dict(scope='HOST only: real pinned memory objects and real ARM64 guest controls; mmap/memory/wrapper units sanitized, remaining dependency not fully; no iPad/Steam reclamation fix claim',tests=tests)
(out/'evidence.json').write_text(json.dumps(evidence,indent=2)+'\n');print(json.dumps(evidence))
PY
