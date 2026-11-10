#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Compare real distribution Xlib with/without our diagnostic interposer.

Four sequential private controls; exact pixels/returns and explicit cap/fork
isolation. Requires our prebuilt normal.elf/stress.elf/xlib-window-trace.so in
the artifact directory. No Steam or on-device result is implied.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('artifact',type=Path)
p.add_argument('source_root',type=Path)
p.add_argument('output',type=Path)
p.add_argument('--ish',type=Path,help='Explicit pinned host CLI when artifacts are nested')
a=p.parse_args();art,source,out=(getattr(a,k).resolve() for k in ('artifact','source_root','output'))
assert all(str(path).startswith('/Volumes/easystore/') for path in (art,source,out))
assert not out.exists() and (source/'meta.db').is_file()
for name in ('Steam/config/loginusers.vdf','Steam/userdata','root/.steam/config/loginusers.vdf'):
    assert not (source/'data'/name).exists()
users=subprocess.run(['lsof','-t',str(source/'meta.db')],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True)
assert not users.stdout.strip(),'Source root is in use; preserved'
out.mkdir(mode=0o700)
lab=Path(__file__).resolve().parents[1];ish=a.ish.resolve() if a.ish else art.parent/'host/ish'
tests={};trace_results={}
for mode,stress,traced in [('normal-plain',False,False),('normal-traced',False,True),('stress-plain',True,False),('stress-traced',True,True)]:
    root=out/(mode+'-root');subprocess.run(['cp','-cpR',str(source),str(root)],check=True,timeout=180)
    command=[sys.executable,str(lab/'tools/run-x11-window-control.py'),str(ish),str(root),str(art/('stress.elf' if stress else 'normal.elf')),str(out/mode)]
    if traced:command+=['--preload',str(art/'xlib-window-trace.so')]
    with (out/(mode+'.log')).open('xb') as log:result=subprocess.run(command,stdout=log,stderr=log,timeout=110)
    assert not result.returncode,(mode,'inspect private output; do not start another runtime on failure')
    record=json.loads((out/mode/'result.json').read_text());tests[mode]=record
    for role in ('parent','child'):assert record['reports'][role]['extra_attributes']==('4000' if stress else '0')
    if traced:
        summaries=[];by_pid={};capped_pids=set()
        for line in (out/mode/'runtime.log').read_text(errors='replace').splitlines():
            if line.startswith('X11_WINDOW_TRACE_CAPPED '):
                note=dict(item.split('=') for item in line.split()[1:]);assert set(note)=={'pid','omitted'} and note['omitted']=='1'
                pid=int(note['pid']);assert pid not in capped_pids;capped_pids.add(pid);continue
            if not line.startswith('X11_WINDOW_TRACE_V1 '):continue
            row=dict(item.split('=') for item in line.split()[1:]);assert set(row)=={'pid','tid','op','phase','call','window','result','mono_ns'}
            row={k:int(v) for k,v in row.items()};assert row['op'] in (1,2) and row['phase'] in (0,1,2)
            if row['phase']==2:assert row['call']==0 and row['window']==0 and row['result'] in (1,2)
            assert row['pid'] not in capped_pids
            by_pid.setdefault(row['pid'],[]).append((line,row))
        assert len(by_pid)==2
        for pid,raw_rows in by_pid.items():
            rows=[row for _,row in raw_rows];data=('\n'.join(line for line,_ in raw_rows)+'\n').encode();assert len(data)+96<=512*1024
            capped=pid in capped_pids;assert capped==stress
            calls={}
            for row in rows:
                if row['phase']==2:continue
                key=row['call']
                if row['phase']==0:assert key not in calls;calls[key]=[row]
                else:
                    assert key in calls and len(calls[key])==1
                    begin=calls[key][0];assert (begin['op'],begin['window'])==(row['op'],row['window']);calls[key].append(row)
            if not capped:assert all(len(pair)==2 for pair in calls.values())
            ends=[row for row in rows if row['phase']==1]
            summary=dict(pid=pid,bytes=len(data),capped=capped,rows=len(rows),get_success=sum(row['op']==1 and row['result']!=0 for row in ends),get_failure=sum(row['op']==1 and row['result']==0 for row in ends),destroy=sum(row['op']==2 for row in ends),sha256=hashlib.sha256(data).hexdigest())
            summaries.append(summary)
            (out/mode/(f'numeric-trace-{pid}.log')).write_bytes(data)
        if not stress:
            assert sorted(s['get_success'] for s in summaries)==[32,33]
            assert all(s['get_failure']==16 and s['destroy']==16 for s in summaries)
        trace_results[mode]=summaries
for kind in ('normal','stress'):
    for role in ('parent','child'):
        left=tests[kind+'-plain']['reports'][role];right=tests[kind+'-traced']['reports'][role]
        assert left==right,(kind,role,'actual Xlib return/counters/pixels changed')
evidence=dict(scope='HOST real ARM64 distribution Xlib/glibc and own Xvfb windows. Exact plain/traced returns/pixels match, PID-qualified numeric stderr records, explicit bounded-cap continuation. NOT actual Steam/CEF or iPad/game/stability success',
              tests=tests,trace_results=trace_results,tracer_sha256=hashlib.sha256((art/'xlib-window-trace.so').read_bytes()).hexdigest())
(out/'evidence.json').write_text(json.dumps(evidence,indent=2)+'\n');print(json.dumps(evidence))
