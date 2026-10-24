#!/usr/bin/env python3
"""Check real/soft/guard interval parsing, half-open boundaries and redaction."""
from pathlib import Path
import importlib.util,json,tempfile
root=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('pool_inventory',root/'tools/analyze-steam-ui-pools.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
fixture='''ignored password=DO_NOT_PUBLISH refresh_token=DO_NOT_PUBLISH
[cage] holdback reserved 0x7200000000+0x1ffff0000 rev=ml433
[fex-arena] ml793 PUBLISHED [0x7c00000000,0x8000000000) size=0x400000000
[jumbo] hinted reserve 0x371000000000 size=0x400000000 failed (0xc0000018) — offset-preserving retry -> 0x7800000000 (0x0)
[jumbo] cand plain slot=0x7800000000 size=0x400000000 st=0xc0000018
[soft-pool] GRANTED soft 0x7800000000 (base returned 0x77ffff0000, size=0x400010000) — unbacked
[steam-ui-reserve] reject-soft-overlap candidate=0x7800000000 size=0x400000000 view=0x7800000000 view_size=0x400000000
[jumbo] hinted reserve 0x371000000000 size=0x400000000 failed (0xc0000018) — offset-preserving retry -> 0x0 (0xc0000017)
'''
with tempfile.TemporaryDirectory() as td:
    p=Path(td)/'fixture.txt';p.write_text(fixture);d=m.analyze(p)
assert len(d['events'])==4 and len(d['historical_intersections'])==1
assert d['historical_intersections'][0]['intersection_size']==0x400000000
assert d['events'][-1]['base']==0x77ffff0000 and d['events'][-1]['size']==0x400010000
assert len(d['rejected_overlaps'])==1 and len(d['failed_slots'])==1
assert 'DO_NOT_PUBLISH' not in json.dumps(d)
assert not m.intersects(dict(base=0,size=16),dict(base=16,size=16))
assert m.intersects(dict(base=0,size=16),dict(base=15,size=16))
assert 'release/restart' in ' '.join(d['limits'])
print('PASS: intervals/guard prefix/failure discrimination/half-open boundary/redaction/lifecycle limitation')
