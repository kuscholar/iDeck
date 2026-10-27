#!/usr/bin/env python3
"""Offline archive boundary tests. Does not contain Valve content."""
from pathlib import Path
import importlib.util
import tempfile
import unittest
path = Path(__file__).resolve().parents[2] / 'scripts/experiments/stage-mac-steam.py'
spec = importlib.util.spec_from_file_location('stage_mac', path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class StageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'out'
        self.root.mkdir()
    def test_traversal(self):
        for name in ['../x', '/x', 'a/../../x', '..\\x']:
            with self.assertRaises(ValueError): mod.safe_path(self.root, name)
    def test_symlink_escape(self):
        (self.root / 'link').symlink_to(self.root.parent)
        with self.assertRaises(ValueError): mod.safe_path(self.root, 'link/escape')
        with self.assertRaises(ValueError): mod.write_entry(self.root, 'outside', link='../../outside')
    def test_internal_framework_link(self):
        mod.write_entry(self.root, 'Contents/MacOS/library', data=b'library')
        mod.write_entry(self.root, 'Contents/Frameworks/Helper/link', link='../../MacOS/library')
        self.assertEqual((self.root/'Contents/Frameworks/Helper/link').read_bytes(), b'library')
    def test_macho_mode(self):
        mod.write_entry(self.root, 'program', data=b'\xcf\xfa\xed\xfe' + b'test')
        self.assertEqual((self.root/'program').stat().st_mode & 0o777, 0o755)

unittest.main()
