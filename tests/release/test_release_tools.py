import importlib.util
import plistlib
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('audit_ipa', ROOT / 'tools/audit-ipa.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class PackageChecks(unittest.TestCase):
    def package(self, extras):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        path = Path(temp.name) / 'test.ipa'
        with zipfile.ZipFile(path, 'w') as z:
            z.writestr('Payload/Test.app/Info.plist', plistlib.dumps({
                'CFBundleIdentifier': 'test.example', 'CFBundleVersion': '1'}))
            for name, data in extras:
                z.writestr(name, data)
        return path

    def test_inventory_hashes_contents(self):
        report = audit.audit(self.package([('Payload/Test.app/data', b'abc')]))
        self.assertEqual(report['findings'], [])
        self.assertEqual(report['files'][1]['sha256'],
                         'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad')

    def test_profile_and_valve_payload_are_flagged(self):
        result = audit.audit(self.package([
            ('Payload/Test.app/embedded.mobileprovision', b'profile'),
            ('Payload/Test.app/Steam/steam.exe', b'payload')]))
        self.assertEqual(len(result['findings']), 2)

    def test_traversal_is_flagged_without_extraction(self):
        result = audit.audit(self.package([('../escaped', b'bad')]))
        self.assertEqual(result['findings'][0]['reason'], 'unsafe archive path')

    def test_multiple_apps_rejected(self):
        with self.assertRaises(ValueError):
            audit.audit(self.package([('Payload/Other.app/Info.plist', b'bad')]))

    def test_adhoc_resources_can_be_explicitly_allowed(self):
        path = self.package([('Payload/Test.app/_CodeSignature/CodeResources', b'resources')])
        self.assertTrue(audit.audit(path)['findings'])
        self.assertEqual(audit.audit(path, allow_signature_resources=True)['findings'], [])

    def test_allowing_signature_resources_still_rejects_profiles(self):
        path = self.package([('Payload/Test.app/embedded.mobileprovision', b'profile')])
        self.assertTrue(audit.audit(path, allow_signature_resources=True)['findings'])


if __name__ == '__main__':
    unittest.main()
