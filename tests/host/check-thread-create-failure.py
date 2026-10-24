#!/usr/bin/env python3
"""A thread that cannot be created says why; no Wine runs.

SocialClubHelper.exe's Chrome_IOThread created a thread and the helper died
at once with Chromium's out-of-memory exit and a size of 0 (logs 2026-10-08
13:39:08, build 451, and 16:38:52, build 455; the game then shows "Failed to
initialize. Error code: 17"). Chromium terminates with the stack size it asked
for when CreateThread fails with an out-of-memory error; what failed inside
NtCreateThreadEx after the server made the thread was never logged.
Checks build/ntdll-unix/thread_ios.c:
  - ios_note_thread_create_failure, compiled with a fake task_threads, prints
    the step, the status, the pthread error, the sizes, the creator and the
    task's thread count, and stops after 64 lines;
  - init_thread_stack names every stack before allocating it (kernel, WoW64
    64-bit and 32-bit, emulator, native), and NtCreateThreadEx reports the TEB,
    init_thread_stack and pthread_create failures;
and in build/ntdll-unix/virtual_ios.c that a [va-scan] failure the unclamped
retry absorbs has its own log budget, so it cannot use up the 256 lines kept
for failures that return STATUS_NO_MEMORY.
Needs python3 and a C compiler.
"""
from pathlib import Path
import re
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
thread = (root / 'build/ntdll-unix/thread_ios.c').read_text()
virtual = (root / 'build/ntdll-unix/virtual_ios.c').read_text()

start = thread.index('static void ios_note_thread_create_failure(')
reporter = thread[start:thread.index('\n}\n', start) + 3]

harness = r'''
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stdarg.h>
#include <errno.h>
typedef long LONG; typedef unsigned long SIZE_T; typedef unsigned int NTSTATUS;
typedef void *HANDLE;
typedef unsigned int mach_port_t, mach_msg_type_number_t, thread_act_t;
typedef thread_act_t *thread_act_array_t;
typedef uintptr_t vm_address_t;
#define KERN_SUCCESS 0
static mach_port_t mach_task_self(void) { return 1; }
static thread_act_t fake_acts[3] = { 11, 12, 13 };
static int deallocated;
static int task_threads(mach_port_t t, thread_act_array_t *a, mach_msg_type_number_t *n) { (void)t; *a = fake_acts; *n = 3; return KERN_SUCCESS; }
static int mach_port_deallocate(mach_port_t t, mach_port_t p) { (void)t; (void)p; deallocated++; return 0; }
static int vm_deallocate(mach_port_t t, vm_address_t a, size_t s) { (void)t; (void)a; (void)s; return 0; }
static LONG InterlockedIncrement(LONG *p) { return ++*p; }
typedef struct { HANDLE UniqueProcess, UniqueThread; } CLIENT_ID;
typedef struct { CLIENT_ID ClientId; void *Peb; } TEB;
static TEB fake_teb = { { (HANDLE)0x1f4, (HANDLE)0x234 }, (void *)0x114658000 };
static TEB *NtCurrentTeb(void) { return &fake_teb; }
#define HandleToULong(h) ((unsigned long)(uintptr_t)(h))
static char out[1 << 16]; static size_t outn;
static int fake_dprintf(int fd, const char *f, ...)
{ va_list ap; int w; (void)fd; va_start(ap, f); w = vsnprintf(out + outn, sizeof out - outn, f, ap); va_end(ap); if (w > 0) outn += w; return w; }
#define dprintf fake_dprintf
''' + reporter + r'''
int main(void)
{
    int i, lines = 0;
    char *p;
    ios_note_thread_create_failure("kernel stack", 0xc0000017, 0, 0x100000, 0x1000);
    ios_note_thread_create_failure("pthread_create", 0xc0000017, EAGAIN, 0, 0);
    printf("%s", out);
    if (!strstr(out, "[thr-create] FAILED at kernel stack: status=0xc0000017 pthread=0(-) reserve=0x100000 commit=0x1000 creator pid=01f4 tid=0234 peb=0x114658000; task threads 3\n"))
        { printf("FAIL: the kernel stack line\n"); return 1; }
    if (!strstr(out, "[thr-create] FAILED at pthread_create: status=0xc0000017 pthread=35(") &&
        !strstr(out, "[thr-create] FAILED at pthread_create: status=0xc0000017 pthread=11("))
        { printf("FAIL: the pthread_create line carries no EAGAIN\n"); return 1; }
    if (deallocated != 6) { printf("FAIL: thread ports not released (%d)\n", deallocated); return 1; }
    for (i = 0; i < 100; i++) ios_note_thread_create_failure("TEB", 0xc0000017, 0, 0, 0);
    for (p = out; (p = strstr(p, "[thr-create] FAILED")); p++) lines++;
    if (lines != 64) { printf("FAIL: %d lines, want 64\n", lines); return 1; }
    printf("PASS: a failed step prints its name, status, pthread error, sizes, creator and the task's thread count; at most 64 lines\n");
    return 0;
}
'''

with tempfile.TemporaryDirectory(prefix='madeira-thread-create-') as directory:
    c = Path(directory) / 'tc.c'
    exe = Path(directory) / 'tc'
    c.write_text(harness)
    build = subprocess.run(['cc', '-std=gnu11', '-Wall', '-Werror', '-Wno-unused-function',
                            '-fsanitize=address,undefined', '-o', str(exe), str(c)], capture_output=True, text=True)
    assert build.returncode == 0, build.stdout + build.stderr
    run = subprocess.run([str(exe)], capture_output=True, text=True)
    print(run.stdout, end='')
    assert run.returncode == 0, run.stdout + run.stderr

its = thread[thread.index('NTSTATUS init_thread_stack( TEB *teb, ULONG_PTR limit, SIZE_T reserve_size, SIZE_T commit_size )\n{'):]
its = its[:its.index('\n}\n')]
allocs = re.findall(r'virtual_alloc_thread_stack\(', its)
steps = re.findall(r'ios_its_step = "([^"]+)";\s*\n\s*if \(\(status = virtual_alloc_thread_stack\(', its)
assert len(allocs) == 5 and steps == ['kernel stack', 'WoW64 64-bit stack', 'WoW64 32-bit stack', 'emulator stack', 'stack'], \
    (len(allocs), steps)
create = thread[thread.index('NTSTATUS WINAPI NtCreateThreadEx('):]
create = create[:create.index('\n}\n')]
assert 'ios_note_thread_create_failure( "TEB", status, 0, stack_reserve, stack_commit );' in create
assert 'ios_note_thread_create_failure( ios_its_step, status, 0, stack_reserve, stack_commit );' in create
assert 'ios_note_thread_create_failure( "pthread_create", status, pthread_err, stack_reserve, stack_commit );' in create
assert create.index('ios_its_step = NULL;') < create.index('init_thread_stack( teb,')
print('PASS: init_thread_stack names each of its 5 stacks; NtCreateThreadEx reports TEB, stack and pthread_create failures')

assert ': ceiling_relaxable ? (++vs_relaxed <= 64 || !(vs_relaxed % 1024)) : (vs_fails++ < 256))' in virtual, \
    'a [va-scan] failure absorbed by the unclamped retry must not spend the STATUS_NO_MEMORY budget'
print('PASS: absorbed [va-scan] failures have their own budget; the 256 lines stay for STATUS_NO_MEMORY')
