#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Madeira Converter Exception: see LICENSE-EXCEPTION.md
"""Restore the logical executable path advertised by the public AppKit shim.
Only edits a converted experimental COPY. Re-sign before installation.
No executable code, authentication, or process policy is changed.
"""
import argparse
import os
from pathlib import Path
import plistlib


def fix_layout(app):
    app = Path(os.path.abspath(app))
    if app != app.resolve():
        raise ValueError('App root must not traverse a symlink')
    info = plistlib.loads((app / 'Info.plist').read_bytes())
    if info.get('SHIMMacRoot') != 'Mac':
        raise ValueError('Not the expected converted Mac layout')
    executable = info['CFBundleExecutable']
    if not isinstance(executable, str) or not executable or executable in ('.', '..') or '/' in executable or '\\' in executable:
        raise ValueError('Unsafe executable name')
    main = app / executable
    if not main.is_file() or main.is_symlink():
        raise ValueError('Expected a regular root executable')
    parent = app / 'Mac/Contents/MacOS'
    if not parent.is_dir() or parent != parent.resolve():
        raise ValueError('Unexpected logical executable parent')
    logical = parent / executable
    if logical.is_symlink():
        if logical.resolve() != main:
            raise ValueError('Existing executable link points elsewhere; preserve it')
        return False
    if logical.exists():
        raise ValueError('Existing logical executable is preserved; inspect it first')
    logical.symlink_to('../../../' + executable)
    if logical.resolve(strict=True) != main:
        raise ValueError('Executable link did not resolve to signed root binary')
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('app', type=Path)
    args = parser.parse_args()
    print('Logical executable link added; re-sign before installation' if fix_layout(args.app) else 'Logical executable already resolves to root binary')


if __name__ == '__main__':
    main()
