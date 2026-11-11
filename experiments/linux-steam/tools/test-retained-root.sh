#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
set -euo pipefail
repo=$(cd "$(dirname "$0")/../../.." && pwd)
: "${LINUX_LAB_ARTIFACTS:?Prepared private host interpreter}"
: "${LINUX_LAB_RETAINED_OUT:?New external output}"
: "${LD_LLD:?Explicit Linux linker}"
case "$LINUX_LAB_RETAINED_OUT" in /Volumes/easystore/*) ;; *) exit 2;; esac
[[ ! -e "$LINUX_LAB_RETAINED_OUT" ]] || exit 2
out="$LINUX_LAB_RETAINED_OUT";mkdir -p -m 700 "$out"
lab="$repo/experiments/linux-steam";src="$repo/vendor/LinuxRunner";host="$LINUX_LAB_ARTIFACTS/host"
for mode in default enabled;do
    flags=(-DIDECK_LAB_GUEST_WAVES=0)
    [[ $mode != enabled ]] || flags=(-DIDECK_LAB_GUEST_WAVES=1)
    xcrun clang -fsanitize=address,undefined -DIDECK_JOIN_GUEST_CAPACITY=2 "${flags[@]}" -Wall -Wextra -Werror -I "$lab/app" \
        "$lab/app/JoinableGuests.c" "$lab/tests/guest-waves-test.c" -o "$out/gates-$mode"
done
python3 "$lab/tools/build-guest-lifetime.py" "$src" "$host" "$host/libish.a" "$out/guest" --sanitize --join-guests --guest-waves
xcrun clang -fsanitize=address,undefined -DGUEST_ARM64=1 -DENGINE_ASBESTOS=1 -DLOG_HANDLER_DPRINTF=1 -DISH_INTERNAL=1 -DIDECK_LAB_GUEST_LIFETIME=1 \
    -I "$src" -I "$host" -I "$lab/app" -Wall -Wextra -Werror -Wno-unused-parameter \
    "$lab/app/LinuxLabRuntime.c" "$lab/app/LabDeviceFS.c" "$lab/app/LabBridge.c" "$lab/app/LaunchProtocol.c" "$lab/tools/retained-root-control.c" \
    "$out/guest/libish.a" -L "$host" -lish_emu -lfakefs -lsqlite3 -o "$out/control"
mkdir "$out/root"
xcrun clang --target=aarch64-linux-gnu --ld-path="$LD_LLD" -nostdlib -static -ffreestanding -fno-builtin -fno-stack-protector -O2 -Wall -Wextra -Werror \
    "$lab/guest/probe.c" "$lab/guest/clone.S" -Wl,-e,_start -o "$out/root/probe"
python3 - "$out" <<'PY'
from pathlib import Path
import hashlib,json,subprocess,sys,time
out=Path(sys.argv[1]);start=time.monotonic()
for mode in ('default','enabled'):
    with (out/f'gates-{mode}.log').open('xb') as log:
        gate=subprocess.run([str(out/f'gates-{mode}')],stdout=log,stderr=log,timeout=10)
    assert gate.returncode==0,(mode,gate.returncode)
with (out/'control.log').open('xb') as log:
    r=subprocess.run([str(out/'control'),str(out/'root')],stdout=log,stderr=log,timeout=30)
assert r.returncode==0,r.returncode
text=(out/'control.log').read_text();rows=[x for x in text.splitlines() if x.startswith('RETAINED_ROOT ')]
assert len(rows)==3,rows
reports={}
for wave in range(1,5):
    data=(out/f'root/wave-{wave}-results.txt').read_bytes();lines=data.decode().splitlines()
    assert len(lines)==16 and all(x.endswith('=PASS') for x in lines)
    reports[str(wave)]=dict(checks=len(lines),sha256=hashlib.sha256(data).hexdigest())
(out/'evidence.json').write_text(json.dumps(dict(scope='HOST retained root FOUR actual ARM64 ELF waves; NOT Steam/Wine/App/iPad or safe handoff',
 status=r.returncode,elapsed_seconds=round(time.monotonic()-start,3),gate_modes=['default','enabled'],rows=rows,per_wave_reports=reports,
 control_sha256=hashlib.sha256((out/'control').read_bytes()).hexdigest(),log_sha256=hashlib.sha256(text.encode()).hexdigest()),indent=2)+'\n')
print('HOST retained root/init/mm + four real ARM64 ELF waves PASS, original one-shot API unchanged')
PY
