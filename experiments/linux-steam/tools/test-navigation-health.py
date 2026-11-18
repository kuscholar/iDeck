#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Run the real numeric health writer past its log cap; no guest/UI stubs."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('output', type=Path)
a = p.parse_args()
out = a.output.resolve()
assert str(out).startswith('/Volumes/easystore/') and not out.exists()
out.mkdir(mode=0o700, parents=True)
lab = Path(__file__).resolve().parents[1]
fixture = r'''
#include "NativeKernelLog.h"
#include <assert.h>
#include <errno.h>
#include <pthread.h>
#include <stdio.h>
#include <stdint.h>
#include <stdatomic.h>
#include <sys/wait.h>
#include <unistd.h>
#if IDECK_LAB_NATIVE_JIT
#include "LabNativeJIT.h"
void ideck_lab_native_jit_read(struct ideck_lab_native_jit_stats *s){
    /* Serializer bounds fixture, not actual native execution evidence. */
    *s=(struct ideck_lab_native_jit_stats){-1,UINT64_MAX,UINT64_MAX,UINT64_MAX};
}
#endif
#if IDECK_LAB_MAP_PTE_PREFLIGHT
_Atomic uint64_t ideck_map_pte_allocation_failures=11; /* serializer fixture only */
#endif
#if IDECK_LAB_FIBER_HASH_GUARD
_Atomic uint64_t ideck_fiber_hash_growth_failures=7; // serializer fixture only
#endif
#if IDECK_LAB_COW_BROKER
#include "CowBackingBroker.h"
#include <sys/mman.h>
#endif
#if IDECK_LAB_FRAME_SNAPSHOT_POOL
extern void pool_control_prepare(void);
extern void pool_control_release(void);
#endif
#if IDECK_LAB_CLI_INPUT
static void *writer(void *unused){
    (void)unused;
    for(unsigned i=0;i<500;i++)assert(!ideck_native_note_navigation(i%10));
    return NULL;
}
#endif
int main(int argc,char **argv){
    assert(argc==2);
#if IDECK_LAB_CLI_INPUT
    assert(ideck_native_note_navigation(0)==-ENODEV);
#endif
    assert(!ideck_native_log_start(argv[1]));
#if IDECK_LAB_FRAME_SNAPSHOT_POOL
    pool_control_prepare();
#endif
    assert(!ideck_native_health(60,"guest-running",7,0));
#if IDECK_LAB_CLI_INPUT
    assert(ideck_native_note_navigation(10)==-EINVAL);
    assert(ideck_native_note_navigation(UINT32_MAX)==-EINVAL);
    pthread_t threads[8];
    for(unsigned i=0;i<8;i++)assert(!pthread_create(&threads[i],NULL,writer,NULL));
    for(unsigned i=0;i<100;i++)assert(!ideck_native_health(60,"guest-running",7,0));
    for(unsigned i=0;i<8;i++)assert(!pthread_join(threads[i],NULL));
    pid_t child=fork();assert(child>=0);
    if(!child)_exit(ideck_native_note_navigation(0)==-EXDEV?0:1);
    int status;assert(waitpid(child,&status,0)==child&&WIFEXITED(status)&&!WEXITSTATUS(status));
#endif
    char line[1024];for(unsigned i=0;i<1023;i++)line[i]='x';line[1023]=0;
    for(unsigned i=0;i<5000;i++)ideck_native_log_line(line);
    size_t capped=ideck_native_log_bytes();assert(capped<=IDECK_NATIVE_LOG_LIMIT);
#if IDECK_LAB_CLI_INPUT
    assert(!ideck_native_note_navigation(9));
#endif
    assert(!ideck_native_health(60,"guest-running",7,0));
    assert(ideck_native_log_bytes()==capped);
#if IDECK_LAB_COW_BROKER
    void *a=ideck_cow_broker_allocate(4096),*b=ideck_cow_broker_allocate(8192);
    assert(a!=MAP_FAILED&&b!=MAP_FAILED);
    assert(ideck_cow_broker_release_owned(a,4096)==1);
    assert(!ideck_native_health(60,"guest-running",7,0));
    assert(ideck_cow_broker_release_owned(b,8192)==1);
    assert(!ideck_native_health(60,"guest-running",7,0));
#endif
#if IDECK_LAB_FRAME_SNAPSHOT_POOL
    pool_control_release();
    assert(!ideck_native_health(60,"guest-running",7,0));
#endif
    puts(ideck_native_health_name());return 0;
}
'''
(out/'control.c').write_text(fixture)
(out/'pool-control.m').write_text('''#import "FrameSnapshotPool.h"
#include <assert.h>
static IDECKFrameSnapshotPool *pool;static NSData *frame;
void pool_control_prepare(void){@autoreleasepool{
    pool=[[IDECKFrameSnapshotPool alloc]initWithWidth:16 height:16];assert(pool);
    frame=[pool snapshotPixels:[NSData dataWithLength:16*16*4] width:16 height:16];assert(frame);
}}
void pool_control_release(void){frame=nil;pool=nil;}
'''.replace('[NSData dataWithLength:', '[NSMutableData dataWithLength:'))
tests = []
for enabled, policy, broker, snapshot,pool,hashguard,jit,pte in ((0,0,0,0,0,0,0,0),(1,0,0,0,0,0,0,0),(1,1,0,0,0,0,0,0),(1,1,1,0,0,0,0,0),(1,1,1,1,0,0,0,0),(1,1,1,0,1,0,0,0),(1,1,1,0,1,1,0,0),(1,1,1,0,1,1,1,0),(1,1,1,0,1,1,1,1)):
    private = out/f'gate{enabled}-policy{policy}-broker{broker}-snapshot{snapshot}-pool{pool}-hash{hashguard}-jit{jit}-pte{pte}'
    private.mkdir(mode=0o700)
    binary = out/f'control{enabled}-policy{policy}-broker{broker}-snapshot{snapshot}-pool{pool}-hash{hashguard}-jit{jit}-pte{pte}'
    command = ['xcrun', 'clang', '-Wall', '-Wextra', '-Werror',
               '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
               f'-DIDECK_LAB_CLI_INPUT={enabled}', f'-DIDECK_LAB_GAME_FILE_POLICY={policy}',
               f'-DIDECK_LAB_COW_BROKER={broker}',
               f'-DIDECK_LAB_RFB_CHECKED_SNAPSHOT={snapshot}',
               f'-DIDECK_LAB_FRAME_SNAPSHOT_POOL={pool}',
               f'-DIDECK_LAB_FIBER_HASH_GUARD={hashguard}',
               f'-DIDECK_LAB_NATIVE_JIT={jit}',
               f'-DIDECK_LAB_MAP_PTE_PREFLIGHT={pte}',
               '-I'+str(lab/'app'), str(out/'control.c'), str(lab/'app/NativeKernelLog.c')]
    if policy:
        command += [str(lab/'app'/name) for name in
                    ('GameFilePolicy.c', 'GameFiles.c', 'LaunchProtocol.c')]
    if broker:command += [str(lab/'app/CowBackingBroker.c')]
    if snapshot:command += ['-fobjc-arc','-fblocks','-I'+str(lab.parents[1]/'vendor/LinuxRunner/app/LinuxRunner'),str(lab/'app/CheckedFrameSnapshot.m'),str(lab.parents[1]/'vendor/LinuxRunner/app/LinuxRunner/RFBProtocol.c'),'-framework','Foundation']
    if pool:command += ['-fobjc-arc','-fblocks','-I'+str(lab.parents[1]/'vendor/LinuxRunner/app/LinuxRunner'),str(lab/'app/FrameSnapshotPool.m'),str(out/'pool-control.m'),str(lab.parents[1]/'vendor/LinuxRunner/app/LinuxRunner/RFBProtocol.c'),'-framework','Foundation']
    command += ['-o', str(binary)]
    subprocess.run(command, check=True)
    result = subprocess.run([binary, private], check=True, capture_output=True, text=True, timeout=60)
    receipt = json.loads((private/result.stdout.strip()).read_text())
    assert receipt['append_log_capped'] and receipt['append_log_stopped']
    assert receipt['tracked_guest_entries'] == 7
    if enabled:
        assert receipt['cli_navigation'] == {'sequence': 4001, 'last_action': 9,
                                             'dispatch_only': True, 'physical_touch_test': False}
    else:
        assert 'cli_navigation' not in receipt
    if policy:
        assert receipt['file_policy']['query_status'] < 0
        assert not receipt['file_policy']['game_launched']
    else:
        assert 'file_policy' not in receipt
    if broker:
        s=receipt['cow_broker']
        assert s['alloc']==s['release']==2 and s['map_attempts']==s['unmaps']==1
        assert s['live_slots']==s['live_chunks']==s['logical_bytes']==s['reserved_native_bytes']==0
        assert s['advice_calls']==1 and not s['advice_failures'] and not s['ownership_errors']
        assert not s['physical_reclaim_measured']
    else:assert 'cow_broker' not in receipt
    if snapshot:assert receipt['frame_snapshot']==dict(calls=0,failures=0,live_frames=0,live_bytes=0,peak_live_bytes=0,releases=0)
    else:assert 'frame_snapshot' not in receipt
    if pool:assert receipt['frame_pool']==dict(preparations=1,allocation_failures=0,native_buffers=0,native_bytes=0,calls=1,invalid=0,exhausted=0,live_slots=0,peak_slots=1,releases=1)
    else:assert 'frame_pool' not in receipt
    if hashguard:assert receipt['fiber_hash_growth_failures']==7
    else:assert 'fiber_hash_growth_failures' not in receipt
    if jit:assert receipt['native_jit']==dict(compiled=True,activation_status=-1,blocks=2**64-1,segments=2**64-1,code_bytes=2**64-1,TXM_requested=False)
    else:assert 'native_jit' not in receipt
    if pte:assert receipt['map_pte_allocation_failures']==11
    else:assert 'map_pte_allocation_failures' not in receipt
    tests.append({'gate': enabled, 'file_policy_gate': policy, 'broker_gate':broker,'command': command, 'exit': result.returncode,
                  'receipt': receipt})
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
(out/'evidence.json').write_text(json.dumps({
    'scope': 'HOST real native health writer, 8 concurrent writers/4001 dispatch counts, '
             'invalid/unstarted/foreign PID refusals and post-cap persistence, gates 0/1; '
             'NOT Darwin notification delivery, Steam response, physical touch or iPad validation',
    'tests': tests,
    'sources_sha256': {path.name: sha(path) for path in
                       [lab/'app/NativeKernelLog.c', lab/'app/NativeKernelLog.h', out/'control.c']}
}, indent=2)+'\n')
print('HOST numeric navigation receipt: gates0/1, concurrency/refusals/post-cap PASS')
