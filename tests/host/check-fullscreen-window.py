#!/usr/bin/env python3
"""Full screen moves the game's window over the monitor (madeira.cfg
fullscreen-window = 1); no Wine, no Metal.

Cuts mad_swap_fullscreen_window and swap_SetFullscreenState out of
madeira-d3d12/src/pe/madeira_d3d12.c, compiles them on the host with stub
user32 / kernel32 calls and checks:
  - off by default: entering full screen records the state and touches no
    window, as before;
  - on: entering full screen (windowed -> full screen only) moves the window to
    the monitor's rectangle with SWP_ASYNCWINDOWPOS | SWP_NOZORDER |
    SWP_NOOWNERZORDER | SWP_NOACTIVATE, after recording the state; full screen
    -> full screen and leaving full screen move nothing;
  - user32 is looked up at run time (no new import): no user32, a missing
    function, a dead window or no monitor info leave the window alone;
  - the switch is read once; the [swap-diag] line says whether it moved.
The catalog lists fullscreen-window, off by default.
"""
from pathlib import Path
import os, re, shutil, subprocess, sys, tempfile

root = Path(__file__).resolve().parents[2]
src = (root / "madeira-d3d12/src/pe/madeira_d3d12.c").read_text()
ok = True


def check(what, cond):
    global ok
    print(("ok   " if cond else "FAIL ") + what)
    ok &= bool(cond)


start = src.index("static int g_fs_window = -1;")
end = src.index("\n}\n", src.index("static HRESULT STDMETHODCALLTYPE swap_SetFullscreenState(")) + 3
cut = src[start:end]
check("the two functions are found together", "static int mad_swap_fullscreen_window(" in cut)
check("no user32 import: looked up with GetProcAddress",
      all('GetProcAddress(u, "%s")' % f in cut for f in ("IsWindow", "MonitorFromWindow", "GetMonitorInfoW", "SetWindowPos"))
      and 'GetModuleHandleW(L"user32.dll")' in cut and "LoadLibrary" not in cut)
cat = (root / "app/Madeira/ConfigCatalog.generated.swift").read_text()
check("catalog lists fullscreen-window, off by default",
      re.search(r'key: "fullscreen-window".*kind: \.bool, defaultValue: "0"', cat) is not None)

harness = r'''
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <stdarg.h>
#include <wchar.h>
typedef int BOOL; typedef unsigned DWORD; typedef unsigned UINT; typedef long LONG; typedef uint64_t UINT64;
typedef long HRESULT; typedef void *HWND; typedef void *HMONITOR; typedef void *HMODULE;
typedef struct { LONG left, top, right, bottom; } RECT;
typedef struct { DWORD cbSize; RECT rcMonitor, rcWork; DWORD dwFlags; } MONITORINFO;
typedef void (*FARPROC)(void);
#define WINAPI
#define STDMETHODCALLTYPE
#define S_OK 0L
#define MONITOR_DEFAULTTOPRIMARY 1
#define SWP_NOSIZE 0x0001
#define SWP_NOMOVE 0x0002
#define SWP_NOZORDER 0x0004
#define SWP_NOACTIVATE 0x0010
#define SWP_NOOWNERZORDER 0x0200
#define SWP_ASYNCWINDOWPOS 0x4000
typedef struct IDXGISwapChain4 IDXGISwapChain4; typedef struct IDXGIOutput IDXGIOutput;
struct mad_swapchain { int vtbl; HWND hwnd; struct { BOOL Windowed; } fs; struct { UINT Width, Height; } desc; };
static long long cfg = 0; static int cfg_reads, have_user32 = 1, live = 1, have_info = 1, missing_fn, moves, lines;
static HWND moved_hwnd; static int mx, my, mw, mh; static UINT mflags; static char last[600];
static long long mad_cfg_int_pe(const char *k, long long d) { cfg_reads++; return strcmp(k, "fullscreen-window") ? d : cfg; }
static void d3d12_log(const char *f, ...) { (void)f; }
static UINT64 mad_tick(void) { return 0; }
static double mad_swd_ms(UINT64 t) { (void)t; return 0.0; }
static volatile LONG g_swd_fs_n;
static int mad_swd_take(volatile LONG *n, LONG *seq) { *seq = ++*n; return 1; }
static void mad_swd_log(const char *f, ...) { va_list a; va_start(a, f); vsnprintf(last, sizeof last, f, a); va_end(a); lines++; }
static LONG InterlockedIncrement(volatile LONG *p) { return ++*p; }
static DWORD GetCurrentThreadId(void) { return 0x460; }
static BOOL WINAPI fake_IsWindow(HWND h) { return live && h == (HWND)0x200f2; }
static HMONITOR WINAPI fake_MonitorFromWindow(HWND h, DWORD f) { (void)h; return f == MONITOR_DEFAULTTOPRIMARY ? (HMONITOR)0x10001 : 0; }
static BOOL WINAPI fake_GetMonitorInfoW(HMONITOR m, MONITORINFO *mi) {
    if (!have_info || m != (HMONITOR)0x10001 || mi->cbSize != sizeof *mi) return 0;
    mi->rcMonitor.left = 0; mi->rcMonitor.top = 0; mi->rcMonitor.right = 1568; mi->rcMonitor.bottom = 720; return 1; }
static BOOL WINAPI fake_SetWindowPos(HWND h, HWND after, int x, int y, int w, int hh, UINT fl) {
    (void)after; moves++; moved_hwnd = h; mx = x; my = y; mw = w; mh = hh; mflags = fl; return 1; }
static HMODULE GetModuleHandleW(const wchar_t *n) { return have_user32 && !wcscmp(n, L"user32.dll") ? (HMODULE)0x7700 : 0; }
static FARPROC GetProcAddress(HMODULE m, const char *n) {
    if (m != (HMODULE)0x7700) return 0;
    if (missing_fn && !strcmp(n, "GetMonitorInfoW")) return 0;
    if (!strcmp(n, "IsWindow")) return (FARPROC)fake_IsWindow;
    if (!strcmp(n, "MonitorFromWindow")) return (FARPROC)fake_MonitorFromWindow;
    if (!strcmp(n, "GetMonitorInfoW")) return (FARPROC)fake_GetMonitorInfoW;
    if (!strcmp(n, "SetWindowPos")) return (FARPROC)fake_SetWindowPos;
    return 0; }
''' + cut + r'''
static int bad;
#define EXPECT(c, w) do { if (!(c)) { printf("FAIL %s\n", w); bad = 1; } } while (0)
int main(void) {
    struct mad_swapchain s = { 0, (HWND)0x200f2, { 1 }, { 1280, 648 } };
    IDXGISwapChain4 *T = (IDXGISwapChain4 *)&s;
    EXPECT(swap_SetFullscreenState(T, 1, 0) == S_OK && !s.fs.Windowed && moves == 0, "off: recorded only");
    EXPECT(strstr(last, "recorded only") != 0, "off: the line says recorded only");
    swap_SetFullscreenState(T, 0, 0); swap_SetFullscreenState(T, 1, 0);
    EXPECT(cfg_reads == 1 && moves == 0, "off: read once, nothing moved");
    g_fs_window = -1; cfg = 1; s.fs.Windowed = 1;
    EXPECT(swap_SetFullscreenState(T, 1, 0) == S_OK && !s.fs.Windowed, "on: full screen recorded");
    EXPECT(moves == 1 && moved_hwnd == (HWND)0x200f2 && mx == 0 && my == 0 && mw == 1568 && mh == 720, "on: over the whole monitor");
    EXPECT(mflags == (SWP_NOZORDER | SWP_NOOWNERZORDER | SWP_NOACTIVATE | SWP_ASYNCWINDOWPOS), "on: posted, no z-order or activation change");
    EXPECT(strstr(last, "window moved over the monitor (fullscreen-window)") != 0, "on: the line says it moved");
    swap_SetFullscreenState(T, 1, 0);
    EXPECT(moves == 1, "full screen -> full screen: nothing moves");
    swap_SetFullscreenState(T, 0, 0);
    EXPECT(moves == 1 && s.fs.Windowed, "leaving full screen moves nothing");
    have_user32 = 0; swap_SetFullscreenState(T, 1, 0); swap_SetFullscreenState(T, 0, 0); have_user32 = 1;
    EXPECT(moves == 1, "no user32: nothing");
    missing_fn = 1; swap_SetFullscreenState(T, 1, 0); swap_SetFullscreenState(T, 0, 0); missing_fn = 0;
    EXPECT(moves == 1, "a missing user32 function: nothing");
    live = 0; swap_SetFullscreenState(T, 1, 0); swap_SetFullscreenState(T, 0, 0); live = 1;
    EXPECT(moves == 1, "a dead window: nothing");
    have_info = 0; swap_SetFullscreenState(T, 1, 0); swap_SetFullscreenState(T, 0, 0); have_info = 1;
    EXPECT(moves == 1, "no monitor info: nothing");
    s.hwnd = 0; swap_SetFullscreenState(T, 1, 0); swap_SetFullscreenState(T, 0, 0); s.hwnd = (HWND)0x200f2;
    EXPECT(moves == 1, "no window: nothing");
    swap_SetFullscreenState(T, 1, 0);
    EXPECT(moves == 2 && cfg_reads == 2, "on again: moved; the switch was read once per session");
    if (!bad) printf("ok\n");
    return bad;
}
'''
cc = os.environ.get("CC") or shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
if not cc:
    print("note: no host C compiler; runtime checks skipped")
else:
    with tempfile.TemporaryDirectory() as t:
        t = Path(t)
        (t / "h.c").write_text(harness)
        exe = t / "h"
        r = subprocess.run([cc, "-std=gnu11", "-Wall", "-Wno-unused-function", "-Wno-cast-function-type",
                            "-o", str(exe), str(t / "h.c")], capture_output=True, text=True)
        if r.returncode:
            print(r.stderr[-3000:])
        out = subprocess.run([str(exe)], capture_output=True, text=True).stdout if exe.exists() else ""
        check("fullscreen-window runtime (off, on, transitions, missing pieces, read once)", r.returncode == 0 and out.strip() == "ok")
        if out.strip() != "ok":
            print(out[:3000])

print("PASS" if ok else "FAILED")
sys.exit(0 if ok else 1)
