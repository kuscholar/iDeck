#!/usr/bin/env python3
"""Every child gets the JIT pool's variables; no Wine runs.

The emulators read WINE_IOS_JIT_RX/SIZE/RW from the Windows environment to find
the RW alias of their code buffer. services.exe builds a service's environment
from the registry, so RockstarService.exe ran without them and every store into
its code buffer was a Mach fault (build 447: 1.09M emulated stores). Compiles the
production ios_env_with from build/ntdll-unix/process_ios.c and checks:
  - a block without the three gets them appended, entries kept as they were;
  - names are matched in any case and only as whole names (NAME=);
  - only the missing ones are added, only when the app has a value;
  - an empty or NULL block works, the result ends in the double NUL;
and textually that NtCreateUserProcess applies it (MADEIRA_JIT_ENV_INHERIT=0
off) before the environment is measured and sent with new_process.
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
call = 'ios_env_with( params->Environment, jit_names, 3, getenv, &len, &added );'
assert call in create
assert '{ "WINE_IOS_JIT_RX", "WINE_IOS_JIT_SIZE", "WINE_IOS_JIT_RW" }' in create
assert 'const char *keep = getenv( "MADEIRA_JIT_ENV_INHERIT" );' in create
site = create[create.index(call):][:900]
assert 'params->Environment = env;' in site and 'params->EnvironmentSize = len * sizeof(WCHAR);' in site
assert '[jit-env] %s starts without the JIT pool' in site
# before the block is measured and copied into the new_process request
assert create.index(call) < create.index('env_size = get_env_size( params, &winedebug );')
assert create.index(call) < create.index('wine_server_add_data( req, params->Environment, env_size );')

code = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef unsigned short WCHAR;
typedef size_t SIZE_T;
'''
code += function(source, 'static WCHAR *ios_env_with(')
code += r'''
static const char *const names[] = { "WINE_IOS_JIT_RX", "WINE_IOS_JIT_SIZE", "WINE_IOS_JIT_RW" };
static int no_size;
static char *get( const char *name )
{
    if (!strcmp( name, "WINE_IOS_JIT_RX" )) return "148000000";
    if (!strcmp( name, "WINE_IOS_JIT_SIZE" )) return no_size ? NULL : "38000000";
    if (!strcmp( name, "WINE_IOS_JIT_RW" )) return "7918c00000";
    return NULL;
}
/* "A=1|B=2|" -> a WCHAR multi-sz (| ends an entry), with the final NUL */
static WCHAR *block( const char *s )
{
    static WCHAR buf[4][512];
    static int slot;
    WCHAR *b = buf[slot++ & 3];
    int i;
    for (i = 0; s[i]; i++) b[i] = s[i] == '|' ? 0 : (unsigned char)s[i];
    b[i] = 0;
    return b;
}
/* the block as "A=1|B=2|" (entries up to the empty one) */
static const char *text( const WCHAR *b, SIZE_T len )
{
    static char out[1024];
    SIZE_T i;
    for (i = 0; i + 1 < len && i < sizeof(out) - 1; i++) out[i] = b[i] ? (char)b[i] : '|';
    out[i] = 0;
    if (len < 2 || b[len - 1] != 0 || b[len - 2] != 0) return "<no double NUL>";
    return out;
}
#define FAIL(...) do { fprintf( stderr, __VA_ARGS__ ); return 1; } while (0)
int main( void )
{
    SIZE_T len;
    unsigned int added;
    WCHAR *r;
    const char *t;

    r = ios_env_with( block( "PATH=C:\\windows|SystemRoot=C:\\windows|" ), names, 3, get, &len, &added );
    t = r ? text( r, len ) : "NULL";
    if (!r || added != 7 || strcmp( t, "PATH=C:\\windows|SystemRoot=C:\\windows|WINE_IOS_JIT_RX=148000000|"
                                     "WINE_IOS_JIT_SIZE=38000000|WINE_IOS_JIT_RW=7918c00000|" ))
        FAIL( "service block: %s (added %u)\n", t, added );
    free( r );

    if (ios_env_with( block( "A=1|wine_ios_jit_rx=1|Wine_Ios_Jit_Size=2|WINE_IOS_JIT_RW=3|" ), names, 3, get, &len, &added ) || added)
        FAIL( "a block that has all three (any case) was changed\n" );

    r = ios_env_with( block( "WINE_IOS_JIT_RX=148000000|X=y|" ), names, 3, get, &len, &added );
    t = r ? text( r, len ) : "NULL";
    if (!r || added != 6 || strcmp( t, "WINE_IOS_JIT_RX=148000000|X=y|WINE_IOS_JIT_SIZE=38000000|WINE_IOS_JIT_RW=7918c00000|" ))
        FAIL( "only the missing two: %s (added %u)\n", t, added );
    free( r );

    r = ios_env_with( block( "WINE_IOS_JIT_RXX=1|WINE_IOS_JIT_RX|WINE_IOS_JIT_SIZE=1|WINE_IOS_JIT_RW=2|" ), names, 3, get, &len, &added );
    t = r ? text( r, len ) : "NULL";
    if (!r || added != 1 || strcmp( t, "WINE_IOS_JIT_RXX=1|WINE_IOS_JIT_RX|WINE_IOS_JIT_SIZE=1|WINE_IOS_JIT_RW=2|"
                                     "WINE_IOS_JIT_RX=148000000|" ))
        FAIL( "look-alike names counted: %s (added %u)\n", t, added );
    free( r );

    no_size = 1;
    r = ios_env_with( block( "" ), names, 3, get, &len, &added );
    t = r ? text( r, len ) : "NULL";
    if (!r || added != 5 || strcmp( t, "WINE_IOS_JIT_RX=148000000|WINE_IOS_JIT_RW=7918c00000|" ))
        FAIL( "empty block, SIZE unset in the app: %s (added %u)\n", t, added );
    free( r );
    no_size = 0;

    r = ios_env_with( NULL, names, 3, get, &len, &added );
    t = r ? text( r, len ) : "NULL";
    if (!r || added != 7 || len != strlen( t ) + 1)
        FAIL( "NULL block: %s (added %u, len %zu)\n", t, added, len );
    free( r );
    return 0;
}
'''

with tempfile.TemporaryDirectory(prefix='madeira-jit-env-') as directory:
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
print('PASS: a child whose environment lacks WINE_IOS_JIT_RX/SIZE/RW (a service) gets the app\'s values; '
      'present ones (any case) and look-alike names are left alone')
