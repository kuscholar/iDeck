#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
set -euo pipefail
repo=$(cd "$(dirname "$0")/../../.." && pwd)
: "${LINUX_LAB_ARTIFACTS:?Prepared host interpreter required}"
: "${LINUX_LAB_FILES_BRIDGE_OUT:?NEW private external output required}"
: "${LD_LLD:=ld.lld}"
case "$LINUX_LAB_FILES_BRIDGE_OUT" in /Volumes/easystore/*) ;; *) exit 2;; esac
[[ ! -e "$LINUX_LAB_FILES_BRIDGE_OUT" ]] || exit 2
mkdir -m 700 "$LINUX_LAB_FILES_BRIDGE_OUT"
lab="$repo/experiments/linux-steam";src="$repo/vendor/LinuxRunner";host="$LINUX_LAB_ARTIFACTS/host";out="$LINUX_LAB_FILES_BRIDGE_OUT"
[[ $(git -C "$src" rev-parse HEAD) == d1419782da2e299fe22f1ddb85c70ae3d1e276b1 ]] || exit 2
[[ -z $(git -C "$src" status --porcelain --untracked-files=no) ]] || exit 2
xcrun clang -fsanitize=address,undefined -DIDECK_LAB_GAME_FILE_POLICY=1 -DGUEST_ARM64=1 -DENGINE_ASBESTOS=1 -DLOG_HANDLER_DPRINTF=1 -DISH_INTERNAL=1 \
    -I "$src" -I "$host" -I "$lab/app" -Wall -Wextra -Werror -Wno-unused-parameter \
    "$lab/app/LinuxLabRuntime.c" "$lab/app/LabDeviceFS.c" "$lab/app/LabBridge.c" "$lab/app/LaunchProtocol.c" "$lab/app/GameFiles.c" "$lab/app/GameFilePolicy.c" "$lab/app/NativeKernelLog.c" "$lab/tools/files-bridge-control.c" \
    "$host/libish.a" -L "$host" -lish_emu -lfakefs -lsqlite3 -o "$out/control"
for shared in 0 1;do
    xcrun clang --target=aarch64-linux-gnu --ld-path="$(command -v "$LD_LLD")" -nostdlib -static -ffreestanding -fno-builtin -fno-stack-protector -O2 -Wall -Wextra -Werror \
        -DPROBE_SHARED="$shared" "$lab/guest/files-bridge-probe.c" -Wl,-e,_start -o "$out/probe-$shared.elf"
done
xcrun clang --target=aarch64-linux-gnu --ld-path="$(command -v "$LD_LLD")" -nostdlib -static -ffreestanding -fno-builtin -fno-stack-protector -O2 -Wall -Wextra -Werror \
    "$lab/guest/compatibility.c" "$lab/guest/compat-start.S" -Wl,-e,_start -o "$out/ideck-madeira"
python3 - "$out" <<'PY'
from pathlib import Path
import hashlib,json,subprocess,sys
out=Path(sys.argv[1]);tests=[]
for mode in ('default','shared','symlink'):
    root=out/mode;root.mkdir(mode=0o700);common=root/('mnt/ideck/SteamLibrary/steamapps/common' if mode=='shared' else 'Steam/steamapps/common');game=common/'Control Game';game.mkdir(parents=True)
    payload=bytearray(128);payload[:2]=b'MZ';payload[60]=64;payload[64:68]=b'PE\0\0';payload[68:70]=(0x8664).to_bytes(2,'little');payload[70]=1;payload[84]=2;payload[86]=2;payload[88:90]=(0x20b).to_bytes(2,'little')
    if mode=='symlink':
        outside=out/'outside-own-fixture.exe';outside.write_bytes(payload);(game/'control.exe').symlink_to(outside)
    else:(game/'control.exe').write_bytes(payload)
    (root/'probe').write_bytes((out/('probe-1.elf' if mode=='shared' else 'probe-0.elf')).read_bytes());(root/'probe').chmod(0o700)
    (root/'ideck-madeira').write_bytes((out/'ideck-madeira').read_bytes());(root/'ideck-madeira').chmod(0o700)
    with (out/(mode+'.log')).open('xb') as f:r=subprocess.run([str(out/'control'),str(root),mode],stdout=f,stderr=f,timeout=30)
    tests.append(dict(mode=mode,status=r.returncode,log_sha256=hashlib.sha256((out/(mode+'.log')).read_bytes()).hexdigest()));assert r.returncode==0,tests[-1]
    receipts=list((root/'NativeDiagnostics').glob('health-*.json'));assert len(receipts)==1
    receipt=json.loads(receipts[0].read_text());observed=receipt['file_policy'];assert observed['query_status']==0 and observed['submitted']==1 and observed['completed_sequence']==1 and observed['appid']==480 and observed['diagnostic_only'] and not observed['game_launched']
    assert observed['status']<0 if mode=='symlink' else observed['status']==0
    assert observed['machine']==(0 if mode=='symlink' else 0x8664)
    tests[-1]['health_sha256']=hashlib.sha256(receipts[0].read_bytes()).hexdigest()
evidence=dict(scope='HOST real ARM64 exec/helper/IPC into native file policy; synthetic AppID480/PE identity only. Wrapper125 is NOT a game/Steam Play/license/device success. Native wrapper/policy units sanitized, dependency not fully.',tests=tests,
    helper_sha256=hashlib.sha256((out/'ideck-madeira').read_bytes()).hexdigest())
(out/'evidence.json').write_text(json.dumps(evidence,indent=2)+'\n');print(json.dumps(evidence))
PY
