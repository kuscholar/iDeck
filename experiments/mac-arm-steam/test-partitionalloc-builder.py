#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Madeira Converter Exception: see LICENSE-EXCEPTION.md
"""Source trust-boundary checks; optional real public-source fixture, no device."""
import importlib.util, json, os, pathlib, shutil, tempfile, unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('builder', REPO/'scripts/experiments/build-partitionalloc-probe.py')
builder = importlib.util.module_from_spec(spec); spec.loader.exec_module(builder)

class BoundaryTests(unittest.TestCase):
    def test_unknown_receipt_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root=pathlib.Path(folder); (root/'source-receipt.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'Wrong source receipt'): builder.verify(root)

    def test_optional_source_tamper(self):
        value=os.environ.get('IDECK_PA126_SOURCE')
        if not value: self.skipTest('Provide verified private public-source checkout for tamper test')
        source=pathlib.Path(value).resolve(); builder.verify(source)
        with tempfile.TemporaryDirectory() as folder:
            root=pathlib.Path(folder)
            receipt=(source/'source-receipt.json').read_bytes(); (root/'source-receipt.json').write_bytes(receipt)
            names=[x['path'] for x in json.loads(receipt)['files']]+list(builder.HEADERS)+['LICENSE']
            for name in names:
                dest=root/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source/name,dest)
            builder.verify(root)
            target=root/'partition_alloc/partition_address_space.cc'
            original=target.read_bytes();target.write_bytes(original+b'\n// changed\n')
            with self.assertRaisesRegex(ValueError,'Modified Chromium source'): builder.verify(root)
            target.write_bytes(original); (root/'build/build_config.h').write_text('// changed')
            with self.assertRaisesRegex(ValueError,'Modified build header'): builder.verify(root)
            shutil.copyfile(source/'build/build_config.h',root/'build/build_config.h')
            target.unlink();target.symlink_to(source/'partition_alloc/partition_address_space.cc')
            with self.assertRaisesRegex(ValueError,'Unsafe source'): builder.verify(root)

if __name__=='__main__': unittest.main()
