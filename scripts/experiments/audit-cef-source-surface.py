#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Madeira Converter Exception: see LICENSE-EXCEPTION.md
"""Check candidate CEF126 headers against captured genuine binary metadata.

Runs only the two reviewed, SHA256-pinned upstream Python hashing modules in a
temporary directory. Never builds/loads CEF, writes headers or changes hashes.
Passing this surface gate is NOT full ABI/behavior compatibility evidence.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

spec = importlib.util.spec_from_file_location('loader_audit', Path(__file__).with_name('audit-mac-cef-loader.py'))
loader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(loader)
MODULES = {
    'cef_api_hash.py': '0da2d49c671d02375ddcca21605d65a4c7ac359294bde09cc2425c5026553e95',
    'file_util.py': '6828b86262dd88116e8fe98ff9c2259c67e15269b75eaa7537521bf143358c41',
}


def compare(metadata, hashes, declarations):
    if (metadata.get('mode') != 'static read-only; CEF not initialized' or
        metadata.get('version', {}).get('cefMajor') != 126):
        raise ValueError('Expected actual CEF126 static metadata report')
    actual = metadata['publicABIIdentifiers']
    for value in [actual['platform'], actual['universal'], hashes['mac'], hashes['universal']]:
        if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{40}', value):
            raise ValueError('Invalid API fingerprint')
    missing = sorted(set(loader.CUSTOM)-set(declarations))
    return {'platformMatches': actual['platform'] == hashes['mac'],
            'universalMatches': actual['universal'] == hashes['universal'],
            'missingRequiredDeclarations': missing,
            'surfaceGatePasses': actual['platform'] == hashes['mac'] and
                actual['universal'] == hashes['universal'] and not missing}


def calculate(source):
    include = source/'include'
    if not include.is_dir() or include.is_symlink():
        raise ValueError('Expected ordinary CEF include directory')
    inputs = {}
    total = 0
    for path in sorted(include.rglob('*')):
        if path.is_symlink():
            raise ValueError('Reject symlinked candidate headers')
        if not path.is_file() or path.suffix != '.h':
            continue
        if total+path.stat().st_size > 32*1024*1024 or len(inputs) >= 4096:
            raise ValueError('Candidate header budget exceeded')
        data = path.read_bytes()
        total += len(data)
        if total > 32*1024*1024 or len(inputs) >= 4096:
            raise ValueError('Candidate header budget exceeded')
        inputs[str(path.relative_to(source))] = hashlib.sha256(data).hexdigest()
    if not inputs:
        raise ValueError('No candidate headers')
    with tempfile.TemporaryDirectory(prefix='ideck-cef-hash-') as temporary:
        for name, expected in MODULES.items():
            original = source/'tools'/name
            if original.is_symlink():
                raise ValueError('Reject symlinked hashing module')
            data = original.read_bytes()
            if hashlib.sha256(data).hexdigest() != expected:
                raise ValueError('Hashing module requires source review: '+name)
            (Path(temporary)/name).write_bytes(data)
        # Only these reviewed modules can be imported from this directory.
        command = '''import sys,json
sys.path.insert(0,sys.argv[1])
from cef_api_hash import cef_api_hash
from file_util import read_file
from pathlib import Path
calculator=cef_api_hash(sys.argv[2])
hashes=calculator.calculate()
names=set()
for filename in calculator._cef_api_hash__get_filenames():
    if filename in calculator.excluded_files or filename=='internal/cef_string.h':
        continue
    objects=calculator._cef_api_hash__parse_objects(read_file(str(Path(sys.argv[2])/filename)))
    names.update(o['name'] for o in objects if o['text'].startswith('CEF_EXPORT'))
print(json.dumps({'hashes':hashes,'declarations':sorted(names)}))'''
        completed = subprocess.run([sys.executable, '-I', '-B', '-c', command, temporary, str(include)],
                                   text=True, capture_output=True, check=True, timeout=30)
        result = json.loads(completed.stdout)
    return result['hashes'], result['declarations'], inputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--binary-metadata', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='New report file; existing paths are refused')
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        raise ValueError('Preserve existing output; select a new report path')
    source = args.source.resolve()
    output = args.output.resolve()
    if source == output or source in output.parents or output == args.binary_metadata.resolve():
        raise ValueError('Report must not overwrite source or binary metadata')
    metadata = json.loads(args.binary_metadata.read_text())
    hashes, declarations, inputs = calculate(source)
    result = compare(metadata, hashes, declarations)
    report = {'mode': 'source-surface check only; no CEF/client execution',
              'binaryMetadataSHA256': hashlib.sha256(args.binary_metadata.read_bytes()).hexdigest(),
              'calculatedHashes': hashes, 'comparison': result,
              'headerFingerprints': inputs, 'hashingModuleFingerprints': MODULES,
              'limits': ['API hashes fingerprint declaration text, including parameter names.',
                         'Mismatch alone is not an exhaustive ABI incompatibility proof.',
                         'Passing surface checks does not validate struct layouts, callback ownership or implementation semantics.',
                         'Never spoof hashes or implement no-op exports to turn this gate green.']}
    with args.output.open('x') as stream:
        stream.write(json.dumps(report, indent=2)+'\n')
    print(json.dumps(result, indent=2))
    return 0 if result['surfaceGatePasses'] else 2


if __name__ == '__main__':
    sys.exit(main())
