#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Real ARM64 X11 protocol/paint controls in a caller-prepared NEW private root.

Refuses recognizable account data and occupied display; no Steam launch or
credentials. Caller must verify stopped root and no overlapping experiments.
No arbitrary app/UI command interface is exposed. Private outputs only.
"""
import argparse
import fcntl
import hashlib
import json
from pathlib import Path
import subprocess
import time

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('ish', type=Path)
p.add_argument('root', type=Path)
p.add_argument('elf', type=Path)
p.add_argument('output', type=Path)
p.add_argument('--preload',type=Path,help='Our own bounded ARM64 numeric Xlib diagnostic library, test process only')
a = p.parse_args()
ish, root, elf, out = (getattr(a, name).resolve() for name in ('ish', 'root', 'elf', 'output'))
assert all(str(path).startswith('/Volumes/easystore/') for path in (root, elf, out))
assert not out.exists() and (root/'data').is_dir() and (root/'meta.db').is_file()
for name in ('Steam/config/loginusers.vdf', 'Steam/userdata', 'root/.steam/config/loginusers.vdf'):
    assert not (root/'data'/name).exists(), 'Recognizable account data; preserved'
assert not (root/'data/tmp/.X97-lock').exists()
payload = elf.read_bytes()
assert 0 < len(payload) <= 262144 and payload[:4] == b'\x7fELF' and payload[18:20] == b'\xb7\0'
out.mkdir(mode=0o700)
lab = Path(__file__).resolve().parents[1]
with (root/'.ideck-x11-window.lock').open('x') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    # Install via the real guest VFS so fakefs metadata stays coherent; never
    # write meta.db or fabricate metadata with host SQL/file operations.
    with (out/'install.log').open('xb') as log:
        install = subprocess.run([str(ish), '-f', str(root), '/bin/sh', '-c',
                                  'set -eu; umask 077; test ! -e /x11-window-probe; cat > /x11-window-probe; chmod 700 /x11-window-probe'],
                                 input=payload, stdout=log, stderr=log, timeout=30)
    assert not install.returncode, 'Guest VFS install failed; inspect private log'
    preload_hash=None
    script=(lab/'guest/x11-window-control.sh').read_text()
    if a.preload:
        preload=a.preload.resolve();assert str(preload).startswith('/Volumes/easystore/')
        library=preload.read_bytes();assert 0<len(library)<=262144 and library[:4]==b'\x7fELF' and library[16:20]==b'\x03\0\xb7\0'
        with (out/'preload-install.log').open('xb') as log:
            installation=subprocess.run([str(ish),'-f',str(root),'/bin/sh','-c',
                'set -eu; umask 077; test ! -e /ideck-x11-window-trace.so; cat > /ideck-x11-window-trace.so; chmod 600 /ideck-x11-window-trace.so'],input=library,stdout=log,stderr=log,timeout=30)
        assert not installation.returncode
        target='timeout 60 /x11-window-probe';assert script.count(target)==1
        script=script.replace(target,'LD_PRELOAD=/ideck-x11-window-trace.so '+target)
        preload_hash=hashlib.sha256(library).hexdigest()
    command = [str(ish), '-f', str(root), '/bin/sh', '-c', script]
    start = time.monotonic()
    with (out/'runtime.log').open('xb') as log:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=log)
        # Timeout is observation failure, not proof of guest/X11 crash. Keep
        # the exact live PID for follow-up; do not auto-kill/restart on timeout.
        (out/'observer.json').write_text(json.dumps(dict(pid=process.pid, command=command, scope='Own isolated host X11 control'))+'\n')
        try:
            status = process.wait(timeout=100)
        except subprocess.TimeoutExpired:
            (out/'result.json').write_text(json.dumps(dict(status='observer-timeout-live-state-unproven', pid=process.pid))+'\n')
            raise
    reports = {}
    for role in ('parent', 'child'):
        report = root/'data'/('x11-window-'+role+'.txt')
        if not report.exists():
            reports[role] = dict(missing=True)
            continue
        data = report.read_bytes()
        assert len(data) <= 4096
        (out/report.name).write_bytes(data)
        reports[role] = dict(line.split('=', 1) for line in data.decode().splitlines() if '=' in line)
    result = dict(scope='HOST real ARM64 Linux/Xvfb/X11 own-window lifetime and pixel controls; not Steam/CEF, iOS/Metal or stability success',
                  status=status, elapsed_seconds=round(time.monotonic()-start, 3), reports=reports,
                  elf_sha256=hashlib.sha256(payload).hexdigest(),preload_sha256=preload_hash,runtime_log_sha256=hashlib.sha256((out/'runtime.log').read_bytes()).hexdigest())
    (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    for report in reports.values():
        assert report.get('status') == '0' and report['live_attributes'] == '32' and report['expected_bad_windows'] == '16' and report['images'] == '16' and report['pixel_comparisons'] == '32768', result
    assert not status, result
    print(json.dumps(result))
