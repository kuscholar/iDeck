#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
set -euo pipefail
repo=$(cd "$(dirname "$0")/../../.." && pwd)
: "${LINUX_LAB_ARTIFACTS:?Prepared host interpreter required}"
: "${LINUX_LAB_TRACE_ELF:?Own compiled ARM64 shared library required}"
: "${LINUX_LAB_TRACE_INSTALL_OUT:?New private external output required}"
case "$LINUX_LAB_TRACE_INSTALL_OUT" in /Volumes/easystore/*) ;; *) exit 2;; esac
[[ ! -e "$LINUX_LAB_TRACE_INSTALL_OUT" ]] || exit 2
mkdir -m 700 "$LINUX_LAB_TRACE_INSTALL_OUT"
lab="$repo/experiments/linux-steam";src="$repo/vendor/LinuxRunner";host="$LINUX_LAB_ARTIFACTS/host";out="$LINUX_LAB_TRACE_INSTALL_OUT"
[[ $(git -C "$src" rev-parse HEAD) == d1419782da2e299fe22f1ddb85c70ae3d1e276b1 && -z $(git -C "$src" status --porcelain --untracked-files=no) ]] || exit 2
xcrun clang -fsanitize=address,undefined -DGUEST_ARM64=1 -DENGINE_ASBESTOS=1 -DLOG_HANDLER_DPRINTF=1 -DISH_INTERNAL=1 \
    -I "$src" -I "$host" -I "$lab/app" -Wall -Wextra -Werror -Wno-unused-parameter \
    "$lab/app/X11TraceInstall.c" "$lab/app/LabDeviceFS.c" "$lab/tools/x11-trace-install-control.c" \
    -L "$host" -lish -lish_emu -lfakefs -lsqlite3 -o "$out/control"
python3 - "$out" "$LINUX_LAB_TRACE_ELF" <<'PY'
from pathlib import Path
import hashlib,json,subprocess,sys
out,elf=map(Path,sys.argv[1:]);tests=[]
for mode in ('positive','conflict','symlink','target-symlink','stale','published-stage','noninit','invalid'):
    with (out/(mode+'.log')).open('xb') as log:result=subprocess.run([str(out/'control'),str(out/(mode+'-root')),str(elf),mode],stdout=log,stderr=log,timeout=20)
    lines=[s for s in (out/(mode+'.log')).read_text().splitlines() if s.endswith('=PASS') or s.endswith('=FAIL')]
    tests.append(dict(mode=mode,status=result.returncode,checks=lines,log_sha256=hashlib.sha256((out/(mode+'.log')).read_bytes()).hexdigest()))
    assert result.returncode==0 and lines and all(s.endswith('=PASS') for s in lines),tests[-1]
evidence=dict(scope='HOST actual pinned fakefs/VFS and native installer ASan/UBSan; not actual Steam load, iPad or game execution',tests=tests,elf_sha256=hashlib.sha256(elf.read_bytes()).hexdigest())
(out/'evidence.json').write_text(json.dumps(evidence,indent=2)+'\n');print(json.dumps(evidence))
PY
