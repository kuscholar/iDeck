#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception-1
"""Summarize numeric lease observations without authorizing reservation reuse."""
import argparse
import json
from pathlib import Path
import re

FIELDS = set("seq seconds nanos event slot owner base size requested resolved type status remaining pid tid".split())
HEX = set("owner base size requested resolved type status".split())


def analyze(raw):
    if not raw or len(raw) > 512 * 1024:
        raise ValueError("empty or oversized evidence")
    lines = raw.splitlines(keepends=True)
    partial = not lines[-1].endswith(b"\n")
    if partial:
        lines.pop()  # Never interpret an incomplete final write.
    records, budget = [], False
    previous_time = (0, 0)
    for line in lines:
        if budget:
            raise ValueError("records after terminal budget marker")
        if len(line) > 384:
            raise ValueError("record exceeds writer bound")
        event = json.loads(line)
        if event == {"event": "budget-exhausted", "complete": False}:
            budget = True
            continue
        if not isinstance(event, dict) or set(event) != FIELDS:
            raise ValueError("unexpected schema; do not print input payload")
        for name in FIELDS - HEX - {"event"}:
            if type(event[name]) is not int:
                raise ValueError("non-integer metadata")
        if event["seq"] != len(records) + 1 or len(records) >= 4096:
            raise ValueError("sequence gap, mixed files or excessive records")
        if event["event"] not in ("adopt", "refuse", "free"):
            raise ValueError("unknown operation")
        if not 0 <= event["slot"] < 20 or event["slot"] == 3:
            raise ValueError("not a guest lease slot")
        if event["remaining"] not in (-1, 0, 1):
            raise ValueError("invalid remaining-view observation")
        if event["seconds"] < 0 or not 0 <= event["nanos"] < 1000000000:
            raise ValueError("invalid monotonic time")
        now = (event["seconds"], event["nanos"])
        if now < previous_time:
            raise ValueError("non-monotonic or mixed evidence")
        previous_time = now
        for name in HEX:
            if not isinstance(event[name], str) or not re.fullmatch(r"0x[0-9a-f]{1,16}", event[name]):
                raise ValueError("invalid numeric metadata")
        if not all(0 <= event[n] <= 0xffffffff for n in ("pid", "tid")):
            raise ValueError("invalid guest process/thread identity")
        records.append(event)
    if not records:
        raise ValueError("no complete observations")
    slots = {}
    for event in records:
        row = slots.setdefault(str(event["slot"]), {
            "successful_adopts": 0, "failed_adopts": 0, "refusals": 0,
            "successful_frees_with_view_remaining": 0,
            "successful_frees_without_observed_view": 0,
            "failed_frees": 0, "preserve_placeholder_frees": 0, "unknown_frees": 0,
            "observed_owners": [], "last_sequence": 0})
        if event["owner"] not in row["observed_owners"]:
            row["observed_owners"].append(event["owner"])
        row["last_sequence"] = event["seq"]
        success = int(event["status"], 16) == 0
        if event["event"] == "adopt":
            row["successful_adopts" if success else "failed_adopts"] += 1
        elif event["event"] == "refuse":
            row["refusals"] += 1
        elif not success:
            row["failed_frees"] += 1
        elif int(event["type"], 16) & 2:  # MEM_PRESERVE_PLACEHOLDER
            row["preserve_placeholder_frees"] += 1
        elif not int(event["type"], 16) & 0x8000 or event["remaining"] == -1:
            row["unknown_frees"] += 1
        else:
            row["successful_frees_with_view_remaining" if event["remaining"] else
                "successful_frees_without_observed_view"] += 1
    return {"scope": "observations only; native claims remain retained; never permission to recycle",
            "observations": len(records), "partial_tail_ignored": partial,
            "budget_exhausted": budget, "complete_runtime_coverage": False, "slots": slots}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(analyze(args.evidence.read_bytes()), indent=2))
    except (ValueError, OSError):
        parser.exit(1, "Invalid or incomplete lease evidence; no lifecycle conclusion.\n")
