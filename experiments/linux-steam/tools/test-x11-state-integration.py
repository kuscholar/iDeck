#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Compile actual Lab shell contract with enabled/disabled/invalid gates.

Emits bytes only, NEVER executes a shell/guest/Steam or operates a device.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);a=p.parse_args()
out=a.output.resolve();assert str(out).startswith('/Volumes/easystore/') and not out.exists();out.mkdir(mode=0o700)
lab=Path(__file__).resolve().parents[1]
fixture=out/'fixture.c';fixture.write_text('#include <stdio.h>\n#include "LinuxSteamSession.h"\nint main(void){const char args[]=IDECK_LINUX_STEAM_ARGS;return fwrite(args,1,sizeof args,stdout)==sizeof args?0:1;}\n')
tests=[]
cases = [
    ('off', 0, 1, 1, 1, 0, True),
    ('on', 1, 1, 1, 1, 0, True),
    ('big-picture', 1, 1, 1, 1, 1, True),
    ('no-frontend', 1, 0, 1, 1, 0, False),
    ('no-log', 1, 1, 0, 1, 0, False),
    ('no-tool', 1, 1, 1, 0, 0, False),
]
for label,state,frontend,native,tool,big_picture,valid in cases:
    exe=out/label
    cmd=['xcrun','clang','-Wall','-Wextra','-Werror','-I'+str(lab/'app'),'-DIDECK_LAB_X11_STATE='+str(state),'-DIDECK_LAB_STEAM_FRONTEND='+str(frontend),'-DIDECK_LAB_NATIVE_LOG='+str(native),'-DIDECK_LAB_COMPAT_TOOL='+str(tool),'-DIDECK_LAB_STEAM_BIG_PICTURE='+str(big_picture),str(fixture),'-o',str(exe)]
    r=subprocess.run(cmd,capture_output=True,timeout=20);(out/(label+'.log')).write_bytes(r.stderr)
    assert (r.returncode==0)==valid
    if valid:
        wire=subprocess.check_output([str(exe)],timeout=5);parts=wire.split(b'\0');assert parts[0]==b'/bin/sh' and parts[1]==b'-c'
        script=parts[2].decode()
        ui_arg = ' -gamepadui' if big_picture else ' -nobigpicture'
        assert './steamrtarm64/steam -clientbeta steamdeck_stable' + ui_arg in script
        assert script.count(' -gamepadui') == big_picture
        assert script.count(' -nobigpicture') == 1 - big_picture
        assert ('/ideck-diagnostics/x11-window-state-v1 > /tmp/ideck-x11-state.jsonl' in script)==bool(state)
        assert script.count('qpid=$!')==state
        if state:assert script.index('qpid=$!')<script.index('./steamrtarm64/steam') and 'test -z "$qpid" || kill "$qpid"' in script
        (out/(label+'-command.bin')).write_bytes(wire)
    tests.append(dict(label=label,compile_exit=r.returncode,valid=valid))
desktop = (out/'on-command.bin').read_bytes()
assert (out/'big-picture-command.bin').read_bytes() == desktop.replace(b' -nobigpicture', b' -gamepadui')
e=dict(scope='HOST actual compile-gated Lab command bytes only; no shell/runtime/device execution',tests=tests,source_sha256=hashlib.sha256((lab/'app/LinuxSteamSession.h').read_bytes()).hexdigest())
(out/'evidence.json').write_text(json.dumps(e,indent=2)+'\n');print(json.dumps(e))
