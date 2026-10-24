#!/usr/bin/env python3
"""MADEIRA_PRELOAD_DLLS: DLLs loaded and pinned at the first D3D12CreateDevice.

RDR2 on build 476 (2026-10-09 16:51) loaded xinput1_4.dll only at its first
XInput call, when the JIT pool had no room left for the copy, so neither the
controller nor the on-screen controls reached the game. The opt-in switch loads
the named DLLs when the process creates (or probes) its first D3D12 device,
while the pool still has room, and pins them so they are never copied again.

Checks: both D3D12 entry points call it after the graphics pin and never from
DllMain; it stays outside the graphics pin block; compiled with stubs, the list
is split on ';' and trimmed, each name is loaded and pinned by address once per
process, an unset or too long value loads nothing, and the last error survives.
"""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
source = (root / 'madeira-d3d12/src/pe/madeira_d3d12.c').read_text()


def function(text, signature):
    start = text.index(signature)
    return text[start:text.index('\n}', start) + 2] + '\n'


block = source[source.index('/* madeira preload begin */'):source.index('/* madeira preload end */')]
pin = source[source.index('/* madeira graphics pin begin */'):source.index('/* madeira graphics pin end */')]
assert 'mad_preload_dlls' not in pin and 'LoadLibrary' not in pin, 'the graphics pin block stays as it was'
direct = function(source, '__declspec(dllexport) HRESULT WINAPI MadeiraD3D12CreateDevice(')
standard = function(source, 'HRESULT WINAPI D3D12CreateDevice(')
main = function(source, 'BOOL WINAPI DllMain(')
assert 'mad_preload_dlls' not in main, 'never from DllMain'
assert direct.index('mad_pin_graphics_dlls();') < direct.index('mad_preload_dlls();') < direct.index('build_vtables();')
assert 'if (!device) {\n        mad_pin_graphics_dlls();\n        mad_preload_dlls();' in standard, 'the probe path too'
assert source.count('mad_preload_dlls();') == 2
assert 'GetEnvironmentVariableA("MADEIRA_PRELOAD_DLLS"' in block
print('PASS: both D3D12 entry points, after the graphics pin, never from DllMain')

harness = r'''
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef unsigned long DWORD; typedef long LONG; typedef void *HMODULE; typedef const char *LPCSTR; typedef int BOOL;
#define GET_MODULE_HANDLE_EX_FLAG_PIN 0x1
#define GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS 0x4
#define FAIL(...) do { fprintf(stderr, __VA_ARGS__); exit(1); } while (0)
static const char *env_value;
static char loaded[8][64]; static int nloaded, npinned, nlogs;
static DWORD last_error = 1234;
static LONG InterlockedExchange(volatile LONG *p, LONG v) { LONG o = *p; *p = v; return o; }
static DWORD GetLastError(void) { return last_error; }
static void SetLastError(DWORD e) { last_error = e; }
static DWORD GetEnvironmentVariableA(LPCSTR name, char *out, DWORD size)
{
    size_t n;
    if (strcmp(name, "MADEIRA_PRELOAD_DLLS")) FAIL("reads %s\n", name);
    if (!env_value) { last_error = 203; return 0; }
    n = strlen(env_value);
    if (n >= size) return (DWORD)n + 1;
    memcpy(out, env_value, n + 1);
    return (DWORD)n;
}
static HMODULE LoadLibraryA(LPCSTR name)
{
    last_error = 5;
    if (!strcmp(name, "missing.dll")) { last_error = 126; return NULL; }
    strcpy(loaded[nloaded], name);
    return (HMODULE)(size_t)(0x10000 * ++nloaded);
}
static BOOL GetModuleHandleExA(DWORD flags, LPCSTR name, HMODULE *out)
{
    if (flags != (GET_MODULE_HANDLE_EX_FLAG_PIN | GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS)) FAIL("flags %#lx\n", flags);
    if ((size_t)name != (size_t)(0x10000 * nloaded)) FAIL("pins by the loaded module's address\n");
    *out = (HMODULE)name; npinned++;
    return 1;
}
static void d3d12_log(const char *fmt, ...) { va_list a; va_start(a, fmt); vprintf(fmt, a); va_end(a); nlogs++; }
''' + block + r'''
int main(void)
{
    env_value = " xinput1_4.dll ; ;missing.dll;dinput8.dll";
    mad_preload_dlls();
    if (nloaded != 2 || strcmp(loaded[0], "xinput1_4.dll") || strcmp(loaded[1], "dinput8.dll"))
        FAIL("loaded %d: %s %s\n", nloaded, loaded[0], loaded[1]);
    if (npinned != 2 || nlogs != 3) FAIL("pinned %d, logged %d\n", npinned, nlogs);
    if (last_error != 1234) FAIL("last error %lu\n", last_error);
    mad_preload_dlls();
    if (nloaded != 2 || nlogs != 3) FAIL("a second device loads nothing\n");
    printf("PASS: the list is split on ';' and trimmed, each DLL is loaded and pinned by address once, "
           "a missing one is logged, the last error is kept\n");
    return 0;
}
'''
harness_off = harness.split('int main(void)')[0] + r'''
int main(void)
{
    mad_preload_dlls();                    /* unset */
    if (nloaded || nlogs || last_error != 1234) FAIL("unset: loaded %d logged %d\n", nloaded, nlogs);
    return 0;
}
'''
harness_long = harness.split('int main(void)')[0] + r'''
int main(void)
{
    static char big[400];
    memset(big, 'a', sizeof big - 1);
    env_value = big;
    mad_preload_dlls();                    /* longer than the buffer */
    if (nloaded || nlogs) FAIL("too long: loaded %d logged %d\n", nloaded, nlogs);
    return 0;
}
'''
cc = os.environ.get('CC', 'cc')
if not shutil.which(cc):
    print('SKIP: no C compiler')
else:
    with tempfile.TemporaryDirectory(prefix='madeira-preload-') as directory:
        for name, text in (('on', harness), ('off', harness_off), ('long', harness_long)):
            c = Path(directory) / (name + '.c')
            c.write_text(text)
            exe = Path(directory) / name
            subprocess.run([cc, '-std=c11', '-Wall', '-Werror', str(c), '-o', str(exe)], check=True)
            subprocess.run([str(exe)], check=True)
    print('PASS: unset or longer than its buffer, nothing is loaded')
