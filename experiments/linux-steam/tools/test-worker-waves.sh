#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
set -euo pipefail
repo=$(cd "$(dirname "$0")/../../.." && pwd)
: "${LINUX_LAB_WORKER_WAVES_OUT:?New private external output}"
case "$LINUX_LAB_WORKER_WAVES_OUT" in /Volumes/easystore/*) ;; *) exit 2;; esac
[[ ! -e "$LINUX_LAB_WORKER_WAVES_OUT" ]] || exit 2
mkdir -p -m 700 "$LINUX_LAB_WORKER_WAVES_OUT"
python3 - "$repo" "$LINUX_LAB_WORKER_WAVES_OUT" <<'PY'
from pathlib import Path
import hashlib,json,subprocess,sys
repo,out=map(Path,sys.argv[1:]);lab=repo/'experiments/linux-steam';rows=[]
for mode,flags in [('default',[]),('enabled',['-DIDECK_LAB_WORKER_WAVES=1'])]:
    binary=out/mode
    subprocess.run(['xcrun','clang','-fsanitize=address,undefined','-Wall','-Wextra','-Werror','-I',str(lab/'app'),
        *flags,str(lab/'app/NativeWorkerJoins.c'),str(lab/'tests/worker-waves-test.c'),'-o',str(binary)],check=True)
    result=subprocess.run([str(binary)],capture_output=True,text=True,timeout=20)
    text=result.stdout+result.stderr;(out/(mode+'.log')).write_text(text)
    assert result.returncode==0,text
    rows.append(dict(mode=mode,status=result.returncode,binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),log_sha256=hashlib.sha256(text.encode()).hexdigest()))
(out/'evidence.json').write_text(json.dumps(dict(scope='HOST registry worker/reaper reopen, not full provider or runtime restart',tests=rows),indent=2)+'\n')
print('Default refusal and20 actual worker/reaper waves PASS; not Steam or iPad proof')
PY
