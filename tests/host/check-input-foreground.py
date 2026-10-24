#!/usr/bin/env python3
"""Opt-in foreground for a process when no window is foreground (MADEIRA_INPUT_FOREGROUND); no Wine runs.

Horizon Zero Dawn (build 471, 2026-10-09 15:01) showed its window with
SWP_NOACTIVATE only and reads no XInput, so GetForegroundWindow() stayed NULL
and the wineserver queued none of the injected keys or taps for it as raw
input. build/win32u-unix/driver_ios.c ios_foreground_if_none makes the polling
or posting process's main window foreground while no window is foreground.
Compiles the production function with stubs and checks:
  - off unless MADEIRA_INPUT_FOREGROUND is exactly "1";
  - never while any window is foreground;
  - the process's main window is made foreground through the internal path;
  - nothing without a main window; at most once per 250 ms;
and textually that injected keys and mouse events, and every message poll,
pass through it before the input is sent.
Needs python3 and a C compiler.
"""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
driver = (root / 'build/win32u-unix/driver_ios.c').read_text()


def function(source, signature):
    start = source.index(signature)
    return source[start:source.index('\n}\n', start) + 3]


body = function(driver, 'static void ios_foreground_if_none( const char *why )\n{')   # the definition, not the declaration
mouse = function(driver, 'void winios_drv_post_mouse(')
key = function(driver, 'void winios_drv_post_key(')
events = function(driver, 'static BOOL winios_drv_process_events( DWORD mask )')
assert mouse.index('ios_foreground_if_none(') < mouse.index('send_hardware_message('), 'before the mouse event is sent'
assert key.index('ios_foreground_if_none(') < key.index('send_hardware_message('), 'before the key is sent'
assert 'ios_foreground_if_none( "a message poll" );' in events
assert driver.index('static void ios_foreground_if_none( const char *why );') < driver.index('void winios_drv_post_mouse(')
assert driver.index('static HWND ios_main_window( DWORD pid )') < driver.index('static void ios_foreground_if_none( const char *why )\n{')
print('PASS: injected keys and mouse events and every message poll pass through ios_foreground_if_none')

harness = r'''
#define _GNU_SOURCE
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
typedef int BOOL; typedef unsigned int DWORD; typedef void *HWND;
#define TRUE 1
#define FALSE 0
#define FAIL(...) do { fprintf(stderr, __VA_ARGS__); exit(1); } while (0)
static HWND foreground, main_window;
static int set_calls, set_internal, set_mouse;
static HWND set_hwnd;
static long long clock_ns;
static HWND NtUserGetForegroundWindow(void) { return foreground; }
static DWORD GetCurrentProcessId(void) { return 0x24; }
static HWND ios_main_window( DWORD pid ) { return pid == 0x24 ? main_window : 0; }
static BOOL set_foreground_window( HWND hwnd, BOOL mouse, BOOL internal )
{
    set_calls++; set_hwnd = hwnd; set_mouse = mouse; set_internal = internal; foreground = hwnd;
    return TRUE;
}
static int fake_clock_gettime( clockid_t id, struct timespec *ts )
{
    (void)id; ts->tv_sec = clock_ns / 1000000000LL; ts->tv_nsec = clock_ns % 1000000000LL; return 0;
}
#define clock_gettime fake_clock_gettime
''' + body + r'''
int main(void)
{
    HWND game = (HWND)0x20038;

    clock_ns = 5000000000LL;
    main_window = game;
    ios_foreground_if_none( "test" );
    if (set_calls) FAIL( "acted without MADEIRA_INPUT_FOREGROUND\n" );
    printf( "PASS: nothing happens without MADEIRA_INPUT_FOREGROUND=1\n" );
    return 0;
}
'''

on_harness = harness.replace(r'''int main(void)
{''', r'''int main(void)
{
    if (getenv( "SECOND" )) goto second;''').replace(r'''    printf( "PASS: nothing happens without MADEIRA_INPUT_FOREGROUND=1\n" );
    return 0;
}''', r'''    printf( "PASS: nothing happens without MADEIRA_INPUT_FOREGROUND=1\n" );
    return 0;
second:
    clock_ns = 5000000000LL;
    main_window = (HWND)0x20038;
    foreground = (HWND)0x10036;
    ios_foreground_if_none( "test" );
    if (set_calls) FAIL( "took the foreground while another window held it\n" );
    foreground = 0;
    main_window = 0;
    ios_foreground_if_none( "test" );
    if (set_calls) FAIL( "acted without a main window\n" );
    clock_ns += 300000000LL;
    main_window = (HWND)0x20038;
    ios_foreground_if_none( "test" );
    if (set_calls != 1 || set_hwnd != (HWND)0x20038 || !set_internal || set_mouse)
        FAIL( "main window not made foreground internally: calls %d hwnd %p internal %d mouse %d\n",
              set_calls, set_hwnd, set_internal, set_mouse );
    foreground = 0;
    clock_ns += 100000000LL;
    ios_foreground_if_none( "test" );
    if (set_calls != 1) FAIL( "acted twice within 250 ms\n" );
    clock_ns += 200000000LL;
    ios_foreground_if_none( "test" );
    if (set_calls != 2) FAIL( "did not act again after 250 ms\n" );
    printf( "PASS: never while a window is foreground, never without a main window, the main window made "
            "foreground through the internal path, at most every 250 ms\n" );
    return 0;
}''')

with tempfile.TemporaryDirectory(prefix='madeira-fg-') as directory:
    temporary = Path(directory)
    cc = os.environ.get('CC', 'cc')
    if not shutil.which(cc):
        raise SystemExit('SKIP: no C compiler')
    source = temporary / 'fg.c'
    source.write_text(on_harness)
    binary = temporary / 'fg'
    subprocess.run([cc, '-std=c11', '-Wall', '-Werror', '-Wno-unused-function', str(source), '-pthread', '-o',
                    str(binary)], check=True)
    env = {k: v for k, v in os.environ.items() if k != 'MADEIRA_INPUT_FOREGROUND'}
    subprocess.run([str(binary)], check=True, env=env)
    for value in ('0', '', '10', 'yes'):
        subprocess.run([str(binary)], check=True, env=dict(env, MADEIRA_INPUT_FOREGROUND=value))
    subprocess.run([str(binary)], check=True, env=dict(env, MADEIRA_INPUT_FOREGROUND='1', SECOND='1'))
print('PASS: only MADEIRA_INPUT_FOREGROUND=1 turns it on')
