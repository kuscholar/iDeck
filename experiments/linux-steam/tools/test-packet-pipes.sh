#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
set -euo pipefail
repo=$(cd "$(dirname "$0")/../../.." && pwd)
: "${LINUX_LAB_ARTIFACTS:?Set the private external artifact root}"
: "${LINUX_LAB_PACKET_TEST_DIR:?Set a NEW private test directory}"
: "${NINJA:=ninja}"
: "${LD_LLD:=ld.lld}"
NINJA=$(command -v "$NINJA")
LD_LLD=$(command -v "$LD_LLD")
case "$LINUX_LAB_PACKET_TEST_DIR" in /Volumes/easystore/*) ;; *) exit 2;; esac
[[ ! -e "$LINUX_LAB_PACKET_TEST_DIR" ]] || { echo 'Test output must be new' >&2; exit 2; }
mkdir -p "$LINUX_LAB_PACKET_TEST_DIR/root"
lab="$repo/experiments/linux-steam"
python3 "$lab/tools/build-pipe-observer.py" "$repo/vendor/LinuxRunner" \
    "$LINUX_LAB_ARTIFACTS/host" "$NINJA" "$LINUX_LAB_PACKET_TEST_DIR/runtime" --packet-pipes --sanitize
for name in packet-pipe-probe packet-pipe-integration; do
    xcrun clang --target=aarch64-linux-gnu --ld-path="$LD_LLD" -nostdlib -static \
        -ffreestanding -fno-builtin -fno-stack-protector -O2 -Wall -Wextra -Werror \
        "$lab/guest/$name.c" -Wl,-e,_start -o "$LINUX_LAB_PACKET_TEST_DIR/root/$name"
done
python3 - "$LINUX_LAB_ARTIFACTS" "$LINUX_LAB_PACKET_TEST_DIR" <<'PY'
from pathlib import Path
import json,subprocess,sys
base,out=map(lambda p:Path(p).resolve(),sys.argv[1:])
results=[]
for name,exe,program,expected in [
    ('base-blocker',base/'host/ish','/packet-pipe-probe',1),
    ('packet-basic',out/'runtime/ish-pipe-observer','/packet-pipe-probe',0),
    ('packet-contract',out/'runtime/ish-pipe-observer','/packet-pipe-integration',0)]:
    with (out/(name+'.log')).open('wb') as log:
        result=subprocess.run([str(exe),'-r',str(out/'root'),program],stdout=log,stderr=subprocess.STDOUT,timeout=25)
    assert result.returncode==expected,(name,result.returncode)
    text=(out/(name+'.log')).read_text()
    if name=='base-blocker':assert 'steam-packet-create-status=-22' in text
    if name=='packet-basic':assert 'packet-boundaries-short-read-cloexec-nonblock=PASS' in text
    if name=='packet-contract':assert sum(line.endswith('=PASS') for line in text.splitlines())==16 and '=FAIL' not in text
    results.append(dict(control=name,returncode=result.returncode,expected=expected))
(out/'results.json').write_text(json.dumps(dict(scope='host interpreter only; changed pipe unit ASan/UBSan',results=results,device=False),indent=2)+'\n')
print('Base blocker reproduced; packet basic and16 contract-result lines pass. No device/UI claim.')
PY
