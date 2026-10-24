#!/usr/bin/env python3
"""Unchanged ClipCursor requests notify no one (build/wineserver/queue_ios.c); no Wine runs.

Compiles the production set_clip_rectangle (and its ios_clip_dedupe switch)
against a stub desktop and counts the WM_WINE_CLIPCURSOR notifications it queues
for the foreground thread and posts to the desktop thread:
  - the first clip after none, a different rectangle, other flags and every
    reset notify exactly as before;
  - the same rectangle with the same flags and no reset updates nothing and
    queues nothing (counted in ios_clip_repeats_skipped);
  - a rectangle that clamps to the current one counts as the same;
  - NOCLIP after NOCLIP stays silent, as upstream;
  - MADEIRA_CLIP_NOTIFY_ALWAYS=1 notifies every clip again;
and textually that the set_cursor census reports the flags and the skip count.
Needs python3 and a C compiler (CC, default cc).
"""
from pathlib import Path
import os
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
queue = (root / 'build/wineserver/queue_ios.c').read_text()
request = (root / 'build/wineserver/request_ios.c').read_text()

start = queue.index('/* madeira-bcd: a ClipCursor that changes nothing')
end = queue.index('\n}\n', queue.index('void set_clip_rectangle(')) + 3
code = queue[start:end]

harness = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define SET_CURSOR_HANDLE 0x01
#define SET_CURSOR_CLIP   0x08
#define SET_CURSOR_NOCLIP 0x10
#define WM_WINE_CLIPCURSOR 0x80000004
#define FALSE 0
struct rectangle { int left, top, right, bottom; };
typedef struct { struct { int x, y; unsigned int last_change; struct rectangle clip; } cursor; } desktop_shm_t;
struct desktop { desktop_shm_t *shared; unsigned int clip_flags; };
#define SHARED_WRITE_BEGIN( object, type ) do { type *shared = (type *)(object);
#define SHARED_WRITE_END } while (0)
#define max(a,b) ((a) > (b) ? (a) : (b))
#define min(a,b) ((a) < (b) ? (a) : (b))
static int queued, posted, warped;
static void get_virtual_screen_rect( struct desktop *d, struct rectangle *r, int raw ) { (void)d; (void)raw; r->left = 0; r->top = 0; r->right = 1920; r->bottom = 1080; }
static void set_cursor_pos( struct desktop *d, int x, int y ) { d->shared->cursor.x = x; d->shared->cursor.y = y; warped++; }
static void post_desktop_message( struct desktop *d, unsigned int m, unsigned long w, long l ) { (void)d; (void)m; (void)w; (void)l; posted++; }
static void queue_cursor_message( struct desktop *d, unsigned int win, unsigned int m, unsigned long w, long l ) { (void)d; (void)win; (void)m; (void)w; (void)l; queued++; }
''' + code + r'''
static int fails;
#define CHECK(c) do { if (!(c)) { fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #c); fails++; } } while (0)
int main( int argc, char **argv )
{
    desktop_shm_t shm = { { 100, 100, 0, { 0, 0, 1920, 1080 } } };
    struct desktop d = { &shm, SET_CURSOR_NOCLIP };
    struct rectangle game = { 0, 0, 1280, 720 }, wide = { -50, -50, 1280, 720 }, other = { 0, 0, 1280, 700 };
    int i;
    (void)argv;
    if (argc > 1)   /* MADEIRA_CLIP_NOTIFY_ALWAYS=1 */
    {
        set_clip_rectangle( &d, &game, SET_CURSOR_CLIP, 0 );
        for (i = 0; i < 5; i++) set_clip_rectangle( &d, &game, SET_CURSOR_CLIP, 0 );
        CHECK( queued == 6 && !ios_clip_repeats_skipped );
        if (!fails) puts( "PASS: MADEIRA_CLIP_NOTIFY_ALWAYS=1 notifies every clip" );
        return fails != 0;
    }
    set_clip_rectangle( &d, &game, SET_CURSOR_CLIP, 0 );            /* first clip */
    CHECK( queued == 1 && shm.cursor.clip.right == 1280 );
    for (i = 0; i < 100; i++) set_clip_rectangle( &d, &game, SET_CURSOR_CLIP, 0 );
    CHECK( queued == 1 && ios_clip_repeats_skipped == 100 );        /* repeats: silent */
    set_clip_rectangle( &d, &wide, SET_CURSOR_CLIP, 0 );            /* clamps to the same rect */
    CHECK( queued == 1 && ios_clip_repeats_skipped == 101 );
    set_clip_rectangle( &d, &other, SET_CURSOR_CLIP, 0 );           /* a different rect */
    CHECK( queued == 2 && shm.cursor.clip.bottom == 700 );
    set_clip_rectangle( &d, &other, SET_CURSOR_CLIP | 0x20, 0 );    /* other flags */
    CHECK( queued == 3 );
    set_clip_rectangle( &d, NULL, SET_CURSOR_NOCLIP, 1 );           /* reset (foreground change) */
    CHECK( queued == 4 && posted == 1 );
    set_clip_rectangle( &d, NULL, SET_CURSOR_NOCLIP, 1 );           /* every reset notifies */
    CHECK( queued == 5 && posted == 2 );
    set_clip_rectangle( &d, NULL, SET_CURSOR_NOCLIP, 0 );           /* NOCLIP after NOCLIP: silent, as upstream */
    CHECK( queued == 5 );
    set_clip_rectangle( &d, &game, SET_CURSOR_CLIP, 0 );            /* clip again after the reset */
    CHECK( queued == 6 );
    shm.cursor.x = 1500;                                            /* the warp still runs before the check */
    set_clip_rectangle( &d, &game, SET_CURSOR_CLIP, 0 );
    CHECK( warped >= 1 && shm.cursor.x == 1279 && queued == 6 );
    if (!fails) puts( "PASS: first clip, other rects, other flags and resets notify; identical repeats are skipped" );
    return fails != 0;
}
'''

with tempfile.TemporaryDirectory() as tmp:
    c = Path(tmp) / 'clip.c'
    c.write_text(harness)
    exe = Path(tmp) / 'clip'
    subprocess.run([os.environ.get('CC', 'cc'), '-std=gnu11', '-Wall', '-Werror', '-Wno-unused-function',
                    str(c), '-o', str(exe)], check=True)
    out = subprocess.run([str(exe)], capture_output=True, text=True)
    print(out.stdout.strip() or out.stderr.strip())
    assert out.returncode == 0
    out = subprocess.run([str(exe), 'always'], capture_output=True, text=True,
                         env=dict(os.environ, MADEIRA_CLIP_NOTIFY_ALWAYS='1'))
    print(out.stdout.strip() or out.stderr.strip())
    assert out.returncode == 0

census = request[request.index('static unsigned long cursor_flags[6];'):]
assert 'thread->req.set_cursor_request.flags' in census
assert 'unchanged ClipCursor notifications skipped so far: %lu' in census
print('PASS: the [srv-req] census reports set_cursor by flag and the skipped repeats')

# the select census (which waits fastsync could answer in the client)
sel = request[request.index('static unsigned long sel_shape[7], sel_obj[8], sel_multi_sem;'):]
sel = sel[:sel.index('if (req == REQ_set_cursor)')]
assert 'if (!obj) clear_error();' in sel and 'release_object( obj );' in sel, 'the lookup leaves no error or reference behind'
assert 'shape = (thread->req.select_request.flags & SELECT_ALERTABLE) ? 1 : 0;' in sel
assert 'type == &semaphore_type ? 0' in sel
assert '[srv-req] select by shape: single %lu, single alertable %lu, any of many %lu' in request
print('PASS: the [srv-req] census reports select by shape and by the first object waited on')
