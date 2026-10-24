#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Write the licence notices of every crate compiled into libmadeira_rppairing.a.

Walks the normal (non-build, non-dev) dependency graph for aarch64-apple-ios
from Cargo.lock, skips proc-macro crates (they run at compile time and are not
in the binary), and copies each crate's LICENSE/COPYING/NOTICE files from the
cargo registry. Usage: notices.py <output file>
"""
import json
import subprocess
import sys
from pathlib import Path

here = Path(__file__).resolve().parent
metadata = json.loads(subprocess.run(
    ['cargo', 'metadata', '--format-version', '1', '--locked', '--filter-platform', 'aarch64-apple-ios'],
    cwd=here, check=True, capture_output=True, text=True).stdout)
packages = {p['id']: p for p in metadata['packages']}
nodes = {n['id']: n for n in metadata['resolve']['nodes']}
root = metadata['resolve']['root']

shipped, todo = set(), [root]
while todo:
    node = nodes[todo.pop()]
    for dep in node['deps']:
        if not any(kind['kind'] is None for kind in dep['dep_kinds']):
            continue
        package = packages[dep['pkg']]
        if any('proc-macro' in target['kind'] for target in package['targets']):
            continue
        if dep['pkg'] not in shipped:
            shipped.add(dep['pkg'])
            todo.append(dep['pkg'])

out = ['Third-party notices for libmadeira_rppairing.a (build/rppairing-ios), generated',
       'by build/rppairing-ios/notices.py from Cargo.lock. Each crate is listed with the',
       'licence it declares and the licence files it ships.', '']
missing, seen = [], {}
for package in sorted((packages[i] for i in shipped), key=lambda p: (p['name'], p['version'])):
    folder = Path(package['manifest_path']).parent
    files = sorted(f for f in folder.iterdir()
                   if f.is_file() and f.name.upper().startswith(('LICENSE', 'LICENCE', 'COPYING', 'NOTICE')))
    out.append('=' * 78)
    out.append(f"{package['name']} {package['version']} ({package.get('license') or 'see files'})")
    if package.get('repository'):
        out.append(package['repository'])
    if not files:
        missing.append(package['name'])
        out.append('(no licence file in the published crate; licence as declared above)')
    for f in files:
        text = f.read_text(errors='replace').rstrip()
        if text in seen:
            out.append(f'--- {f.name}: same text as {seen[text]} above ---')
        else:
            seen[text] = f"{package['name']} {f.name}"
            out += ['', f'--- {f.name} ---', text]
    out.append('')

Path(sys.argv[1]).write_text('\n'.join(out) + '\n')
print(f'{len(shipped)} crates -> {sys.argv[1]}' + (f" (no licence file: {', '.join(missing)})" if missing else ''))
