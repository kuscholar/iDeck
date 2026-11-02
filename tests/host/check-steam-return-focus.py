#!/usr/bin/env python3
"""Test production bounded focus/queue handoff with synthetic Windows replies."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
source = (root / 'build/ideck-control/ideck-control.c').read_text()
policy = source[source.index('static int focus_existing_big_picture(void)'):source.index('static const char *return_to_steam(void)')]
harness = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <wchar.h>
#undef NULL
#define NULL 0
typedef uintptr_t HWND,DWORD_PTR;
typedef unsigned DWORD;
typedef int BOOL;
typedef wchar_t WCHAR;
#define ERROR_SUCCESS 0
#define ERROR_ACCESS_DENIED 5
#define WM_NULL 0
#define SMTO_ABORTIFHUNG 2
#define SMTO_BLOCK 1
#define SMTO_ERRORONEXIT 32
#define SW_RESTORE 9
#define TRUE 1
#define FALSE 0
static HWND steam_window,foreground;
static long long steam_area;
static int exists,responsive,iconic,eligible,attach_ok,queued,attached;
static int foreground_kind;
static int probes,focus_calls,attach_calls,detach_calls,restores,sleeps;
static int accepted_but_not_focused;
static DWORD error,first_error,probe_error;
static int status_responsive,status_focused,status_attached,status_detached;
static int status_explorer,status_attempted;static DWORD status_attach_error;
static int find_big_picture;
static void EnumWindows(int callback,int unused) {
    (void)callback;(void)unused;steam_window=exists?10:0;
}
static void SetLastError(DWORD value){error=value;}
static DWORD GetLastError(void){return error;}
static int SendMessageTimeoutW(HWND window,unsigned msg,int w,int l,unsigned flags,unsigned timeout,DWORD_PTR *result) {
    assert(window==10&&msg==WM_NULL&&!w&&!l&&flags==35&&timeout==500&&result);
    probes++;error=probe_error;return responsive;
}
static int IsIconic(HWND window){assert(window==10);return iconic;}
static void ShowWindowAsync(HWND window,int mode){assert(window==10&&mode==9);restores++;}
static HWND GetForegroundWindow(void){return foreground;}
static BOOL SetForegroundWindow(HWND window) {
    assert(window==10);focus_calls++;
    if(first_error&&!attached){error=first_error;return 0;}
    queued=!accepted_but_not_focused;return 1;
}
static void Sleep(unsigned ms){assert(ms==50);sleeps++;if(queued){foreground=10;queued=0;}}
static DWORD GetWindowThreadProcessId(HWND window,DWORD *pid){assert(window==20);*pid=200;return 2;}
static DWORD GetCurrentThreadId(void){return 1;}
static int image(DWORD pid,wchar_t *path){
    assert(pid==200);
    wcscpy(path,foreground_kind==1?L"c:\\windows\\system32\\explorer.exe":
                foreground_kind==2?L"c:\\other\\explorer.exe":eligible?L"c:\\steam.exe":L"c:\\other.exe");return 1;
}
static int game_window(HWND window){assert(window==20);return 0;}
static BOOL AttachThreadInput(DWORD self,DWORD other,int join) {
    assert(self==1&&other==2);
    if(join){assert(!attached);attach_calls++;attached=attach_ok;if(!attach_ok)error=5;return attach_ok;}
    assert(attached);detach_calls++;attached=0;return 1;
}
static void return_focus_status(int alive,DWORD pe,DWORD fe,DWORD pid,int joined,int detached,int focused,
                                int explorer,int attempted,DWORD attach_error) {
    (void)pe;(void)fe;(void)pid;status_explorer=explorer;status_attempted=attempted;status_attach_error=attach_error;
    status_responsive=alive;status_focused=focused;
    status_attached=joined;status_detached=detached;
}
static void reset(void) {
    steam_window=0;steam_area=0;foreground=20;exists=responsive=eligible=attach_ok=1;
    iconic=queued=attached=probes=focus_calls=attach_calls=detach_calls=restores=sleeps=0;
    error=first_error=probe_error=0;accepted_but_not_focused=0;
    foreground_kind=0;status_explorer=status_attempted=0;status_attach_error=0;
    status_responsive=status_focused=status_attached=status_detached=-1;
}
'''
tests = r'''
int main(void) {
    reset();exists=0;assert(focus_existing_big_picture()==-1&&probes==0&&focus_calls==0);
    reset();responsive=0;probe_error=1460;
    assert(focus_existing_big_picture()==-2&&probes==1&&focus_calls==0&&attach_calls==0);
    assert(status_responsive==0&&status_focused==0);
    reset();foreground=10;assert(focus_existing_big_picture()==1&&focus_calls==0&&attach_calls==0);
    reset();iconic=1;assert(focus_existing_big_picture()==1&&focus_calls==1&&sleeps==1&&restores==1);
    reset();first_error=5;
    assert(focus_existing_big_picture()==1&&focus_calls==2&&attach_calls==1&&detach_calls==1&&!attached);
    assert(status_attached==1&&status_detached==1&&status_focused==1);
    reset();first_error=5;eligible=0;
    assert(focus_existing_big_picture()==0&&focus_calls==1&&attach_calls==0&&detach_calls==0);
    reset();first_error=5;eligible=0;foreground_kind=1;
    assert(focus_existing_big_picture()==1&&attach_calls==1&&detach_calls==1); /* Other system explorer window. */
    assert(status_explorer==1&&status_attempted==1&&status_attach_error==0&&!attached);
    reset();first_error=5;eligible=0;
    assert(focus_existing_big_picture()==0&&attach_calls==0); /* Not system explorer. */
    reset();first_error=5;eligible=0;foreground_kind=2;
    assert(focus_existing_big_picture()==0&&attach_calls==0); /* Non-system executable. */
    reset();first_error=5;attach_ok=0;
    assert(focus_existing_big_picture()==0&&focus_calls==1&&attach_calls==1&&detach_calls==0&&!attached);
    assert(status_attempted==1&&status_attach_error==5);
    reset();first_error=6;
    assert(focus_existing_big_picture()==0&&focus_calls==1&&attach_calls==0);
    reset();accepted_but_not_focused=1;
    assert(focus_existing_big_picture()==0&&focus_calls==1&&attach_calls==0&&status_focused==0);
    puts("PASS production return focus: bounded WM_NULL, actual foreground match, access-denied-only owned queue handoff and paired detach (ASan/UBSan)");
}
'''
with tempfile.TemporaryDirectory() as directory:
    directory = Path(directory)
    c = directory / 'focus.c'
    c.write_text(harness + policy + tests)
    subprocess.run(['clang', '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined',
                    str(c), '-o', str(directory / 'test')], check=True)
    subprocess.run([str(directory / 'test')], check=True)
