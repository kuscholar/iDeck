#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception-1
"""Read-only CEF import/export/header inventory; never an ABI certification.

Inputs are the owner's local PE files and a pinned upstream CEF include tree.
Nothing is loaded, executed, installed or modified. JSON contains only public
symbol names, source-header digests and binary digests, never account data.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys


def blocks(text, kind):
    """Extract complete top-level LLVM records, including nested delay imports."""
    lines = text.splitlines()
    result = []
    active, depth = None, 0
    for line in lines:
        if active is None:
            if line == kind + " {":
                active, depth = [], 1
            continue
        depth += line.count("{") - line.count("}")
        if depth == 0:
            result.append("\n".join(active))
            active = None
        else:
            active.append(line)
    if active is not None:
        raise ValueError("truncated LLVM " + kind + " record")
    return result


def imports(text):
    if "Format: COFF-x86-64\n" not in text:
        raise ValueError("consumer must be an AMD64 PE, not i386/ARM64EC")
    result = {"direct": set(), "delayed": set()}
    for kind, bucket in (("Import", "direct"), ("DelayImport", "delayed")):
        for block in blocks(text, kind):
            name = re.search(r"^  Name: (.+)$", block, re.M)
            if not name or name[1].lower() != "libcef.dll":
                continue
            symbols = re.findall(r"^\s+Symbol: (.*)$", block, re.M)
            if not symbols:
                raise ValueError("empty libcef import record")
            for symbol in symbols:
                match = re.fullmatch(r"(cef_\w+) \(\d+\)", symbol)
                if not match:
                    raise ValueError("unresolved/non-CEF libcef import; no coverage claim")
                result[bucket].add(match[1])
    if not (result["direct"] | result["delayed"]):
        raise ValueError("no libcef imports; wrong input or incomplete LLVM output")
    return result


def exports(text):
    if "Format: COFF-x86-64\n" not in text:
        raise ValueError("CEF must be an AMD64 PE")
    names = set()
    for block in blocks(text, "Export"):
        name = re.search(r"^  Name: (\S+)$", block, re.M)
        if name:
            if name[1] in names:
                raise ValueError("duplicate export; ambiguous coverage")
            names.add(name[1])
    if "cef_api_hash" not in names or "cef_initialize" not in names:
        raise ValueError("required CEF export inventory missing or incomplete")
    return names


def headers(root):
    root = Path(root)
    if not (root / "capi/cef_app_capi.h").is_file():
        raise ValueError("expected a complete pinned CEF include directory")
    names = set()
    digest = hashlib.sha256()
    files = sorted(root.rglob("*.h"))
    for path in files:
        raw = path.read_bytes()
        digest.update(path.relative_to(root).as_posix().encode() + b"\0")
        digest.update(hashlib.sha256(raw).digest())
        text = re.sub(r"/\*.*?\*/|//[^\n]*", " ", raw.decode("utf-8"), flags=re.S)
        for declaration in re.finditer(r"\bCEF_EXPORT(?:_C)?\b([^;{]*);", text):
            names.update(re.findall(r"\b(cef_\w+)\s*\(", declaration[1]))
    if not {"cef_api_hash", "cef_initialize"} <= names:
        raise ValueError("upstream C API header inventory incomplete")
    return names, {"files": len(files), "tree_sha256": digest.hexdigest()}


def inventory(required, reference, declared, candidate=None):
    all_required = required["direct"] | required["delayed"]
    result = {
        "scope": "symbol-name inventory only; not signatures, API hashes, struct layout or runtime ABI",
        "required_direct": sorted(required["direct"]),
        "required_delayed": sorted(required["delayed"]),
        "required_unique_count": len(all_required),
        "reference_missing_required": sorted(all_required - reference),
        "not_declared_in_upstream_headers": sorted(all_required - declared),
        "candidate_binary_inspected": candidate is not None,
        "candidate_missing_required": None if candidate is None else sorted(all_required - candidate),
        "ABI_compatibility": "NOT_VALIDATED; even complete name coverage is insufficient",
    }
    return result


def dump(tool, path, option):
    run = subprocess.run([tool, "--file-headers", option, str(path)],
                         capture_output=True, text=True, timeout=30, check=True)
    if len(run.stdout) > 8 * 1024 * 1024:
        raise ValueError("LLVM inventory exceeds diagnostic bound")
    return run.stdout


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--llvm-readobj", required=True)
    parser.add_argument("--consumer", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--upstream-include", type=Path, required=True)
    parser.add_argument("--candidate", type=Path)
    args = parser.parse_args()
    required = imports(dump(args.llvm_readobj, args.consumer, "--coff-imports"))
    reference = exports(dump(args.llvm_readobj, args.reference, "--coff-exports"))
    declared, tree = headers(args.upstream_include)
    candidate = None if args.candidate is None else exports(
        dump(args.llvm_readobj, args.candidate, "--coff-exports"))
    result = inventory(required, reference, declared, candidate)
    result["input_sha256"] = {"consumer": digest(args.consumer),
                              "reference": digest(args.reference)}
    if args.candidate:
        result["input_sha256"]["candidate"] = digest(args.candidate)
    result["upstream_headers"] = tree
    print(json.dumps(result, indent=2))
    return 2 if result["reference_missing_required"] or result["candidate_missing_required"] else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print("CEF inventory failed: " + str(error), file=sys.stderr)
        sys.exit(1)
