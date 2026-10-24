#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Madeira Converter Exception: see LICENSE-EXCEPTION.md
"""Stage public Valve Windows client packages, never account data or a live prefix.

Input is an explicitly saved steam_client_win32/steam_client_win64 manifest from Valve's HTTPS CDN.
The manifest's signatures are not verified by this utility; package SHA-256 and
size are verified against that manifest. Keep its hash with experiment evidence.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import tempfile
import urllib.request
import zipfile

CDN = 'https://client-update.akamai.steamstatic.com/'


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def parse_manifest(text, architecture="win64"):
    tokens = re.findall(r'"[^"\r\n]*"|[{}]', text)
    pos = 0

    def obj(nested=False):
        nonlocal pos
        result = {}
        while pos < len(tokens):
            key = tokens[pos]
            pos += 1
            if key == '}':
                if not nested:
                    raise ValueError('Unexpected closing brace')
                return result
            if not key.startswith('"') or pos == len(tokens):
                raise ValueError('Invalid manifest key')
            key = key[1:-1]
            value = tokens[pos]
            pos += 1
            if key in result:
                raise ValueError('Duplicate manifest key')
            if value == '{':
                result[key] = obj(True)
            elif value.startswith('"'):
                result[key] = value[1:-1]
            else:
                raise ValueError('Invalid manifest value')
        if nested:
            raise ValueError('Missing closing brace')
        return result

    if architecture not in ('win32', 'win64'):
        raise ValueError('Unsupported architecture')
    root = obj()[architecture]
    packages = {k: v for k, v in root.items() if isinstance(v, dict) and 'file' in v}
    packages['steam_' + architecture] = root['steam_' + architecture]['steamrow']
    for p in packages.values():
        if not re.fullmatch(r'[A-Za-z0-9_.-]+', p['file']):
            raise ValueError('Invalid package filename')
        if not re.fullmatch(r'[a-f0-9]{64}', p['sha2']) or not 0 < int(p['size']) < 1024**3:
            raise ValueError('Invalid package digest/size')
    for required in tuple(name + architecture for name in ('bins_', 'bins_cef_', 'bins_webhelpers_', 'steam_')):
        if required not in packages:
            raise ValueError('Missing package: ' + required)
    return root['version'], packages


def safe_member(info):
    name = info.filename.replace('\\', '/')
    path = PurePosixPath(name)
    mode = info.external_attr >> 16
    if (not name or path.is_absolute() or '..' in path.parts or ':' in name
            or stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR)):
        raise ValueError('Unsafe ZIP member')
    if not path.parts:
        raise ValueError('Empty ZIP member')
    return path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--manifest', type=Path, required=True)
    ap.add_argument('--architecture', choices=('win32', 'win64'), default='win64')
    ap.add_argument('--cache', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True, help='Must not exist')
    args = ap.parse_args()
    if args.output.exists() or args.output.is_symlink():
        ap.error('Output must be a new staging directory, never a live installation')
    version, packages = parse_manifest(args.manifest.read_text(), args.architecture)
    args.cache.mkdir(parents=True, exist_ok=True)

    def fetch(item):
        name, p = item
        target = args.cache / p['file']
        if not (target.is_file() and target.stat().st_size == int(p['size']) and digest(target) == p['sha2']):
            part = target.with_suffix(target.suffix + '.partial')
            with urllib.request.urlopen(CDN + p['file'], timeout=90) as response, part.open('wb') as f:
                shutil.copyfileobj(response, f)
            if part.stat().st_size != int(p['size']) or digest(part) != p['sha2']:
                raise ValueError('Package size/digest mismatch: ' + name)
            part.replace(target)
        print('VERIFIED ' + name, flush=True)
        return target

    with ThreadPoolExecutor(max_workers=4) as pool:
        archives = list(pool.map(fetch, packages.items()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='steam-ui-stage-', dir=args.output.parent) as td:
        stage = Path(td) / 'Steam'
        stage.mkdir()
        total = 0
        for archive in archives:
            with zipfile.ZipFile(archive) as z:
                for info in z.infolist():
                    relative = safe_member(info)
                    dest = stage.joinpath(*relative.parts)
                    if info.is_dir():
                        dest.mkdir(parents=True, exist_ok=True)
                        continue
                    total += info.file_size
                    if total > 3 * 1024**3:
                        raise ValueError('Expanded client exceeds 3 GiB limit')
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    if dest.exists():
                        with z.open(info) as f:
                            if hashlib.sha256(f.read()).hexdigest() != digest(dest):
                                raise ValueError('Conflicting package file: ' + str(relative))
                    else:
                        with z.open(info) as src, dest.open('xb') as out:
                            shutil.copyfileobj(src, out)
        report = {'source': CDN + 'steam_client_' + args.architecture, 'version': version,
                  'manifest_sha256': digest(args.manifest),
                  'integrity': 'HTTPS manifest and package SHA256; manifest signatures not independently verified',
                  'packages': packages, 'expanded_bytes': total,
                  'files': {str(p.relative_to(stage)): {'bytes': p.stat().st_size, 'sha256': digest(p)}
                            for p in sorted(stage.rglob('*')) if p.is_file()}}
        (Path(td) / 'inventory.json').write_text(json.dumps(report, indent=2) + '\n')
        stage.rename(args.output)
        shutil.copyfile(Path(td) / 'inventory.json', args.output.parent / (args.output.name + '-inventory.json'))
    print('STAGED Valve ' + args.architecture + ' client ' + version + ' (not executed)', flush=True)


if __name__ == '__main__':
    main()
