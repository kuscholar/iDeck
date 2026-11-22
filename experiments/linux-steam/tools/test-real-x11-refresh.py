#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Bounded host control on an owned clone of a stopped, unauthenticated fakefs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import subprocess
import time


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


password_name = 'ideck-static-refresh-password'


def assert_clean(root):
    for name in ('Steam/config/loginusers.vdf', 'Steam/userdata', 'root/.steam/config/loginusers.vdf',
                 'tmp/.X99-lock', 'tmp/.X11-unix/X99', f'tmp/{password_name}'):
        if (root/'data'/name).exists():
            raise SystemExit('Stopped, unauthenticated control root required')


p = argparse.ArgumentParser(description=__doc__)
for name in ('ish', 'stopped_root', 'output'):
    p.add_argument(name, type=Path)
a = p.parse_args()
ish, source, out = (p.resolve() for p in (a.ish, a.stopped_root, a.output))
lab = Path(__file__).resolve().parents[1]
vendor = lab.parents[1]/'vendor/LinuxRunner/app/LinuxRunner'
if not all(p.is_relative_to(Path('/Volumes/easystore')) for p in (ish, source, out)) or out.is_relative_to(source):
    raise SystemExit('Use separate external experiment storage')
db = source/'meta.db'
assert db.is_file() and (source/'data').is_dir()
assert_clean(source)
for path in (db,source/'meta.db-wal',source/'meta.db-shm'):
    if path.exists() and subprocess.run(['lsof','-t',str(path)], capture_output=True, timeout=8).stdout.strip():
        raise SystemExit('Source fakefs is in use')
if subprocess.run(['lsof','-t','-nP','-iTCP:5993','-sTCP:LISTEN'],capture_output=True,timeout=8).stdout.strip():
    raise SystemExit('Display port already in use')
volume = plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/easystore'],timeout=8))
assert volume['VolumeUUID'] == '580CADCD-33F5-4D78-9530-2287615873CA'

os.umask(0o077)
out.mkdir(mode=0o700)
root = out/'root'
source_db_sha = sha(db)
subprocess.run(['/bin/cp','-cRp',source,root],check=True,timeout=90)
assert sha(root/'meta.db') == source_db_sha
assert_clean(root)

gen = out/'generated'
subprocess.run(['python3',lab/'tools/build-rfb-lifetime.py',gen,'--frame-snapshot-pool'],check=True,timeout=30)
control = out/'viewer'
fixture = lab/'tests/rfb-real-refresh-control.m'
compile_args = ['xcrun','clang','-fobjc-arc','-fblocks','-DIDECK_LAB_RFB_LIFETIME=1','-Wall','-Wextra','-Werror',
                '-Wno-unused-function','-Wno-misleading-indentation','-fsanitize=address,undefined','-fno-sanitize-recover=all',
                '-I',gen,'-I',lab/'app','-I',vendor,fixture,lab/'app/LabRFBClient.m',lab/'app/FrameSnapshotPool.m',
                vendor/'RFBProtocol.c','-framework','Foundation','-o',control]
with (out/'viewer-build.log').open('xb') as log:
    subprocess.run(compile_args,check=True,stdout=log,stderr=log,timeout=60)

recipe = lab/'guest/x11-control.sh'
script = recipe.read_text()
assert script.count('x11vnc -norc') == 1
script = script.replace('x11vnc -norc','x11vnc -shared -norc')
assert script.count('/tmp/ideck-vnc-password') == 2
password_path = '/tmp/'+password_name
script = script.replace('/tmp/ideck-vnc-password',password_path)
assert script.count('    wait || :\n') == 1
script = script.replace('    wait || :\n',f'    wait || :\n    rm -f {password_path}\n')
deps = {p:sha(root/'data'/'usr/bin'/p) for p in ('Xvfb','x11vnc')}
with (out/'host-display.log').open('xb') as log:
    guest = subprocess.Popen([ish,'-f',root,'/bin/sh','-c',script,'ideck-host-x11-refresh','--display-only','18'],
                             stdin=subprocess.DEVNULL,stdout=log,stderr=log)
    try:
        stop = time.monotonic()+12
        while time.monotonic()<stop and guest.poll() is None:
            listening = subprocess.run(['lsof','-t','-a','-p',str(guest.pid),'-nP','-iTCP:5993','-sTCP:LISTEN'],
                                       capture_output=True,timeout=4)
            if str(guest.pid).encode() in listening.stdout.splitlines():
                break
            time.sleep(.15)
        else:
            raise RuntimeError('Own LinuxRunner display listener was not observed')
        check = subprocess.run([control,root/'data/tmp'/password_name],capture_output=True,text=True,timeout=15)
        (out/'viewer.log').write_text(check.stdout+check.stderr)
        guest_exit = guest.wait(timeout=23)
    finally:
        if guest.poll() is None:
            guest.terminate()
            try:
                guest.wait(timeout=5)
            except subprocess.TimeoutExpired:
                guest.kill()
                guest.wait(timeout=5)

assert sha(db) == source_db_sha
assert check.returncode == 0 and guest_exit == 0, (check.returncode,guest_exit)
assert not (root/'data/tmp'/password_name).exists(), 'Guest fixture cleanup did not remove its temporary password'
seen = json.loads(check.stdout)
result = dict(scope='HOST LinuxRunner with actual Xvfb/x11vnc and Lab framebuffer pool; own idle desktop only',
              viewer=seen,display_exit=guest_exit,linuxrunner=sha(ish),source_db_sha256=source_db_sha,
              dependencies_sha256=deps,recipe_sha256=sha(recipe),fixture_sha256=sha(fixture),
              viewer_sha256=sha(control),generated_sha256=sha(gen/'LabRFBJoined.generated.inc'),
              runner_sha256=sha(Path(__file__)),
              expected_static_refresh=(seen['full_written']==1 and seen['updates_started']==2 and seen['updates_decoded']==2
                                       and seen['frames']==2 and seen['identical_second']==1 and seen['pool_exhausted']==0))
(out/'evidence.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
raise SystemExit(0 if result['expected_static_refresh'] else 1)
