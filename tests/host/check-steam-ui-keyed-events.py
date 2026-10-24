#!/usr/bin/env python3
"""Exercise production per-process default-event resolver with concurrent callers."""
import pathlib, subprocess, tempfile
root=pathlib.Path(__file__).resolve().parents[2]
s=(root/'build/ntdll-unix/sync_ios.c').read_text()
resolver=s[s.index('static pthread_mutex_t ios_keyed_lock'):s.index('static void ios_keyed_observe')]
harness=r'''
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <assert.h>
typedef void *HANDLE; typedef unsigned NTSTATUS; typedef unsigned ULONG_PTR;
typedef struct { int unused; } PEB;
typedef struct { PEB *Peb; struct { HANDLE UniqueProcess; } ClientId; } TEB;
static _Thread_local TEB thread_teb;
#define NtCurrentTeb() (&thread_teb)
#define STATUS_SUCCESS 0
#define STATUS_NO_MEMORY 0xc0000017U
#define GENERIC_READ 1
#define GENERIC_WRITE 2
static unsigned creates; static int fail_create;
static NTSTATUS NtCreateKeyedEvent(HANDLE *out,int access,void *attr,int flags) {
    (void)access;(void)attr;(void)flags;
    if(fail_create)return STATUS_NO_MEMORY;
    *out=(HANDLE)(uintptr_t)(0x1000+ ++creates);return 0;
}
'''
tests=r'''
static PEB processes[130]; static HANDLE resolved[8];
static void *worker(void *arg) {
    unsigned n=(unsigned)(uintptr_t)arg;
    thread_teb.Peb=&processes[0];thread_teb.ClientId.UniqueProcess=(HANDLE)1;
    assert(!ios_keyed_resolve(&resolved[n]));return NULL;
}
int main(void) {
    HANDLE h=NULL;pthread_t threads[8];unsigned i;
    unsetenv("MADEIRA_STEAM_UI_SESSION");
    assert(!ios_keyed_resolve(&h)&&!h&&!creates);
    setenv("MADEIRA_STEAM_UI_SESSION","1",1);
    h=(HANDLE)42;assert(!ios_keyed_resolve(&h)&&h==(HANDLE)42&&!creates);
    for(i=0;i<8;i++)assert(!pthread_create(&threads[i],NULL,worker,(void *)(uintptr_t)i));
    for(i=0;i<8;i++){pthread_join(threads[i],NULL);assert(resolved[i]==resolved[0]);}
    assert(creates==1);
    thread_teb.Peb=&processes[1];thread_teb.ClientId.UniqueProcess=(HANDLE)2;h=NULL;
    fail_create=1;assert(ios_keyed_resolve(&h)==STATUS_NO_MEMORY&&!h);
    fail_create=0;assert(!ios_keyed_resolve(&h)&&h!=resolved[0]&&creates==2);
    for(i=2;i<128;i++) {
        thread_teb.Peb=&processes[i];thread_teb.ClientId.UniqueProcess=(HANDLE)(uintptr_t)(i+1);h=NULL;
        assert(!ios_keyed_resolve(&h)&&h);
    }
    thread_teb.Peb=&processes[128];thread_teb.ClientId.UniqueProcess=(HANDLE)129;h=NULL;
    assert(ios_keyed_resolve(&h)==STATUS_NO_MEMORY&&!h&&creates==128);
    puts("PASS: production keyed resolver isolation, concurrent identity, explicit/ordinary paths, create failure and bounded capacity");
}
'''
with tempfile.TemporaryDirectory() as d:
    p=pathlib.Path(d);(p/'test.c').write_text(harness+resolver+tests)
    subprocess.run(['clang','-std=c11','-Werror','-Wno-pointer-to-int-cast','-fsanitize=address,undefined','-pthread',str(p/'test.c'),'-o',str(p/'check')],check=True)
    subprocess.run([str(p/'check')],check=True)
