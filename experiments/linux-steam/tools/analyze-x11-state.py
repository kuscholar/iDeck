#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Interpret numeric X11 observer records without claiming Steam/UI health.

Read-only PRIVATE artifact analysis. No device, shell, network or guest action.
Before/after files must be two copies of one append-only observation stream.
Even a growing stream is NOT bound to a current native PID/build by this schema;
the operator must independently verify device/session identity and physical UI.
"""
import argparse
import hashlib
import json
from pathlib import Path

MAX_BYTES = 2097152
ROW_KEYS = set('schema status error requests begin_mono_ms root root_width root_height focus revert_to children_total children_recorded focus_extra elapsed_ms atomic_snapshot Steam_UI_qualified root_attributes windows_bottom_to_top_then_extra_focus'.split())
WINDOW_KEYS = set('id x_error attributes_valid geometry_valid map_state override_redirect class event_mask x y width height'.split())


def integer(value, lower, upper, label):
    if type(value) is not int or not lower <= value <= upper:
        raise ValueError('Invalid numeric field: ' + label)
    return value


def window(value):
    if type(value) is not dict or set(value) != WINDOW_KEYS:
        raise ValueError('Invalid window record fields')
    for key in WINDOW_KEYS:
        lower, upper = (-32768, 32767) if key in ('x', 'y') else (0, 4294967295)
        if key in ('width', 'height'):
            upper = 65535
        elif key in ('attributes_valid', 'geometry_valid', 'override_redirect'):
            upper = 1
        elif key in ('class', 'map_state'):
            upper = 2
        integer(value[key], lower, upper, key)
    if value['geometry_valid'] and not value['attributes_valid']:
        raise ValueError('Geometry without attributes')
    if value['attributes_valid'] and value['class'] not in (1, 2):
        raise ValueError('Invalid valid-window class')


def row(value):
    if type(value) is not dict or set(value) != ROW_KEYS:
        raise ValueError('Unsupported X11 state schema fields')
    if value['atomic_snapshot'] is not False or value['Steam_UI_qualified'] is not False:
        raise ValueError('Record claims unsupported atomic/UI qualification')
    for key in ROW_KEYS - {'root_attributes', 'windows_bottom_to_top_then_extra_focus', 'atomic_snapshot', 'Steam_UI_qualified'}:
        integer(value[key], 0, 9223372036854775807 if key in ('begin_mono_ms', 'elapsed_ms') else 4294967295, key)
    if value['schema'] != 1 or value['status'] > 1 or value['revert_to'] > 2 or value['focus_extra'] > 1 or value['requests'] > 72:
        raise ValueError('Unsupported status/schema/request count')
    total, count = value['children_total'], value['children_recorded']
    if total > 65535 or count > 32 or count > total:
        raise ValueError('Invalid bounded child count')
    items = value['windows_bottom_to_top_then_extra_focus']
    if type(items) is not list or len(items) != count + value['focus_extra']:
        raise ValueError('Window count differs from record bounds')
    window(value['root_attributes'])
    for item in items:
        window(item)
    if value['status'] == 0:
        if value['error'] or not value['root'] or count != min(total, 32):
            raise ValueError('Inconsistent successful sample')
        integer(value['root_width'], 1, 65535, 'root_width')
        integer(value['root_height'], 1, 65535, 'root_height')
        root = value['root_attributes']
        if root['id'] != value['root'] or not root['attributes_valid'] or not root['geometry_valid'] or root['x_error']:
            raise ValueError('Successful sample missing root attributes')
        ids = [item['id'] for item in items]
        if len(set(ids)) != len(ids) or any(i <= 1 or i == value['root'] for i in ids):
            raise ValueError('Invalid or repeated child/focus IDs')
        if value['focus_extra'] and items[-1]['id'] != value['focus']:
            raise ValueError('Extra focus does not match focus ID')
    return value


def load_stream(path):
    with Path(path).open('rb') as file:
        raw = file.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError('Observer stream exceeds byte cap')
    last = raw.rfind(b'\n') + 1
    complete, trailing = raw[:last], raw[last:]
    if len(trailing) >= 16384:
        raise ValueError('Partial record exceeds row cap')
    lines = complete.splitlines()
    if len(lines) > 120:
        raise ValueError('Observer stream exceeds record cap')
    records = []
    for index, line in enumerate(lines):
        if not line or len(line) >= 16384:
            raise ValueError('Invalid complete record length')
        try:
            records.append(row(json.loads(line)))
        except (ValueError, RecursionError, UnicodeError, TypeError, KeyError):
            # Never echo arbitrary input text/fields from a wrong/private log.
            raise ValueError('Invalid complete observer record at index ' + str(index)) from None
    return dict(raw=raw, complete=complete, records=records, trailing_bytes=len(trailing))


def describe(value):
    if value['status']:
        return dict(status='observer-error', error=value['error'], begin_mono_ms=value['begin_mono_ms'], inference_allowed=False)
    count = value['children_recorded']
    top = value['windows_bottom_to_top_then_extra_focus'][:count]
    visible = [w for w in top if w['attributes_valid'] and w['geometry_valid'] and not w['x_error'] and w['class'] == 1 and w['map_state'] == 2]
    width, height = value['root_width'], value['root_height']
    intersects = [w for w in visible if max(0, w['x']) < min(width, w['x'] + w['width']) and max(0, w['y']) < min(height, w['y'] + w['height'])]
    focus = value['focus']
    focus_kind = 'none' if focus == 0 else 'pointer-root' if focus == 1 else 'root' if focus == value['root'] else 'queried-window'
    focused = next((w for w in value['windows_bottom_to_top_then_extra_focus'] if w['id'] == focus), None)
    # Focus-extra coordinates are relative to an UNKNOWN parent, not the root.
    # Never include that rectangle in root-child coverage or stacking analysis.
    return dict(status='sampled', begin_mono_ms=value['begin_mono_ms'], elapsed_ms=value['elapsed_ms'],
                children_total=value['children_total'], omitted_children=value['children_total'] - count,
                viewable_input_output_root_children=[w['id'] for w in visible],
                intersecting_root_children=[w['id'] for w in intersects],
                topmost_sampled_intersecting_child=intersects[-1]['id'] if intersects else None,
                rectangle_covers_root=[w['id'] for w in intersects if w['x'] <= 0 and w['y'] <= 0 and w['x'] + w['width'] >= width and w['y'] + w['height'] >= height],
                focus=focus, focus_kind=focus_kind,
                focused_window_map_state=focused['map_state'] if focused and focused['attributes_valid'] and not focused['x_error'] else None,
                focused_window_geometry_parent_known=focus in {w['id'] for w in top},
                root_substructure_redirect_selected=bool(value['root_attributes']['event_mask'] & (1 << 20)),
                root_sample_viewable=value['root_attributes']['map_state'] == 2,
                inference_allowed=False)


def analyze(before_path, after_path):
    before, after = load_stream(before_path), load_stream(after_path)
    # Bytes of an incomplete prior line must also survive. Counts or filenames
    # alone cannot distinguish rotation/truncation/replacement from append.
    prefix = after['raw'].startswith(before['raw'])
    added = len(after['records']) - len(before['records']) if prefix else 0
    clocks = [r['begin_mono_ms'] for r in after['records']]
    regressed = any(b < a for a, b in zip(clocks, clocks[1:]))
    added_clocks = clocks[len(before['records']):] if prefix else []
    anchored_clocks = ([before['records'][-1]['begin_mono_ms']] if before['records'] else []) + added_clocks
    advanced = added > 0 and all(b > a for a, b in zip(anchored_clocks, anchored_clocks[1:]))
    return dict(scope='Numeric X11 artifact comparison only; NOT current-device/session binding, WM presence, pixels, input delivery or Steam/game stability',
                before_sha256=hashlib.sha256(before['raw']).hexdigest(), after_sha256=hashlib.sha256(after['raw']).hexdigest(),
                before_complete_rows=len(before['records']), after_complete_rows=len(after['records']),
                before_partial_bytes=before['trailing_bytes'], after_partial_bytes=after['trailing_bytes'],
                stream_prefix_preserved=prefix, new_complete_rows=added, clock_regressed=regressed,
                new_record_time_advanced=advanced,
                new_sample_in_supplied_stream=prefix and advanced and not regressed and bool(after['records']) and after['records'][-1]['status'] == 0,
                latest_before=describe(before['records'][-1]) if before['records'] else None,
                latest_after=describe(after['records'][-1]) if after['records'] else None,
                native_session_bound=False, cause_proven=False, Steam_UI_qualified=False, game_return_qualified=False,
                limits=['Non-atomic samples may race window destruction/map/resize.',
                        'Rectangle intersection is not visible pixels or opaque occlusion; no shape/alpha/content sampled.',
                        'Truncation/replacement, unchanged/duplicated records, partial lines or stalled/regressed time cannot establish freshness.',
                        'Even append and increasing guest monotonic time do not bind this schema to the current native PID/build.',
                        'SubstructureRedirect selection is not proof a working window manager is present.'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('before', type=Path)
    parser.add_argument('after', type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(analyze(args.before, args.after), indent=2))
    except (ValueError, OSError) as error:
        parser.exit(2, str(error) + '\n')
