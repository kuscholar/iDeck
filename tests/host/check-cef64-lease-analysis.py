#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception-1
import importlib.util
import json
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[2] / "tools/analyze-cef64-leases.py"
spec = importlib.util.spec_from_file_location("lease_analysis", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def record(seq=1, **changes):
    row = dict(seq=seq, seconds=10, nanos=seq, event="adopt", slot=8,
               owner="0x120000000", base="0x7140000000", size="0x20000000",
               requested="0x0", resolved="0x0", type="0x2000", status="0x0",
               remaining=-1, pid=32, tid=36)
    row.update(changes)
    return json.dumps(row).encode() + b"\n"


class AnalysisTests(unittest.TestCase):
    def test_failed_adopt_is_not_an_allocation(self):
        report = module.analyze(record(status="0xc0000017"))
        self.assertEqual(report["slots"]["8"]["successful_adopts"], 0)
        self.assertEqual(report["slots"]["8"]["failed_adopts"], 1)
        self.assertFalse(report["complete_runtime_coverage"])

    def test_placeholder_failed_and_remaining_frees_are_distinct(self):
        data = record() + record(2, event="free", type="0x8002", remaining=0)
        data += record(3, event="free", type="0x8000", remaining=0, status="0xc0000017")
        data += record(4, event="free", type="0x8000", remaining=1)
        data += record(5, event="free", type="0x8000", remaining=0)
        row = module.analyze(data)["slots"]["8"]
        for key in ("preserve_placeholder_frees", "failed_frees",
                    "successful_frees_with_view_remaining", "successful_frees_without_observed_view"):
            self.assertEqual(row[key], 1)

    def test_partial_and_budget_are_never_complete(self):
        report = module.analyze(record() + b'{"seq":2')
        self.assertEqual(report["observations"], 1)
        self.assertTrue(report["partial_tail_ignored"])
        footer = b'{"event":"budget-exhausted","complete":false}\n'
        self.assertTrue(module.analyze(record() + footer)["budget_exhausted"])
        with self.assertRaises(ValueError):
            module.analyze(record() + footer + record(2))

    def test_invalid_mixed_or_payload_records_are_rejected(self):
        for data in (b"", b'x' * (512 * 1024 + 1), record(2), record() + record(),
                     record(slot=3), record(status="account-payload"), record(seq=True),
                     record(extra="unexpected"), record() + record(2, seconds=9)):
            with self.subTest(size=len(data)), self.assertRaises(ValueError):
                module.analyze(data)


if __name__ == "__main__":
    unittest.main()
