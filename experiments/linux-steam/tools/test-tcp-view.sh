#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
set -euo pipefail
umask 077
repo=$(cd "$(dirname "$0")/../../.." && pwd)
: "${LINUX_LAB_ARTIFACTS:?Set the verified private external artifact root}"
: "${LINUX_LAB_TCP_TEST_DIR:?Set a NEW private test directory}"
: "${NINJA:=ninja}"
: "${LD_LLD:=ld.lld}"
NINJA=$(command -v "$NINJA")
LD_LLD=$(command -v "$LD_LLD")
case "$LINUX_LAB_TCP_TEST_DIR" in /Volumes/easystore/*) ;; *) exit 2;; esac
[[ ! -e "$LINUX_LAB_TCP_TEST_DIR" ]] || { echo 'Test output must be new' >&2; exit 2; }
mkdir -p "$LINUX_LAB_TCP_TEST_DIR/root"
lab="$repo/experiments/linux-steam"
python3 "$lab/tools/build-pipe-observer.py" "$repo/vendor/LinuxRunner" \
    "$LINUX_LAB_ARTIFACTS/host" "$NINJA" "$LINUX_LAB_TCP_TEST_DIR/packet" --packet-pipes --sanitize --archive-only
python3 "$lab/tools/build-tcp-view.py" "$repo/vendor/LinuxRunner" \
    "$LINUX_LAB_ARTIFACTS/host" "$LINUX_LAB_TCP_TEST_DIR/packet/libish.a" "$NINJA" "$LINUX_LAB_TCP_TEST_DIR/runtime" --sanitize
for name in tcp-view-probe tcp-lsof-probe; do
    lsof_control=0
    [[ "$name" != tcp-lsof-probe ]] || lsof_control=1
    xcrun clang --target=aarch64-linux-gnu --ld-path="$LD_LLD" -nostdlib -static \
        -ffreestanding -fno-builtin -fno-stack-protector -O2 -Wall -Wextra -Werror \
        "-DIDECK_TCP_LSOF=$lsof_control" "$lab/guest/tcp-view-probe.c" -Wl,-e,_start -o "$LINUX_LAB_TCP_TEST_DIR/root/$name"
done
python3 - "$LINUX_LAB_ARTIFACTS" "$LINUX_LAB_TCP_TEST_DIR" <<'PY'
from pathlib import Path
import json, os, subprocess, sys
base, out = [Path(x).resolve() for x in sys.argv[1:]]
rows = subprocess.check_output(['ps', '-axo', 'comm='], text=True).splitlines()
assert not any(Path(x.strip()).name in {'ish', 'ish-pipe-observer', 'ish-tcp-view'} for x in rows), 'stop other Lab runtimes first'
results = []
for name, exe, expected in [('base-negative', base/'host/ish', 1), ('tcp-positive', out/'runtime/ish-tcp-view', 0)]:
    with (out/(name+'.log')).open('xb') as log:
        r = subprocess.run([str(exe), '-r', str(out/'root'), '/tcp-view-probe'], stdout=log, stderr=subprocess.STDOUT, timeout=30)
    text = (out/(name+'.log')).read_text(errors='replace')
    assert r.returncode == expected, (name, r.returncode)
    if expected == 0: assert text.count('=PASS') == 17 and '=FAIL' not in text
    results.append(dict(name=name, status=r.returncode, expected=expected, passed=text.count('=PASS'), failed=text.count('=FAIL')))
if os.environ.get('LINUX_LAB_DISTRO_ROOT'):
    root = Path(os.environ['LINUX_LAB_DISTRO_ROOT']).resolve()
    assert (root/'meta.db').is_file() and (root/'data/usr/bin/lsof').exists()
    for f in ['Steam/config/loginusers.vdf', 'root/.steam/config/loginusers.vdf']:
        assert not (root/'data'/f).exists(), 'use only a stopped unauthenticated root'
    env = os.environ.copy()
    env['ISH_BIND_MOUNTS'] = '/control=' + str(out/'root') + ':ro'
    with (out/'official-lsof.log').open('xb') as log:
        r = subprocess.run([str(out/'runtime/ish-tcp-view'), '-f', str(root), '/bin/sh', '-c', 'exec /control/tcp-lsof-probe'], env=env, stdout=log, stderr=subprocess.STDOUT, timeout=40)
    text = (out/'official-lsof.log').read_text(errors='replace')
    assert r.returncode == 0 and text.count('=PASS') == 19 and 'unsupported format' not in text
    results.append(dict(name='official-lsof', status=0, passed=19, scope='real guest PID, IPv4 and IPv6'))
(out/'results.json').write_text(json.dumps(dict(scope='host ARM64 interpreter; changed units sanitized, not whole-runtime coverage', results=results, device=False), indent=2)+'\n')
print('Host TCP controls pass; no device or Steam UI claim.')
PY
