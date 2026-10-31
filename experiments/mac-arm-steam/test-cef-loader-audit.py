# SPDX-License-Identifier: GPL-3.0-or-later
# Madeira Converter Exception: see LICENSE-EXCEPTION.md
"""Synthetic, non-executed ARM64 loader blocks; no Valve fixture payload."""
import importlib.util
from pathlib import Path
import struct
import unittest

p = Path(__file__).resolve().parents[2]/'scripts/experiments/audit-mac-cef-loader.py'
spec = importlib.util.spec_from_file_location('loader_audit', p)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
BASE = 0x100000000


def branch(at, target, link=False):
    return (0x94000000 if link else 0x14000000) | (((target-at)//4) & 0x3ffffff)


def adrp(at, target, register):
    delta = ((target & ~4095)-(at & ~4095))//4096
    return 0x90000000 | ((delta & 3) << 29) | (((delta >> 2) & 0x7ffff) << 5) | register


def fixture():
    data = bytearray(0x4000)
    struct.pack_into('<8I', data, 0, 0xfeedfacf, 0x100000c, 0, 6, 1, 152, 0, 0)
    struct.pack_into('<II16sQQQQIIII', data, 32, 0x19, 152, b'__TEXT', BASE, len(data), 0, len(data), 7, 5, 1, 0)
    struct.pack_into('<16s16sQQIIIIIIII', data, 104, b'__text', b'__TEXT', BASE+0x400, 0x800, 0x400, 2, 0, 0, 0, 0, 0, 0)
    def put(at, ws): struct.pack_into('<'+'I'*len(ws), data, at, *ws)
    resolver = 0x800
    put(resolver, [0xd10143ff, 0xa9047bfd, 0x910103fd, 0xf81f83a0, 0xf81f03a1,
                   adrp(resolver+20, 0x3000, 8), 0xf9400100,
                   0xf85f03a1, branch(resolver+32, 0xa00, True), 0xf81e83a0,
                   0xf85e83a8, 0xb5000008 | (((0x850-(resolver+44))//4) << 5)])
    put(0x850, [0xf85e83a0, 0xa9447bfd, 0x910143ff, 0xd65f03c0])
    put(0x900, [0xb85fc3a0, 0xa9427bfd, 0x9100c3ff, 0xd65f03c0])
    for i, name in enumerate(m.CUSTOM):
        at = 0x400+i*0x40
        text = 0x1800+i*0x80
        data[text:text+len(name)+1] = name.encode()+b'\0'
        put(at, [0xf9400be0, adrp(at+4, text, 1), 0x91000021 | ((text & 4095) << 10),
                 branch(at+12, resolver, True), adrp(at+16, 0x3000, 8), 0x91000108,
                 0xf9000100 | (i << 10), 0xf9400108 | (i << 10),
                 0xb5000088, 0x14000001, 0xb81fc3bf, branch(at+44, 0x900)])
    return data


class Tests(unittest.TestCase):
    def check(self, data): return m.audit(m.abi.MachO(data), BASE+0xa00)
    def test_all_seven(self):
        result = self.check(fixture())
        self.assertEqual(set(result), set(m.CUSTOM))
        self.assertTrue(all(x['nullLookupReturnsZero'] for x in result.values()))
        self.assertEqual(result[m.CUSTOM[0]]['lookupRVA'], 0x400)
    def test_conditional_inverted_refused(self):
        data = fixture(); struct.pack_into('<I', data, 0x420, 0xb4000088)
        with self.assertRaises(ValueError): self.check(data)
    def test_success_on_missing_refused(self):
        data = fixture(); struct.pack_into('<I', data, 0x428, 0xb81fc3a0)
        with self.assertRaises(ValueError): self.check(data)
    def test_wrong_slot_refused(self):
        data = fixture(); struct.pack_into('<I', data, 0x41c, 0xf9400508)
        with self.assertRaises(ValueError): self.check(data)
    def test_aliased_slots_refused(self):
        data = fixture()
        struct.pack_into('<I', data, 0x458, 0xf9000100)
        struct.pack_into('<I', data, 0x45c, 0xf9400108)
        with self.assertRaises(ValueError): self.check(data)
    def test_wrong_resolver_import_refused(self):
        with self.assertRaises(ValueError): m.audit(m.abi.MachO(fixture()), BASE+0xa04)
    def test_changed_resolver_argument_refused(self):
        data = fixture(); struct.pack_into('<I', data, 0x81c, 0xf85f03a2)
        with self.assertRaises(ValueError): self.check(data)
    def test_wrong_return_refused(self):
        data = fixture(); struct.pack_into('<I', data, 0x850, 0xf85e83a1)
        with self.assertRaises(ValueError): self.check(data)
    def test_missing_name_refused(self):
        data = fixture(); data[0x1800] = ord('x')
        with self.assertRaises(ValueError): self.check(data)
    def test_ambiguous_lookup_refused(self):
        data = fixture(); data[0x600:0x630] = data[0x400:0x430]
        # Re-encode PC-relative fields of the second independent lookup.
        struct.pack_into('<I', data, 0x60c, branch(0x60c, 0x800, True))
        struct.pack_into('<I', data, 0x62c, branch(0x62c, 0x900))
        with self.assertRaises(ValueError): self.check(data)
    def test_section_file_mapping_refused(self):
        data = fixture(); struct.pack_into('<I', data, 104+48, 0x404)
        with self.assertRaises(ValueError): self.check(data)
    def test_stub_parser_ignores_got(self):
        text = 'Indirect symbols for (__TEXT,__stubs) 1 entries\n0x0000000100000a00 5 _dlsym\nIndirect symbols for (__DATA,__got) 1 entries\n0x0000000100003000 5 _dlsym\n'
        self.assertEqual(m.find_dlsym_stub(text), BASE+0xa00)
        with self.assertRaises(ValueError): m.find_dlsym_stub(text+text)
    def test_fat_bounds_and_ambiguity(self):
        thin = fixture(); offset = 0x1000
        data = bytearray(offset)+thin
        struct.pack_into('>7I', data, 0, 0xcafebabe, 1, 0x100000c, 0, offset, len(thin), 12)
        self.assertEqual(m.arm64_slice(data), thin)
        struct.pack_into('>I', data, 20, len(data))
        with self.assertRaises(ValueError): m.arm64_slice(data)
        data = bytearray(offset)+thin+thin
        struct.pack_into('>I', data, 0, 0xcafebabe)
        struct.pack_into('>I', data, 4, 2)
        for i in range(2):
            struct.pack_into('>5I', data, 8+i*20, 0x100000c, 0, offset+i*len(thin), len(thin), 12)
        with self.assertRaises(ValueError): m.arm64_slice(data)
    def test_truncated_text_refused(self):
        with self.assertRaises(ValueError): self.check(fixture()[:0x900])


unittest.main()
