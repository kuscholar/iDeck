#!/usr/bin/env python3
"""Run the actual opt-in x64 ROOT iterator, including concurrent enumerations."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
source = (root / "build/crypto-unix/crypt32_unixlib_ios.c").read_text()
start = source.index("extern int madeira_cef64_standalone_layout(void);")
end = source.index("/* The WoW64 enumeration:", start)
actual = source[start:end]
with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    (tmp / "test.c").write_text(r'''
#include <assert.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "wine/list.h"
typedef int NTSTATUS;
#define STATUS_SUCCESS 0
#define STATUS_INVALID_PARAMETER -1
#define STATUS_NO_MORE_ENTRIES -2
struct enum_root_certs_params { void *buffer; size_t size; size_t *needed; };
struct root_cert { struct list entry; size_t size; unsigned char data[16]; };
static struct list root_cert_list=LIST_INIT(root_cert_list);
static pthread_mutex_t ios_root_lock=PTHREAD_MUTEX_INITIALIZER;
static int loaded, loads, held=1, legacy_calls;
static const char *option="1", *session="1";
static void ios_load_roots_locked(void) { if(!loaded){loaded=1;loads++;} }
static NTSTATUS ios_enum_root_certs_legacy(void *p) { (void)p;legacy_calls++;return 17; }
static _Thread_local struct { void *Peb; } teb;
#define NtCurrentTeb() (&teb)
static const char *option_getenv(const char *key) {
 if(!strcmp(key,"MADEIRA_CEF64_ROOT_STORE"))return option;
 assert(!strcmp(key,"MADEIRA_STEAM_UI_SESSION"));return session;
}
#define getenv option_getenv
int madeira_cef64_standalone_layout(void) { return held; }
''' + actual + r'''
static void one_walk(void) {
 const size_t sizes[]={2,4,1};unsigned char b[16];size_t needed=0;
 struct enum_root_certs_params p={b,0,&needed};
 for(unsigned i=0;i<3;i++){
  memset(b,0xcc,sizeof(b));p.size=0;
  assert(enum_root_certs(&p)==0 && needed==sizes[i] && b[0]==0xcc);
  p.size=needed;assert(enum_root_certs(&p)==0 && needed==sizes[i]);
  for(size_t j=0;j<needed;j++)assert(b[j]==i+1);
 }
 assert(enum_root_certs(&p)==STATUS_NO_MORE_ENTRIES);
}
static pthread_barrier_t barrier;
static void *worker(void *id) {
 teb.Peb=id;pthread_barrier_wait(&barrier);one_walk();one_walk();return NULL;
}
int main(void) {
 struct root_cert certs[3]={0};size_t sizes[]={2,4,1};
 for(unsigned i=0;i<3;i++){certs[i].size=sizes[i];memset(certs[i].data,i+1,sizes[i]);list_add_tail(&root_cert_list,&certs[i].entry);}
 teb.Peb=(void*)1;one_walk();one_walk();assert(loads==1);
 unsigned char b[16]={0};size_t needed=0;struct enum_root_certs_params p={b,sizeof(b),&needed};
 assert(enum_root_certs(&p)==0 && b[0]==1);
 teb.Peb=(void*)2;assert(enum_root_certs(&p)==0 && b[0]==1);
 teb.Peb=NULL;assert(enum_root_certs(&p)==STATUS_INVALID_PARAMETER);
 teb.Peb=(void*)1;
 const char *bad[]={NULL,"0","11","true","1 "};
 for(unsigned i=0;i<5;i++){option=bad[i];assert(enum_root_certs(&p)==17);}option="1";
 for(unsigned i=0;i<5;i++){session=bad[i];assert(enum_root_certs(&p)==17);}session="1";
 held=0;assert(enum_root_certs(&p)==17);held=-1;assert(enum_root_certs(&p)==17);held=1;
 assert(legacy_calls==12);
 pthread_t threads[64];pthread_barrier_init(&barrier,NULL,64);
 for(uintptr_t i=0;i<64;i++)assert(!pthread_create(&threads[i],NULL,worker,(void*)(i+3)));
 for(unsigned i=0;i<64;i++)assert(!pthread_join(threads[i],NULL));
 pthread_barrier_destroy(&barrier);
 assert(loads==1 && list_count(&root_cert_list)==3);
 for(unsigned i=0;i<3;i++)for(size_t j=0;j<certs[i].size;j++)assert(certs[i].data[j]==i+1);
 puts("PASS actual ROOT iterator: immutable trust bytes, retry/end/reset/owner/gates and64 concurrent readers");
 return 0;
}
''')
    # macOS has no POSIX barriers; use a small condition-variable test barrier.
    p = tmp / "test.c"
    s = p.read_text().replace("static pthread_barrier_t barrier;", r'''
static struct { pthread_mutex_t m; pthread_cond_t c; unsigned n; } barrier={PTHREAD_MUTEX_INITIALIZER,PTHREAD_COND_INITIALIZER,0};
static void test_barrier(void) {
 pthread_mutex_lock(&barrier.m);barrier.n++;
 if(barrier.n==64)pthread_cond_broadcast(&barrier.c);
 else while(barrier.n<64)pthread_cond_wait(&barrier.c,&barrier.m);
 pthread_mutex_unlock(&barrier.m);
}
''').replace("pthread_barrier_wait(&barrier)", "test_barrier()")
    s = s.replace("pthread_barrier_init(&barrier,NULL,64);", "")
    s = s.replace("pthread_barrier_destroy(&barrier);", "")
    p.write_text(s)
    subprocess.run(["clang", "-std=c11", "-Wall", "-Wextra", "-Werror", "-pthread",
                    "-fsanitize=address,undefined", "-I", str(root / "wine/include"),
                    str(p), "-o", str(tmp / "test")], check=True)
    subprocess.run([str(tmp / "test")], check=True, timeout=30)
