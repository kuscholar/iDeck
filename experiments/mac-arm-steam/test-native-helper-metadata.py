#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Madeira Converter Exception: see LICENSE-EXCEPTION.md
# Synthetic bytes only: no Valve payload needed to test fail-closed contracts.
import hashlib,importlib.util,struct,unittest
from pathlib import Path
p=Path(__file__).resolve().parents[2]/'scripts/experiments/prepare-native-steam-helper-bundle.py';s=importlib.util.spec_from_file_location('native',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def fixture():
 commands=[];names=['__PAGEZERO','__TEXT','__DATA_CONST','__DATA','__LINKEDIT']
 for name in names:
  ns=int(name=='__TEXT');raw=bytearray(72+80*ns);struct.pack_into('<II16sQQQQIIII',raw,0,0x19,len(raw),name.encode(),0 if name=='__PAGEZERO' else 0x100000000,0x100000000 if name=='__PAGEZERO' else 4096,0,0 if name=='__PAGEZERO' else 4096,0 if name=='__PAGEZERO' else 5,0 if name=='__PAGEZERO' else 5,ns,0)
  if ns:struct.pack_into('<16s16sQQI',raw,72,b'__text',b'__TEXT',0x100000800,4,2048)
  commands.append(bytes(raw))
 commands+=[struct.pack('<12I',0x80000022,48,0,0,0,0,0,0,0,0,0,0),struct.pack('<IIQQ',0x80000028,24,2048,0),struct.pack('<II8s',0xe,16,b'dyld\0\0\0\0')]
 joined=b''.join(commands);b=bytearray(4096);struct.pack_into('<8I',b,0,0xfeedfacf,0x100000c,0,2,len(commands),len(joined),0x200000,0);b[32:32+len(joined)]=joined;b[2048:2052]=b'CODE';return bytes(b)
class Tests(unittest.TestCase):
 def test_metadata_payload_and_indices(self):
  b=fixture();out,r=m.adapt_metadata(b,hashlib.sha256(b).hexdigest());end=r['originalCommandEnd'];self.assertEqual(out[end:],b[end:]);self.assertEqual(struct.unpack_from('<I',out,12)[0],8);self.assertTrue(r['dyldInfoStreamsUnchanged']);self.assertEqual(len(r['segmentsPreserved']),5)
 def test_production_hash_refuses_fixture(self):
  with self.assertRaises(ValueError):m.adapt_metadata(fixture())
 def test_bad_command_bounds(self):
  b=bytearray(fixture());struct.pack_into('<I',b,20,99999)
  with self.assertRaises(ValueError):m.adapt_metadata(bytes(b),hashlib.sha256(b).hexdigest())
 def test_changed_segment_contract(self):
  b=fixture().replace(b'__DATA_CONST',b'__DATA_OTHER')
  with self.assertRaises(ValueError):m.adapt_metadata(b,hashlib.sha256(b).hexdigest())
 def test_unbacked_bind_stream(self):
  b=bytearray(fixture());off=32
  for _ in range(struct.unpack_from('<I',b,16)[0]):
   c,n=struct.unpack_from('<II',b,off)
   if c==0x80000022:struct.pack_into('<II',b,off+8,4094,100)
   off+=n
  with self.assertRaises(ValueError):m.adapt_metadata(bytes(b),hashlib.sha256(b).hexdigest())
if __name__=='__main__':unittest.main()
