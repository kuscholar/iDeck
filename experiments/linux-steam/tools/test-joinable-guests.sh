#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
set -euo pipefail
repo=$(cd "$(dirname "$0")/../../.." && pwd)
: "${LINUX_LAB_ARTIFACTS:?Prepared private host interpreter required}"
: "${LINUX_LAB_JOIN_OUT:?New private external output required}"
: "${LD_LLD:=ld.lld}"
case "$LINUX_LAB_JOIN_OUT" in /Volumes/easystore/*) ;; *) exit 2;; esac
[[ ! -e "$LINUX_LAB_JOIN_OUT" ]] || exit 2
mkdir -m 700 "$LINUX_LAB_JOIN_OUT"
out="$LINUX_LAB_JOIN_OUT";lab="$repo/experiments/linux-steam";src="$repo/vendor/LinuxRunner";host="$LINUX_LAB_ARTIFACTS/host"
for mode in normal failure;do
    flags=(-DIDECK_HOST_JOIN_CREATE_EAGAIN=0);[[ $mode != failure ]] || flags=(-DIDECK_HOST_JOIN_CREATE_EAGAIN=1)
    xcrun clang -fsanitize=address,undefined -fno-omit-frame-pointer -DIDECK_JOIN_GUEST_CAPACITY=8 "${flags[@]}" -Wall -Wextra -Werror -I "$lab/app" \
        "$lab/app/JoinableGuests.c" "$lab/tests/joinable-guests-test.c" -o "$out/control-$mode"
done
python3 "$lab/tools/build-guest-lifetime.py" "$src" "$host" "$host/libish.a" "$out/guest-archive" --sanitize --join-guests
xcrun clang -fsanitize=address,undefined -DIDECK_LAB_GUEST_LIFETIME=1 -DGUEST_ARM64=1 -DENGINE_ASBESTOS=1 -DLOG_HANDLER_DPRINTF=1 -DISH_INTERNAL=1 \
    -I "$src" -I "$host" -I "$lab/app" -Wall -Wextra -Werror -Wno-unused-parameter \
    "$lab/app/LinuxLabRuntime.c" "$lab/app/LabDeviceFS.c" "$lab/app/LabBridge.c" "$lab/app/LaunchProtocol.c" "$lab/tools/joinable-guest-control.c" \
    "$out/guest-archive/libish.a" -L "$host" -lish_emu -lfakefs -lsqlite3 -o "$out/guest-control"
for mode in ordinary orphan;do
    args=("$lab/guest/session-lifecycle-probe.c");[[ $mode != ordinary ]] || args=("$lab/guest/probe.c" "$lab/guest/clone.S")
    xcrun clang --target=aarch64-linux-gnu --ld-path="$(command -v "$LD_LLD")" -nostdlib -static -ffreestanding -fno-builtin -fno-stack-protector -O2 -Wall -Wextra -Werror \
        "${args[@]}" -Wl,-e,_start -o "$out/$mode.elf"
done
python3 - "$out" <<'PY'
from pathlib import Path
import hashlib,json,subprocess,sys,time
out=Path(sys.argv[1]);tests=[]
for mode in ('tls','failure','ordinary','orphan'):
    if mode in ('tls','failure'):command=[str(out/('control-failure' if mode=='failure' else 'control-normal')),mode]
    else:
        root=out/(mode+'-root');root.mkdir(mode=0o700);(root/'probe').write_bytes((out/(mode+'.elf')).read_bytes());(root/'probe').chmod(0o700)
        command=[str(out/'guest-control'),str(root),mode]
    start=time.monotonic()
    with (out/(mode+'.log')).open('xb') as log:result=subprocess.run(command,stdin=subprocess.DEVNULL,stdout=log,stderr=log,timeout=20)
    row=dict(mode=mode,status=result.returncode,elapsed_seconds=round(time.monotonic()-start,3),log_sha256=hashlib.sha256((out/(mode+'.log')).read_bytes()).hexdigest());tests.append(row)
    assert not result.returncode,row
    if mode=='ordinary':
        lines=(out/'ordinary-root/probe-results.txt').read_text().splitlines();assert len(lines)==16 and all(line.endswith('=PASS') for line in lines)
evidence=dict(scope='HOST tracked child pthread join/TLS and actual ARM64 guest controls; NOT full Linux quiescence, iOS runtime, Wine/game/return or stability success',tests=tests,
    archive_sha256=hashlib.sha256((out/'guest-archive/libish.a').read_bytes()).hexdigest())
(out/'evidence.json').write_text(json.dumps(evidence,indent=2)+'\n');print(json.dumps(evidence))
PY
