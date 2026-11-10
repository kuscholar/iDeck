#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
set -euo pipefail
repo=$(cd "$(dirname "$0")/../../.." && pwd)
: "${LINUX_LAB_ARTIFACTS:?Prepared private external host build required}"
: "${LINUX_LAB_PROFILE_OUT:?New private external output required}"
: "${LD_LLD:=ld.lld}"
case "$LINUX_LAB_PROFILE_OUT" in /Volumes/easystore/*) ;; *) exit 2;; esac
[[ ! -e "$LINUX_LAB_PROFILE_OUT" ]] || exit 2
out="$LINUX_LAB_PROFILE_OUT";mkdir -m 700 "$out";lab="$repo/experiments/linux-steam"
src="$repo/vendor/LinuxRunner";host="$LINUX_LAB_ARTIFACTS/host"
mkdir "$out/source";cp -R "$lab/app" "$lab/guest" "$out/source/"
cp "$lab/tools/joined-profile-control.c" "$out/source/"
python3 "$lab/tools/build-guest-lifetime.py" "$src" "$host" "$host/libish.a" "$out/guest-archive" --sanitize --join-guests
python3 "$lab/tools/build-native-workers.py" "$src" "$host" "$out/guest-archive/libish.a" "$out/profile-archive" --sanitize --join-workers --stop-profile
xcrun clang -fsanitize=address,undefined -DIDECK_LAB_GUEST_LIFETIME=1 -DIDECK_LAB_NATIVE_WORKERS=1 -DGUEST_ARM64=1 -DENGINE_ASBESTOS=1 -DLOG_HANDLER_DPRINTF=1 -DISH_INTERNAL=1 \
    -I "$src" -I "$host" -I "$out/source/app" -Wall -Wextra -Werror -Wno-unused-parameter \
    "$out/source/app/LinuxLabRuntime.c" "$out/source/app/LabDeviceFS.c" "$out/source/app/LabBridge.c" "$out/source/app/LaunchProtocol.c" \
    "$out/source/joined-profile-control.c" "$out/profile-archive/libish.a" -L "$host" -lish_emu -lfakefs -lsqlite3 -o "$out/control"
for mode in enabled disabled;do
    args=("$out/source/guest/profile-stop-probe.c")
    [[ $mode != disabled ]] || args=("$out/source/guest/probe.c" "$out/source/guest/clone.S")
    xcrun clang --target=aarch64-linux-gnu --ld-path="$(command -v "$LD_LLD")" -nostdlib -static -ffreestanding -fno-builtin -fno-stack-protector -O2 -Wall -Wextra -Werror \
        "${args[@]}" -Wl,-e,_start -o "$out/$mode.elf"
done
python3 - "$out" <<'PY'
from pathlib import Path
import hashlib,json,os,re,subprocess,sys,time
out=Path(sys.argv[1]);rows=[];environment=dict(os.environ)
environment.pop('ISH_GUEST_PROFILE',None);environment.pop('ISH_GUEST_PROFILE_HZ',None)
for mode in ('enabled','disabled','producer-leak'):
    root=out/(mode+'-root');root.mkdir(mode=0o700);binary=out/('disabled.elf' if mode=='disabled' else 'enabled.elf')
    (root/'probe').write_bytes(binary.read_bytes());(root/'probe').chmod(0o700)
    profile=out/(mode+'-private-profile.txt');start=time.monotonic()
    with (out/(mode+'.log')).open('xb') as log:result=subprocess.run([str(out/'control'),str(root),str(profile),mode],stdin=subprocess.DEVNULL,stdout=log,stderr=log,env=environment,timeout=20)
    row=dict(mode=mode,status=result.returncode,elapsed_seconds=round(time.monotonic()-start,3),log_sha256=hashlib.sha256((out/(mode+'.log')).read_bytes()).hexdigest())
    if not result.returncode and mode!='disabled':
        data=profile.read_bytes();first=data.splitlines()[0].decode();m=re.fullmatch(r'PROFILE interval_us=1000 samples=(\d+) dropped=(\d+)',first)
        assert m and int(m[1])>0,'No actual guest profile samples, not a positive sampling result'
        row.update(samples=int(m[1]),dropped=int(m[2]),private_profile_sha256=hashlib.sha256(data).hexdigest(),private_profile_bytes=len(data))
    if not result.returncode and mode=='disabled':
        lines=(root/'probe-results.txt').read_text().splitlines();assert len(lines)==16 and all(s.endswith('=PASS') for s in lines)
    rows.append(row)
    if result.returncode:break
record=dict(scope='HOST actual pinned native profiler, real ARM64 workload, cooperative stop/full pthread join/buffer release; NOT full Linux teardown, Wine/game or iPad success',tests=rows,
    sources={str(p.relative_to(out/'source')):hashlib.sha256(p.read_bytes()).hexdigest() for p in (out/'source').rglob('*') if p.is_file()},
    archive_sha256=hashlib.sha256((out/'profile-archive/libish.a').read_bytes()).hexdigest())
(out/'evidence.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
assert len(rows)==3 and all(not x['status'] for x in rows),rows
PY
