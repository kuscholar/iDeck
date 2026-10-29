#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Madeira Converter Exception: see LICENSE-EXCEPTION.md
"""Real own-source fixture: instruction and fixup ordinals, guard failures, dyld.
No Valve binary or device needed. Temporary own binaries are removed afterward.
"""
import hashlib,importlib.util,json,struct,subprocess,tempfile,unittest
from pathlib import Path
REPO=Path(__file__).resolve().parents[2];spec=importlib.util.spec_from_file_location('bundle',REPO/'scripts/experiments/make-synthetic-helper-bundle.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
def segments(b):
 out=[];off=32
 for _ in range(struct.unpack_from('<I',b,16)[0]):
  c,n=struct.unpack_from('<II',b,off)
  if c==0x19:out.append(b[off+8:off+24].rstrip(b'\0'))
  off+=n
 return out
class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory(prefix='ideck-own-bundle-');cls.root=Path(cls.temp.name);cls.binary=cls.root/'fixture'
  subprocess.run(['xcrun','clang','-target','arm64-apple-macos14','-Wl,-exported_symbol,_IDeckFixtureRead','-Wl,-exported_symbol,_IDeckFixtureMarker','-Wl,-exported_symbol,_main',str(REPO/'experiments/mac-arm-steam/synthetic-helper-fixture.c'),'-o',str(cls.binary)],check=True)
  cls.data=cls.binary.read_bytes();cls.sha=hashlib.sha256(cls.data).hexdigest()
 @classmethod
 def tearDownClass(cls):cls.temp.cleanup()
 def test_payload_and_fixup_segment_ordinals(self):
  out,r=mod.transform(self.data,self.sha);self.assertEqual(out[32+struct.unpack_from('<I',self.data,20)[0]:],self.data[32+struct.unpack_from('<I',self.data,20)[0]:]);self.assertEqual(segments(out),segments(self.data));self.assertTrue(r['metadataOnly']);self.assertEqual(struct.unpack_from('<I',out,12)[0],8)
 def test_bad_digest(self):
  with self.assertRaises(ValueError):mod.transform(self.data,'0'*64)
 def test_missing_unique_own_marker(self):
  b=self.data.replace(mod.MARKER,b'X'*len(mod.MARKER))
  with self.assertRaises(ValueError):mod.transform(b,hashlib.sha256(b).hexdigest())
 def test_corrupt_command_bounds(self):
  b=bytearray(self.data);struct.pack_into('<I',b,20,len(b))
  with self.assertRaises(ValueError):mod.transform(bytes(b),hashlib.sha256(b).hexdigest())
 def test_sidecar_preserved(self):
  target=self.root/'must-not-create.bundle';side=target.with_suffix('.bundle.json');side.write_text('preserve')
  r=subprocess.run(['python3',str(REPO/'scripts/experiments/make-synthetic-helper-bundle.py'),'--input',str(self.binary),'--expected-sha256',self.sha,'--output',str(target)],capture_output=True,text=True);self.assertNotEqual(r.returncode,0);self.assertFalse(target.exists());self.assertEqual(side.read_text(),'preserve')
 def test_signed_host_constructor_without_main(self):
  out,_=mod.transform(self.data,self.sha);p=self.root/'own.bundle';p.write_bytes(out);subprocess.run(['codesign','--force','--sign','-',str(p)],check=True,capture_output=True)
  runner=self.root/'runner';subprocess.run(['xcrun','clang','-target','arm64-apple-macos14',str(REPO/'experiments/mac-arm-steam/test-synthetic-helper-host.c'),'-o',str(runner)],check=True)
  r=subprocess.run([str(runner),str(self.binary),str(p)],capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr);self.assertIn('constructor1/main0',r.stdout)
if __name__=='__main__':unittest.main()
