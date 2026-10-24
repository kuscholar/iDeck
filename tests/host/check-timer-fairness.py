#!/usr/bin/env python3
"""madeira-bcd: WM_TIMER is not starved by a WM_PAINT that never ends
(build/wineserver/queue_ios.c, madeira_timer_starved).

The Rockstar Games Launcher installer's install page repaints its status line
for good (219 paints a second, wake bits QS_PAINT|QS_TIMER). Paint goes before
timer, and its status text and finish page run on a timer, so it stayed at
"Preparing to Install..." after its work was done (logs 2026-10-03 17:14 and
2026-10-12 10:00).

Checks:
  1. source: the helper reads MADEIRA_TIMER_FAIRNESS (0: strict order) and a
     100 ms limit; get_message's guard sits after the hardware messages and
     before WM_PAINT, only when a paint is pending, and hands over the timer as
     the stock timer branch does; that branch is still there;
  2. the helper, compiled on the host: nothing expired, 50 ms and a real-time
     expiry are not starved; 150 ms is; MADEIRA_TIMER_FAIRNESS=0 never;
  3. get_message's guard, paint and timer branches, compiled on the host with
     the file's own find_expired_timer and check_msg_filter: with a paint always
     pending and a 50 ms timer, 2 simulated seconds deliver a timer about every
     150 ms (due again within 50 ms, then 100 ms of waiting); with
     MADEIRA_TIMER_FAIRNESS=0 none, as before; with no paint pending every
     expired timer goes out at once, as before.
Needs `cc` on PATH.
"""
from pathlib import Path
import os
import re
import shutil
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[2]
src = (root / 'build/wineserver/queue_ios.c').read_text()
cc = os.environ.get('CC') or shutil.which('cc') or shutil.which('clang') or shutil.which('gcc')
failures = []


def check(cond, what):
    print(('PASS: ' if cond else 'FAIL: ') + what)
    if not cond:
        failures.append(what)


def function(text, signature):
    start = text.index(signature)
    return text[start:text.index('\n}\n', start) + 3]


# ------------------------------------------------------------------ 1. source
helper = function(src, 'static int madeira_timer_starved( struct msg_queue *queue )')
check('getenv( "MADEIRA_TIMER_FAIRNESS" )' in helper and "enabled = !(env && env[0] == '0');" in helper,
      'MADEIRA_TIMER_FAIRNESS=0 turns it off; anything else (or unset) leaves it on')
check('return monotonic_time + timer->when > (timeout_t)100 * 10000;' in helper and 'if (timer->when > 0) return 0;' in helper,
      'a timer counts as starved once its monotonic expiry is more than 100 ms old')
handler = function(src, 'DECL_HANDLER(get_message)')
hw = handler.index('get_hardware_message( current, req->hw_id, get_win, req->get_first, req->get_last, req->flags, reply ))')
guard = handler.index('madeira_timer_starved( queue )')
paint = handler.index('/* now check for WM_PAINT */')
stock_timer = handler.index('/* now check for timer */')
check(hw < guard < paint < stock_timer, "the guard sits after the hardware messages and before WM_PAINT; the stock timer branch follows")
block = handler[handler.rindex('    if ((filter & QS_TIMER) && (filter & QS_PAINT)', 0, guard):paint]
check('queue->paint_count &&' in block and
      '(timer = find_expired_timer( queue, get_win, req->get_first,\n                                     req->get_last, (req->flags & PM_REMOVE) )))' in block and
      'reply->wparam = timer->id;' in block and 'reply->lparam = timer->lparam;' in block,
      'only with a paint pending; the timer goes out as the stock branch hands it over (same filter, PM_REMOVE restarts it)')
check('[timer-fair]' in block and '<= 8 ||' in block and '% 1000' in block, 'logged: the first 8 times, then every 1000th')
check(src.count('madeira_timer_starved(') == 2, 'one helper, one caller')

# ------------------------------------------------------------------ 2.+3. compiled
struct_timer = src[src.index('struct timer\n{'):src.index('};', src.index('struct timer\n{')) + 3]
filter_fn = function(src, 'static inline int check_msg_filter( unsigned int msg, unsigned int first, unsigned int last )')
find_fn = function(src, 'static struct timer *find_expired_timer( struct msg_queue *queue, user_handle_t win,')
branches = handler[handler.rindex('    if ((filter & QS_TIMER) && (filter & QS_PAINT)', 0, guard):handler.index('    SHARED_WRITE_BEGIN', stock_timer)]

harness = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "wine/list.h"
typedef long long timeout_t;
typedef long long abstime_t;
typedef unsigned int user_handle_t;
typedef unsigned long long lparam_t;
#define QS_TIMER 0x0010
#define QS_PAINT 0x0020
#define PM_REMOVE 0x0001
#define WM_PAINT 0x000f
#define WM_TIMER 0x0113
#define MSG_POSTED 2
timeout_t monotonic_time;
STRUCT_TIMER
struct msg_queue { int paint_count; struct list pending_timers; struct list expired_timers; };
struct thread { unsigned int id; } current_thread = { 0xcc }, *current = &current_thread;
struct request { unsigned int get_first, get_last, flags; } request, *req = &request;
struct replyt { int type; user_handle_t win; unsigned int msg; lparam_t wparam, lparam; int x, y; unsigned int time; } replyv, *reply = &replyv;
static void get_message_defaults( struct msg_queue *q, int *x, int *y, unsigned int *t ) { *x = *y = 0; *t = 0; }
static user_handle_t find_window_to_repaint( user_handle_t win, struct thread *t ) { return 0x20052; }
/* the timer moves back to the pending list, due one period later (restart_timer) */
static void restart_timer( struct msg_queue *queue, struct timer *timer )
{
    list_remove( &timer->entry );
    while (-timer->when <= monotonic_time) timer->when -= (timeout_t)timer->rate * 10000;
    list_add_tail( &queue->pending_timers, &timer->entry );
}
/* the server's timeout: a due pending timer moves to the expired list (timer_callback) */
static void expire( struct msg_queue *queue )
{
    struct timer *timer, *next;
    LIST_FOR_EACH_ENTRY_SAFE( timer, next, &queue->pending_timers, struct timer, entry )
        if (-timer->when <= monotonic_time) { list_remove( &timer->entry ); list_add_tail( &queue->expired_timers, &timer->entry ); }
}
FILTER_FN
FIND_FN
HELPER_FN
static unsigned int get_message( struct msg_queue *queue, unsigned int filter )
{
    struct timer *timer;
    user_handle_t get_win = 0;
BRANCHES
    return 0;
}
int main( int argc, char **argv )
{
    struct msg_queue queue = { 0 };
    struct timer timer = { 0 };
    list_init( &queue.pending_timers ); list_init( &queue.expired_timers );
    if (!strcmp( argv[1], "helper" ))
    {
        /* nothing expired; 50 ms, 150 ms, a real-time expiry */
        int none = madeira_timer_starved( &queue );
        monotonic_time = 10000000;
        timer.rate = 50; timer.when = -(monotonic_time - 50 * 10000);
        list_add_tail( &queue.expired_timers, &timer.entry );
        int fifty = madeira_timer_starved( &queue );
        timer.when = -(monotonic_time - 150 * 10000);
        int onefifty = madeira_timer_starved( &queue );
        timer.when = 1;
        int realtime = madeira_timer_starved( &queue );
        printf( "none=%d fifty=%d onefifty=%d realtime=%d\n", none, fifty, onefifty, realtime );
        return 0;
    }
    /* "paint": a paint always pending; "nopaint": none. A 50 ms timer; 4.5 ms a message, 2 s. */
    int paint = !strcmp( argv[1], "paint" );
    unsigned int timers = 0, paints = 0, first = 0;
    monotonic_time = 10000000;
    timer.rate = 50; timer.win = 0x20052; timer.msg = WM_TIMER; timer.id = 7;
    timer.when = -(monotonic_time + 50 * 10000);
    list_add_tail( &queue.pending_timers, &timer.entry );
    req->get_first = 0; req->get_last = ~0u; req->flags = PM_REMOVE;
    for (int i = 0; i < 445; i++)
    {
        monotonic_time += 45000;
        expire( &queue );
        queue.paint_count = paint;
        unsigned int msg = get_message( &queue, QS_TIMER | QS_PAINT );
        if (msg == WM_TIMER) { timers++; if (!first) first = i; }
        else if (msg == WM_PAINT) paints++;
    }
    printf( "timers=%u paints=%u first=%u\n", timers, paints, first );
    return 0;
}
'''
branches_body = branches.replace('reply->win = find_window_to_repaint', 'reply->win = find_window_to_repaint')
branches_body = branches_body.replace('        return;\n', '        return reply->msg;\n')
code = (harness.replace('STRUCT_TIMER', struct_timer).replace('FILTER_FN', filter_fn).replace('FIND_FN', find_fn)
        .replace('HELPER_FN', helper).replace('BRANCHES', branches_body))

if not cc:
    print('SKIP: no C compiler; the compiled checks did not run')
else:
    with tempfile.TemporaryDirectory(prefix='madeira-timer-fair-') as d:
        c = Path(d) / 'fair.c'
        exe = Path(d) / 'fair'
        c.write_text(code)
        build = subprocess.run([cc, '-std=gnu99', '-I', str(root / 'wine/include'), str(c), '-o', str(exe)],
                               capture_output=True, text=True)
        check(build.returncode == 0, 'the helper and get_message\'s branches compile on the host' +
              ('' if build.returncode == 0 else ': ' + build.stderr[:800]))
        if build.returncode == 0:
            def run(mode, fairness=None):
                env = dict(os.environ)
                env.pop('MADEIRA_TIMER_FAIRNESS', None)
                if fairness is not None:
                    env['MADEIRA_TIMER_FAIRNESS'] = fairness
                out = subprocess.run([str(exe), mode], capture_output=True, text=True, env=env).stdout.strip()
                return dict(kv.split('=') for kv in out.split())
            h = run('helper')
            check(h == {'none': '0', 'fifty': '0', 'onefifty': '1', 'realtime': '0'},
                  'nothing expired, 50 ms and a real-time expiry: not starved; 150 ms: starved (%s)' % h)
            check(run('helper', '0')['onefifty'] == '0' and run('helper', '1')['onefifty'] == '1',
                  'MADEIRA_TIMER_FAIRNESS=0: never; =1: as the default')
            on = run('paint')
            # A delivered timer is due again within its 50 ms period, then waits 100 ms: ~150 ms apart.
            check(10 <= int(on['timers']) <= 16 and int(on['paints']) > 400 and 25 <= int(on['first']) <= 40,
                  'a paint always pending: timers still run, about every 150 ms, the first after ~150 ms (%s)' % on)
            off = run('paint', '0')
            check(off['timers'] == '0', 'MADEIRA_TIMER_FAIRNESS=0: the paint starves every timer, as before (%s)' % off)
            quiet = run('nopaint')
            check(37 <= int(quiet['timers']) <= 41 and quiet['paints'] == '0',
                  'no paint pending: each 50 ms timer goes out when it expires, as before (%s)' % quiet)

print('FAIL' if failures else 'PASS')
sys.exit(1 if failures else 0)
