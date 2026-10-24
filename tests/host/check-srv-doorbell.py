#!/usr/bin/env python3
"""The wineserver request doorbell (build/wineserver/fd_ios.c); no Wine runs.

Compiles the production ios_wineserver_wake / ios_wineserver_ring and
ios_doorbell_service from fd_ios.c against stubs (a POSIX semaphore for the Mach
one, a fake request channel per thread) and runs client threads that write a
request, ring and wait for the reply against a server loop that sleeps on the
semaphore, clears the pending flag and serves only the rung threads. The full
scan is OFF in the model, so every request must be found through its bell:
  - no request is ever lost (each client gets every reply) under contention;
  - a request left partly unread (ios_doorbell_poll_thread returning 1) is rung
    again by the loop and finished on a later pass;
  - a ring without a usable thread id raises the full-scan flag instead.
Then textually: the client rings with its own thread id after the write, the
loop serves the bells after the wait and before the per-fd scan, synthesises
POLLIN for client fds only on a full-scan pass, and MADEIRA_SRV_DOORBELL=0 makes
every pass a full scan.
Needs python3 and a C compiler with pthreads (CC, default cc).
"""
from pathlib import Path
import os
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
src = (root / 'build/wineserver/fd_ios.c').read_text()
req = (root / 'build/wineserver/request_ios.c').read_text()
ntdll = (root / 'build/ntdll-unix/server_ios.c').read_text()

wake = src[src.index('static volatile int ios_srv_wake_pending;'):]
wake = wake[:wake.index('\n}\n', wake.index('void ios_wineserver_ring(')) + 3]
service = src[src.index('static unsigned long long ios_bell_threads, ios_bell_again;'):]
service = service[:service.index('\n#endif', service.index('static void ios_doorbell_service(void)'))]

harness = r'''
#include <pthread.h>
#include <semaphore.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <errno.h>
typedef int semaphore_t;
static sem_t real_sem;
static semaphore_t ios_srv_wake_sem = 1;
#define semaphore_signal(s) sem_post(&real_sem)
''' + wake + r'''
#define NTHREADS 8
#define NREQ 200000
static volatile int written[NTHREADS], replied[NTHREADS], partial_once[NTHREADS];
static volatile int stop;
static unsigned long long served, partials;
static unsigned int tid_of(int k) { return 0x20 + 4 * k * 37; }  /* spread over words */
int ios_doorbell_poll_thread( unsigned int tid )
{
    int k;
    for (k = 0; k < NTHREADS; k++) if (tid_of(k) == tid) break;
    if (k == NTHREADS) { fprintf(stderr, "unknown tid %x\n", tid); exit(1); }
    if (!__atomic_load_n(&written[k], __ATOMIC_ACQUIRE)) return 0;      /* EAGAIN */
    if (partial_once[k] && (served % 97) == 0)                         /* half a request */
    { partial_once[k] = 0; partials++; return 1; }
    __atomic_store_n(&written[k], 0, __ATOMIC_RELAXED);
    served++;
    __atomic_store_n(&replied[k], 1, __ATOMIC_RELEASE);
    return 0;
}
''' + service + r'''
static void *client(void *arg)
{
    int k = (int)(long)arg, n;
    for (n = 0; n < NREQ; n++)
    {
        partial_once[k] = 1;
        __atomic_store_n(&replied[k], 0, __ATOMIC_RELAXED);
        __atomic_store_n(&written[k], 1, __ATOMIC_RELEASE);    /* write( request_fd ) */
        ios_wineserver_ring( tid_of(k) );
        while (!__atomic_load_n(&replied[k], __ATOMIC_ACQUIRE)) ;   /* wait_reply */
    }
    return NULL;
}
static void *server(void *arg)
{
    while (!__atomic_load_n(&stop, __ATOMIC_ACQUIRE))
    {
        struct timespec ts;
        clock_gettime(CLOCK_REALTIME, &ts);
        ts.tv_sec += 5;                       /* no 1 ms tick: only the wake may drive passes */
        if (sem_timedwait(&real_sem, &ts) && errno == ETIMEDOUT && !__atomic_load_n(&stop, __ATOMIC_ACQUIRE))
        {
            int k, busy = 0;
            for (k = 0; k < NTHREADS; k++) busy |= written[k];
            if (busy) { fprintf(stderr, "LOST: a written request had no bell for 5 s\n"); exit(1); }
        }
        if (ios_srv_wake_coalesce) __atomic_store_n( &ios_srv_wake_pending, 0, __ATOMIC_SEQ_CST );
        ios_doorbell_service();
        /* a re-rung (partial) request needs another pass: the real loop's 1 ms tick */
        { unsigned w; for (w = 0; w < IOS_SRV_BELL_WORDS; w++) if (ios_srv_bell[w]) { sem_post(&real_sem); break; } }
    }
    return NULL;
}
int main(void)
{
    pthread_t c[NTHREADS], s;
    long k;
    sem_init(&real_sem, 0, 0);
    ios_srv_wake_coalesce = 1;
    pthread_create(&s, NULL, server, NULL);
    for (k = 0; k < NTHREADS; k++) pthread_create(&c[k], NULL, client, (void *)k);
    for (k = 0; k < NTHREADS; k++) pthread_join(c[k], NULL);
    __atomic_store_n(&stop, 1, __ATOMIC_RELEASE); sem_post(&real_sem);
    pthread_join(s, NULL);
    if (served != (unsigned long long)NTHREADS * NREQ) { fprintf(stderr, "served %llu\n", served); return 1; }
    if (!partials || ios_bell_again != partials) { fprintf(stderr, "partials %llu again %llu\n", partials, ios_bell_again); return 1; }
    /* a ring without a usable thread id */
    ios_srv_bell_full = 0; ios_wineserver_ring( 0 );
    if (!ios_srv_bell_full) { fprintf(stderr, "tid 0 did not ask for a full scan\n"); return 1; }
    ios_srv_bell_full = 0; ios_wineserver_ring( 0x40002 );
    if (!ios_srv_bell_full) { fprintf(stderr, "odd tid did not ask for a full scan\n"); return 1; }
    ios_srv_bell_full = 0; ios_wineserver_ring( 4 * IOS_SRV_BELL_WORDS * 64 );
    if (!ios_srv_bell_full) { fprintf(stderr, "tid past the table did not ask for a full scan\n"); return 1; }
    printf("served %llu requests through bells alone, %llu partial reads rung again\n", served, partials);
    return 0;
}
'''

with tempfile.TemporaryDirectory() as tmp:
    c = Path(tmp) / 'bell.c'
    c.write_text(harness)
    exe = Path(tmp) / 'bell'
    cc = os.environ.get('CC', 'cc')
    subprocess.run([cc, '-O2', '-pthread', '-std=gnu11', '-Wall', '-Werror', '-Wno-unused-function',
                    str(c), '-o', str(exe)], check=True)
    out = subprocess.run([str(exe)], check=True, capture_output=True, text=True, timeout=600)
    print('PASS:', out.stdout.strip())

# --- textual wiring -----------------------------------------------------------
call = ntdll[ntdll.index('unsigned int server_call_unlocked( void *req_ptr )'):]
call = call[:call.index('\n}\n')]
assert call.index('send_request( req )') < call.index('ios_wineserver_ring( HandleToULong( NtCurrentTeb()->ClientId.UniqueThread ) );') \
    < call.index('return wait_reply( req );'), 'ring after the write, before the wait'
loop = src[src.index('void main_loop(void)'):]
assert loop.index('semaphore_timedwait( ios_srv_wake_sem, wts );') < loop.index('ios_doorbell_service();') \
    < loop.index('if (!ios_fd_is_inet( i, pollfd[i].fd )) continue;'), 'bells after the wait, before the scans'
assert loop.index('__atomic_store_n( &ios_srv_wake_pending, 0, __ATOMIC_SEQ_CST );') < loop.index('ios_doorbell_service();'), \
    'the pending flag is cleared before the bells are taken'
assert 'else ios_full_scan = 1;' in loop, 'MADEIRA_SRV_DOORBELL=0: every pass is a full scan'
assert 'ios_slow_pass = !ios_doorbell || ios_full_scan || now_ns - ios_last_slow >= ios_slow_ns;' in loop, \
    'sockets and fds are scanned when a full scan is due, every MADEIRA_SRV_POLL_US, or always without the doorbell'
assert loop.index('ios_doorbell_service();') < loop.index('if (!ios_slow_pass) continue;') \
    < loop.index('if (!ios_fd_is_inet( i, pollfd[i].fd )) continue;'), 'a request pass returns to the wait before the scans'
assert 'fprintf( stderr, "[srv-doorbell]' in loop, 'the heartbeat reaches the session log'
assert 'if (ios_full_scan)\n                            {\n                                revents |= POLLIN;' in loop, \
    'client fds get the synthetic POLLIN only on a full-scan pass'
poll_thread = req[req.index('int ios_doorbell_poll_thread( unsigned int tid )'):]
poll_thread = poll_thread[:poll_thread.index('\n}\n')]
assert 'clear_error();' in poll_thread and 'release_object( thread );' in poll_thread
assert 'again = thread->request_fd && thread->req_toread;' in poll_thread
fd_in = src[src.index('void ios_fd_poll_in( struct fd *fd )'):]
fd_in = fd_in[:fd_in.index('\n}\n')]
assert 'poll_users[user] != fd' in fd_in and '!(pollfd[user].events & POLLIN)' in fd_in
print('PASS: client rings after its write; the loop serves bells after the wait, scans every client fd only when due')
