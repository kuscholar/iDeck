#!/usr/bin/env python3
"""Reproduce the public shim's advertised path without Valve code or device."""
import importlib.util
from pathlib import Path
import plistlib
import tempfile
import unittest
path = Path(__file__).resolve().parents[2] / 'scripts/experiments/fix-mac-executable-layout.py'
spec = importlib.util.spec_from_file_location('layout', path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class LayoutTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.app = Path(self.temp.name).resolve() / 'Converted.app'
        (self.app / 'Mac/Contents/MacOS').mkdir(parents=True)
        (self.app/'Info.plist').write_bytes(plistlib.dumps({'SHIMMacRoot':'Mac','CFBundleExecutable':'program'}))
        (self.app/'program').write_bytes(b'synthetic-probe')
    def test_missing_then_resolved(self):
        logical = self.app/'Mac/Contents/MacOS/program'
        with self.assertRaises(FileNotFoundError): logical.resolve(strict=True)
        self.assertTrue(mod.fix_layout(self.app))
        self.assertEqual(logical.resolve(strict=True),self.app/'program')
        self.assertFalse(mod.fix_layout(self.app))
    def test_preserve_conflicting_file_and_link(self):
        logical = self.app/'Mac/Contents/MacOS/program'
        logical.write_bytes(b'preserve')
        with self.assertRaises(ValueError): mod.fix_layout(self.app)
        self.assertEqual(logical.read_bytes(),b'preserve')
        logical.unlink(); logical.symlink_to('/outside')
        with self.assertRaises(ValueError): mod.fix_layout(self.app)
        self.assertEqual(str(logical.readlink()),'/outside')
    def test_framework_alias(self):
        frameworks=self.app/'Mac/Contents/Frameworks';frameworks.mkdir()
        (frameworks/'library').write_bytes(b'framework')
        self.assertTrue(mod.fix_layout(self.app))
        self.assertEqual((self.app/'Mac/Contents/MacOS/Frameworks/library').read_bytes(),b'framework')
        self.assertFalse(mod.fix_layout(self.app))
    def test_preserve_framework_alias_conflict(self):
        (self.app/'Mac/Contents/Frameworks').mkdir()
        alias=self.app/'Mac/Contents/MacOS/Frameworks';alias.symlink_to('/outside')
        with self.assertRaises(ValueError): mod.fix_layout(self.app)
        self.assertEqual(str(alias.readlink()),'/outside')
    def test_reject_framework_target_escape(self):
        (self.app/'Mac/Contents/Frameworks').symlink_to('/outside')
        with self.assertRaises(ValueError): mod.fix_layout(self.app)
    def test_reject_parent_link(self):
        parent = self.app/'Mac/Contents/MacOS'; parent.rmdir(); parent.symlink_to(self.app)
        with self.assertRaises(ValueError): mod.fix_layout(self.app)

unittest.main()
