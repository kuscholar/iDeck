#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Functional artifact-analysis controls, optionally using real Xvfb receipts.

Does not start a runtime, operate a device, or edit an app/rootfs/signed build.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('output', type=Path)
p.add_argument('--real-fixture', type=Path, help='Private result of run-x11-state-control.py')
a = p.parse_args()
out = a.output.resolve()
assert str(out).startswith('/Volumes/easystore/') and not out.exists()
out.mkdir(mode=0o700)
source = Path(__file__).with_name('analyze-x11-state.py')
spec = importlib.util.spec_from_file_location('state_analysis', source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
checks = []


def window(i, mapped=2, **fields):
    value = dict(id=i, x_error=0, attributes_valid=1, geometry_valid=1,
                 map_state=mapped, override_redirect=0, **{'class': 1}, event_mask=0,
                 x=0, y=0, width=640, height=480)
    value.update(fields)
    return value


def sample(time=1000):
    return dict(schema=1, status=0, error=0, requests=8, begin_mono_ms=time,
                root=543, root_width=640, root_height=480, focus=2001,
                revert_to=1, children_total=2, children_recorded=2,
                focus_extra=0, elapsed_ms=2, atomic_snapshot=False, Steam_UI_qualified=False,
                root_attributes=window(543),
                windows_bottom_to_top_then_extra_focus=[window(2001), window(2002, 0)])


def encoded(value):
    return json.dumps(value).encode() + b'\n'


def compare(name, before, after):
    first, last = out/(name + '-before.jsonl'), out/(name + '-after.jsonl')
    first.write_bytes(before)
    last.write_bytes(after)
    result = module.analyze(first, last)
    assert result['native_session_bound'] is False and result['Steam_UI_qualified'] is False
    assert result['cause_proven'] is False and result['game_return_qualified'] is False
    checks.append(name)
    return result


initial = sample()
later = sample(31000)
later['focus'] = 2002
later['windows_bottom_to_top_then_extra_focus'] = [window(2001, 0), window(2002)]
before, after = encoded(initial), encoded(initial) + encoded(later)
result = compare('append-map-and-focus', before, after)
assert result['new_sample_in_supplied_stream'] and result['new_complete_rows'] == 1
assert result['latest_after']['focus'] == 2002 and result['latest_after']['viewable_input_output_root_children'] == [2002]
assert not compare('unchanged-is-not-fresh', before, before)['new_sample_in_supplied_stream']
result = compare('duplicate-is-not-fresh', before, before + before)
assert result['new_complete_rows'] == 1 and not result['new_record_time_advanced'] and not result['new_sample_in_supplied_stream']
assert not compare('replacement-is-not-append', before, encoded(later))['stream_prefix_preserved']
result = compare('partial-is-not-a-sample', before, before + encoded(later)[:40])
assert not result['new_sample_in_supplied_stream'] and result['after_partial_bytes'] == 40
result = compare('partial-line-completed', before + encoded(later)[:40], after)
assert result['new_sample_in_supplied_stream'] and result['new_complete_rows'] == 1
result = compare('empty-no-ui-inference', b'', b'')
assert result['latest_after'] is None
result = compare('clock-regression-not-fresh', before, before + encoded(sample(9)))
assert result['clock_regressed'] and not result['new_sample_in_supplied_stream']

focused_child = sample()
focused_child.update(focus=3000, focus_extra=1)
focused_child['windows_bottom_to_top_then_extra_focus'].append(window(3000))
result = compare('nested-focus-not-root-coverage', b'', encoded(focused_child))['latest_after']
assert result['rectangle_covers_root'] == [2001] and not result['focused_window_geometry_parent_known']
gone = sample()
gone['windows_bottom_to_top_then_extra_focus'][0] = window(2001, 0, x_error=3, attributes_valid=0, geometry_valid=0)
result = compare('lost-window-not-known-unmapped', b'', encoded(gone))['latest_after']
assert result['focused_window_map_state'] is None and result['viewable_input_output_root_children'] == []
offscreen = sample()
offscreen['windows_bottom_to_top_then_extra_focus'][0].update(x=-900, width=200)
assert compare('offscreen-rectangle', b'', encoded(offscreen))['latest_after']['intersecting_root_children'] == []
input_only = sample()
input_only['windows_bottom_to_top_then_extra_focus'][0]['class'] = 2
assert compare('input-only-not-render-surface', b'', encoded(input_only))['latest_after']['viewable_input_output_root_children'] == []
for focus, kind in [(0, 'none'), (1, 'pointer-root'), (543, 'root')]:
    special = sample()
    special['focus'] = focus
    assert compare('focus-' + kind, b'', encoded(special))['latest_after']['focus_kind'] == kind
failed = sample()
failed.update(status=1, error=110)
result = compare('probe-error-not-browser-death', b'', encoded(failed))
assert result['latest_after']['status'] == 'observer-error' and not result['new_sample_in_supplied_stream']

for label, change in [
    ('unsupported-qualification', lambda d: d.update(Steam_UI_qualified=True)),
    ('bool-not-integer', lambda d: d.update(status=False)),
    ('wrong-count', lambda d: d.update(children_recorded=3)),
    ('duplicate-id', lambda d: d['windows_bottom_to_top_then_extra_focus'][1].update(id=2001)),
    ('unbounded-windows', lambda d: d.update(children_total=100, children_recorded=100)),
    ('invalid-geometry', lambda d: d['windows_bottom_to_top_then_extra_focus'][0].update(x=-40000)),
    ('missing-schema', lambda d: d.pop('schema')),
    ('unrecognized-fields', lambda d: d.update(unrecognized_metadata='not forwarded')),
]:
    value = copy.deepcopy(initial)
    change(value)
    file = out/(label + '.jsonl')
    file.write_bytes(encoded(value))
    try:
        module.load_stream(file)
    except ValueError as error:
        assert 'not forwarded' not in str(error)
        checks.append(label)
    else:
        raise AssertionError(label)
for label, raw in [('partial-row-cap', b'x' * 16384), ('byte-cap', b'x' * (module.MAX_BYTES + 1)), ('record-cap', before * 121), ('malformed-complete-row', b'{\n')]:
    file = out/(label + '.jsonl')
    file.write_bytes(raw)
    try:
        module.load_stream(file)
    except ValueError:
        checks.append(label)
    else:
        raise AssertionError(label)

real = []
if a.real_fixture:
    fixture = a.real_fixture.resolve()
    records = [(fixture/('state-' + str(i) + '.json')).read_bytes() for i in range(4)]
    ids = json.loads((fixture/'evidence.json').read_text())['ids']
    previous = b''
    for i, data in enumerate(records):
        current = previous + data
        result = compare('real-Xvfb-' + str(i), previous, current)
        value = result['latest_after']
        assert result['new_complete_rows'] == 1 and value['focus'] == ids['b' if i == 1 else 'a']
        assert ids['c'] not in value['viewable_input_output_root_children']
        assert (ids['a'] in value['viewable_input_output_root_children']) == (i != 1)
        assert (ids['b'] in value['viewable_input_output_root_children']) == (i != 3)
        real.append(dict(case=i, source_sha256=hashlib.sha256(data).hexdigest(), analysis=value))
        previous = current
evidence = dict(scope='HOST private artifact parser/interpretation controls, including existing real Linux Xvfb fixture receipts if provided; NOT new runtime/Air/Steam/UI validation',
                checks=checks, real_Xvfb_artifacts=real, source_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
(out/'evidence.json').write_text(json.dumps(evidence, indent=2) + '\n')
print(json.dumps(dict(passed=len(checks), real_Xvfb_receipts=len(real), scope=evidence['scope'])))
