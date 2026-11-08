#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest

class Overlay(unittest.TestCase):
    def test_guest_directory_metadata_and_exact_binary(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); block = 'bins_linuxarm64_linuxarm64'
            component = root/'parts'/block/'steamrtarm64'
            component.mkdir(parents=True)
            payload = b'\x7fELFexact fixture bytes'
            (component/'steam').write_bytes(payload)
            manifest = root/'manifest'
            manifest.write_text('"%s" {"file" "bins.zip.abc" "sha2" "%s" "size" "1"}' % (block,'0'*64))
            output = root/'overlay.tar.gz'
            subprocess.run([sys.executable,str(Path(__file__).parents[1]/'tools/make-steam-overlay.py'),str(manifest),str(root/'parts'),str(output)],check=True,capture_output=True)
            with tarfile.open(output) as t:
                self.assertTrue(t.getmember('Steam').isdir())
                self.assertTrue(t.getmember('Steam/steamrtarm64').isdir())
                self.assertEqual(t.extractfile('Steam/steamrtarm64/steam').read(),payload)
                self.assertEqual(t.getmember('Steam/steamrtarm64/steam').mode,0o755)
                self.assertEqual(t.extractfile('Steam/package/beta').read(),b'steamdeck_stable\n')
                self.assertEqual(t.getmember('root/.steam/steam').linkname,'/Steam')

if __name__ == '__main__': unittest.main()
