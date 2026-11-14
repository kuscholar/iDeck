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
#include <sys/wait.h>
#include <unistd.h>
#if IDECK_LAB_CLI_INPUT
static void *writer(void *unused){
    (void)unused;
    for(unsigned i=0;i<500;i++)assert(!ideck_native_note_navigation(i%9));
    return NULL;
}
#endif
int main(int argc,char **argv){
    assert(argc==2);
#if IDECK_LAB_CLI_INPUT
    assert(ideck_native_note_navigation(0)==-ENODEV);
#endif
    assert(!ideck_native_log_start(argv[1]));
    assert(!ideck_native_health(60,"guest-running",7,0));
#if IDECK_LAB_CLI_INPUT
    assert(ideck_native_note_navigation(9)==-EINVAL);
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
    assert(!ideck_native_note_navigation(8));
#endif
    assert(!ideck_native_health(60,"guest-running",7,0));
    assert(ideck_native_log_bytes()==capped);
    puts(ideck_native_health_name());return 0;
}
'''
(out/'control.c').write_text(fixture)
tests = []
for enabled, policy in ((0, 0), (1, 0), (1, 1)):
    private = out/f'gate{enabled}-policy{policy}'
    private.mkdir(mode=0o700)
    binary = out/f'control{enabled}-policy{policy}'
    command = ['xcrun', 'clang', '-Wall', '-Wextra', '-Werror',
               '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
               f'-DIDECK_LAB_CLI_INPUT={enabled}', f'-DIDECK_LAB_GAME_FILE_POLICY={policy}',
               '-I'+str(lab/'app'), str(out/'control.c'), str(lab/'app/NativeKernelLog.c')]
    if policy:
        command += [str(lab/'app'/name) for name in
                    ('GameFilePolicy.c', 'GameFiles.c', 'LaunchProtocol.c')]
    command += ['-o', str(binary)]
    subprocess.run(command, check=True)
    result = subprocess.run([binary, private], check=True, capture_output=True, text=True, timeout=25)
    receipt = json.loads((private/result.stdout.strip()).read_text())
    assert receipt['append_log_capped'] and receipt['append_log_stopped']
    assert receipt['tracked_guest_entries'] == 7
    if enabled:
        assert receipt['cli_navigation'] == {'sequence': 4001, 'last_action': 8,
                                             'dispatch_only': True, 'physical_touch_test': False}
    else:
        assert 'cli_navigation' not in receipt
    if policy:
        assert receipt['file_policy']['query_status'] < 0
        assert not receipt['file_policy']['game_launched']
    else:
        assert 'file_policy' not in receipt
    tests.append({'gate': enabled, 'file_policy_gate': policy, 'command': command, 'exit': result.returncode,
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
