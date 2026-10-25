#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Collect license texts from the locked target dependency graph, recursively.

The result is a conservative input inventory, not a claim that every dependency
survives dead stripping. Build/proc-macro-only crates are not runtime inputs.
"""
import argparse
import json
import subprocess
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('manifest', type=Path)
p.add_argument('--package', required=True)
p.add_argument('--output', required=True, type=Path)
p.add_argument('--inventory', required=True, type=Path)
p.add_argument('--supplemental', type=Path,
               help='Versioned, provenance-recorded notices omitted from published crates')
args = p.parse_args()
metadata = json.loads(subprocess.check_output([
    'cargo', 'metadata', '--manifest-path', str(args.manifest.resolve()), '--locked',
    '--offline', '--format-version', '1', '--filter-platform', 'aarch64-apple-ios'],
    cwd=args.manifest.resolve().parent))
packages = {x['id']: x for x in metadata['packages']}
nodes = {x['id']: x for x in metadata['resolve']['nodes']}
roots = [x['id'] for x in metadata['packages'] if x['name'] == args.package]
assert len(roots) == 1, 'Package name must uniquely identify the root'
selected, pending = set(), roots.copy()
while pending:
    key = pending.pop()
    if key in selected:
        continue
    selected.add(key)
    for dep in nodes[key]['deps']:
        if not any(k['kind'] is None for k in dep['dep_kinds']):
            continue
        if any('proc-macro' in t['kind'] for t in packages[dep['pkg']]['targets']):
            continue
        pending.append(dep['pkg'])

texts = ['Notices for ' + args.package + ' (aarch64-apple-ios)',
         'Generated from the locked aarch64-apple-ios normal dependency graph.',
         'Conservative inventory before dead stripping. Component licenses remain unchanged.', '']
inventory, missing = [], []
for package in sorted((packages[x] for x in selected), key=lambda x: (x['name'], x['version'])):
    folder = Path(package['manifest_path']).parent
    files = sorted(f for f in folder.rglob('*') if f.is_file()
                   and f.name.upper().startswith(('LICENSE', 'LICENCE', 'COPYING', 'NOTICE', 'COPYRIGHT'))
                   and not any(x in f.relative_to(folder).parts for x in ['target', '.git']))
    # Workspace packages may keep their shared license at the workspace root.
    if not files and folder.parent == Path(metadata['workspace_root']):
        files = sorted(f for f in folder.parent.iterdir() if f.is_file()
                       and f.name.upper().startswith(('LICENSE', 'COPYING', 'NOTICE')))
    supplemental = None
    if not files and args.supplemental:
        supplemental = args.supplemental / (package['name'] + '-' + package['version'])
        if supplemental.is_dir():
            files = sorted(f for f in supplemental.iterdir() if f.is_file())
    if not files:
        missing.append(package['name'] + ' ' + package['version'])
    record = {'name': package['name'], 'version': package['version'],
              'declared_license': package.get('license'),
              'repository': package.get('repository'),
              'authors': package.get('authors', []),
              'supplemental': supplemental.name if supplemental and files else None,
              'license_files': [str(f.relative_to(folder)) if f.is_relative_to(folder)
                                else f.name for f in files]}
    inventory.append(record)
    texts += ['=' * 78, package['name'] + ' ' + package['version'],
              'Declared license: ' + str(package.get('license') or 'see workspace license below')]
    for f in files:
        texts += ['', '--- ' + (str(f.relative_to(folder)) if f.is_relative_to(folder)
                               else '../' + f.name) + ' ---', f.read_text(errors='replace')]
args.output.write_text('\n'.join(texts) + '\n')
args.inventory.write_text(json.dumps({'target': 'aarch64-apple-ios',
                                    'packages': inventory, 'missing_license_text': missing}, indent=2) + '\n')
print(f'{len(inventory)} input packages; {len(missing)} missing license texts')
if missing:
    print('\n'.join(missing))
    raise SystemExit(1)
