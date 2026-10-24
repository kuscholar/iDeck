#!/usr/bin/env python3
"""32-bit table of the iOS audio driver (build/ntdll-unix/audio_null_ios.c); no Wine runs.

Part A: the wow64 table has the same 37 slots in the same order as the 64-bit table, and every
entry it shares with the 64-bit table is one that ignores its arguments or whose argument block
has no pointer.  Part B compiles the production render-scratch allocator against stubs: a caller
without a guest window gets calloc() (the upstream path, no virtual-memory call), a 32-bit caller
gets an allocation with a guest ceiling inside its window, and an allocation outside the window
is refused.
"""
from pathlib import Path
import re, subprocess, tempfile

root = Path(__file__).resolve().parents[2]
src = (root / "build/ntdll-unix/audio_null_ios.c").read_text()

def table(name):
    body = src[src.index("const void *%s[] = {" % name):]
    body = body[:body.index("};")]
    return re.findall(r"^\s*(\w+),\s*/\*\s*(\w+)", body, re.M)

t64, t32 = table("audio_null_ios_unix_call_funcs"), table("audio_null_ios_unix_call_wow64_funcs")
assert len(t64) == len(t32) == 37, (len(t64), len(t32))
assert [s for _, s in t64] == [s for _, s in t32], "slot order"
shared_ok = {"process_attach", "process_detach", "start", "stop", "reset", "timer_loop",
             "release_render_buffer", "release_capture_buffer", "set_sample_rate", "is_started",
             "get_loopback_capture_device", "midi_get_driver", "midi_init", "midi_release",
             "midi_out_message", "midi_in_message", "midi_notify_wait", "aux_message"}
for (f64, slot), (f32, _) in zip(t64, t32):
    if f32 == f64:
        assert slot in shared_ok, ("shared entry with a pointer-carrying block", slot)
    else:
        assert f32.startswith("ios_wow64_"), (slot, f32)
print("PASS: 37 slots in the same order; shared entries ignore their args or carry no pointers")

a = src.index("static BYTE *ios_audio_alloc_scratch(")
b = src.index("static NTSTATUS ios_process_attach(void *args)")
alloc = src[a:b]
harness = r"""
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
typedef unsigned char BYTE; typedef uint32_t UINT32, DWORD; typedef uintptr_t UINT_PTR; typedef int NTSTATUS;
typedef void *HANDLE;
#define IOS_CURRENT_PROCESS ((HANDLE)(intptr_t)-1)
#define IOS_MEM_COMMIT 0x1000u
#define IOS_MEM_RESERVE 0x2000u
#define IOS_MEM_RELEASE 0x8000u
#define IOS_PAGE_READWRITE 4u
static unsigned long base; static int allocs, frees; static UINT_PTR last_zero_bits; static int place_outside;
static unsigned long ios_wow_base(void) { return base; }
static int ios_wow_in_window(const void *p) { return base && (uintptr_t)p >= base && (uintptr_t)p < base + 0x100000000ull; }
static char arena[1 << 20];
static NTSTATUS NtAllocateVirtualMemory(HANDLE h, void **ret, UINT_PTR zb, UINT_PTR *size, DWORD t, DWORD p)
{ (void)h; (void)t; (void)p; (void)size; allocs++; last_zero_bits = zb;
  *ret = place_outside ? (void *)arena : (void *)(base + 0x100000); return 0; }
static NTSTATUS NtFreeVirtualMemory(HANDLE h, void **a, UINT_PTR *s, DWORD t) { (void)h; (void)a; (void)s; (void)t; frees++; return 0; }
""" + alloc + r"""
int main(void)
{
    int guest; BYTE *p;
    p = ios_audio_alloc_scratch(1024, 4, &guest);
    if (!p || guest || allocs) return 1;
    ios_audio_free_scratch(p, guest);
    if (frees) return 2;
    base = 0x7100000000ul;
    p = ios_audio_alloc_scratch(1024, 4, &guest);
    if (!guest || allocs != 1 || last_zero_bits != 1 || !ios_wow_in_window(p)) return 3;
    ios_audio_free_scratch(p, guest);
    if (frees != 1) return 4;
    place_outside = 1;
    p = ios_audio_alloc_scratch(1024, 4, &guest);
    if (p || guest || frees != 2) return 5;
    puts("ok");
    return 0;
}
"""
with tempfile.TemporaryDirectory() as t:
    c = Path(t) / "scratch.c"; c.write_text(harness)
    exe = Path(t) / "scratch"
    subprocess.run(["cc", "-std=gnu11", "-Wall", "-Wno-unused-function", "-fsanitize=address,undefined",
                    str(c), "-o", str(exe)], check=True)
    out = subprocess.run([str(exe)], capture_output=True, text=True)
    assert out.returncode == 0 and out.stdout.strip() == "ok", (out.returncode, out.stdout, out.stderr)
print("PASS: no window -> calloc and free (upstream); 32-bit caller -> guest-ceiling allocation in its window; outside the window -> refused")
