#!/usr/bin/env python3
"""Inventory an IPA without extracting it. This is not license clearance."""
import argparse
import hashlib
import io
import json
import plistlib
import tarfile
import zipfile
from pathlib import Path, PurePosixPath


def audit(path):
    findings, files, nested = [], [], []
    forbidden = {'steam.exe', 'steamwebhelper.exe', 'libcef.dll', 'loginusers.vdf',
                 'localconfig.vdf', 'embedded.mobileprovision'}

    def inspect(name):
        p = PurePosixPath(name)
        if p.is_absolute() or '..' in p.parts:
            findings.append({'path': name, 'reason': 'unsafe archive path'})
        if (p.name.lower() in forbidden or p.name.lower().startswith('ssfn')
                or p.suffix.lower() in {'.p12', '.p8', '.key', '.mobileprovision'}
                or '_CodeSignature' in p.parts):
            findings.append({'path': name, 'reason': 'excluded payload or signing material'})

    with zipfile.ZipFile(path) as z:
        if len(z.namelist()) != len(set(z.namelist())):
            raise ValueError('duplicate ZIP paths')
        info_paths = [n for n in z.namelist()
                      if n.startswith('Payload/') and n.count('/') == 2
                      and n.endswith('.app/Info.plist')]
        if len(info_paths) != 1:
            raise ValueError('expected exactly one main app')
        info = plistlib.loads(z.read(info_paths[0]))
        for entry in z.infolist():
            inspect(entry.filename)
            if entry.is_dir():
                continue
            data = z.read(entry)  # also checks each CRC
            files.append({'path': entry.filename, 'bytes': len(data),
                          'sha256': hashlib.sha256(data).hexdigest(),
                          'wine_builtin_marker': data.startswith(b'MZ') and
                          b'Wine builtin DLL' in data[:256]})
            if entry.filename.endswith('prefix-template.tar.gz'):
                with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as tar:
                    for member in tar:
                        inspect(member.name)
                        nested.append(member.name)
                        if member.issym() or member.islnk():
                            inspect(member.linkname)
    return {'ipa_sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest(),
            'version': info.get('CFBundleShortVersionString'),
            'build': info.get('CFBundleVersion'),
            'bundle_id': info.get('CFBundleIdentifier'), 'files': files,
            'prefix_members': nested, 'findings': findings,
            'limits': 'Name/structure checks are not exhaustive secret scanning, '
                      'binary provenance, license approval, or runtime validation.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ipa', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    result = audit(args.ipa)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(f"Inventoried {len(result['files'])} files; {len(result['findings'])} findings")
    raise SystemExit(1 if result['findings'] else 0)
