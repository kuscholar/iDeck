#!/usr/bin/env python3
"""A console's conhost.exe starts without a window; no Wine runs.

kernelbase starts conhost.exe with a window unless the program asked for none
(CREATE_NO_WINDOW appends --headless). In a Dock session that window is
dockhost.exe's console at 0,0 of the virtual desktop. Compiles the production
ios_image_name_is / sc_switch_end / console_headless_cmdline from
build/ntdll-unix/process_ios.c and checks:
  - `conhost.exe --server 0x34` gets ` --headless` appended;
  - a pseudo-console's conhost (already --headless) and --unix stay as they are;
  - conhost.exe without --server, look-alike images and look-alike switches stay;
  - env.MADEIRA_CONSOLE_WINDOW=1 keeps the window; a too small buffer changes nothing;
and textually that NtCreateUserProcess applies it after the ARM64EC refusal and
before the child's startup info is built from the command line.
Needs python3 and a C compiler (AddressSanitizer/UBSan when available).
"""
from pathlib import Path
import os
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
source = (root / 'build/ntdll-unix/process_ios.c').read_text()


def function(text, signature):
    start = text.index(signature)
    return text[start:text.index('\n}', start) + 2] + '\n'


create = function(source, 'NTSTATUS WINAPI NtCreateUserProcess(')
call = 'o = console_headless_cmdline( window, params->ImagePathName.Buffer,'
assert call in create
assert 'const char *window = getenv( "MADEIRA_CONSOLE_WINDOW" );' in create
site = create[create.index(call):][:1200]
assert 'if (o < 0) free( nbuf );' in site
assert 'params->CommandLine.Buffer = nbuf;' in site and 'params->CommandLine.Length = o * sizeof(WCHAR);' in site
assert '[console] the console of %s starts without a window' in site
# after the ARM64EC refusal (a refused conhost needs no flag), before the startup info copies the command line
assert create.index('if (ec_conhost_refuse(') < create.index(call) < create.index('create_startup_info( attr.ObjectName')

code = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef unsigned short WCHAR;
'''
code += function(source, 'static int ios_image_name_is(')
code += function(source, 'static int sc_switch_end(')
code += function(source, 'static int console_headless_cmdline(')
code += r'''
static WCHAR in[2][160], out[200];
static int w( int slot, const char *s )
{
    int i;
    for (i = 0; s[i]; i++) in[slot][i] = (unsigned char)s[i];
    in[slot][i] = 0;
    return i;
}
static int run( const char *env, const char *image, const char *cl, int cap )
{
    int il = w( 0, image ), cll = w( 1, cl );
    memset( out, 0xff, sizeof(out) );
    return console_headless_cmdline( env, in[0], il, in[1], cll, out, cap );
}
static int is( int len, const char *want )
{
    int i;
    if (len != (int)strlen( want ) || out[len] != 0) return 0;
    for (i = 0; i < len; i++) if (out[i] != (unsigned char)want[i]) return 0;
    return 1;
}
#define FAIL(m) do { fprintf( stderr, "%s\n", m ); return 1; } while (0)
int main( void )
{
    static const char ch[] = "C:\\windows\\system32\\conhost.exe";
    static const char alloc[] = "\"C:\\windows\\system32\\conhost.exe\" --server 0x34";
    int n;

    n = run( NULL, ch, alloc, 200 );
    if (!is( n, "\"C:\\windows\\system32\\conhost.exe\" --server 0x34 --headless" )) FAIL( "AllocConsole conhost kept its window" );
    n = run( "0", "\\??\\C:\\Windows\\System32\\CONHOST.EXE", "conhost.exe --server 0x108", 200 );
    if (!is( n, "conhost.exe --server 0x108 --headless" )) FAIL( "upper-case image / MADEIRA_CONSOLE_WINDOW=0 kept the window" );
    if (run( "1", ch, alloc, 200 ) != -1) FAIL( "MADEIRA_CONSOLE_WINDOW=1 hid the window" );
    if (run( NULL, ch, "\"C:\\windows\\system32\\conhost.exe\" --headless --width 80 --height 25 --signal 0x10 --server 0x14", 200 ) != -1)
        FAIL( "pseudo-console conhost changed" );
    if (run( NULL, ch, "conhost.exe --unix --width 80 --height 25 --server 0x8", 200 ) != -1) FAIL( "--unix conhost changed" );
    if (run( NULL, ch, "conhost.exe", 200 ) != -1 || run( NULL, ch, "conhost.exe --serverx 0x4", 200 ) != -1)
        FAIL( "conhost without --server changed" );
    if (run( NULL, ch, "conhost.exe --server 0x4 --headlessly", 200 ) == -1) FAIL( "--headlessly taken for --headless" );
    if (run( NULL, "C:\\x\\notconhost.exe", "notconhost.exe --server 0x4", 200 ) != -1 ||
        run( NULL, "C:\\windows\\system32\\cmd.exe", "cmd.exe /c x --server 0x4", 200 ) != -1)
        FAIL( "look-alike image changed" );
    if (run( NULL, ch, alloc, (int)strlen( alloc ) + 11 ) != -1) FAIL( "no room for the NUL, changed anyway" );
    if (!is( run( NULL, ch, alloc, (int)strlen( alloc ) + 12 ), "\"C:\\windows\\system32\\conhost.exe\" --server 0x34 --headless" ))
        FAIL( "exact-size buffer refused" );
    return 0;
}
'''

with tempfile.TemporaryDirectory(prefix='madeira-console-headless-') as directory:
    folder = Path(directory)
    src = folder / 'check.c'
    src.write_text(code)
    exe = folder / 'check'
    cc = os.environ.get('CC', 'cc')
    flags = [cc, '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function', '-g', str(src), '-o', str(exe)]
    sanitize = ['-fsanitize=address,undefined', '-fno-sanitize-recover=all']
    if subprocess.run(flags[:1] + sanitize + flags[1:], capture_output=True).returncode != 0:
        r = subprocess.run(flags, capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
    r = subprocess.run([str(exe)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
print('PASS: a console\'s conhost.exe starts --headless (no window) unless MADEIRA_CONSOLE_WINDOW=1; '
      'pseudo-consoles, --unix and look-alikes are left alone')
