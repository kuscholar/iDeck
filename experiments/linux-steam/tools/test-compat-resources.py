#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Exercise the actual Xcode resource phase, including reused build products.

Host-only synthetic resources. No device, Valve, account or game operation.
"""
import hashlib
import json
import os
from pathlib import Path
import plistlib
import subprocess
import sys

out = Path(sys.argv[1]).resolve()
assert str(out).startswith('/Volumes/easystore/') and not out.exists()
out.mkdir(mode=0o700)
lab = Path(__file__).resolve().parents[1]
project = plistlib.loads((lab / 'LinuxLab.xcodeproj/project.pbxproj').read_bytes())
phase = project['objects']['000000000000000000000008']['shellScript']
script = out / 'actual-build-phase.sh'
script.write_text(phase)
source = out / 'source'
source.mkdir()
for name in ('probe.elf', 'packet-probe.elf', 'tcp-probe.elf', 'ideck-madeira','xlib-window-trace.so'):
    (source / name).write_bytes(b'HOST SYNTHETIC RESOURCE ' + name.encode())
product = out / 'products/LinuxLab.app'
product.mkdir(parents=True)
compat = product / 'LabCompatibility'
diagnostics=product/'LabDiagnostics'
env = dict(os.environ, LINUX_LAB_BUILD_DIR=str(source), SRCROOT=str(lab),
           TARGET_BUILD_DIR=str(out / 'products'),
           UNLOCALIZED_RESOURCES_FOLDER_PATH='LinuxLab.app')
results = []


def run(name, tool, frontend, expected,trace='0',native='0'):
    with (out / (name + '.log')).open('xb') as log:
        result = subprocess.run(['bash', str(script)], stdout=log, stderr=log,
                                timeout=15, env=dict(env, LINUX_LAB_COMPAT_TOOL=tool,
                                                     LINUX_LAB_STEAM_FRONTEND=frontend,
                                                     LINUX_LAB_X11_TRACE=trace,LINUX_LAB_NATIVE_LOG=native))
    assert result.returncode == expected, (name, result.returncode)
    results.append(dict(mode=name, exit=result.returncode))


run('default-fresh', '0', '0', 0)
assert not compat.exists()
run('explicit-enabled', '1', '1', 0)
assert {p.name for p in compat.iterdir()} == {'ideck-madeira', 'compatibilitytool.vdf', 'toolmanifest.vdf'}
assert (compat / 'ideck-madeira').read_bytes() == (source / 'ideck-madeira').read_bytes()
run('default-reused-products', '0', '0', 0)
assert not compat.exists()
run('enabled-again', '1', '1', 0)
(compat / 'unrelated-own-fixture').write_text('preserve')
run('default-preserve-unknown', '0', '0', 0)
assert [p.name for p in compat.iterdir()] == ['unrelated-own-fixture']
assert (compat / 'unrelated-own-fixture').read_text() == 'preserve'
run('missing-frontend-refused', '1', '0', 2)
assert not (compat / 'ideck-madeira').exists()
assert not diagnostics.exists()
run('trace-explicit-enabled','1','1',0,trace='1',native='1')
assert (diagnostics/'xlib-window-trace.so').read_bytes()==(source/'xlib-window-trace.so').read_bytes()
run('trace-off-reused-products','0','0',0)
assert not diagnostics.exists()
run('trace-enabled-again','1','1',0,trace='1',native='1')
(diagnostics/'unrelated-own-fixture').write_text('preserve')
run('trace-off-preserve-unknown','0','0',0)
assert [p.name for p in diagnostics.iterdir()]==['unrelated-own-fixture']
assert (diagnostics/'unrelated-own-fixture').read_text()=='preserve'
run('trace-missing-native-log-refused','1','1',2,trace='1')
assert not (diagnostics/'xlib-window-trace.so').exists()
evidence = dict(scope='HOST actual Xcode resource phase with synthetic helper; no device/runtime execution',
                script_sha256=hashlib.sha256(phase.encode()).hexdigest(), tests=results)
(out / 'evidence.json').write_text(json.dumps(evidence, indent=2) + '\n')
print(json.dumps(evidence))
