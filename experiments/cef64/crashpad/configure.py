#!/usr/bin/env python3
"""Prepare a separate CEF config candidate; never change a live prefix in-place.

SPDX-License-Identifier: GPL-3.0-or-later
Madeira Converter Exception: see LICENSE-EXCEPTION.md
"""
import argparse
import hashlib
import json
from pathlib import Path

HANDLER = r"C:\iDeckCEF64Crashpad\crashpad_handler.exe"


def configure(data):
    if len(data) > 65536 or b"\0" in data:
        raise ValueError("unsupported crash configuration")
    text = data.decode("utf-8-sig")
    bom = b"\xef\xbb\xbf" if data.startswith(b"\xef\xbb\xbf") else b""
    newline = "\r\n" if "\r\n" in text else "\n"
    if not text:
        return ("[Config]" + newline + "ExternalHandler=" + HANDLER + newline).encode()
    lines = text.splitlines(keepends=True)
    sections = [i for i, line in enumerate(lines) if line.strip().lower() == "[config]"]
    if len(sections) != 1 or lines[sections[0]].strip() != "[Config]":
        raise ValueError("ambiguous or missing exact Config section; preserve original")
    start = sections[0]
    end = next((i for i in range(start + 1, len(lines)) if lines[i].strip().startswith("[")), len(lines))
    entries = [i for i in range(start + 1, end)
               if lines[i].strip().split("=", 1)[0].strip().lower() == "externalhandler"]
    if len(entries) > 1:
        raise ValueError("duplicate ExternalHandler entries")
    if entries:
        line = lines[entries[0]].strip()
        if line != "ExternalHandler=" + HANDLER:
            raise ValueError("preserve pre-existing different external handler")
        return data
    if not lines[start].endswith(("\r", "\n")):
        lines[start] += newline
    lines.insert(start + 1, "ExternalHandler=" + HANDLER + newline)
    return bom + "".join(lines).encode("utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="omit only after verifying the original is absent")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        raise ValueError("output must be a new private candidate, not the original")
    if args.input and (args.input.is_symlink() or not args.input.is_file()):
        raise ValueError("input must be a regular private file")
    original = args.input.read_bytes() if args.input else b""
    candidate = configure(original)
    with args.output.open("xb") as output:
        output.write(candidate)
    print(json.dumps({"original_sha256": hashlib.sha256(original).hexdigest(),
                      "candidate_sha256": hashlib.sha256(candidate).hexdigest(),
                      "changed": candidate != original, "live_prefix_modified": False}))
