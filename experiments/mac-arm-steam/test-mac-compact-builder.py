# SPDX-License-Identifier: GPL-3.0-or-later
# Madeira Converter Exception: see LICENSE-EXCEPTION.md
"""Synthetic source/metadata contracts; actual source compilation is separate."""
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

path=Path(__file__).resolve().parents[2]/'scripts/experiments/build-mac-compact-allocator.py'
spec=importlib.util.spec_from_file_location('mac_compact',path)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class Tests(unittest.TestCase):
    def test_config_enables_dynamic_masks_only_for_optin(self):
        text='#if PA_BUILDFLAG(HAS_64_BIT_POINTERS) && BUILDFLAG(IS_IOS)\nvalue\n#endif\n'
        out=m.patched('partition_alloc_config.h',text)
        self.assertIn('IDECK_MAC_COMPACT_POOLS != 1',out)
        self.assertIn('BUILDFLAG(IS_IOS) || defined(IDECK_MAC_COMPACT_POOLS)',out)
        self.assertIn('!BUILDFLAG(IS_MAC)',out)
    def test_header_exposes_existing_small_pool_constants(self):
        text='#if BUILDFLAG(IS_IOS)\nexisting256MiBconstants\n#endif\n  PA_ALWAYS_INLINE static size_t RegularPoolSize();\n  PA_ALWAYS_INLINE static size_t BRPPoolSize();'
        out=m.patched('partition_address_space.h',text)
        self.assertIn('existing256MiBconstants',out)
        self.assertIn('defined(IDECK_MAC_COMPACT_POOLS)',out)
        self.assertIn('return kRegularPoolSizeForIOSTestProcess;',out)
    def test_source_keeps_unopted_ios_selection(self):
        text='#if BUILDFLAG(IS_IOS)\n#include <mach-o/dyld.h>\n#endif\n#if !BUILDFLAG(IS_IOS)\n#error Dynamic pool size is only supported on iOS.\n#endif\nnamespace {\nbool IsIOSTestProcess() {\nreturn has_suffix("Runner") || has_suffix("ios_web_view_inttests");\n}\n#endif  // PA_CONFIG(DYNAMICALLY_SELECT_POOL_SIZE)\n\nvoid PartitionAddressSpace::Init()'
        out=m.patched('partition_address_space.cc',text)
        self.assertIn('#if !defined(IDECK_MAC_COMPACT_POOLS)',out)
        self.assertIn('return has_suffix("Runner") || has_suffix("ios_web_view_inttests");',out)
    def test_changed_or_duplicate_source_refused(self):
        for text in ['different source','#if BUILDFLAG(IS_IOS)\n#if BUILDFLAG(IS_IOS)']:
            with self.assertRaises(ValueError):m.patched('partition_address_space.h',text)
    def test_unknown_patch_target_refused(self):
        with self.assertRaises(ValueError):m.patched('unrelated.h','keep unchanged')
    def test_instruction_hash_ignores_only_noncode_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'synthetic';data=bytearray(0x400)
            struct.pack_into('<8I',data,0,0xfeedfacf,0x100000c,0,8,1,152,0,0)
            struct.pack_into('<II16sQQQQIIII',data,32,0x19,152,b'__TEXT',0,0x400,0,0x400,7,5,1,0)
            struct.pack_into('<16s16sQQIIIIIIII',data,104,b'__text',b'__TEXT',0x200,16,0x200,2,0,0,0,0,0,0)
            data[0x200:0x210]=b'own-test-bytes16!';p.write_bytes(data);before=m.text_hash(p)
            data[0x300]=1;p.write_bytes(data);self.assertEqual(m.text_hash(p),before)
            data[0x200]^=1;p.write_bytes(data);self.assertNotEqual(m.text_hash(p),before)
    def test_unbacked_text_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'bad';p.write_bytes(b'not Mach-O')
            with self.assertRaises(ValueError):m.text_hash(p)


unittest.main()
