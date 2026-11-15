#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Explicit LLDB device-only, PC-only attached Lab observation.

Import under LLDB AFTER an explicit device-only CLI attachment, with
IDECK_PC_SNAPSHOT_CONFIG pointing to the caller's private config after fresh
CoreDevice PID/installed-URI validation. No expressions,
locals/arguments, target-memory dumps/writes, launch/restart or process kill.
LLDB must remain interactive until the result confirms a successful detach;
NEVER unconditionally quit/kill the debugger on a timeout or failed detach.
Temporary attachment stops the target. Always attempt detach(resume) in finally.
Optional caller_thread_ids selects at most two native threads for three caller
PCs each. LLDB unwinding can read stack return-address slots; no stack payload
dump, locals/arguments, evaluated code or other registers are requested. The
two-second collection budget is checked between SB API calls, not a hard limit
on blocking debugger calls. Keep the debugger open until cleanup is confirmed.
Do not poll Python SB APIs while device attachment is still pending: even a
GetSelectedTarget/GetState query can block before the stop event, preventing
queued cleanup commands from executing. Wait for the debugger's actual native
stop event before importing this collector. Never force-kill a hung debugger.
"""
import json
import os
from pathlib import Path
import re
import time


def capture(debugger, config, api):
    destination = Path(config['result'])
    assert str(destination).startswith('/Volumes/easystore/GitHub/FunProjects/.madeira-install/')
    assert not destination.exists() and config['preflight_identity_verified'] is True
    assert config['capture_existing_attachment_only'] is True
    assert re.fullmatch(r'[0-9A-Fa-f]{8}-[0-9A-Fa-f]{16}', config['device'])
    assert config['model'] == 'iPad13,1'
    assert config['expected_executable'] == 'Madeira' and config['bundle'] == 'com.kuschqin.ideck.freshtest'
    pid = config['pid']
    assert type(pid) is int and pid > 0
    caller_tids = config.get('caller_thread_ids', [])
    assert type(caller_tids) is list and len(caller_tids) <= 2
    assert all(type(tid) is int and tid > 0 for tid in caller_tids)
    report = dict(scope='One selected Air Lab, native PC metadata only; not guest/UI/game health',
                  pid=pid, phase='preparing', attached=False, detached=False,
                  locals_or_payload_read=False, target_memory_written=False, process_restarted=False,
                  stack_return_address_unwinding_requested=bool(caller_tids), threads=[])
    process = None
    observation_start = None

    def save():
        destination.write_text(json.dumps(report, indent=2) + '\n')

    save()
    try:
        debugger.SetAsync(False)
        observation_start = time.monotonic()
        target = debugger.GetSelectedTarget()
        process = target.GetProcess()
        if not process.IsValid() or process.GetProcessID() != pid:
            raise RuntimeError('existing-attachment-identity-mismatch')
        report['initial_process_state'] = process.GetState()
        if process.GetState() != api.eStateStopped:
            raise RuntimeError('attachment-not-ready')
        report['attached'] = True
        report['target_triple'] = target.GetTriple() or ''
        if '-ios' not in report['target_triple'] or 'simulator' in report['target_triple']:
            raise RuntimeError('unexpected-target-platform')
        if target.GetExecutable().GetFilename() != config['expected_executable']:
            raise RuntimeError('unexpected-target-executable')
        main_module = target.FindModule(target.GetExecutable())
        actual_uuid = main_module.GetUUIDString() if main_module.IsValid() else ''
        if not actual_uuid or actual_uuid.replace('-', '').lower() != config['expected_binary_uuid'].replace('-', '').lower():
            raise RuntimeError('unexpected-target-binary-uuid')
        report['binary_uuid_matches_preflight'] = True
        report['phase'] = 'sampling'
        save()
        count = process.GetNumThreads()
        report['total_threads'] = count
        maximum = min(count, 16)
        indices = sorted({round(i * (count - 1) / (maximum - 1)) if maximum > 1 else 0 for i in range(maximum)})
        start = time.monotonic()
        for index in indices:
            if time.monotonic() - start > 2:
                report['collection_budget_reached'] = True
                break
            thread = process.GetThreadAtIndex(index)
            frame = thread.GetFrameAtIndex(0)
            pc = frame.GetPC()
            if pc == api.LLDB_INVALID_ADDRESS:
                continue
            item = dict(index=index, tid=thread.GetThreadID(), pc=pc)
            module = frame.GetModule()
            if module.IsValid():
                item['module'] = module.GetFileSpec().GetFilename()
                base = module.GetObjectFileHeaderAddress().GetLoadAddress(target)
                if base != api.LLDB_INVALID_ADDRESS and base <= pc:
                    item['module_base'] = base
                    item['module_offset'] = pc - base
            report['threads'].append(item)
            if item['tid'] in caller_tids:
                # At most three caller PCs for two explicitly selected native
                # threads. LLDB's unwinder may read stack return-address slots;
                # no expressions, arguments, locals or object data are queried.
                item['callers'] = []
                for depth in range(1, 4):
                    if time.monotonic() - start > 2:
                        report['collection_budget_reached'] = True
                        break
                    caller = thread.GetFrameAtIndex(depth)
                    address = caller.GetPC()
                    if address == api.LLDB_INVALID_ADDRESS:
                        break
                    entry = dict(depth=depth, pc=address)
                    owner = caller.GetModule()
                    if owner.IsValid():
                        entry['module'] = owner.GetFileSpec().GetFilename()
                        origin = owner.GetObjectFileHeaderAddress().GetLoadAddress(target)
                        if origin != api.LLDB_INVALID_ADDRESS and origin <= address:
                            entry['module_base'] = origin
                            entry['module_offset'] = address - origin
                    item['callers'].append(entry)
        report['collection_ms'] = round((time.monotonic() - start) * 1000)
    except BaseException as error:
        report['error_type'] = type(error).__name__
        if isinstance(error, RuntimeError) and str(error) in {'existing-attachment-identity-mismatch','attachment-not-ready','unexpected-target-platform','unexpected-target-executable','unexpected-target-binary-uuid'}:
            report['error_tag'] = str(error)
        # No exception payload, evaluated expression, register contents other
        # than PC, names, arguments or guest object bytes are recorded.
    finally:
        if process is None:
            target = debugger.GetSelectedTarget()
            process = target.GetProcess() if target.IsValid() else None
        if process is not None and process.IsValid():
            state = process.GetState()
            report['state_before_cleanup'] = state
            if process.GetProcessID() != pid:
                report['foreign_process_preserved'] = True
            elif state in (api.eStateConnected, api.eStateAttaching):
                report['attachment_pending'] = True
            elif state == api.eStateDetached:
                report['detached'] = True
            elif state == api.eStateExited:
                report['target_exited'] = True
                report['detached'] = True
            else:
                report['detach_attempted'] = True
                try:
                    result = process.Detach(False)
                    report['detach_error_code'] = result.GetError()
                    report['state_after_detach'] = process.GetState()
                    report['detached'] = result.Success() and process.GetState() == api.eStateDetached
                except BaseException as error:
                    report['detach_exception_type'] = type(error).__name__
        else:
            report['detached'] = not report['attached']
        if observation_start is not None:
            report['collector_through_detach_ms'] = round((time.monotonic() - observation_start) * 1000)
        report['phase'] = 'done' if report['detached'] else 'cleanup-required-keep-debugger-open'
        save()
    return report


def __lldb_init_module(debugger, internal_dict):
    del internal_dict
    path = os.environ.get('IDECK_PC_SNAPSHOT_CONFIG')
    if not path:
        return
    import lldb
    capture(debugger, json.loads(Path(path).read_text()), lldb)
