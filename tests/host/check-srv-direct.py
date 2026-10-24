#!/usr/bin/env python3
"""Direct wineserver requests (env.MADEIRA_SRV_DIRECT, off by default); no Wine runs.

With the switch a listed request runs on the calling thread under the server's lock
(build/wineserver/request_ios.c ios_srv_direct_call) instead of travelling through the
thread's request pipe to the server thread; the server loop holds the same lock for
everything it does except its sleep (build/wineserver/fd_ios.c ios_srv_loop_enter/leave/
exit). Horizon Zero Dawn's menu sent ~6,900 requests a second (build 493, 2026-10-11),
each two thread switches and five or more system calls.

Compiles the production ios_srv_loop_enter/leave/exit, ios_srv_direct_level,
ios_srv_run_direct and ios_srv_direct_call on this host with stand-ins (a pthread mutex for
os_unfair_lock, a fake thread table and handler table) and checks, under ThreadSanitizer and
then AddressSanitizer + UBSan:
  - mutual exclusion: client threads running a handler that does unprotected
    read-modify-write work on the server's state, against a loop thread doing the same
    between sleeps, while a third thread turns the switch off, to 1 and to 2: no update is
    lost, no handler ever overlaps the loop's work, and no handler runs once the loop has
    seen the switch off;
  - not taken (0, the pipe): switch off, loop not running or exited, an unlisted request, a
    level-2 request at level 1, an unknown thread, another thread's TEB, a thread with a
    request half read or a reply half written, data sizes that do not add up;
  - taken: the request and its data (three pieces) reach the handler as read_request leaves
    them, the reply and its data come back, the request data is freed, the census counts it;
  - a request that ends its thread returns -1, frees the request data once and leaves the
    caller's reply untouched (the caller then fails on its closed pipe, as today);
  - a timer added by a direct request wakes the loop once, after the lock is released.
Then textually: the whitelist (no thread or process lifetime, suspension, context, APC,
async I/O or message requests), the loop's lock discipline around its sleep, the timer flag
in add_timeout_user, the client hook in server_call_unlocked (after the abort and [bg-qos]
checks, before the write, only with the switch on), the bridge's per-launch global, the
catalog entry and the CI step.
Needs python3 and a C compiler with pthreads (CC, default cc).
"""
from pathlib import Path
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
FD = (ROOT / "build/wineserver/fd_ios.c").read_text(encoding="utf-8")
REQ = (ROOT / "build/wineserver/request_ios.c").read_text(encoding="utf-8")
NTDLL = (ROOT / "build/ntdll-unix/server_ios.c").read_text(encoding="utf-8")
BRIDGE = (ROOT / "app/Madeira/WineProcessBridge.m").read_text(encoding="utf-8")
CAT = (ROOT / "app/Madeira/ConfigCatalog.generated.swift").read_text(encoding="utf-8")
CI_FILE = ROOT / ".github/workflows/build-ipa.yml"   # the fork's CI only; upstream has no .github
CI = CI_FILE.read_text(encoding="utf-8") if CI_FILE.exists() else None

failures = []


def check(cond, what):
    print(("PASS " if cond else "FAIL ") + what)
    if not cond:
        failures.append(what)


def func_body(src, signature):
    i = src.find(signature)
    if i < 0:
        return ""
    j = src.find("{", i)
    depth = 0
    for k in range(j, len(src)):
        if src[k] == "{":
            depth += 1
        elif src[k] == "}":
            depth -= 1
            if depth == 0:
                return src[i:k + 1]
    return ""


enter = func_body(FD, "static void ios_srv_loop_enter(void)")
leave = func_body(FD, "static void ios_srv_loop_leave(void)")
exit_ = func_body(FD, "static void ios_srv_loop_exit(void)")
level = func_body(REQ, "static int ios_srv_direct_level( enum request req )")
run = func_body(REQ, "static int ios_srv_run_direct( struct thread *thread, union generic_reply *reply, void *reply_data )")
call = func_body(REQ, "int ios_srv_direct_call( unsigned int tid, client_ptr_t teb, const union generic_request *request,")
try_direct = func_body(NTDLL, "static BOOL ios_srv_try_direct( struct __server_request_info *req, unsigned int *status )")
check(all((enter, leave, exit_, level, run, call, try_direct)), "the loop's lock helpers, the direct-request functions "
      "and the client's ios_srv_try_direct are found")
g0 = REQ.find("os_unfair_lock ios_srv_lock = OS_UNFAIR_LOCK_INIT;")
g1 = REQ.find("extern volatile int g_madeira_srv_direct;  /* WineProcessBridge.m */")
check(0 <= g0 < g1, "the direct-request globals are found")
globals_block = REQ[g0:g1]

listed1 = re.findall(r"case (REQ_\w+):", level[:level.find("return 1;")])
listed2 = re.findall(r"case (REQ_\w+):", level[level.find("return 1;"):level.find("return 2;")])
names = sorted(set(listed1 + listed2))

harness = r'''
#define _GNU_SOURCE
#include <pthread.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/uio.h>
#include <time.h>
#include <unistd.h>

typedef pthread_mutex_t os_unfair_lock;
#define OS_UNFAIR_LOCK_INIT PTHREAD_MUTEX_INITIALIZER
#define os_unfair_lock_lock(l) pthread_mutex_lock(l)
#define os_unfair_lock_unlock(l) pthread_mutex_unlock(l)
#ifndef __APPLE__
typedef int qos_class_t;   /* Apple's <pthread.h> declares it (sys/qos.h) */
#endif
typedef unsigned int data_size_t;
typedef unsigned long long client_ptr_t;
enum request { REQ_new_thread, REQ_terminate_thread, REQ_suspend_thread, @NAMES@, REQ_NB_REQUESTS };
struct request_header { int req; data_size_t request_size; data_size_t reply_size; };
struct reply_header { unsigned int error; data_size_t reply_size; };
union generic_request { struct request_header request_header; char pad[64]; };
union generic_reply { struct reply_header reply_header; char pad[64]; };
enum run_state { RUNNING, TERMINATED };
struct thread
{
    int refs;
    unsigned int id;
    client_ptr_t teb;
    enum run_state state;
    void *request_fd, *reply_fd;
    union generic_request req;
    void *req_data;
    unsigned int req_toread;
    void *reply_data;
    unsigned int reply_size, reply_towrite;
    unsigned int error;
    int exit_code;
};
#define NTHREADS 8
static struct thread threads[NTHREADS];
static struct thread *current;
static unsigned int global_error;
static int debug_level;
static volatile long census_n, time_n, wake_n;
static void trace_request(void) {}
static void trace_reply( enum request req, union generic_reply *reply ) { (void)req; (void)reply; }
static void clear_error(void) { if (current) current->error = 0; else global_error = 0; }
static void set_error( unsigned int e ) { if (current) current->error = e; else global_error = e; }
static struct thread *get_thread_from_id( unsigned int id )
{
    int i;
    for (i = 0; i < NTHREADS; i++)
        if (threads[i].id == id) { threads[i].refs++; return &threads[i]; }
    set_error( 0xc000000b );
    return NULL;
}
static void release_object( struct thread *t ) { t->refs--; }
static void set_current_time(void) { time_n++; }
static void ios_req_census( struct thread *t, enum request req ) { (void)t; (void)req; census_n++; }
static void kill_thread( struct thread *t, int violent )
{
    (void)violent;
    t->state = TERMINATED;
    if (current == t) current = NULL;
    free( t->req_data ); t->req_data = NULL;
    free( t->reply_data ); t->reply_data = NULL;
    t->request_fd = t->reply_fd = NULL;
}
void ios_wineserver_wake(void) { __atomic_fetch_add( &wake_n, 1, __ATOMIC_SEQ_CST ); }
volatile int g_madeira_srv_direct;
static qos_class_t ios_srv_qos_set;
static int ios_srv_qos_follow_seen, ios_srv_qos_gen_seen;
static void (*req_handlers[REQ_NB_REQUESTS])( const void *req, void *reply );
@GLOBALS@
static int ios_srv_loop_locked;
@ENTER@
@LEAVE@
@EXIT@
@LEVEL@
@RUN@
@CALL@

/* ---- the client (build/ntdll-unix/server_ios.c) --------------------------------- */
#include <errno.h>
typedef int BOOL;
#define TRUE 1
#define FALSE 0
typedef unsigned long ULONG_PTR;
#define __SERVER_MAX_DATA 5
struct __server_request_info
{
    union { union generic_request req; union generic_reply reply; } u;
    unsigned int data_count;
    void *reply_data;
    struct { const void *ptr; data_size_t size; } data[__SERVER_MAX_DATA];
};
struct fake_teb { struct { void *UniqueProcess, *UniqueThread; } ClientId; };
static __thread struct fake_teb *fake_teb_now;
static struct fake_teb *NtCurrentTeb(void) { return fake_teb_now; }
#define HandleToULong(h) ((unsigned long)(unsigned long long)(h))
@TRY@

/* ---- the model ---------------------------------------------------------------- */
static long shared;                 /* server state, deliberately unprotected */
static volatile int inside;         /* 1 the loop, 2 a handler */
static volatile int stop;
static long loop_work, direct_ok, direct_pipe, off_runs;
static volatile int loop_saw_off;   /* the loop entered a pass with the switch off */
static void server_work( int who )
{
    volatile int k;
    long v;
    if (__atomic_exchange_n( &inside, who, __ATOMIC_SEQ_CST ))
    {
        fprintf( stderr, "OVERLAP: %d entered while %d was inside\n", who, inside );
        exit( 1 );
    }
    v = shared;
    for (k = 0; k < 40; k++) ;
    shared = v + 1;
    __atomic_store_n( &inside, 0, __ATOMIC_SEQ_CST );
}
static void handler_work( const void *req, void *reply )
{
    (void)req;
    server_work( 2 );
    (void)reply;
    if (!ios_srv_direct_live) { fprintf( stderr, "a handler ran with the loop not locking\n" ); exit( 1 ); }
    set_error( 0x77 );
}
static void *loop_thread( void *arg )
{
    (void)arg;
    ios_srv_loop_enter();
    while (!__atomic_load_n( &stop, __ATOMIC_ACQUIRE ))
    {
        server_work( 1 );
        loop_work++;
        if (!ios_srv_loop_locked) __atomic_fetch_add( &off_runs, 1, __ATOMIC_RELAXED );
        ios_srv_loop_leave();
        sched_yield();
        ios_srv_loop_enter();
    }
    ios_srv_loop_exit();
    return NULL;
}
/* the clients go on past 60000 calls each until both paths have run 1000 times and the
 * loop has run a pass with the switch off (the loop thread may start late, or get little
 * CPU, on a loaded or sanitized host: it gets the lock only once the switch goes off and
 * counts that pass as locked), at most 20 s; meanwhile they yield, so the loop runs */
static int stress_need_more( const struct timespec *t0 )
{
    struct timespec t;
    if (__atomic_load_n( &direct_ok, __ATOMIC_RELAXED ) > 1000 &&
        __atomic_load_n( &direct_pipe, __ATOMIC_RELAXED ) > 1000 &&
        __atomic_load_n( &off_runs, __ATOMIC_RELAXED ) > 0) return 0;
    sched_yield();
    clock_gettime( CLOCK_MONOTONIC, &t );
    return t.tv_sec - t0->tv_sec < 20;
}
static void *client_thread( void *arg )
{
    int k = (int)(long)arg, n;
    struct timespec t0;
    clock_gettime( CLOCK_MONOTONIC, &t0 );
    for (n = 0; n < 60000 || stress_need_more( &t0 ); n++)
    {
        union { union generic_request req; union generic_reply reply; } u;
        int r;
        memset( &u, 0, sizeof(u) );
        u.req.request_header.req = (n & 1) ? REQ_event_op : REQ_select;
        r = ios_srv_direct_call( threads[k].id, threads[k].teb, &u.req, NULL, 0, &u.reply, NULL );
        if (r == 1)
        {
            if (u.reply.reply_header.error != 0x77) { fprintf( stderr, "reply lost\n" ); exit( 1 ); }
            __atomic_fetch_add( &direct_ok, 1, __ATOMIC_RELAXED );
        }
        else if (r == 0) __atomic_fetch_add( &direct_pipe, 1, __ATOMIC_RELAXED );
        else { fprintf( stderr, "unexpected %d\n", r ); exit( 1 ); }
    }
    return NULL;
}
static void *toggle_thread( void *arg )
{
    int i;
    (void)arg;
    for (i = 0; !__atomic_load_n( &stop, __ATOMIC_ACQUIRE ); i++)
    {
        __atomic_store_n( &g_madeira_srv_direct, i % 3, __ATOMIC_RELEASE );
        usleep( 300 );
    }
    return NULL;
}

static int bad;
static void expect( int ok, const char *what ) { printf( "%s: %s\n", ok ? "PASS" : "FAIL", what ); if (!ok) bad = 1; }
static unsigned char seen_data[64];
static data_size_t seen_size;
static void handler_data( const void *req, void *reply )
{
    (void)req;
    seen_size = current->req.request_header.request_size;
    if (seen_size) memcpy( seen_data, current->req_data, seen_size < 64 ? seen_size : 64 );
    current->reply_data = malloc( 5 );
    memcpy( current->reply_data, "abcde", 5 );
    current->reply_size = 5;
    ((union generic_reply *)reply)->reply_header.error = 0x1234;   /* overwritten from current->error */
    set_error( 0x55 );
    errno = ENOENT;   /* as a failed open() in a real handler would */
}
static void handler_kill( const void *req, void *reply ) { (void)req; (void)reply; kill_thread( current, 0 ); }
struct timer_flag;
extern volatile int ios_srv_timer_added;
static void handler_timer( const void *req, void *reply ) { (void)req; (void)reply; ios_srv_timer_added = 1; }

static int one( int k, enum request req, const struct iovec *vec, unsigned int count, data_size_t size,
                union generic_reply *reply_out, void *reply_data, data_size_t reply_max )
{
    union { union generic_request req; union generic_reply reply; } u;
    int r;
    memset( &u, 0, sizeof(u) );
    u.req.request_header.req = req;
    u.req.request_header.request_size = size;
    u.req.request_header.reply_size = reply_max;
    r = ios_srv_direct_call( threads[k].id, threads[k].teb, &u.req, vec, count, &u.reply, reply_data );
    if (reply_out) *reply_out = u.reply;
    return r;
}

int main( int argc, char **argv )
{
    pthread_t lt, tt, ct[4];
    long i;
    int r;
    union generic_reply rep;
    char rd[16];
    struct iovec v[3];

    for (i = 0; i < NTHREADS; i++)
    {
        threads[i].id = 0x20 + 4 * i;
        threads[i].teb = 0x7000000000ull + 0x10000 * i;
        threads[i].request_fd = threads[i].reply_fd = (void *)1;
        threads[i].refs = 1;
    }
    for (i = 0; i < REQ_NB_REQUESTS; i++) req_handlers[i] = handler_work;

    if (argc > 1 && !strcmp( argv[1], "stress" ))
    {
        pthread_create( &lt, NULL, loop_thread, NULL );
        pthread_create( &tt, NULL, toggle_thread, NULL );
        for (i = 0; i < 4; i++) pthread_create( &ct[i], NULL, client_thread, (void *)i );
        for (i = 0; i < 4; i++) pthread_join( ct[i], NULL );
        __atomic_store_n( &stop, 1, __ATOMIC_RELEASE );
        pthread_join( tt, NULL );
        pthread_join( lt, NULL );
        expect( shared == loop_work + direct_ok, "no update of the server state was lost" );
        expect( direct_ok > 1000 && direct_pipe > 1000, "both paths ran while the switch moved" );
        expect( off_runs > 0, "the loop also ran passes without the lock (switch off)" );
        expect( !ios_srv_direct_live, "the exited loop leaves direct requests off" );
        r = one( 0, REQ_event_op, NULL, 0, 0, NULL, NULL, 0 );
        expect( r == 0, "after the loop exits a request goes through the pipe" );
        printf( "loop passes %ld, direct %ld, through the pipe %ld\n", loop_work, direct_ok, direct_pipe );
        return bad;
    }

    /* ---- single-threaded behaviour ---- */
    g_madeira_srv_direct = 1;
    r = one( 0, REQ_event_op, NULL, 0, 0, NULL, NULL, 0 );
    expect( r == 0, "the loop has not taken the lock yet: the pipe" );
    ios_srv_loop_enter();   /* loop locks, live */
    expect( ios_srv_direct_live == 1 && ios_srv_loop_locked == 1, "the loop takes the lock and marks direct requests live" );
    ios_srv_loop_leave();   /* sleeping */

    req_handlers[REQ_event_op] = handler_data;
    v[0].iov_base = "0123"; v[0].iov_len = 4;
    v[1].iov_base = "45678"; v[1].iov_len = 5;
    v[2].iov_base = "9"; v[2].iov_len = 1;
    memset( rd, 0, sizeof(rd) );
    census_n = 0;
    r = one( 1, REQ_event_op, v, 3, 10, &rep, rd, 8 );
    expect( r == 1, "a listed request runs on the calling thread" );
    expect( seen_size == 10 && !memcmp( seen_data, "0123456789", 10 ), "its data reach the handler in one piece" );
    expect( rep.reply_header.error == 0x55 && rep.reply_header.reply_size == 5 && !memcmp( rd, "abcde", 5 ),
            "the reply's status, size and data come back" );
    expect( threads[1].req_data == NULL && threads[1].reply_data == NULL && current == NULL,
            "request and reply data are released, current is cleared" );
    expect( census_n == 1 && time_n >= 1, "the census counts it and the clock is updated first" );
    expect( threads[1].refs == 1, "the thread reference is released" );

    r = one( 1, REQ_event_op, v, 3, 11, NULL, rd, 8 );
    expect( r == 0, "data that do not add up to the request size: the pipe" );
    r = one( 1, REQ_event_op, v, 3, 9, NULL, rd, 8 );
    expect( r == 0, "data longer than the request size: the pipe" );
    r = one( 1, REQ_new_thread, NULL, 0, 0, NULL, NULL, 0 );
    expect( r == 0, "an unlisted request (new_thread): the pipe" );
    r = one( 1, REQ_select, NULL, 0, 0, NULL, NULL, 0 );
    expect( r == 0, "a level-2 request (select) at level 1: the pipe" );
    g_madeira_srv_direct = 2;
    req_handlers[REQ_select] = handler_work;
    r = one( 1, REQ_select, NULL, 0, 0, NULL, NULL, 0 );
    expect( r == 1, "select at level 2 runs directly" );
    {
        union { union generic_request req; union generic_reply reply; } u;
        memset( &u, 0, sizeof(u) );
        u.req.request_header.req = REQ_event_op;
        r = ios_srv_direct_call( 0x999, threads[1].teb, &u.req, NULL, 0, &u.reply, NULL );
        expect( r == 0 && global_error == 0, "an unknown thread id: the pipe, and the lookup error is cleared" );
        r = ios_srv_direct_call( threads[1].id, threads[2].teb, &u.req, NULL, 0, &u.reply, NULL );
        expect( r == 0, "another thread's TEB: the pipe" );
    }
    threads[3].req_toread = 8;
    expect( one( 3, REQ_event_op, NULL, 0, 0, NULL, NULL, 0 ) == 0, "a request half read from the pipe: the pipe" );
    threads[3].req_toread = 0; threads[3].reply_towrite = 4;
    expect( one( 3, REQ_event_op, NULL, 0, 0, NULL, NULL, 0 ) == 0, "a reply half written: the pipe" );
    threads[3].reply_towrite = 0;

    req_handlers[REQ_close_handle] = handler_kill;
    memset( &rep, 0x5a, sizeof(rep) );
    {
        union { union generic_request req; union generic_reply reply; } u;
        memset( &u, 0, sizeof(u) );
        u.req.request_header.req = REQ_close_handle;
        u.req.request_header.request_size = 4;
        v[0].iov_base = "kill"; v[0].iov_len = 4;
        r = ios_srv_direct_call( threads[4].id, threads[4].teb, &u.req, v, 1, &u.reply, NULL );
        expect( r == -1 && u.req.request_header.req == REQ_close_handle && u.req.request_header.request_size == 4,
                "a request that ends its thread returns -1 and leaves the request for the pipe untouched" );
        expect( threads[4].state == TERMINATED && threads[4].req_data == NULL, "its data are freed once (ASan)" );
        expect( one( 4, REQ_event_op, NULL, 0, 0, NULL, NULL, 0 ) == 0, "a terminated thread: the pipe" );
    }

    req_handlers[REQ_set_timer] = handler_timer;
    wake_n = 0;
    expect( one( 5, REQ_set_timer, NULL, 0, 0, NULL, NULL, 0 ) == 1 && wake_n == 1 && !ios_srv_timer_added,
            "a timer added before the loop's wake wakes it once and clears the flag" );
    expect( one( 5, REQ_event_op, NULL, 0, 0, NULL, rd, 8 ) == 1 && wake_n == 1, "no timer: no wake" );

    {   /* the client's own entry point, end to end */
        struct fake_teb teb6;
        struct __server_request_info rq;
        unsigned int status = 0;
        char out[16];
        memset( &rq, 0, sizeof(rq) );
        teb6.ClientId.UniqueThread = (void *)(unsigned long)threads[6].id;
        threads[6].teb = (client_ptr_t)(unsigned long)&teb6;
        fake_teb_now = &teb6;
        req_handlers[REQ_event_op] = handler_data;
        rq.u.req.request_header.req = REQ_event_op;
        rq.u.req.request_header.request_size = 10;
        rq.u.req.request_header.reply_size = 8;
        rq.data[0].ptr = "01234"; rq.data[0].size = 5;
        rq.data[1].ptr = "56789"; rq.data[1].size = 5;
        rq.data_count = 2;
        rq.reply_data = out;
        errno = 1234;
        expect( ios_srv_try_direct( &rq, &status ) == TRUE && status == 0x55 && rq.u.reply.reply_header.reply_size == 5
                && !memcmp( out, "abcde", 5 ) && !memcmp( seen_data, "0123456789", 10 ),
                "ios_srv_try_direct: the request and its two data pieces in, the status and reply data out" );
        expect( errno == 1234, "the caller's errno survives the handler's system calls" );
        rq.u.req.request_header.req = REQ_new_thread;
        rq.data_count = 0;
        rq.u.req.request_header.request_size = 0;
        expect( ios_srv_try_direct( &rq, &status ) == FALSE && rq.u.req.request_header.req == REQ_new_thread,
                "ios_srv_try_direct: a request it does not take is left for the pipe, unchanged" );
        fake_teb_now = NULL;
    }

    g_madeira_srv_direct = 0;
    expect( one( 5, REQ_event_op, NULL, 0, 0, NULL, rd, 8 ) == 0, "switch off: the pipe at once" );
    ios_srv_loop_enter();
    expect( ios_srv_direct_live == 0 && ios_srv_loop_locked == 0, "the loop sees the switch off: no lock, not live" );
    g_madeira_srv_direct = 1;
    expect( one( 5, REQ_event_op, NULL, 0, 0, NULL, rd, 8 ) == 0, "switched on again but the loop has not locked: the pipe" );
    ios_srv_loop_enter();
    ios_srv_loop_exit();
    expect( ios_srv_direct_live == 0 && ios_srv_loop_locked == 0 && one( 5, REQ_event_op, NULL, 0, 0, NULL, rd, 8 ) == 0,
            "the loop's exit turns direct requests off" );
    return bad;
}
'''

harness = (harness.replace("@NAMES@", ", ".join(n for n in names if n not in ("REQ_new_thread", "REQ_terminate_thread", "REQ_suspend_thread")))
           .replace("@GLOBALS@", globals_block).replace("@ENTER@", enter).replace("@LEAVE@", leave)
           .replace("@EXIT@", exit_).replace("@LEVEL@", level).replace("@RUN@", run).replace("@CALL@", call).replace("@TRY@", try_direct))

cc = os.environ.get("CC") or shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
if not cc:
    check(False, "a C compiler is available")
else:
    tmp = Path(tempfile.mkdtemp(prefix="srvdirect-"))
    (tmp / "h.c").write_text(harness)
    base = [cc, "-std=gnu11", "-g", "-O1", "-Wall", "-Wno-unused-function", "-Werror=implicit-function-declaration", "-pthread"]
    for san, label in (("thread", "ThreadSanitizer"), ("address,undefined", "AddressSanitizer + UBSan")):
        exe = tmp / ("h-" + san.split(",")[0])
        b = subprocess.run(base + ["-fsanitize=" + san, "-fno-sanitize-recover=all", str(tmp / "h.c"), "-o", str(exe)],
                           capture_output=True, text=True)
        check(b.returncode == 0, "the harness compiles with " + label + ("" if not b.returncode else ": " + b.stderr[-1500:]))
        if b.returncode:
            continue
        env = dict(os.environ, ASAN_OPTIONS="detect_leaks=0", TSAN_OPTIONS="halt_on_error=1")
        for mode in ("", "stress"):
            r = subprocess.run([str(exe)] + ([mode] if mode else []), capture_output=True, text=True, env=env, timeout=600)
            out = r.stdout.strip()
            print("\n".join("    " + l for l in out.splitlines()))
            check(r.returncode == 0 and "FAIL" not in out,
                  "%s, %s: every behaviour check passes, no sanitizer report%s" % (
                      label, "stress (loop, 4 clients, switch toggling)" if mode else "single-threaded cases",
                      "" if r.returncode == 0 else ": " + r.stderr[-1500:]))
    shutil.rmtree(tmp, ignore_errors=True)

# ---- textual ---------------------------------------------------------------------
never = ("REQ_new_thread", "REQ_init_first_thread", "REQ_init_thread", "REQ_terminate_thread", "REQ_terminate_process",
         "REQ_suspend_thread", "REQ_resume_thread", "REQ_get_thread_context", "REQ_set_thread_context", "REQ_queue_apc",
         "REQ_new_process", "REQ_get_new_process_info", "REQ_read", "REQ_write", "REQ_ioctl", "REQ_register_async",
         "REQ_get_message", "REQ_send_message", "REQ_post_quit_message", "REQ_set_queue_mask", "REQ_alloc_file_handle",
         "REQ_dup_handle", "REQ_get_inproc_sync_fd")
check(not any(n in names for n in never), "no thread/process lifetime, suspension, context, APC, async I/O, message "
      "or descriptor-in-flight request is listed")
check({"REQ_create_file", "REQ_get_handle_fd", "REQ_close_handle", "REQ_open_mapping", "REQ_remove_completion",
       "REQ_release_semaphore", "REQ_event_op"} <= set(listed1),
      "level 1 covers the requests the HZD census ranks highest (file, descriptor, close, mapping, completion, semaphore, event)")
check(set(listed2) == {"REQ_select", "REQ_create_timer", "REQ_open_timer", "REQ_set_timer", "REQ_cancel_timer",
                       "REQ_get_timer_info", "REQ_set_cursor"},
      "level 2 adds select, the timer requests and set_cursor only")
check("thread->teb != teb" in call and "thread->req_toread" in call and "thread->reply_towrite" in call,
      "the thread must be the caller (TEB) with no request half read and no reply half written")
check(call.find("set_current_time();") < call.find("ios_srv_run_direct( thread, &reply, reply_data );"),
      "the clock is updated before the handler, as the loop does after each wake")
check(call.find("os_unfair_lock_unlock( &ios_srv_lock );\n    if (wake) ios_wineserver_wake();") > 0,
      "the timer wake is sent after the lock is released")
m = re.search(r"static void call_req_handler\( struct thread \*thread \)\n\{(.*?)\n\}\n", REQ, re.S)
check(bool(m) and "ios_req_census( thread, req );" in m.group(1) and "ios_req_census( thread, req );" in run,
      "the pipe path and the direct path share one census")
for step in ("current->reply_size = 0;", "clear_error();", "reply->reply_header.error = current->error;",
             "reply->reply_header.reply_size = current->reply_size;", "kill_thread( current, 1 );", "current = NULL;"):
    check(step in run, "the direct path repeats call_req_handler's step: " + step)

loop = FD[FD.find("void main_loop(void)"):]
i_enter0 = loop.find("ios_srv_loop_enter();   /* madeira-bcd: MADEIRA_SRV_DIRECT; the lock is let go only to sleep */")
i_while = loop.find("while (active_users)")
i_tmo = loop.find("timeout = get_next_timeout( &next_ts );")
i_flag = loop.find("ios_srv_timer_added = 0;")
i_wake_at = loop.find("ios_srv_loop_wake_at = monotonic_counter() + sleep_ns / 100;")
i_leave = loop.find("ios_srv_loop_leave();", i_wake_at)
i_sem = loop.find("semaphore_timedwait( ios_srv_wake_sem, wts );")
i_enter1 = loop.find("ios_srv_loop_enter();    /* madeira-bcd: MADEIRA_SRV_DIRECT */")
i_bell = loop.find("ios_doorbell_service();")
i_exit = loop.find("ios_srv_loop_exit();")
i_exited = loop.find('ws_log("[wineserver-fd] main_loop EXITED!')
check(0 <= i_enter0 < i_while < i_tmo < i_flag < i_wake_at < i_leave < i_sem < i_enter1 < i_bell < i_exit < i_exited,
      "the loop locks before its first pass, publishes its wake time and unlocks only around the sleep, "
      "relocks before the bells, and turns direct requests off when it ends")
check(loop.count("ios_srv_loop_leave();") == 1 and loop.count("ios_srv_loop_enter();") == 2,
      "the loop lets the lock go in exactly one place")
atu = func_body(FD, "struct timeout_user *add_timeout_user( timeout_t when, timeout_callback func, void *private )")
check("if (__atomic_load_n( &ios_srv_direct_live, __ATOMIC_RELAXED ))" in atu and
      "if (due < (timeout_t)ios_srv_loop_wake_at) ios_srv_timer_added = 1;" in atu and
      atu.find("list_add_before( ptr, &user->entry );") < atu.find("ios_srv_timer_added = 1;"),
      "add_timeout_user flags a timer due before the sleeping loop wakes, only while direct requests are live")

cu = func_body(NTDLL, "unsigned int server_call_unlocked( void *req_ptr )")
i_abort = cu.find("if (ios_section_state() & IOS_SECTION_ABORT) return STATUS_THREAD_IS_TERMINATING;")
i_bg = cu.find("ios_bg_qos_check();")
i_direct = cu.find("if (__atomic_load_n( &g_madeira_srv_direct, __ATOMIC_RELAXED ) > 0 && ios_srv_try_direct( req, &ret ))\n        return ret;")
i_send = cu.find("if ((ret = send_request( req ))) return ret;")
check(0 <= i_abort < i_direct < i_send and (i_bg < 0 or i_bg < i_direct),
      "the client tries a direct request after the abort check (and the [bg-qos] check, where there is one), "
      "before writing to its pipe, and only with the switch on")
td = func_body(NTDLL, "static BOOL ios_srv_try_direct( struct __server_request_info *req, unsigned int *status )")
check("if (ret <= 0) return FALSE;" in td and "*status = req->u.reply.reply_header.error;" in td and
      "(client_ptr_t)(ULONG_PTR)NtCurrentTeb()" in td,
      "anything not taken (or a request that ended the thread) goes on to the pipe; the TEB names the caller")
check(td.find("int ret, err = errno;") < td.find("ios_srv_direct_call(") < td.find("errno = err;") < td.find("if (ret <= 0) return FALSE;"),
      "the caller's errno is the same after a direct request as after a pipe round trip")

check("volatile int g_madeira_srv_direct = 0;" in BRIDGE, "the bridge defines g_madeira_srv_direct, off")
i_env = BRIDGE.find('fprintf(stderr, "[madeira-env] game %s=%s\\n", k.UTF8String, v.UTF8String);')
i_set = BRIDGE.find("g_madeira_srv_direct = (dr && (dr[0] == '1' || dr[0] == '2') && !dr[1]) ? dr[0] - '0' : 0;")
i_end = BRIDGE.find('unsetenv("MADEIRA_SRV_ECO_FOLLOW"); unsetenv("MADEIRA_SRV_DIRECT");')
i_clear = BRIDGE.find("g_madeira_srv_direct = 0;", i_end)
i_stop = BRIDGE.find("wineserver_stop();", i_end)
check(0 <= i_env < i_set and 'const char *dr = getenv("MADEIRA_SRV_DIRECT");' in BRIDGE[i_env:i_set],
      "the bridge sets it from MADEIRA_SRV_DIRECT (1 or 2) after the game's env lines")
check(i_set < i_end < i_clear < i_stop, "the session end unsets it and clears the global before the server stops")

check('key: "env.MADEIRA_SRV_DIRECT"' in CAT and re.search(r'key: "env.MADEIRA_SRV_DIRECT", title: "[^"]+", kind: \.text, '
                                                          r'defaultValue: "0"', CAT) is not None,
      "the catalog documents env.MADEIRA_SRV_DIRECT, default 0")
if CI is not None:
    check("python3 tests/host/check-srv-direct.py" in CI, "CI runs this check")

print()
if failures:
    print("%d check(s) failed" % len(failures))
    sys.exit(1)
print("all checks passed")
