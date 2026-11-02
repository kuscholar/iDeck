#!/usr/bin/env python3
"""Test profile/device/identity isolation and refusal to replace a running app.

Synthetic fixtures only: not an Apple renewal, signature or installation test.
"""
import copy
import datetime as dt
import hashlib
import importlib.util
from pathlib import Path
import plistlib
import sys
import tempfile
from unittest.mock import patch

root = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('refresh_signing', root / 'tools/refresh-development-signing.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
now = dt.datetime(2026, 10, 30, tzinfo=dt.timezone.utc)
identity = hashlib.sha1(b'certificate').hexdigest()


def profile(bundle):
    return {'Entitlements': {'application-identifier': 'PREFIX.' + bundle, 'get-task-allow': True},
            'TeamIdentifier': ['TEAM'], 'ProvisionedDevices': ['PHONE'],
            'DeveloperCertificates': [b'certificate'], 'ExpirationDate': now + dt.timedelta(days=1)}


a, b = profile('app'), profile('app.JITHelper')


def select(p, q):
    return m.select_profiles([('main', p), ('helper', q)], ('app', 'app.JITHelper'),
                             'TEAM', 'PHONE', identity, now)


assert select(a, b)
newer = copy.deepcopy(b)
newer['ExpirationDate'] += dt.timedelta(days=2)
long_main = copy.deepcopy(a)
long_main['ExpirationDate'] += dt.timedelta(days=4)
assert m.select_profiles([('main', long_main), ('old', b), ('new', newer)],
                         ('app', 'app.JITHelper'), 'TEAM', 'PHONE', identity, now)[1][0] == 'new'
newer['ProvisionedDevices'] = ['IPAD']
assert m.select_profiles([('main', long_main), ('old', b), ('new', newer)],
                         ('app', 'app.JITHelper'), 'TEAM', 'PHONE', identity, now)[1][0] == 'old'
for field, bad in [('ProvisionedDevices', ['IPAD']), ('TeamIdentifier', ['OTHER']),
                   ('ExpirationDate', now), ('DeveloperCertificates', [b'other'])]:
    p = copy.deepcopy(b)
    p[field] = bad
    assert select(a, p) is None, field
for value in ['PREFIX.*', 'PREFIX.other.JITHelper', 'OTHER.app.JITHelper']:
    p = copy.deepcopy(b)
    p['Entitlements']['application-identifier'] = value
    assert select(a, p) is None, value
p = copy.deepcopy(b)
p['Entitlements']['get-task-allow'] = False
assert select(a, p) is None
path = '/private/var/containers/Bundle/Application/UUID/Madeira.app/'
apps = [{'bundleIdentifier': 'app', 'url': 'file://' + path}]
m.assert_idle(apps, [], 'app')
for candidates, processes in [([], []), (apps + apps, []),
                              (apps, [{'executable': path + 'Madeira'}]),
                              (apps, [{'executable': path + 'PlugIns/helper'}])]:
    try:
        m.assert_idle(candidates, processes, 'app')
    except RuntimeError:
        pass
    else:
        raise AssertionError('Unsafe upgrade accepted')

with tempfile.TemporaryDirectory() as directory:
    directory = Path(directory)
    app = directory / 'Madeira.app'
    helper = app / 'PlugIns/MadeiraJITHelper.appex'
    helper.mkdir(parents=True)
    (app / 'Info.plist').write_bytes(plistlib.dumps({'CFBundleIdentifier': 'app', 'CFBundleVersion': '115'}))
    (helper / 'Info.plist').write_bytes(plistlib.dumps({'CFBundleIdentifier': 'app.JITHelper'}))
    args = ['refresh', '--app', str(app), '--device', 'PHONE', '--team', 'TEAM',
            '--identity', identity, '--work-dir', str(directory / 'not-created'), '--check-only']
    aa, bb = copy.deepcopy(a), copy.deepcopy(b)
    for p in (aa, bb):
        p['ExpirationDate'] = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=1)
    with patch.object(sys, 'argv', args), patch.object(m, 'cached_profiles', return_value=[('a', aa), ('b', bb)]), \
            patch.object(m.subprocess, 'run', side_effect=AssertionError('Read-only check must not invoke tools')):
        assert m.main() == 0
        bb['ProvisionedDevices'] = ['IPAD']
        assert m.main() == 2
    assert not (directory / 'not-created').exists()
print('PASS: exact profiles, device, expiry, identity, prefix and active-app refusal (synthetic)')
