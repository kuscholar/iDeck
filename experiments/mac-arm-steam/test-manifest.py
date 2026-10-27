#!/usr/bin/env python3
"""Offline checks for official manifest parsing and package path/hash gates."""
from pathlib import Path
import importlib.util
import unittest
path = Path(__file__).resolve().parents[2] / 'scripts/experiments/fetch-mac-steam.py'
spec = importlib.util.spec_from_file_location('fetch_mac', path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class ManifestTests(unittest.TestCase):
    def test_nested_variants(self):
        obj = mod.parse_vdf('"osx" { "version" "123" "steam_osx" { "file" "default" "variant" { "file" "other" } } }')
        self.assertEqual(obj['osx']['steam_osx']['file'], 'default')
        self.assertEqual(obj['osx']['steam_osx']['variant']['file'], 'other')
    def test_truncated_or_duplicate(self):
        for text in ['"osx" { "x" "y"', '"osx" { "x" }', '}', '"x" "y" "x" "z"']:
            with self.assertRaises(ValueError): mod.parse_vdf(text)
    def test_package_checks(self):
        item = {'file': 'steam_osx.zip.' + 'a'*40, 'size': '100', 'sha2': 'b'*64}
        self.assertEqual(mod.validate_package(item)[2], 100)
        for key, value in [('file','../steam.zip.'+'a'*40),('file','https://example.com/x'),('sha2','bad'),('size','0'),('size',str(2**31))]:
            with self.assertRaises(ValueError): mod.validate_package(dict(item, **{key:value}))

unittest.main()
