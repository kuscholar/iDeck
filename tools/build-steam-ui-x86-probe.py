#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Madeira Converter Exception: see LICENSE-EXCEPTION.md
"""Build the isolated i386 loader probe; never fetch or distribute Valve code."""
import argparse
import hashlib
from pathlib import Path
import struct
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--toolchain', required=True, type=Path)
parser.add_argument('--output', required=True, type=Path)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
tools = args.toolchain.resolve() / 'bin'
for name in ('i686-w64-mingw32-dlltool', 'i686-w64-mingw32-clang'):
    if not (tools / name).is_file():
        parser.error('missing tool: ' + name)
output = args.output.resolve()
if output.exists():
    parser.error('output already exists; choose a new path')
output.parent.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(prefix='madeira-x86-probe-') as temp:
    library = Path(temp) / 'chrome-elf32.lib'
    exe = Path(temp) / 'probe.exe'
    subprocess.run([str(tools / 'i686-w64-mingw32-dlltool'), '-d',
                    str(root / 'tests/steam-ui/chrome-elf.def'), '-l', str(library)], check=True)
    subprocess.run([str(tools / 'i686-w64-mingw32-clang'), '-O2', '-static',
                    '-Wl,--no-insert-timestamp', str(root / 'tests/steam-ui/chrome-elf-heap.c'),
                    str(library), '-o', str(exe)], check=True)
    data = exe.read_bytes()
    offset = struct.unpack_from('<I', data, 60)[0]
    if data[:2] != b'MZ' or data[offset:offset+4] != b'PE\0\0' or struct.unpack_from('<H', data, offset+4)[0] != 0x14c:
        raise SystemExit('compiler did not produce i386 PE')
    with output.open('xb') as handle:
        handle.write(data)
print('i386 PE SHA256=' + hashlib.sha256(data).hexdigest())
print('This is not full libcef/Steam/UI validation; supply genuine matching DLLs separately.')
