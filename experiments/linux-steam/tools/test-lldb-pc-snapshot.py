#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Host-only fake SB API checks for read scope and mandatory detach/resume.
No LLDB/device API or app is invoked by these tests.
"""
import argparse
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);a=p.parse_args()
out=a.output.resolve();assert str(out).startswith('/Volumes/easystore/') and not out.exists();out.mkdir(mode=0o700)
spec=importlib.util.spec_from_file_location('pc_snapshot',Path(__file__).with_name('lldb_pc_snapshot.py'));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

def run(case):
    calls=[];mode=case
    fs=SimpleNamespace(GetFilename=lambda:'Madeira')
    mod=SimpleNamespace(IsValid=lambda:True,GetFileSpec=lambda:fs,
        GetObjectFileHeaderAddress=lambda:SimpleNamespace(GetLoadAddress=lambda t:0x1000),
        GetUUIDString=lambda:'1'*32 if mode=='wrong-uuid' else '0'*32)
    class Frame:
        def GetPC(self):
            if mode=='read-error':raise ValueError('PRIVATE_NOT_FORWARDED')
            return 0x1234
        def GetModule(self):return mod
        def GetVariables(self,*args):raise AssertionError('Variables must never be read')
    thread=SimpleNamespace(GetFrameAtIndex=lambda n:Frame(),GetThreadID=lambda:99)
    class Process:
        state=2 if mode=='not-ready' else 6 if mode=='not-stopped' else 5
        def IsValid(self):return mode!='no-process'
        def GetProcessID(self):return 44 if mode=='wrong-pid' else 43
        def GetState(self):return self.state
        def GetNumThreads(self):return 100
        def GetThreadAtIndex(self,n):calls.append(('read',n));return thread
        def Detach(self,keep_stopped):
            calls.append(('detach',keep_stopped))
            if mode=='detach-exception':raise RuntimeError('PRIVATE_NOT_FORWARDED')
            if mode!='detach-failed':self.state=9
            return SimpleNamespace(Success=lambda:mode!='detach-failed',GetError=lambda:1 if mode=='detach-failed' else 0)
    process=Process()
    target=SimpleNamespace(IsValid=lambda:True,GetProcess=lambda:process,GetTriple=lambda:'arm64-apple-macosx' if mode=='wrong-platform' else 'arm64-apple-ios27.2',GetExecutable=lambda:fs,FindModule=lambda f:mod)
    debugger=SimpleNamespace(SetAsync=lambda b:None,GetSelectedTarget=lambda:target)
    api=SimpleNamespace(eStateStopped=5,eStateConnected=2,eStateAttaching=3,eStateDetached=9,eStateExited=10,LLDB_INVALID_ADDRESS=(1<<64)-1)
    config=dict(result=str(out/(case+'.json')),preflight_identity_verified=True,capture_existing_attachment_only=True,device='00000000-0000000000000000',model='iPad13,1',expected_executable='Madeira',bundle='com.kuschqin.ideck.freshtest',pid=43,expected_binary_uuid='0'*32)
    if mode=='callers':config['caller_thread_ids']=[99]
    result=module.capture(debugger,config,api)
    assert 'PRIVATE_NOT_FORWARDED' not in json.dumps(result)
    assert not result['locals_or_payload_read'] and not result['target_memory_written'] and not result['process_restarted']
    assert all(c[1] is False for c in calls if c[0]=='detach')
    if mode=='success':assert result['detached'] and len(result['threads'])==16 and result['threads'][0]['module_offset']==0x234
    elif mode=='no-process':assert not result['attached'] and result['detached'] and not any(c[0]=='read' for c in calls)
    elif mode=='wrong-pid':assert not result['detached'] and result['foreign_process_preserved'] and not any(c[0] in ('read','detach') for c in calls)
    elif mode in ('wrong-platform','wrong-uuid','not-stopped'):assert result['detached'] and not any(c[0]=='read' for c in calls)
    elif mode=='callers':assert result['detached'] and len(result['threads'])==16 and all(len(t['callers'])==3 for t in result['threads'])
    elif mode=='read-error':assert result['detached'] and result['error_type']=='ValueError'
    elif mode=='not-ready':assert result['attachment_pending'] and not any(c[0] in ('read','detach') for c in calls) and not result['detached']
    else:assert not result['detached'] and result['phase']=='cleanup-required-keep-debugger-open'
    return dict(case=case,detached=result['detached'],metadata_threads=len(result['threads']))

results=[run(s) for s in ['success','no-process','wrong-pid','wrong-platform','wrong-uuid','not-stopped','not-ready','read-error','detach-failed','detach-exception','callers']]
(out/'evidence.json').write_text(json.dumps(dict(scope='HOST fake SB API only; no actual debugger/device action',tests=results),indent=2)+'\n');print('PASS11 host cleanup/identity/PC-only controls; no device qualification')
