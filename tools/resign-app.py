#!/usr/bin/env python3
"""Re-sign an extracted iDeck app using your own matching development profiles.

Operate on a disposable extracted copy, never the original build or installed app.
This tool does not log into Apple or create profiles. No bundle ID rewriting.
"""
import argparse
import datetime
import plistlib
import shutil
import subprocess
import tempfile
from pathlib import Path


def run(*args):
    subprocess.run(args, check=True)


def profile_entitlements(bundle, profile):
    data = subprocess.check_output(['security', 'cms', '-D', '-i', str(profile)],
                                   stderr=subprocess.DEVNULL)
    p = plistlib.loads(data)
    info = plistlib.loads((bundle / 'Info.plist').read_bytes())
    e = p['Entitlements']
    app_id = e['application-identifier']
    # AppIdentifierPrefix can differ from TeamIdentifier for older accounts.
    if app_id.split('.', 1)[1] != info['CFBundleIdentifier']:
        raise ValueError('Profile must exactly match bundle identifier (no wildcard)')
    if p['ExpirationDate'] <= datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None):
        raise ValueError('Development profile expired')
    if e.get('get-task-allow') is not True or not p.get('ProvisionedDevices'):
        raise ValueError('JIT requires a device development profile with get-task-allow')
    e['keychain-access-groups'] = [app_id]
    return e


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('app', type=Path)
    p.add_argument('--identity', required=True)
    p.add_argument('--keychain', type=Path, help='Optional keychain containing the signing identity')
    p.add_argument('--app-profile', required=True, type=Path)
    p.add_argument('--helper-profile', required=True, type=Path)
    args = p.parse_args()
    app = args.app.resolve()
    helper = app / 'PlugIns/MadeiraJITHelper.appex'
    pairs = [(app, args.app_profile), (helper, args.helper_profile)]
    entitlements = [profile_entitlements(b, f) for b, f in pairs]
    if entitlements[0]['application-identifier'].split('.')[0] != entitlements[1]['application-identifier'].split('.')[0]:
        raise ValueError('Main app and helper profiles must share an App ID prefix')
    with tempfile.TemporaryDirectory(prefix='ideck-resign-') as temp:
        def sign(path, entitlement=None):
            cmd = ['codesign', '--force', '--sign', args.identity, '--timestamp=none']
            if args.keychain:
                cmd += ['--keychain', str(args.keychain)]
            if entitlement is not None:
                dest = Path(temp) / (path.name + '.plist')
                dest.write_bytes(plistlib.dumps(entitlement))
                cmd += ['--entitlements', str(dest)]
            run(*cmd, str(path))
        for bundle, profile in pairs:
            shutil.copyfile(profile, bundle / 'embedded.mobileprovision')
        for path in sorted(app.rglob('*.dylib')):
            sign(path)
        for path in sorted(app.rglob('*.framework'), key=lambda x: len(x.parts), reverse=True):
            sign(path)
        sign(helper, entitlements[1])
        sign(app, entitlements[0])
        run('codesign', '--verify', '--deep', '--strict', str(app))
    print('Local signing verified. Installation, JIT and Steam still need device testing.')


if __name__ == '__main__':
    main()
