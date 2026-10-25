#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Package an unsigned Xcode product with ad-hoc signatures and no profiles.

Ad-hoc signatures have no signing certificate. Recipients must re-sign with
their own matching development profiles; this does not make the IPA installable.
"""
import argparse
import importlib.util
import plistlib
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('app', type=Path)
p.add_argument('output', type=Path)
p.add_argument('--entitlements', required=True, type=Path)
args = p.parse_args()
assert args.app.suffix == '.app'
assert not args.output.exists(), 'Refusing to overwrite an existing package'
entitlements = plistlib.loads(args.entitlements.read_bytes())
assert set(entitlements) <= {'get-task-allow', 'com.apple.security.cs.allow-jit',
                             'com.apple.developer.kernel.increased-memory-limit'}
assert entitlements.get('get-task-allow') is True
with tempfile.TemporaryDirectory(prefix='ideck-package-') as temp:
    payload = Path(temp) / 'Payload'
    payload.mkdir()
    app = payload / args.app.name
    shutil.copytree(args.app, app)
    # Mono is fetched separately; do not accidentally ship a local development copy.
    shutil.rmtree(app / 'wine-mono', ignore_errors=True)
    for profile in app.rglob('*.mobileprovision'):
        profile.unlink()
    for signature in list(app.rglob('_CodeSignature')):
        shutil.rmtree(signature)
    helper = app / 'PlugIns/MadeiraJITHelper.appex'
    assert (helper / 'Info.plist').is_file(), 'JIT helper must be retained'
    helper_entitlements = Path(temp) / 'helper.plist'
    helper_entitlements.write_bytes(plistlib.dumps({'get-task-allow': True}))

    def sign(path, entitlement=None):
        cmd = ['codesign', '--force', '--sign', '-', '--timestamp=none']
        if entitlement:
            cmd += ['--entitlements', str(entitlement)]
        subprocess.run(cmd + [str(path)], check=True)

    for binary in sorted(app.rglob('*.dylib')):
        sign(binary)
    for framework in sorted(app.rglob('*.framework'), key=lambda x: len(x.parts), reverse=True):
        sign(framework)
    sign(helper, helper_entitlements)
    sign(app, args.entitlements.resolve())
    subprocess.run(['codesign', '--verify', '--deep', '--strict', str(app)], check=True)
    details = subprocess.check_output(['codesign', '-dv', str(app)], stderr=subprocess.STDOUT, text=True)
    assert 'Signature=adhoc' in details and 'TeamIdentifier=not set' in details
    with zipfile.ZipFile(args.output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for f in sorted(payload.rglob('*')):
            if f.is_file() and f.name != '.DS_Store':
                assert f.resolve().is_relative_to(payload.resolve()), 'External symlink in package'
                z.write(f, f.relative_to(Path(temp)))

spec = importlib.util.spec_from_file_location('audit_ipa', Path(__file__).with_name('audit-ipa.py'))
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
report = audit.audit(args.output, allow_signature_resources=True)
import json
args.output.with_suffix('.inventory.json').write_text(json.dumps(report, indent=2) + '\n')
assert not report['findings'], report['findings']
print(f"Packaged {len(report['files'])} files; ad-hoc signature and scoped inventory checks passed")
