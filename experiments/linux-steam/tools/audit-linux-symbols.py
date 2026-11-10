#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Reject unnamespaced current references/definitions in LINUX-only objects.

Do not pass Wine or a combined Mach-O, where regular _current is legitimate.
Checking the Linux archive alone is insufficient: every task-header consumer
must use the same forced header or it could bind accidentally to Wine's global.
"""
import argparse
from pathlib import Path
import subprocess
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('objects', nargs='+', type=Path)
args = parser.parse_args()
bad = []
for path in args.objects:
    symbols = subprocess.check_output(['nm', '-m', '-g', str(path)], text=True, stderr=subprocess.DEVNULL)
    if any(line.rstrip().endswith('external _current') for line in symbols.splitlines()):
        bad.append(str(path))
if bad:
    print('REFUSED: unnamespaced Linux task symbol in: ' + ', '.join(bad), file=sys.stderr)
    sys.exit(1)
print('Linux-only object namespace audit PASS; not a whole runtime safety certificate')
