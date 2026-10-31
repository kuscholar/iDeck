#!/usr/bin/env python3
"""Redacted interval inventory from existing Madeira logs; no device operations.

Reports runtime claims and historical intersections, not a live kernel map.
Absent release/owner logs do not establish permanent ownership.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

HEX = r'0x[0-9a-fA-F]+'


def analyze_fex(lines):
    """Categorical failures only; absence of a match never proves runtime success."""
    counters = dict(ir_buffer_rejections=0, decoder_buffer_rejections=0, allocator_fatals=0,
                    thread_initialization_failures=0, thread_state_unavailable=0,
                    census_allocation_failures=0, owned_arena_scan_failures=0)
    thread_statuses = {}
    censuses = []
    ranges = set()
    scans = {}
    samples = []

    def failure(kind, line):
        counters[kind] += 1
        if len(samples) < 16:
            samples.append(dict(kind=kind, line=line))

    for number, line in enumerate(lines, 1):
        if '[ideck-fex-ir] rejected NULL or out-of-bounds IR buffer' in line:
            failure('ir_buffer_rejections', number)
        if '[ideck-fex-decoder] rejected NULL or undersized/out-of-bounds decode buffer' in line:
            failure('decoder_buffer_rejections', number)
        if 'FEXAlloc could not allocate' in line:
            failure('allocator_fatals', number)
        if '[FEX-iOS] ThreadInit: thread state unavailable' in line:
            failure('thread_state_unavailable', number)
        match = re.search(r'(?:^|\s)([0-9a-f]{4,8}):err:module:loader_init\s+'
                          r'arm64ec_thread_init failed (?:0x)?([0-9a-f]{8})(?:\s|$)',
                          line, re.I)
        if match and int(match[2], 16):
            failure('thread_initialization_failures', number)
            status = '0x%08x' % int(match[2], 16)
            thread_statuses[status] = thread_statuses.get(status, 0) + 1
        match = re.search(r'\[fex-va\] live arena=(' + HEX + r')\.\.(' + HEX + r')', line)
        if match:
            start, end = int(match[1], 16), int(match[2], 16)
            if start < end:
                ranges.add((start, end))
                allowed = {'request', 'align_mask', 'views', 'covered', 'free',
                           'committed', 'overlap', 'holes', 'maxgap', 'max_aligned_gap'}
                values = {key: int(value, 16 if value.lower().startswith('0x') else 10)
                          for key, value in re.findall(r'\b(\w+)=(0x[0-9a-fA-F]+|\d+)\b', line)
                          if key in allowed}
                if values.get('request', 0):
                    failure('census_allocation_failures', number)
                    censuses.append(dict(line=number, arena_start=start, arena_end=end, **values))
                    censuses = censuses[-8:]
        match = re.search(r'\[va-scan\] FAILED window=(' + HEX + r')\.\.(' + HEX + r')', line)
        if match:
            interval = (int(match[1], 16), int(match[2], 16))
            scans[interval] = scans.get(interval, 0) + 1
    counters['owned_arena_scan_failures'] = sum(scans.get(interval, 0) for interval in ranges)
    observed = any(counters.values())
    return dict(assessment='allocation-failure-observed' if observed else 'no-matched-failure',
                counters=counters, thread_failure_statuses=thread_statuses,
                recent_failure_censuses=censuses, bounded_failure_samples=samples,
                limits=['No matched failure is not a PASS, live-process check or UI/game/return validation.',
                        'Counts may contain repeated reports of one failure; they are not distinct failed allocations.',
                        'A census is a historical snapshot, not ownership attribution, a leak proof or current capacity.',
                        'Only categories, numeric fields and log line numbers are emitted; payload strings are excluded.'])


def intersects(a, b):
    return a['base'] < b['base'] + b['size'] and b['base'] < a['base'] + a['size']


def analyze(path):
    raw = path.read_bytes()
    lines = raw.decode('utf-8', errors='replace').splitlines()
    events = []
    rejects = []
    failed = set()
    for n, line in enumerate(lines, 1):
        m = re.search(r'\[cage\] holdback reserved ('+HEX+r')\+('+HEX+r')', line)
        if m:
            events.append(dict(kind='cage-holdback', line=n, base=int(m[1],16), size=int(m[2],16)))
        m = re.search(r'\[fex-arena\].*PUBLISHED \[('+HEX+r'),('+HEX+r')\)', line)
        if m:
            events.append(dict(kind='fex-arena', line=n, base=int(m[1],16), size=int(m[2],16)-int(m[1],16)))
        m = re.search(r'\[jumbo\] hinted reserve '+HEX+r' size=('+HEX+r').*retry -> ('+HEX+r') \(0x0\)', line)
        if m:
            events.append(dict(kind='real-pool-reported', line=n, base=int(m[2],16), size=int(m[1],16)))
        m = re.search(r'\[soft-pool\] GRANTED soft '+HEX+r' \(base returned ('+HEX+r'), size=('+HEX+r')\)', line)
        if m:
            events.append(dict(kind='soft-pool-reported', line=n, base=int(m[1],16), size=int(m[2],16)))
        m = re.search(r'\[steam-ui-reserve\] reject-soft-overlap candidate=('+HEX+r') size=('+HEX+r') view=('+HEX+r') view_size=('+HEX+r')', line)
        if m:
            rejects.append(dict(line=n, candidate=int(m[1],16), size=int(m[2],16),
                                view=int(m[3],16), view_size=int(m[4],16)))
        m = re.search(r'\[jumbo\] cand (?:plain|guard) slot=('+HEX+r').* st=('+HEX+r')', line)
        if m and int(m[2],16):
            failed.add((int(m[1],16),int(m[2],16)))
    overlaps=[]
    for i, b in enumerate(events):
        if b['kind'] != 'soft-pool-reported':
            continue
        for a in events[:i]:
            if a['kind'] in ('real-pool-reported','fex-arena','cage-holdback') and intersects(a,b):
                overlaps.append(dict(earlier_line=a['line'], earlier_kind=a['kind'],
                    soft_line=b['line'], intersection_base=max(a['base'],b['base']),
                    intersection_size=min(a['base']+a['size'],b['base']+b['size'])-max(a['base'],b['base'])))
    return dict(input_run=path.parent.name, input_name=path.name, input_bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
        events=events, rejected_overlaps=rejects, historical_intersections=overlaps,
        failed_slots=[dict(slot=a,status=b) for a,b in sorted(failed)],
        fex_allocation=analyze_fex(lines),
        limits=['Runtime-reported intervals; not a fresh kernel map or per-module owner proof.',
                'Historical intersections ignore release/restart lifecycle; confirm a live view using strict rejection or VirtualQuery.',
                'No inferred reserve-only committed byte totals: existing bigres counters are incomplete.',
                'Unparsed log payloads are excluded; no auth, tokens, commands or strings copied.'])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('logs',nargs='+',type=Path)
    p.add_argument('--output',type=Path)
    p.add_argument('--fail-on-fex-allocation-error', action='store_true',
                   help='Exit 2 for observed allocation/thread-init failures. Exit 0 is not runtime success.')
    args=p.parse_args()
    runs = [analyze(x) for x in args.logs]
    output=json.dumps({'schema':2,'runs':runs},indent=2)+'\n'
    if args.output:
        args.output.write_text(output)
    else:
        print(output,end='')
    return 2 if args.fail_on_fex_allocation_error and any(
        run['fex_allocation']['assessment'] == 'allocation-failure-observed' for run in runs) else 0


if __name__=='__main__':
    raise SystemExit(main())
