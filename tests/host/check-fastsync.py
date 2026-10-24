#!/usr/bin/env python3
# Copyright 2026 125hz.  GPL-3.0-or-later, like the rest of this repository.
"""Opt-in fastsync (wine/include/wine/madeira_fastsync.h, wine/server/event.c,
semaphore.c, thread.c, wine/dlls/ntdll/unix/sync.c).

1. The switches, compiled from the production sources on the host: the
   client's mode parse (madeira_fast_parse_env in sync.c) and the server's
   cell switch (madeira_fastsync_enabled / _sem_enabled in event.c). Unset,
   0/off and unknown values are OFF on both sides; auto, 1/on/yes and cells
   turn it on; madsync's device (inproc_device_fd / get_inproc_device_fd()
   >= 0) turns it off on both sides whatever MADEIRA_FASTSYNC says;
   MADEIRA_FASTSYNC_SEM needs fastsync on.
2. The cell protocol host models against the real header:
   fastsync-cellrace.c (a packed {gen,state} CAS never takes a token out of
   a recycled cell) and fastsync-semrace.c (semaphore conservation, no lost
   wakeup, timed waits, overflow, generation, mixed client/server liveness
   with a control that must stall, and the timeout re-check).
   FASTSYNC_TSAN=1 also runs the semaphore model under ThreadSanitizer.
3. Source checks: every hook is iOS-only, the server allocates a cell only
   when switched on, the timeout re-check and the process-init flush are in
   place, and a closed handle leaves the cache through close_inproc_sync().

Needs the wine submodule checked out and `cc` on PATH.
"""
from pathlib import Path
import os
import re
import shutil
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[2]
header = root / 'wine/include/wine/madeira_fastsync.h'
if not header.exists():
    print('FAIL: wine/include/wine/madeira_fastsync.h missing (check out the wine submodule)')
    sys.exit(1)
sync = (root / 'wine/dlls/ntdll/unix/sync.c').read_text()
event = (root / 'wine/server/event.c').read_text()
thread = (root / 'wine/server/thread.c').read_text()
semaphore = (root / 'wine/server/semaphore.c').read_text()
inproc = (root / 'wine/server/inproc_sync.c').read_text()
server_ios = (root / 'build/ntdll-unix/server_ios.c').read_text()
cc = os.environ.get('CC') or shutil.which('cc') or shutil.which('clang') or shutil.which('gcc')
failures = []


def check(cond, what):
    print(('PASS: ' if cond else 'FAIL: ') + what)
    if not cond:
        failures.append(what)


def between(text, start, end, include_end=True):
    i = text.index(start)
    j = text.index(end, i + len(start))
    return text[i:j + (len(end) if include_end else 0)]


def func(text, header_line):
    """A C function from its first line to the closing brace at column 0."""
    return between(text, header_line, '\n}\n')


# ------------------------------------------------------------------ 1. switches
modes = between(sync, 'enum\n{\n    MADEIRA_FS_MODE_OFF', '};')
env_is = func(sync, 'static int madeira_env_is(')
parse = between(sync, '    const char *e = getenv( "MADEIRA_FASTSYNC" );',
                '    sem = mode != MADEIRA_FS_MODE_OFF && madeira_env_is( e, "1", "on", "yes" );')
srv_on = func(event, 'static int madeira_fastsync_enabled(void)')
srv_sem = func(event, 'int madeira_fastsync_sem_enabled(void)')

harness = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
''' + modes + r'''
static int inproc_device_fd = -1;       /* ntdll: madsync's device, when handed out */
static int device_fd = -1;              /* server: get_inproc_device_fd() */
static int get_inproc_device_fd(void) { return device_fd; }
static int madeira_fastsync_on = -1, madeira_fastsync_sem_on = -1;
''' + env_is + '\n' + srv_on + '\n' + srv_sem + r'''
static void client( int *mode_out, int *asked_out, int *peek_out, int *sem_out )
{
''' + parse + r'''
    *mode_out = mode; *asked_out = asked; *peek_out = peek; *sem_out = sem;
}
static int failed;
static void expect( int cond, const char *what ) { printf( "%s: %s\n", cond ? "PASS" : "FAIL", what ); failed += !cond; }
static void set( const char *name, const char *value ) { if (value) setenv( name, value, 1 ); else unsetenv( name ); }
static void run( const char *fs, const char *sem, int madsync, int want_mode, int want_sem, const char *what )
{
    int mode, asked, peek, csem, srv, ssem;
    char line[256];
    set( "MADEIRA_FASTSYNC", fs ); set( "MADEIRA_FASTSYNC_SEM", sem ); unsetenv( "MADEIRA_FS_POLLPEEK" );
    inproc_device_fd = device_fd = madsync ? 0x6fffffff : -1;
    madeira_fastsync_on = madeira_fastsync_sem_on = -1;
    client( &mode, &asked, &peek, &csem );
    srv = madeira_fastsync_enabled(); ssem = madeira_fastsync_sem_enabled();
    snprintf( line, sizeof(line), "%s: client mode %d (want %d), server cells %d, sem %d/%d (want %d), peek %d",
              what, mode, want_mode, srv, csem, ssem, want_sem, peek );
    expect( mode == want_mode && srv == (want_mode != MADEIRA_FS_MODE_OFF) && csem == want_sem && ssem == want_sem
            && peek == (want_mode != MADEIRA_FS_MODE_OFF), line );
}
int main(void)
{
    int mode, asked, peek, sem;
    run( NULL, NULL, 0, MADEIRA_FS_MODE_OFF, 0, "unset: off (the default)" );
    run( NULL, "1", 0, MADEIRA_FS_MODE_OFF, 0, "MADEIRA_FASTSYNC_SEM alone: off" );
    run( "0", NULL, 0, MADEIRA_FS_MODE_OFF, 0, "0: off" );
    run( "off", "1", 0, MADEIRA_FS_MODE_OFF, 0, "off: off, semaphores too" );
    run( "garbage", NULL, 0, MADEIRA_FS_MODE_OFF, 0, "an unknown value: off" );
    run( "auto", NULL, 0, MADEIRA_FS_MODE_AUTO, 0, "auto: cells, wake path on traffic" );
    run( "auto", "1", 0, MADEIRA_FS_MODE_AUTO, 1, "auto + MADEIRA_FASTSYNC_SEM=1: semaphores too" );
    run( "1", NULL, 0, MADEIRA_FS_MODE_ON, 0, "1: on" );
    run( "on", NULL, 0, MADEIRA_FS_MODE_ON, 0, "on: on" );
    run( "yes", NULL, 0, MADEIRA_FS_MODE_ON, 0, "yes: on" );
    run( "cells", NULL, 0, MADEIRA_FS_MODE_CELLS, 0, "cells: poll answers only" );
    run( NULL, NULL, 1, MADEIRA_FS_MODE_OFF, 0, "madsync, unset: off" );
    run( "auto", "1", 1, MADEIRA_FS_MODE_OFF, 0, "madsync + auto: off on both sides (one engine)" );
    run( "1", NULL, 1, MADEIRA_FS_MODE_OFF, 0, "madsync + 1: off on both sides" );
    setenv( "MADEIRA_FASTSYNC", "auto", 1 ); unsetenv( "MADEIRA_FASTSYNC_SEM" ); inproc_device_fd = 5;
    client( &mode, &asked, &peek, &sem );
    expect( asked == MADEIRA_FS_MODE_AUTO && mode == MADEIRA_FS_MODE_OFF, "madsync: the request is kept for the log line" );
    inproc_device_fd = -1; setenv( "MADEIRA_FS_POLLPEEK", "0", 1 );
    client( &mode, &asked, &peek, &sem );
    expect( mode == MADEIRA_FS_MODE_AUTO && !peek, "MADEIRA_FS_POLLPEEK=0 turns the poll answer off" );
    return failed != 0;
}
'''

models = [('fastsync-cellrace', []), ('fastsync-semrace', [])]
if os.environ.get('FASTSYNC_TSAN') == '1':
    models.append(('fastsync-semrace', ['-fsanitize=thread']))

if not cc:
    check(False, 'a C compiler (cc) on PATH')
else:
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / 'switches.c'
        src.write_text(harness)
        exe = Path(tmp) / 'switches'
        r = subprocess.run([cc, '-O1', '-Wall', '-Wno-unused-function', '-o', str(exe), str(src)],
                           capture_output=True, text=True)
        check(r.returncode == 0, 'switch harness compiles from sync.c and event.c' + ('' if not r.returncode else ': ' + r.stderr[-2000:]))
        if r.returncode == 0:
            r = subprocess.run([str(exe)], capture_output=True, text=True)
            sys.stdout.write(r.stdout)
            check(r.returncode == 0, 'fastsync switches: off unless asked, never with madsync')

        # -------------------------------------------------------------- 2. models
        for name, extra in models:
            exe = Path(tmp) / (name + ('-tsan' if extra else ''))
            r = subprocess.run([cc, '-O2' if not extra else '-O1', '-g', '-Wall', *extra,
                                '-I' + str(root / 'wine/include'), '-o', str(exe),
                                str(root / 'tests/host' / (name + '.c')), '-lpthread'],
                               capture_output=True, text=True)
            label = name + (' (ThreadSanitizer)' if extra else '')
            check(r.returncode == 0, f'{label} compiles against wine/include/wine/madeira_fastsync.h'
                  + ('' if not r.returncode else ': ' + r.stderr[-2000:]))
            if r.returncode:
                continue
            r = subprocess.run([str(exe)], capture_output=True, text=True, timeout=600)
            tail = '\n'.join(r.stdout.strip().splitlines()[-4:])
            print(tail)
            check(r.returncode == 0 and 'WARNING: ThreadSanitizer' not in r.stderr,
                  f'{label} passes (exit {r.returncode})')

# ------------------------------------------------------------------ 3. source checks
block = between(sync, '#ifdef WINE_IOS\n\n/***********************************************************************\n'
                      ' *   Madeira fastsync', '#endif /* WINE_IOS */')
check('#include "wine/madeira_fastsync.h"' in block, 'the client block is iOS-only and uses the shared header')
for name in ['NtSetEvent', 'NtResetEvent', 'NtReleaseSemaphore', 'NtQuerySemaphore',
             'NtWaitForSingleObject', 'NtWaitForMultipleObjects']:
    body = between(sync, f'NTSTATUS WINAPI {name}(', '\n}\n')
    calls = [m.start() for m in re.finditer(r'madeira_fast\w*\(', body)]
    ok = bool(calls)
    for pos in calls:
        pre = body[:pos]
        ok &= pre.rfind('#ifdef WINE_IOS') > pre.rfind('#endif')
    check(ok, f'{name}: every fastsync call is under #ifdef WINE_IOS')
close = func(sync, 'void close_inproc_sync( HANDLE handle )')
check(close.index('madeira_fast_close( handle )') < close.index('if (inproc_device_fd < 0) return;'),
      'close_inproc_sync() drops the handle from the fastsync cache first (every NtClose/dup/APC close)')
init_done = func(server_ios, 'void server_init_process_done(void)')
check('madeira_fast_flush_pid();' in init_done, 'server_init_process_done() flushes a reissued process id')
alloc = func(event, 'static int madeira_cell_alloc_kind(')
check(re.search(r'\{\s*struct madeira_sync_cell \*cell;\s*int idx;\s*if \(!madeira_fastsync_enabled\(\)\) return -1;', alloc)
      is not None, 'the server allocates a cell only when fastsync is switched on')
check('madeira_fastsync_on = on && get_inproc_device_fd() < 0;' in srv_on, 'the server keeps madsync and fastsync exclusive')
check('if (madeira_fastsync_cells_on() && wake_thread( thread ) != 0) return;' in thread,
      'the timeout re-check runs only while fastsync cells exist')
check('madeira_sem_cell_alloc( initial, max )' in semaphore and 'madeira_semaphore_cell_index( obj )' in inproc,
      'semaphores allocate through the same switch and are learnt through get_inproc_sync_fd')
for text, name in [(sync, 'sync.c'), (event, 'event.c'), (semaphore, 'semaphore.c'), (thread, 'thread.c')]:
    added = [l for l in text.splitlines() if 'madeira_' in l.lower() and 'fast' in l.lower()]
    check(not any(re.search(r'\bmalloc|calloc|realloc\b', l) for l in added), f'{name}: no allocation in the fastsync lines')

print('check-fastsync:', 'FAIL' if failures else 'PASS')
sys.exit(1 if failures else 0)
