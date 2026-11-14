#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Build actual ARM64 Linux read-only snapshot and ASan/UBSan protocol controls.

No socket, Steam/app/device process, credential, rootfs or signing operation.
This does NOT establish on-Air execution; the ELF is not yet in the Lab target.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('output',type=Path)
p.add_argument('--ld-lld',type=Path,required=True)
a=p.parse_args();out=a.output.resolve();linker=a.ld_lld.absolute()
# LLVM's multicall driver selects the ELF linker by argv[0] (ld.lld). Do not
# resolve its prepared symlink into the generic lld driver name.
assert str(out).startswith('/Volumes/easystore/') and not out.exists()
assert linker.is_file()
out.mkdir(mode=0o700);lab=Path(__file__).resolve().parents[1]
commands=[['xcrun','clang','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',
           str(lab/'tools/x11-state-control.c'),'-o',str(out/'control')],
          [str(out/'control')],
          ['xcrun','clang','--target=aarch64-linux-gnu','--ld-path='+str(linker),'-nostdlib','-static',
           '-ffreestanding','-fno-builtin','-fno-stack-protector','-O2','-Wall','-Wextra','-Werror',
           str(lab/'guest/x11-window-state.c'),'-Wl,-e,_start','-o',str(out/'x11-window-state.elf')]]
for i,cmd in enumerate(commands):
    with (out/(str(i)+'.log')).open('xb') as log:
        result=subprocess.run(cmd,stdout=log,stderr=log,timeout=60)
    assert not result.returncode,(i,result.returncode,'inspect private log')
elf=(out/'x11-window-state.elf').read_bytes()
assert elf[:6]==b'\x7fELF\x02\x01' and elf[16:20]==b'\x02\0\xb7\0'
evidence=dict(scope='HOST mocked read-only X11 protocol controls and actual static ARM64 Linux ELF build; NOT LinuxRunner execution or Steam/Air/UI validation',
              cases=19,commands=commands,artifacts={name:hashlib.sha256((out/name).read_bytes()).hexdigest() for name in ('control','x11-window-state.elf','1.log')},
              sources={name:hashlib.sha256((lab/name).read_bytes()).hexdigest() for name in ('guest/x11-window-state.c','tools/x11-state-control.c','tools/test-x11-state.py')})
(out/'evidence.json').write_text(json.dumps(evidence,indent=2)+'\n');print(json.dumps(evidence))
