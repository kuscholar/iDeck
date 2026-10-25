#!/usr/bin/env python3
"""Verify a pinned checkout or the hashed source tree supplied in release assets.

IDECK_ALLOW_MODIFIED_SOURCES=1 intentionally permits recipient modifications.
It does not change the recorded baseline revision.
"""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
expected = sys.argv[2]
allow_modified = os.environ.get('IDECK_ALLOW_MODIFIED_SOURCES') == '1'
try:
    top = Path(subprocess.check_output(['git', '-C', str(root), 'rev-parse', '--show-toplevel'],
                                      stderr=subprocess.DEVNULL, text=True).strip()).resolve()
except subprocess.CalledProcessError:
    top = None
if top == root:
    revision = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    assert revision == expected, 'Unexpected source baseline'
    if not allow_modified:
        subprocess.run(['git', '-C', str(root), 'diff', '--exit-code', 'HEAD'], check=True)
else:
    manifest = json.loads((root / '.ideck-source.json').read_text())
    assert manifest['revision'] == expected, 'Unexpected source archive baseline'
    if not allow_modified:
        for name, digest in manifest['files'].items():
            f = root / name
            assert f.resolve().is_relative_to(root), 'Unsafe source manifest path'
            assert hashlib.sha256(f.read_bytes()).hexdigest() == digest, 'Modified source: ' + name
print('Source baseline verified:', expected, '(recipient modifications allowed)' if allow_modified else '')
