#!/usr/bin/env python3
"""Refresh Xcode-managed profiles, re-sign a disposable app, optionally upgrade it.

Uses an existing Xcode account and keychain identity; never enters credentials,
changes keychain settings, uninstalls apps, launches Steam, or schedules a job.
Keep --work-dir outside the source checkout: it contains private signing assets.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import plistlib
import subprocess
import sys
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parents[1]


def eligible(profile, bundle, team, device, identity, until):
    e = profile.get('Entitlements', {})
    expiry = profile.get('ExpirationDate', dt.datetime.min)
    expiry = expiry.replace(tzinfo=dt.timezone.utc) if expiry.tzinfo is None else expiry
    return (e.get('application-identifier', '').split('.', 1)[-1] == bundle
            and team in profile.get('TeamIdentifier', [])
            and device in profile.get('ProvisionedDevices', [])
            and e.get('get-task-allow') is True
            and expiry > until
            and identity.upper() in [hashlib.sha1(c).hexdigest().upper()
                                     for c in profile.get('DeveloperCertificates', [])])


def select_profiles(profiles, bundles, team, device, identity, until):
    """Choose an exact, compatible main/helper pair; never wildcard or other device."""
    candidates = [[(path, p) for path, p in profiles
                   if eligible(p, b, team, device, identity, until)] for b in bundles]
    pairs = [(a, b) for a in candidates[0] for b in candidates[1]
             if a[1]['Entitlements']['application-identifier'].split('.')[0]
             == b[1]['Entitlements']['application-identifier'].split('.')[0]]
    if not pairs:
        return None
    return max(pairs, key=lambda pair: min(p['ExpirationDate'] for _, p in pair))


def cached_profiles():
    profiles = []
    for directory in ('Library/Developer/Xcode/UserData/Provisioning Profiles',
                      'Library/MobileDevice/Provisioning Profiles'):
        for path in (Path.home() / directory).glob('*.mobileprovision'):
            r = subprocess.run(['security', 'cms', '-D', '-i', str(path)],
                               capture_output=True)
            if r.returncode == 0:
                try:
                    profiles.append((path, plistlib.loads(r.stdout)))
                except (ValueError, plistlib.InvalidFileException):
                    pass
    return profiles


def assert_idle(apps, processes, bundle):
    matches = [a for a in apps if a.get('bundleIdentifier') == bundle]
    if len(matches) != 1:
        raise RuntimeError('Upgrade requires one existing matching app; no uninstall/first install performed')
    path = unquote(urlparse(matches[0]['url']).path).rstrip('/') + '/'
    if not path.startswith('/private/var/containers/Bundle/Application/'):
        raise RuntimeError('Unrecognized installed app path; refusing upgrade')
    if any(p.get('executable', '').startswith(path) for p in processes):
        raise RuntimeError('The app/helper is running; save and close it before installation')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app', required=True, type=Path, help='Prepared, resource-complete .app; never modified')
    parser.add_argument('--device', required=True, help='Physical device UDID, not its display name')
    parser.add_argument('--team', required=True)
    parser.add_argument('--identity', required=True, help='Existing certificate SHA-1 fingerprint')
    parser.add_argument('--keychain', type=Path, default=Path.home() / 'Library/Keychains/login.keychain-db')
    parser.add_argument('--project', type=Path, default=ROOT / 'app/Madeira.xcodeproj')
    parser.add_argument('--work-dir', required=True, type=Path)
    parser.add_argument('--derived-data', type=Path)
    parser.add_argument('--check-only', action='store_true', help='Read-only profile check; no renewal/sign/install')
    parser.add_argument('--install', action='store_true', help='Upgrade the idle existing app; no launch')
    args = parser.parse_args()
    if args.check_only and args.install:
        parser.error('--check-only cannot be combined with --install')
    app = args.app.resolve()
    info = plistlib.loads((app / 'Info.plist').read_bytes())
    helper = plistlib.loads((app / 'PlugIns/MadeiraJITHelper.appex/Info.plist').read_bytes())
    bundle = info['CFBundleIdentifier']
    if helper['CFBundleIdentifier'] != bundle + '.JITHelper':
        raise RuntimeError('Unexpected helper bundle identifier')
    def select():
        return select_profiles(cached_profiles(), (bundle, bundle + '.JITHelper'),
                               args.team, args.device, args.identity,
                               dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=10))

    pair = select()
    if args.check_only:
        print('Main/helper exact bundle, team, device, certificate and expiry: '
              + ('PASS' if pair else 'MISSING OR INVALID'))
        return 0 if pair else 2

    work = args.work_dir.resolve()
    if work == ROOT or ROOT in work.parents or work == app or app in work.parents:
        raise RuntimeError('Private work directory must be outside source checkout and input app')
    os.umask(0o077)
    run = work / dt.datetime.now(dt.timezone.utc).strftime('sign-%Y%m%dT%H%M%S-%fZ')
    run.mkdir(parents=True, mode=0o700)
    if pair is None:
        cmd = ['xcodebuild', '-project', str(args.project.resolve()), '-scheme', 'Madeira',
               '-configuration', 'Debug', '-destination', 'id=' + args.device,
               '-derivedDataPath', str(args.derived_data or run / 'DerivedData'),
               '-allowProvisioningUpdates', '-allowProvisioningDeviceRegistration',
               'CODE_SIGNING_ALLOWED=YES', 'CODE_SIGN_STYLE=Automatic',
               'DEVELOPMENT_TEAM=' + args.team, 'MADEIRA_BUNDLE_IDENTIFIER=' + bundle,
               'CURRENT_PROJECT_VERSION=' + info['CFBundleVersion'], 'build']
        log = run / 'provisioning.log'
        print('Requesting profiles through Xcode once; private log:', log, flush=True)
        with log.open('wb') as output:
            result = subprocess.run(cmd, stdout=output, stderr=subprocess.STDOUT)
        pair = select()
        if pair is None:
            raise RuntimeError('Xcode returned %d; no valid main/helper profiles for this device. '
                               'Inspect Xcode account/provisioning UI and private log. '
                               'No Accounts alone does not prove logout. No signing/install performed.'
                               % result.returncode)

    # Verify private-key access without changing the original app or keychain.
    subprocess.run(['codesign', '--dryrun', '--force', '--sign', args.identity,
                    '--keychain', str(args.keychain), str(app)], check=True)
    signed = run / app.name
    subprocess.run(['cp', '-cR', str(app), str(signed)], check=True)
    subprocess.run([sys.executable, str(ROOT / 'tools/resign-app.py'), str(signed),
                    '--identity', args.identity, '--keychain', str(args.keychain),
                    '--app-profile', str(pair[0][0]), '--helper-profile', str(pair[1][0])], check=True)
    subprocess.run(['codesign', '--verify', '--deep', '--strict', str(signed)], check=True)
    receipt = {'bundle': bundle, 'build': info['CFBundleVersion'], 'signed_app': str(signed),
               'profile_expiry_utc': [p['ExpirationDate'].isoformat() for _, p in pair],
               'deep_strict_signature': True, 'installed': False, 'runtime_tested': False}
    receipt_path = run / 'receipt.json'
    receipt_path.write_text(json.dumps(receipt, indent=2) + '\n')

    def device_json(arguments, filename):
        path = run / filename
        subprocess.run(['xcrun', 'devicectl', 'device', *arguments, '--device', args.device,
                        '--timeout', '30', '--json-output', str(path)], check=True,
                       stdout=subprocess.DEVNULL)
        return json.loads(path.read_text())['result']

    if args.install:
        apps = device_json(['info', 'apps', '--bundle-id', bundle], 'before-app.json')['apps']
        processes = device_json(['info', 'processes'], 'before-processes.json')['runningProcesses']
        assert_idle(apps, processes, bundle)
        device_json(['install', 'app', str(signed)], 'install.json')
        after = device_json(['info', 'apps', '--bundle-id', bundle], 'after-app.json')['apps']
        if len(after) != 1 or after[0].get('bundleVersion') != info['CFBundleVersion']:
            raise RuntimeError('Installed version verification failed; inspect private receipts')
        receipt['installed'] = True
        receipt_path.write_text(json.dumps(receipt, indent=2) + '\n')
    print('Receipt:', receipt_path)
    print('Signing' + (' and installation' if receipt['installed'] else '')
          + ' verified. JIT/Steam/gameplay are not tested by this script.')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (RuntimeError, OSError, ValueError, subprocess.CalledProcessError) as error:
        print('STOP:', error, file=sys.stderr)
        sys.exit(1)
