#!/usr/bin/env python3
"""Validate the pinned source patch without downloading or executing Chromium."""
import importlib.util
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("cef64_prepare", root / "experiments/cef64/prepare.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

if len(sys.argv) != 2:
    raise SystemExit("usage: check-cef64-source.py /path/to/exact/upstream/partition_address_space.h")
original = Path(sys.argv[1]).read_bytes()
patched = module.patch_header(original)
before, after = original.decode().splitlines(), patched.decode().splitlines()
changes = [(a, b) for a, b in zip(before, after) if a != b]
assert len(before) == len(after) and len(changes) == 2
for a, b in changes:
    assert "PoolSize = kPoolMaxSize;" in a and "PoolSize = 1 * kGiB;" in b
assert before.count("  static constexpr size_t kConfigurablePoolMaxSize = kPoolMaxSize;") == 1
assert "  static constexpr size_t kConfigurablePoolMaxSize = kPoolMaxSize;" in after
assert [s for s in before if "CHECK" in s or "static_assert" in s] == [s for s in after if "CHECK" in s or "static_assert" in s]
for invalid in (b"", original + b"\n", patched, original.replace(b"kRegularPoolSize", b"xRegularPoolSize")):
    try:
        module.patch_header(invalid)
        raise AssertionError("unrecognized or already patched input accepted")
    except ValueError:
        pass
print("PASS: exact pinned header, only two core-pool constants changed, configurable capacity and checks preserved; no runtime claim")
