#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Madeira Converter Exception: see LICENSE-EXCEPTION.md
"""Stage verified public Steam packages in a NEW private directory, never install.
The resulting bundle is experimental input, not a working macOS/iOS installation.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import stat
import tarfile
import zipfile


def safe_path(root, name):
    name = name.replace('\\', '/')
    part = PurePosixPath(name)
    if part.is_absolute() or '..' in part.parts or not part.parts:
        raise ValueError('Unsafe archive member')
    target = root.joinpath(*part.parts)
    if not target.parent.resolve().is_relative_to(root.resolve()):
        raise ValueError('Archive traversed a symlink outside output')
    return target


def write_entry(root, name, data=None, link=None, directory=False, mode=0o644):
    target = safe_path(root, name)
    if directory:
        target.mkdir(parents=True, exist_ok=True)
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_symlink():
        target.unlink()
    if link is not None:
        if not (target.parent / link).resolve().is_relative_to(root.resolve()):
            raise ValueError('Unsafe archive symlink')
        target.symlink_to(link)
    else:
        target.write_bytes(data)
        macho = data[:4] in (b'\xcf\xfa\xed\xfe', b'\xca\xfe\xba\xbe', b'\xbe\xba\xfe\xca', b'\xce\xfa\xed\xfe')
        target.chmod(0o755 if macho else (mode & 0o777) or 0o644)


def verified_archive(packages, item):
    name = item['file']
    if Path(name).name != name or '/' in name or '\\' in name:
        raise ValueError('Invalid manifest package name')
    path = packages / name
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    if digest.hexdigest() != item['sha2'] or path.stat().st_size != int(item['size']):
        raise ValueError('Package verification failed: ' + name)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packages', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.output.resolve()
    repo = Path(__file__).resolve().parents[2]
    if root == repo or repo in root.parents:
        parser.error('Valve content must be outside the source repository')
    if root.exists():
        parser.error('Output must be new; existing data is never replaced')
    manifest = json.loads((args.packages / 'manifest.json').read_text())
    items = {key: item for key, item in manifest.items() if isinstance(item, dict) and 'file' in item}
    archives = {key: verified_archive(args.packages, item) for key, item in items.items()}
    root.mkdir(parents=True)
    with zipfile.ZipFile(archives['appdmg_osx']) as archive:
        with tarfile.open(fileobj=io.BytesIO(archive.read('SteamMacBootstrapper.tar.gz')), mode='r:gz') as tar:
            for entry in tar:
                if entry.isdir(): write_entry(root, entry.name, directory=True)
                elif entry.issym(): write_entry(root, entry.name, link=entry.linkname)
                elif entry.isfile(): write_entry(root, entry.name, data=tar.extractfile(entry).read(), mode=entry.mode)
                else: raise ValueError('Unsupported tar entry')
    app = root / 'Steam.app'
    if not (app / 'Contents/Info.plist').is_file():
        raise ValueError('Bootstrapper app layout changed')
    for key, path in archives.items():
        if key == 'appdmg_osx': continue
        with zipfile.ZipFile(path) as archive:
            for entry in archive.infolist():
                name = entry.filename.replace('\\', '/')
                base = app / 'Contents' if name.split('/')[0] == 'Frameworks' else app / 'Contents/MacOS'
                base.mkdir(parents=True, exist_ok=True)
                mode = entry.external_attr >> 16
                relative = str((base / name).relative_to(app))
                if entry.is_dir(): write_entry(app, relative, directory=True)
                elif stat.S_ISLNK(mode):
                    # Framework links may legitimately point into Contents/MacOS.
                    # Validate against the complete app root, then write there.
                    write_entry(app, relative, link=archive.read(entry).decode())
                else: write_entry(app, relative, data=archive.read(entry), mode=mode)
    print('Staged official manifest version', manifest['version'])
    print(app)


if __name__ == '__main__':
    main()
