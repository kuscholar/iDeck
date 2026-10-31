# SPDX-License-Identifier: GPL-3.0-or-later
# Madeira Converter Exception: see LICENSE-EXCEPTION.md
import importlib.util
from pathlib import Path
import unittest
import tempfile

p = Path(__file__).resolve().parents[2]/'scripts/experiments/audit-cef-source-surface.py'
spec = importlib.util.spec_from_file_location('surface', p)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class Tests(unittest.TestCase):
    def report(self):
        return {'mode':'static read-only; CEF not initialized', 'version':{'cefMajor':126},
                'publicABIIdentifiers':{'platform':'a'*40, 'universal':'b'*40}}
    def test_matching_surface_is_not_semantics(self):
        x = m.compare(self.report(), {'mac':'a'*40,'universal':'b'*40}, m.loader.CUSTOM)
        self.assertTrue(x['surfaceGatePasses'])
    def test_matching_hash_without_extension_refused(self):
        x = m.compare(self.report(), {'mac':'a'*40,'universal':'b'*40}, m.loader.CUSTOM[1:])
        self.assertFalse(x['surfaceGatePasses']);self.assertEqual(x['missingRequiredDeclarations'], [m.loader.CUSTOM[0]])
    def test_universal_mismatch_refused(self):
        self.assertFalse(m.compare(self.report(), {'mac':'a'*40,'universal':'c'*40}, m.loader.CUSTOM)['surfaceGatePasses'])
    def test_platform_mismatch_refused(self):
        self.assertFalse(m.compare(self.report(), {'mac':'c'*40,'universal':'b'*40}, m.loader.CUSTOM)['surfaceGatePasses'])
    def test_unknown_metadata_refused(self):
        a=self.report();a['version']['cefMajor']=127
        with self.assertRaises(ValueError):m.compare(a,{},[])
    def test_non_hash_payload_refused(self):
        a=self.report();a['publicABIIdentifiers']['platform']='not a fingerprint'
        with self.assertRaises(ValueError):m.compare(a,{'mac':'a'*40,'universal':'b'*40},[])
    def test_unreviewed_module_is_not_executed(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'include').mkdir();(root/'tools').mkdir()
            (root/'include/test.h').write_text('CEF_EXPORT int cef_example(void);')
            sentinel=root/'MUST_NOT_EXECUTE'
            (root/'tools/cef_api_hash.py').write_text('from pathlib import Path\nPath('+repr(str(sentinel))+').touch()')
            with self.assertRaisesRegex(ValueError,'source review'):m.calculate(root)
            self.assertFalse(sentinel.exists())
    def test_header_symlink_is_not_read(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'include').mkdir();target=root/'unrelated'
            target.write_text('preserve unrelated data')
            (root/'include/test.h').symlink_to(target)
            with self.assertRaisesRegex(ValueError,'symlink'):m.calculate(root)
            self.assertEqual(target.read_text(),'preserve unrelated data')
    def test_oversized_header_is_refused_before_loading(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'include').mkdir()
            with (root/'include/large.h').open('wb') as stream:
                stream.truncate(32*1024*1024+1)
            with self.assertRaisesRegex(ValueError,'budget'):m.calculate(root)


unittest.main()
