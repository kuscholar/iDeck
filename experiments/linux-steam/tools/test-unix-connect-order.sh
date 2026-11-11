#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
set -euo pipefail
repo=$(cd "$(dirname "$0")/../../.." && pwd)
: "${LINUX_LAB_ARTIFACTS:?Prepared host interpreter/embed control}"
: "${LINUX_LAB_CONNECT_OUT:?New external private output}"
: "${LD_LLD:?Explicit Linux linker}"
case "$LINUX_LAB_CONNECT_OUT" in /Volumes/easystore/*) ;; *) exit 2;; esac
[[ ! -e "$LINUX_LAB_CONNECT_OUT" ]] || exit 2
out="$LINUX_LAB_CONNECT_OUT";mkdir -p -m 700 "$out"
for mode in early late;do
    flag=0;[[ $mode != early ]] || flag=1
    mkdir "$out/$mode-root"
    xcrun clang --target=aarch64-linux-gnu --ld-path="$LD_LLD" -nostdlib -static -ffreestanding -fno-builtin -fno-stack-protector -O2 -Wall -Wextra -Werror \
        -DSERVER_ACCEPT_EARLY="$flag" "$repo/experiments/linux-steam/guest/unix-connect-order-probe.c" -Wl,-e,_start -o "$out/$mode-root/probe"
done
python3 - "$LINUX_LAB_ARTIFACTS" "$out" <<'PY'
from pathlib import Path
import hashlib,json,subprocess,sys,time
base,out=map(Path,sys.argv[1:]);rows=[]
for mode in ('early','late'):
    began=time.monotonic();intentional=False
    with (out/(mode+'.log')).open('xb') as log:
        child=subprocess.Popen([str(base/'host-embed'),str(out/(mode+'-root'))],stdout=log,stderr=log)
        try:status=child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            intentional=True;child.terminate();status=child.wait(timeout=5)
    report=(out/(mode+'-root/connect-order.txt')).read_text()
    rows.append(dict(mode=mode,status=status,intentionally_terminated_after_timeout=intentional,
        elapsed_seconds=round(time.monotonic()-began,3),guest_rows=report.splitlines(),elf_sha256=hashlib.sha256((out/(mode+'-root/probe')).read_bytes()).hexdigest()))
    if mode=='early':assert not status and 'complete=PASS' in report,(status,report)
    else:assert intentional and report=='listen-ready=PASS\nbefore-connect\n',(status,report)
record=dict(scope='HOST actual minimal ARM64 connect ordering discriminator; NOT sole cause of Xvfb exit, Steam/device/game proof or a socket fix',tests=rows)
(out/'evidence.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
PY
