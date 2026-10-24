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


def intersects(a, b):
    return a['base'] < b['base'] + b['size'] and b['base'] < a['base'] + a['size']


def analyze(path):
    raw = path.read_bytes()
    events = []
    rejects = []
    failed = set()
    for n, line in enumerate(raw.decode('utf-8', errors='replace').splitlines(), 1):
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
        limits=['Runtime-reported intervals; not a fresh kernel map or per-module owner proof.',
                'Historical intersections ignore release/restart lifecycle; confirm a live view using strict rejection or VirtualQuery.',
                'No inferred reserve-only committed byte totals: existing bigres counters are incomplete.',
                'Unparsed log payloads are excluded; no auth, tokens, commands or strings copied.'])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('logs',nargs='+',type=Path)
    p.add_argument('--output',type=Path)
    args=p.parse_args()
    output=json.dumps({'schema':1,'runs':[analyze(x) for x in args.logs]},indent=2)+'\n'
    if args.output:
        args.output.write_text(output)
    else:
        print(output,end='')


if __name__=='__main__':
    main()
