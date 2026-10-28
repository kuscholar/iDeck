#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Madeira Converter Exception: see LICENSE-EXCEPTION.md
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest
path=Path(__file__).resolve().parents[2]/'scripts/experiments/build-mac-process-observer.py'
spec=importlib.util.spec_from_file_location('builder',path);builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
def fixture():
    name=b'@loader_path/libtier0_s.dylib\0';ds=(24+len(name)+7)&~7
    dylib=struct.pack('<6I',0xc,ds,24,0,0,0)+name+b'\0'*(ds-24-len(name))
    segment=bytearray(152);struct.pack_into('<II16sQQQQIIII',segment,0,0x19,152,b'__TEXT',0,512,0,512,5,5,1,0)
    struct.pack_into('<16s16sQQI',segment,72,b'__text',b'__TEXT',500,4,500)
    h=struct.pack('<8I',0xfeedfacf,0x100000c,0,6,2,152+ds,0,0)
    b=bytearray(512);b[:len(h+segment+dylib)]=h+segment+dylib;b[500:504]=b'CODE';return b
class Tests(unittest.TestCase):
    def run_bytes(self,b):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'fixture';p.write_bytes(b);return builder.inspect(p)
    def test_exact(self):
        r=self.run_bytes(fixture());self.assertEqual(r['dependencies'],['@loader_path/libtier0_s.dylib']);self.assertEqual(len(r['textSha256']),64)
    def test_instruction_hash_discriminates(self):
        a=fixture();b=fixture();b[500]=90;self.assertNotEqual(self.run_bytes(a)['textSha256'],self.run_bytes(b)['textSha256'])
    def test_unbacked_text(self):
        b=fixture();struct.pack_into('<I',b,32+72+48,511)
        with self.assertRaises(ValueError):self.run_bytes(b)
    def test_bad_command(self):
        b=fixture();struct.pack_into('<I',b,36,9999)
        with self.assertRaises(ValueError):self.run_bytes(b)
    def test_other_arch_skipped(self):self.assertIsNone(self.run_bytes(b'not-arm64'))
if __name__=='__main__':unittest.main()
