#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception-1
"""Check that incomplete/foreign inputs cannot produce an ABI-success claim."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

path = Path(__file__).resolve().parents[2] / "experiments/cef64/audit-api-imports.py"
spec = importlib.util.spec_from_file_location("cef_inventory", path)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

PREFIX = "Format: COFF-x86-64\n"
DIRECT = "Import {\n  Name: libcef.dll\n  Symbol: cef_initialize (0)\n}\n"
DELAYED = ("DelayImport {\n  Name: LIBCEF.DLL\n  Import {\n"
           "    Symbol: cef_api_hash (8)\n    Address: 0x140001000\n  }\n}\n")
EXPORTS = ("Export {\n  Ordinal: 1\n  Name: cef_initialize\n  RVA: 0x1000\n}\n"
           "Export {\n  Ordinal: 2\n  Name: cef_api_hash\n  RVA: 0x1200\n}\n")


class InventoryTests(unittest.TestCase):
    def test_delayed_import_and_foreign_library(self):
        foreign = "Import {\n  Name: SDL3.dll\n  Symbol: SDL_Init (0)\n}\n"
        result = audit.imports(PREFIX + foreign + DIRECT + DELAYED)
        self.assertEqual(result, {"direct": {"cef_initialize"}, "delayed": {"cef_api_hash"}})

    def test_reject_incomplete_or_wrong_architecture(self):
        for dump in (PREFIX, PREFIX + DIRECT[:-2], PREFIX + DELAYED[:-2],
                     "Format: COFF-i386\n" + DIRECT, "Format: COFF-ARM64EC\n" + DIRECT,
                     PREFIX + DIRECT.replace("cef_initialize (0)", " (71)"),
                     PREFIX + DIRECT.replace("  Symbol: cef_initialize (0)\n", "")):
            with self.subTest(dump=dump), self.assertRaises(ValueError):
                audit.imports(dump)
        for dump in (PREFIX, PREFIX + EXPORTS[:-2],
                     PREFIX + EXPORTS + EXPORTS, "Format: COFF-i386\n" + EXPORTS):
            with self.subTest(dump=dump), self.assertRaises(ValueError):
                audit.exports(dump)

    def test_candidate_missing_is_distinct_from_missing_header_declaration(self):
        result = audit.inventory(audit.imports(PREFIX + DIRECT + DELAYED),
                                 audit.exports(PREFIX + EXPORTS), {"cef_initialize"},
                                 {"cef_api_hash"})
        self.assertEqual(result["reference_missing_required"], [])
        self.assertEqual(result["not_declared_in_upstream_headers"], ["cef_api_hash"])
        self.assertEqual(result["candidate_missing_required"], ["cef_initialize"])
        self.assertTrue(result["ABI_compatibility"].startswith("NOT_VALIDATED"))
        result = audit.inventory(audit.imports(PREFIX + DIRECT), {"cef_initialize"}, set())
        self.assertFalse(result["candidate_binary_inspected"])
        self.assertIsNone(result["candidate_missing_required"])

    def test_multiline_headers_ignore_comments_and_nonexports(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "capi").mkdir()
            (root / "capi/cef_app_capi.h").write_text(
                "/* CEF_EXPORT void cef_fake(void); */\n"
                "// CEF_EXPORT void cef_comment(void);\n"
                "CEF_EXPORT\nint cef_initialize(\nvoid);\n"
                "CEF_EXPORT const char* cef_api_hash(int entry);\n"
                "void cef_not_exported(void);\n")
            names, stamp = audit.headers(root)
            self.assertEqual(names, {"cef_initialize", "cef_api_hash"})
            self.assertEqual(stamp["files"], 1)
            self.assertEqual(len(stamp["tree_sha256"]), 64)
            (root / "capi/cef_app_capi.h").write_text("void cef_not_exported(void);")
            with self.assertRaises(ValueError):
                audit.headers(root)


if __name__ == "__main__":
    unittest.main()
