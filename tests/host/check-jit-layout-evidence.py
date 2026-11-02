#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Prevent the actual smaller pool being mistaken for requested/candidate VA."""
import importlib.util
from pathlib import Path

root = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('layout', root / 'tools/analyze-ideck-jit-layout.py')
layout = importlib.util.module_from_spec(spec)
spec.loader.exec_module(layout)


def fixture(main, c, hole, margin):
    return (f'Running full Wine sequence...\nAllocating 704MB JIT pool\n'
            f'[pool-low] region C 0x12d000000+{c}MB '
            f'(free runs below the window: 0x11c978000+{hole}MB; '
            f'{margin}MB of the run left free for the low images, pool-low-margin = 256)\n'
            f'JIT pool: RX=0x148000000, RW=0x701b000000, size={main}MB\n')


small = fixture(560, 304, 566, 262)
r = layout.analyze(small)
assert r['actual_c_mib'] == 304 and r['actual_main_span_mib'] == 560
assert not r['meets_requested_minima']  # 566 is a candidate hole, not region C.
good = fixture(704, 352, 616, 264)
assert layout.analyze(good)['meets_requested_minima']
assert not layout.analyze(good + small)['meets_requested_minima']
assert layout.analyze(small + good)['meets_requested_minima']
assert not layout.analyze('Allocating 704MB JIT pool')['geometry_observed']
assert not layout.analyze(good.split('JIT pool:')[0])['geometry_observed']
assert not layout.analyze(good + good.split('sequence...')[1])['geometry_observed']
assert not layout.analyze(fixture(704, 352, 616, 128))['meets_requested_minima']
print('PASS actual JIT geometry: smaller actual pool, candidate holes, latest session, '
      'missing/duplicate fields and low margin fail closed')
