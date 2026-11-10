#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
set -euo pipefail
repo=$(cd "$(dirname "$0")/../../.." && pwd)
: "${LINUX_LAB_ARTIFACTS:?Prepared external host build required}"
: "${LINUX_LAB_WORKER_JOINS_OUT:?New external output required}"
: "${LD_LLD:=ld.lld}"
case "$LINUX_LAB_WORKER_JOINS_OUT" in /Volumes/easystore/*) ;; *) exit 2;; esac
[[ ! -e "$LINUX_LAB_WORKER_JOINS_OUT" ]] || exit 2
out="$LINUX_LAB_WORKER_JOINS_OUT";mkdir -m 700 "$out"
lab="$repo/experiments/linux-steam";src="$repo/vendor/LinuxRunner";host="$LINUX_LAB_ARTIFACTS/host"
mkdir -p "$out/source/app" "$out/source/tests" "$out/source/tools"
cp "$lab/app/NativeWorkers.c" "$lab/app/NativeWorkers.h" "$lab/app/NativeWorkerJoins.c" "$lab/app/NativeWorkerJoins.h" "$out/source/app/"
cp "$lab/tests/native-worker-joins-test.c" "$out/source/tests/"
cp "$lab/tools/native-worker-joins-control.c" "$out/source/tools/"
for mode in normal failure join-failure;do
    flags=(-DIDECK_HOST_WORKER_JOIN_CREATE_EAGAIN=0 -DIDECK_HOST_WORKER_JOIN_FAILURE=0)
    [[ $mode != failure ]] || flags=(-DIDECK_HOST_WORKER_JOIN_CREATE_EAGAIN=1 -DIDECK_HOST_WORKER_JOIN_FAILURE=0)
    [[ $mode != join-failure ]] || flags=(-DIDECK_HOST_WORKER_JOIN_CREATE_EAGAIN=0 -DIDECK_HOST_WORKER_JOIN_FAILURE=1)
    xcrun clang -fsanitize=address,undefined -fno-omit-frame-pointer -DIDECK_LAB_JOIN_NATIVE_WORKERS=1 -DIDECK_WORKER_JOIN_CAPACITY=8 "${flags[@]}" \
        -Wall -Wextra -Werror -I "$out/source/app" "$out/source/app/NativeWorkers.c" "$out/source/app/NativeWorkerJoins.c" \
        "$out/source/tests/native-worker-joins-test.c" -o "$out/unit-$mode"
done
python3 "$lab/tools/build-guest-lifetime.py" "$src" "$host" "$host/libish.a" "$out/guest-archive" --sanitize --join-guests
python3 "$lab/tools/build-native-workers.py" "$src" "$host" "$out/guest-archive/libish.a" "$out/worker-archive" --sanitize --join-workers
xcrun clang -fsanitize=address,undefined -DIDECK_LAB_GUEST_LIFETIME=1 -DIDECK_LAB_NATIVE_WORKERS=1 -DGUEST_ARM64=1 -DENGINE_ASBESTOS=1 -DLOG_HANDLER_DPRINTF=1 -DISH_INTERNAL=1 \
    -I "$src" -I "$host" -I "$lab/app" -Wall -Wextra -Werror -Wno-unused-parameter \
    "$lab/app/LinuxLabRuntime.c" "$lab/app/LabDeviceFS.c" "$lab/app/LabBridge.c" "$lab/app/LaunchProtocol.c" "$out/source/tools/native-worker-joins-control.c" \
    "$out/worker-archive/libish.a" -L "$host" -lish_emu -lfakefs -lsqlite3 -o "$out/provider-control"
for mode in ordinary forward;do
    args=("$lab/guest/probe.c" "$lab/guest/clone.S");[[ $mode != forward ]] || args=("$lab/guest/worker-forward-probe.c")
    xcrun clang --target=aarch64-linux-gnu --ld-path="$(command -v "$LD_LLD")" -nostdlib -static -ffreestanding -fno-builtin -fno-stack-protector -O2 -Wall -Wextra -Werror \
        "${args[@]}" -Wl,-e,_start -o "$out/$mode.elf"
done
python3 - "$out" <<'PY'
from pathlib import Path
import hashlib,json,os,subprocess,sys,time
out=Path(sys.argv[1]);rows=[];environment=dict(os.environ);environment.pop('ISH_GUEST_PROFILE',None)
for mode in ('managed','external','reuse','failure','join-failure','timer','timer-tls','tty','ordinary','forward'):
    command=[str(out/('unit-'+(mode if 'failure' in mode else 'normal'))),mode] if mode in ('managed','external','reuse','failure','join-failure') else [str(out/'provider-control'),mode]
    if mode in ('ordinary','forward'):
        root=out/(mode+'-root');root.mkdir(mode=0o700);body=(out/(mode+'.elf')).read_bytes();(root/'probe').write_bytes(body);(root/'probe').chmod(0o700)
        if mode=='forward':(root/'worker-control').write_bytes(body);(root/'worker-control').chmod(0o700)
        command.append(str(root))
    start=time.monotonic()
    with (out/(mode+'.log')).open('xb') as log:result=subprocess.run(command,stdin=subprocess.DEVNULL,stdout=log,stderr=log,env=environment,timeout=45)
    row=dict(mode=mode,status=result.returncode,elapsed_seconds=round(time.monotonic()-start,3),log_sha256=hashlib.sha256((out/(mode+'.log')).read_bytes()).hexdigest());rows.append(row)
    if result.returncode:break
    if mode=='ordinary':
        lines=(root/'probe-results.txt').read_text().splitlines();assert len(lines)==16 and all(line.endswith('=PASS') for line in lines)
record=dict(scope='HOST actual tracked auxiliary pthread joins/TLS/reuse and pinned timer/TTY/forwarders/ARM64 controls; NOT complete Linux teardown, Wine game, iPad or stability proof',tests=rows,
    sources={str(p.relative_to(out/'source')):hashlib.sha256(p.read_bytes()).hexdigest() for p in (out/'source').rglob('*') if p.is_file()},
    archive_sha256=hashlib.sha256((out/'worker-archive/libish.a').read_bytes()).hexdigest())
(out/'evidence.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
assert len(rows)==10 and all(not x['status'] for x in rows),rows
PY
