#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Opt-in guest-thread lifetime hooks in a NEW copied archive, not vendor/base.

Tracks reserved pthread starts and retires only after nested guest-entry cleanup.
No stop/restart, signal-policy, allocation or CPU semantics are changed. A zero
counter alone does NOT prove all native/global resources can coexist with Wine.
"""
import argparse,hashlib,json,shlex,shutil,subprocess
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('source',type=Path);p.add_argument('build',type=Path)
p.add_argument('archive',type=Path);p.add_argument('output',type=Path)
p.add_argument('--sanitize',action='store_true')
p.add_argument('--fail-child-starts',action='store_true',help='HOST NEGATIVE CONTROL ONLY: return EAGAIN from guest child pthread creation')
p.add_argument('--join-guests',action='store_true',help='ISOLATED PROTOTYPE: tracked joinable child pthreads; requires native registry initialization, not full Linux teardown')
p.add_argument('--guest-waves',action='store_true',help='PROTOTYPE: allow explicit reopen after actual joins, preserving cumulative capacity; NOT runtime reset')
a=p.parse_args();source,build,archive,out=[x.resolve() for x in [a.source,a.build,a.archive,a.output]]
assert not (a.join_guests and a.fail_child_starts),'Use independent failure controls, not a mixed prototype'
assert not a.guest_waves or a.join_guests,'Guest waves require actual registered child joins'
pin='d1419782da2e299fe22f1ddb85c70ae3d1e276b1'
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==pin
assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain','--untracked-files=no'],text=True).strip()
assert not out.exists();out.mkdir(parents=True)
hashof=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
original=subprocess.check_output(['git','-C',str(source),'show',pin+':kernel/task.c'])
assert (source/'kernel/task.c').read_bytes()==original
body=original.decode();signature='void task_run_current() {'
assert body.count(signature)==1
body=body.replace(signature,'static void ideck_original_task_run_current(void) {')
lab=Path(__file__).resolve().parents[1]
for f in ['GuestLifetime.c','GuestLifetime.h']:shutil.copy2(lab/'app'/f,out/f)
body='#include "GuestLifetime.c"\n'+body
start='''    int err = pthread_create(&task->thread, &task_thread_attr, task_thread, task);
    if (err != 0)
        return err == EAGAIN ? _EAGAIN : _ENOMEM;'''
replacement='''    ideck_guest_lifetime_reserve();
    int err = pthread_create(&task->thread, &task_thread_attr, task_thread, task);
    if (err != 0) {
        ideck_guest_lifetime_retire(NULL);
        return err == EAGAIN ? _EAGAIN : _ENOMEM;
    }'''
assert body.count(start)==1
if a.fail_child_starts:
 replacement=replacement.replace('int err = pthread_create(&task->thread, &task_thread_attr, task_thread, task);','(void)task; (void)task_thread; int err = EAGAIN; /* explicit host negative control; no native child created */')
body=body.replace(start,replacement)
if a.join_guests:
 for f in ['JoinableGuests.c','JoinableGuests.h']:shutil.copy2(lab/'app'/f,out/f)
 body='#include "JoinableGuests.c"\n'+body
 detached='pthread_attr_setdetachstate(&task_thread_attr, PTHREAD_CREATE_DETACHED);'
 assert body.count(detached)==1
 body=body.replace(detached,'pthread_attr_setdetachstate(&task_thread_attr, PTHREAD_CREATE_JOINABLE);')
 creation='int err = pthread_create(&task->thread, &task_thread_attr, task_thread, task);'
 assert body.count(creation)==1
 body=body.replace(creation,'int err = ideck_joinable_guest_start(&task->thread, &task_thread_attr, task_thread, task);')
body+='''
/* Outside the original entry's TLB/fiber cleanup: runs after those handlers. */
void task_run_current(void) {
    pthread_cleanup_push(ideck_guest_lifetime_retire, NULL);
    ideck_original_task_run_current();
    pthread_cleanup_pop(1);
}
'''
generated=out/'task.c';generated.write_text(body)
entries=json.loads((build/'compile_commands.json').read_text())
entry=next(x for x in entries if x['file'].endswith('/kernel/task.c'))
entry_path=Path(entry['file'])
if not entry_path.is_absolute():entry_path=Path(entry['directory'])/entry_path
assert entry_path.read_bytes()==original
cmd=shlex.split(entry['command']);cmd[cmd.index(entry['file'])]=str(generated)
obj=out/'kernel_task.c.o';cmd[cmd.index('-o')+1]=str(obj)
for key,value in [('-MF',out/'task.d'),('-MQ',obj)]:
 if key in cmd:cmd[cmd.index(key)+1]=str(value)
if a.sanitize:cmd+=['-fsanitize=address,undefined','-fno-omit-frame-pointer']
if a.guest_waves:cmd+=['-DIDECK_LAB_GUEST_WAVES=1']
subprocess.run(cmd,cwd=entry['directory'],check=True)
basehash=hashof(archive);shutil.copy2(archive,out/'libish.a')
subprocess.run(['xcrun','ar','r',str(out/'libish.a'),str(obj)],check=True)
assert hashof(archive)==basehash
(out/'build-evidence.json').write_text(json.dumps(dict(linuxrunner=pin,base_archive_sha256=basehash,
 base_archive_unchanged=True,generated_task_sha256=hashof(generated),hooks_sha256=hashof(out/'GuestLifetime.c'),header_sha256=hashof(out/'GuestLifetime.h'),
 archive_sha256=hashof(out/'libish.a'),sanitized_translation_unit=a.sanitize,injected_child_create_failure=a.fail_child_starts,
 joinable_child_prototype=a.join_guests,guest_wave_prototype=a.guest_waves,join_registry_sha256=hashof(out/'JoinableGuests.c') if a.join_guests else None,
 marker='IDECK_GUEST_LIFETIME_V1'),indent=2)+'\n')
print('Copied guest lifetime archive built; inputs/vendor unchanged')
