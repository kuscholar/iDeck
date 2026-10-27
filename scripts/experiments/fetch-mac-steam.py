#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Madeira Converter Exception: see LICENSE-EXCEPTION.md
"""Download Valve's public macOS client packages to private, untracked storage.
No Steam login, game content, installation, or binary patching is performed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

BASE = 'https://client-update.akamai.steamstatic.com/'


def parse_vdf(text):
    tokens = re.findall(r'"((?:[^"\\]|\\.)*)"|([{}])', text)
    tokens = [brace or value for value, brace in tokens]
    index = 0

    def object_(nested=False):
        nonlocal index
        result = {}
        while index < len(tokens):
            key = tokens[index]
            index += 1
            if key == '}':
                if not nested:
                    raise ValueError('Unexpected closing brace')
                return result
            if key == '{' or index >= len(tokens) or key in result:
                raise ValueError('Malformed or duplicate manifest field')
            value = tokens[index]
            index += 1
            if value == '}':
                raise ValueError('Missing manifest value')
            result[key] = object_(True) if value == '{' else value
        if nested:
            raise ValueError('Unclosed manifest section')
        return result

    return object_()


def validate_package(item):
    name, digest = item['file'], item['sha2']
    if not re.fullmatch(r'[A-Za-z0-9_\-.]+\.zip\.[0-9a-f]{40}', name):
        raise ValueError('Unsafe or unsupported package name')
    if not re.fullmatch(r'[0-9a-f]{64}', digest):
        raise ValueError('Invalid SHA256')
    size = int(item['size'])
    if not 0 < size <= 1024 ** 3:
        raise ValueError('Unsupported package size')
    return name, digest, size


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('packages', nargs='+', help='Top-level official manifest keys')
    args = parser.parse_args()
    root = args.output.resolve()
    repo = Path(__file__).resolve().parents[2]
    if root == repo or repo in root.parents:
        parser.error('Valve files must be outside this source repository')
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=root, prefix='.manifest-', delete=False) as temp:
        manifest_file = Path(temp.name)
    try:
        subprocess.run(['curl', '--fail', '--silent', '--show-error', '--location',
                        '--proto', '=https', '--proto-redir', '=https', '--max-time', '30',
                        BASE + 'steam_client_osx', '-o', str(manifest_file)], check=True)
        manifest = parse_vdf(manifest_file.read_text())['osx']
        selected = {key: validate_package(manifest[key]) for key in args.packages}
        manifest_file.replace(root / 'steam_client_osx.manifest')
        (root / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        print('Official manifest version:', manifest['version'], flush=True)
        for key, (name, digest, size) in selected.items():
            target = root / name
            if not target.exists() or target.stat().st_size != size or sha256(target) != digest:
                partial = target.with_suffix(target.suffix + '.part')
                try:
                    subprocess.run(['curl', '--fail', '--silent', '--show-error', '--location',
                                    '--proto', '=https', '--proto-redir', '=https', '--max-time', '180',
                                    BASE + name, '-o', str(partial)], check=True)
                    if partial.stat().st_size != size or sha256(partial) != digest:
                        raise ValueError('Package size/SHA256 mismatch: ' + key)
                    partial.replace(target)
                finally:
                    partial.unlink(missing_ok=True)
            print(key, digest, 'verified', flush=True)
    finally:
        manifest_file.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
