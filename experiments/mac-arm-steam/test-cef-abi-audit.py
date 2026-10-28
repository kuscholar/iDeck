# SPDX-License-Identifier: GPL-3.0-or-later
"""Synthetic non-executable Mach-O: positive getters and fail-closed boundaries."""
import importlib.util
from pathlib import Path
import struct
import unittest
import tempfile
p=Path(__file__).resolve().parents[2]/'scripts/experiments/audit-mac-cef-abi.py'
s=importlib.util.spec_from_file_location('abi',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def fixture():
    data=bytearray(0x2000);struct.pack_into('<8I',data,0,0xfeedfacf,0x100000c,0,6,1,72,0,0)
    struct.pack_into('<II16sQQQQIIII',data,32,0x19,72,b'__TEXT',0,0x2000,0,0x2000,7,5,0,0)
    for address,maximum,stride,table in [(0x400,7,4,0x1100),(0x500,2,8,0x1200)]:
        words=[0x7100001f|maximum<<10,0x54000069,0x52800000 if stride==4 else 0xd2800000,0xd65f03c0,0xb0000008,0x91000108|((table&4095)<<10),0xb860d900 if stride==4 else 0xf860d900,0xd65f03c0]
        struct.pack_into('<8I',data,address,*words)
    struct.pack_into('<8I',data,0x1100,126,0,0,3171,126,0,6478,183)
    struct.pack_into('<3Q',data,0x1200,0x1300,0x1340,0x1380)
    for pos,letter in [(0x1300,b'a'),(0x1340,b'b'),(0x1380,b'c')]:data[pos:pos+41]=letter*40+b'\0'
    return data
class Tests(unittest.TestCase):
    def test_literals(self):
        version,api=m.extract_public_metadata(m.MachO(fixture()),0x400,0x500)
        self.assertEqual(version['chromeBuild'],6478);self.assertEqual(api['cefCommit'],'c'*40)
    def test_unknown_getter_rejected(self):
        data=fixture();struct.pack_into('<I',data,0x410,0xd503201f)
        with self.assertRaises(ValueError):m.extract_public_metadata(m.MachO(data),0x400,0x500)
    def test_encoded_or_unbacked_pointer_rejected(self):
        data=fixture();struct.pack_into('<Q',data,0x1200,0x1000000000001300)
        with self.assertRaises(ValueError):m.extract_public_metadata(m.MachO(data),0x400,0x500)
    def test_malformed_hash_rejected(self):
        data=fixture();data[0x1300]=ord('z')
        with self.assertRaises(ValueError):m.extract_public_metadata(m.MachO(data),0x400,0x500)
    def test_output_preserves_unrelated_file_and_symlink(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'protected';p.write_bytes(b'preserve binary input')
            with self.assertRaises(ValueError):m.write_report(p,{'mode':'static read-only; CEF not initialized'})
            self.assertEqual(p.read_bytes(),b'preserve binary input')
            link=Path(folder)/'link';link.symlink_to(p)
            with self.assertRaises(ValueError):m.write_report(link,{})
    def test_truncated_commands_rejected(self):
        data=fixture();struct.pack_into('<I',data,20,8)
        with self.assertRaises(ValueError):m.MachO(data)
unittest.main()
