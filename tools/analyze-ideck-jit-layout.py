#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Read actual JIT geometry, never the requested pool or candidate free holes.

This is a log observation, not permission to run a game or recycle any mapping.
Input must be a bounded captured native log from the separately verified process.
"""
import argparse
import json
import re
from pathlib import Path


def analyze(text, required_main=704, required_c=352, required_margin=256):
    # A file can retain older sessions. Consider only the last full Wine start.
    marker = 'Running full Wine sequence...'
    if marker not in text:
        return {'geometry_observed': False, 'meets_requested_minima': False}
    text = text.rsplit(marker, 1)[1]
    c = re.findall(r'\[pool-low\] region C (0x[0-9a-fA-F]+)\+(\d+)MB '
                   r'\(free runs below the window: [^\r\n;]*; '
                   r'(\d+)MB of the run left free', text)
    pool = re.findall(r'JIT pool: RX=(0x[0-9a-fA-F]+), '
                      r'RW=(0x[0-9a-fA-F]+), size=(\d+)MB', text)
    if len(c) != 1 or len(pool) != 1:
        return {'geometry_observed': False, 'meets_requested_minima': False}
    actual_c, margin, actual_main = int(c[0][1]), int(c[0][2]), int(pool[0][2])
    return {
        'geometry_observed': True,
        'actual_main_span_mib': actual_main,
        'actual_c_mib': actual_c,
        'actual_low_image_margin_mib': margin,
        'required_main_span_mib': required_main,
        'required_c_mib': required_c,
        'required_low_image_margin_mib': required_margin,
        'meets_requested_minima': actual_main >= required_main and
            actual_c >= required_c and margin >= required_margin,
        'limitation': 'Span is not contiguous free capacity, usable code bytes, '
                      'lifetime proof or Steam/game validation.'
    }


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('log', type=Path)
    a = p.parse_args()
    if a.log.stat().st_size > 32 * 1024 * 1024:
        p.error('Log exceeds the 32 MiB analysis bound')
    result = analyze(a.log.read_text(errors='replace'))
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['meets_requested_minima'] else 1)
