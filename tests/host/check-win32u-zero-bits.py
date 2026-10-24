#!/usr/bin/env python3
"""win32u allocation ceiling per pseudo-process (build/win32u-unix/syscall_ios.c); no Wine runs.

Compiles the production win32u_zero_bits() against a stubbed TEB and checks: a 64-bit thread
always gets 0 (upstream's value for a 64-bit process) without touching the registry, a WoW64
thread gets HighestUserAddress | 0x7fffffff, a bogus (host-sized) HighestUserAddress falls back
to the 2 GB guest ceiling, and a 64-bit process that runs after a 32-bit one still gets 0.
Also checks that the WM_COPYDATA return buffer in message_ios.c asks the calling process.
"""
from pathlib import Path
import subprocess, tempfile

root = Path(__file__).resolve().parents[2]
src = (root / "build/win32u-unix/syscall_ios.c").read_text()
body = src[src.index("struct ios_zero_bits_entry"):src.index("NTSTATUS win32u_unix_lib_init(void)")]
msg = (root / "build/win32u-unix/message_ios.c").read_text()
assert "ret_extra_buffer, caller_zero_bits()," in msg and "ret_extra_buffer, zero_bits," not in msg

harness = r"""
#include <stdio.h>
#include <stdint.h>
#include <pthread.h>
typedef uintptr_t ULONG_PTR; typedef uint32_t DWORD; typedef int NTSTATUS;
typedef struct { void *UniqueProcess; } CLIENT_ID;
typedef struct { void *Peb; CLIENT_ID ClientId; DWORD WowTebOffset; } TEB;
typedef struct { ULONG_PTR HighestUserAddress; } SYSTEM_BASIC_INFORMATION;
#define SystemEmulationBasicInformation 62
#define HandleToULong(h) ((DWORD)(ULONG_PTR)(h))
static __thread TEB teb;
static ULONG_PTR fake_high; static int queries;
static TEB *NtCurrentTeb(void) { return &teb; }
static NTSTATUS NtQuerySystemInformation( int c, void *info, DWORD len, DWORD *ret )
{ (void)c; (void)len; (void)ret; queries++; ((SYSTEM_BASIC_INFORMATION *)info)->HighestUserAddress = fake_high; return 0; }
""" + body + r"""
static ULONG_PTR as( void *peb, int pid, int wow )
{ teb.Peb = peb; teb.ClientId.UniqueProcess = (void *)(ULONG_PTR)pid; teb.WowTebOffset = wow ? 0x2000 : 0;
  ios_zero_bits_cached_peb = NULL; return win32u_zero_bits(); }
int main(void)
{
    int q;
    fake_high = 0x7ffeffff;
    if (as( (void *)0x1000, 4, 0 ) != 0 || queries) return 1;               /* 64-bit: 0, no query */
    if (as( (void *)0x2000, 8, 1 ) != 0x7fffffff) return 2;                  /* WoW64, 2 GB */
    fake_high = 0xfffeffff;
    if (as( (void *)0x3000, 12, 1 ) != 0xffffffff) return 3;                 /* WoW64, LAA 4 GB */
    fake_high = 0x7ffffffeffffULL;
    if (as( (void *)0x4000, 16, 1 ) != 0x7fffffff) return 4;                 /* host-sized: 2 GB */
    q = queries;
    if (as( (void *)0x2000, 8, 1 ) != 0x7fffffff || queries != q) return 5;  /* cached per (pid, peb) */
    if (as( (void *)0x5000, 20, 0 ) != 0) return 6;                          /* 64-bit after 32-bit */
    puts( "ok" );
    return 0;
}
"""
with tempfile.TemporaryDirectory() as t:
    c = Path(t) / "zb.c"; c.write_text(harness)
    exe = Path(t) / "zb"
    subprocess.run(["cc", "-std=gnu11", "-Wall", "-Wno-unused-function", "-pthread",
                    "-fsanitize=address,undefined", str(c), "-o", str(exe)], check=True)
    out = subprocess.run([str(exe)], capture_output=True, text=True)
    assert out.returncode == 0 and out.stdout.strip() == "ok", (out.returncode, out.stdout, out.stderr)
print("PASS: 64-bit threads get 0 without a query; WoW64 threads get their guest ceiling per (pid, PEB); host-sized limits fall back to 2 GB")
