#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Actual pthread join controls: held TLS destructor and creation failure paths."""
import argparse,hashlib,importlib.util,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);a=p.parse_args()
repo=Path(__file__).resolve().parents[3];source=repo/'experiments/linux-steam/app';out=a.output.resolve()
assert str(out).startswith('/Volumes/easystore/') and not out.exists();out.mkdir(mode=0o700,parents=True)
fixture=r'''#include "WineInitialJoin.h"
#include <assert.h>
#include <errno.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
static pthread_mutex_t gate=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t condition=PTHREAD_COND_INITIALIZER;
static pthread_key_t key;
static int inside_destructor,release_destructor;
static atomic_int calls,body_returned;
static int fail_call;
void wineserver_stop(void);
pthread_t g_wineserver_thread;
int g_wineserver_should_stop, g_wineserver_running;
int control_create(pthread_t *thread,const pthread_attr_t *attr,void *(*entry)(void *),void *argument){
    if(atomic_fetch_add(&calls,1)+1==fail_call)return EAGAIN;
    return pthread_create(thread,attr,entry,argument);
}
static void destroy(void *value){
    assert(value);pthread_mutex_lock(&gate);inside_destructor=1;pthread_cond_broadcast(&condition);
    while(!release_destructor)pthread_cond_wait(&condition,&gate);
    pthread_mutex_unlock(&gate);
}
static void *empty(void *argument);
static void *guest(void *argument){
    (void)argument;
    assert(ideck_lab_wine_initial_report_result(0,0)==EINVAL);
    assert(ideck_lab_wine_initial_report_result(IDECK_WINE_BODY_NORMAL_RETURN,1)==EINVAL);
    assert(!ideck_lab_wine_initial_report_result(IDECK_WINE_BODY_LONGJMP,0xc0000005u));
    assert(ideck_lab_wine_initial_report_result(IDECK_WINE_BODY_NORMAL_RETURN,0)==EALREADY);
    assert(ideck_lab_wine_initial_report_server_join(0,EINVAL)==EINVAL);
    assert(!pthread_create(&g_wineserver_thread,NULL,empty,NULL));
    wineserver_stop();
    assert(g_wineserver_should_stop);
    assert(ideck_lab_wine_initial_report_server_join(0,0)==EALREADY);
    assert(!pthread_setspecific(key,(void *)1));atomic_store(&body_returned,1);return NULL;
}
static void *empty(void *argument){return argument;}
static void *normal(void *argument){
    assert(!ideck_lab_wine_initial_report_result(IDECK_WINE_BODY_NORMAL_RETURN,0));
    if(argument){
        g_wineserver_thread=pthread_self();
        wineserver_stop();
    }else{
        g_wineserver_thread=NULL;
        wineserver_stop();
    }
    return argument;
}
int main(int argc,char **argv){
    assert(argc==2);fail_call=atoi(argv[1]);assert(!pthread_key_create(&key,destroy));
    struct ideck_wine_initial_snapshot value;assert(!ideck_lab_wine_initial_snapshot(&value));
    assert(!value.generation&&!ideck_lab_wine_initial_ready());
    assert(!value.body_result_source);
    assert(!value.server_join_state);
    assert(ideck_lab_wine_initial_report_server_join(1,0)==ENODEV);
    assert(ideck_lab_wine_initial_report_result(IDECK_WINE_BODY_NORMAL_RETURN,0)==ENODEV);
    pthread_attr_t attr;assert(!pthread_attr_init(&attr));assert(!pthread_attr_setdetachstate(&attr,PTHREAD_CREATE_DETACHED));
    pthread_t thread;assert(ideck_lab_wine_initial_create(&thread,&attr,guest,NULL)==EINVAL);
    assert(!ideck_lab_wine_initial_snapshot(&value)&&!value.generation);pthread_attr_destroy(&attr);
    if(fail_call==1){
        assert(ideck_lab_wine_initial_create(&thread,NULL,guest,NULL)==EAGAIN);
        assert(!ideck_lab_wine_initial_snapshot(&value)&&value.phase==IDECK_WINE_INITIAL_START_FAILED&&value.create_error==EAGAIN&&!value.initial_created);
        assert(!ideck_lab_wine_initial_ready());
    }
    assert(!ideck_lab_wine_initial_create(&thread,NULL,guest,NULL));
    pthread_mutex_lock(&gate);while(!inside_destructor)pthread_cond_wait(&condition,&gate);pthread_mutex_unlock(&gate);
    assert(atomic_load(&body_returned));
    assert(!ideck_lab_wine_initial_snapshot(&value)&&value.initial_created&&!value.initial_joined);
    assert(value.body_result_source==IDECK_WINE_BODY_LONGJMP&&value.body_exit_code==0xc0000005u);
    assert(value.server_join_state==IDECK_WINE_SERVER_JOINED&&!value.server_join_error);
    assert(ideck_lab_wine_initial_report_server_join(1,0)==EPERM);
    assert(ideck_lab_wine_initial_report_result(IDECK_WINE_BODY_LONGJMP,0)==EPERM);
    assert(ideck_lab_wine_initial_ready()==EBUSY);
    pthread_t another;assert(ideck_lab_wine_initial_create(&another,NULL,empty,NULL)==EBUSY);
    if(fail_call==2)assert(value.phase==IDECK_WINE_INITIAL_OBSERVER_FAILED&&value.observer_error==EAGAIN);
    else assert(value.phase==IDECK_WINE_INITIAL_ACTIVE&&!value.observer_error);
    pthread_mutex_lock(&gate);release_destructor=1;pthread_cond_broadcast(&condition);pthread_mutex_unlock(&gate);
    if(fail_call==2){
        /* Only this injected failure has no observer: own the one join here. */
        assert(!pthread_join(thread,NULL));
        assert(!ideck_lab_wine_initial_snapshot(&value)&&!value.initial_joined&&value.observer_error==EAGAIN);
        assert(ideck_lab_wine_initial_ready()==EBUSY);
    }else{
        for(unsigned i=0;i<3000;i++){assert(!ideck_lab_wine_initial_snapshot(&value));if(value.initial_joined)break;usleep(1000);}
        assert(value.initial_joined&&value.phase==IDECK_WINE_INITIAL_JOINED&&!value.observer_error);
        assert(!ideck_lab_wine_initial_ready());uint64_t previous=value.generation;
        assert(!ideck_lab_wine_initial_create(&another,NULL,empty,NULL));
        for(unsigned i=0;i<3000;i++){assert(!ideck_lab_wine_initial_snapshot(&value));if(value.initial_joined)break;usleep(1000);}
        assert(value.initial_joined&&value.generation==previous+1);
        assert(!value.server_join_state&&!value.server_join_error);
        assert(!value.body_result_source&&!value.body_exit_code); /* Unknown is not successful exit0. */
        assert(!ideck_lab_wine_initial_create(&another,NULL,normal,NULL));
        for(unsigned i=0;i<3000;i++){assert(!ideck_lab_wine_initial_snapshot(&value));if(value.initial_joined)break;usleep(1000);}
        assert(value.initial_joined&&value.generation==previous+2);
        assert(value.body_result_source==IDECK_WINE_BODY_NORMAL_RETURN&&!value.body_exit_code);
        assert(value.server_join_state==IDECK_WINE_SERVER_NO_HANDLE&&!value.server_join_error);
        assert(!ideck_lab_wine_initial_create(&another,NULL,normal,(void *)1));
        for(unsigned i=0;i<3000;i++){assert(!ideck_lab_wine_initial_snapshot(&value));if(value.initial_joined)break;usleep(1000);}
        assert(value.initial_joined&&value.generation==previous+3);
        assert(value.server_join_state==IDECK_WINE_SERVER_JOIN_FAILED&&value.server_join_error>0);
        printf("HOST server self-join refusal=%d\n",value.server_join_error);
    }
    assert(!pthread_key_delete(key));puts("HOST real initial pthread/TLS join and failure controls PASS; no Wine/Steam/game/return proof");return 0;
}
'''
(out/'control.c').write_text(fixture)
spec=importlib.util.spec_from_file_location('join_patch',repo/'experiments/linux-steam/tools/wine-initial-join.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
server_original=repo/'app/Madeira/WineServerBridge.m'
server=module.patched_server(server_original.read_text())
(out/'WineServerBridge-private.m').write_text(server)
# Exercise the exact copied stop function with owned host fixture globals.
stop=server[server.index('void wineserver_stop(void) {'):]
(out/'server-stop-control.c').write_text('''#include "WineInitialJoin.h"
extern pthread_t g_wineserver_thread;
extern int g_wineserver_should_stop, g_wineserver_running;
static void wine_log_msg(const char *format, ...) {(void)format;}
'''+stop)
common=['xcrun','clang','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-g','-I',str(source)]
commands=[common+['-Dpthread_create=control_create','-c',str(source/'WineInitialJoin.c'),'-o',str(out/'join.o')],common+[str(out/'control.c'),str(out/'server-stop-control.c'),str(out/'join.o'),'-o',str(out/'control')]]
for cmd in commands:subprocess.run(cmd,check=True)
with (out/'control.log').open('x') as log:
    for mode in [0,1,2]:subprocess.run([out/'control',str(mode)],stdout=log,stderr=subprocess.STDOUT,timeout=20,check=True)
original=(repo/'app/Madeira/WineProcessBridge.m').read_text();adapted=module.patched(original)
assert adapted.index('ideck_lab_wine_initial_ready()')<adapted.index('    if (g_prefix_path) free(g_prefix_path);',adapted.index('int wine_process_start('))
assert 'pthread_detach(g_wine_thread)' not in adapted
assert adapted.count('ideck_lab_wine_initial_report_result(')==2
assert adapted.index('ideck_lab_wine_initial_report_result(IDECK_WINE_BODY_LONGJMP')<adapted.index('        g_wine_running = 0;',adapted.index('        if (setjmp('))
(out/'WineProcessBridge-private.m').write_text(adapted)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(out/'evidence.json').write_text(json.dumps({'scope':'HOST server stop join success and missing handle with copied bridge body, self-join refusal from the host pthread API, actual initial pthread+held TLS destructor, body-result owner/duplicate/invalid refusals, uint32 abnormal vs known-normal vs unknown, generation reset, injected create/observer failures and private exact bridge hook; NOT actual Wine workers/device/game/return proof','commands':commands,'modes':[0,1,2],'exit':0,'join_source_sha256':sha(source/'WineInitialJoin.c'),'bridge_original_sha256':sha(repo/'app/Madeira/WineProcessBridge.m'),'bridge_private_sha256':sha(out/'WineProcessBridge-private.m'),'server_original_sha256':sha(server_original),'server_private_sha256':sha(out/'WineServerBridge-private.m'),'server_stop_fixture_sha256':sha(out/'server-stop-control.c'),'fixture_sha256':sha(out/'control.c'),'log_sha256':sha(out/'control.log')},indent=2)+'\n')
print((out/'control.log').read_text())
