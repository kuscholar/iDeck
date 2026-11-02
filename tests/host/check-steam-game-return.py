#!/usr/bin/env python3
"""Exercise the actual return policy; no process launch when BPM already exists."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
source = (root / 'build/ideck-control/ideck-control.c').read_text()
policy = source[source.index('static const char *return_to_steam(void)'):source.index('static UINT key(')]
harness = r'''
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <wchar.h>
static int focus_results[2],focus_calls,open_calls,sleep_calls,open_result;
static int focus_existing_big_picture(void) {
    assert(focus_calls<2);return focus_results[focus_calls++];
}
static int open_steam(const wchar_t *uri) {
    assert(!wcscmp(uri,L"steam://open/bigpicture"));open_calls++;return open_result;
}
static void Sleep(unsigned ms) {assert(ms==200);sleep_calls++;}
static void reset(int first,int second,int opened) {
    focus_results[0]=first;focus_results[1]=second;open_result=opened;
    focus_calls=open_calls=sleep_calls=0;
}
'''
tests = r'''
int main(void) {
    reset(1,-1,0);
    assert(!strcmp(return_to_steam(),"steam-window-focused"));
    assert(focus_calls==1&&open_calls==0&&sleep_calls==0);
    reset(0,-1,1);
    assert(!strcmp(return_to_steam(),"steam-focus-pending"));
    assert(focus_calls==1&&open_calls==0&&sleep_calls==0);
    reset(-2,-1,1);
    assert(!strcmp(return_to_steam(),"steam-window-unresponsive"));
    assert(focus_calls==1&&open_calls==0&&sleep_calls==0);
    reset(-1,-1,0);
    assert(!strcmp(return_to_steam(),"steam-open-failed"));
    assert(focus_calls==1&&open_calls==1&&sleep_calls==0);
    reset(-1,1,1);
    assert(!strcmp(return_to_steam(),"steam-window-focused"));
    assert(focus_calls==2&&open_calls==1&&sleep_calls==1);
    reset(-1,-2,1);
    assert(!strcmp(return_to_steam(),"steam-window-unresponsive"));
    assert(focus_calls==2&&open_calls==1&&sleep_calls==1);
    for(int next=-1;next<=0;next++) {
        reset(-1,next,1);
        assert(!strcmp(return_to_steam(),"big-picture-requested"));
        assert(focus_calls==2&&open_calls==1&&sleep_calls==1);
    }
    puts("PASS production game-return policy: existing BPM/focus denial never spawns; absent window dispatches once; no responsiveness claim (ASan/UBSan)");
}
'''
with tempfile.TemporaryDirectory() as directory:
    directory = Path(directory)
    c = directory / 'return.c'
    c.write_text(harness + policy + tests)
    subprocess.run(['clang', '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined',
                    str(c), '-o', str(directory / 'test')], check=True)
    subprocess.run([str(directory / 'test')], check=True)
