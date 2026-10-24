#!/usr/bin/env python3
"""Check the "[rtcs] pre" rate cap in the unix dbg_write path (loader_ios.c).

Compiles the production ios_rtcs_admit block on the host with a fake clock and
a captured write(), then drives it with real log line shapes. No Wine runs.
"""
from pathlib import Path
import os
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
loader = (root / 'build/ntdll-unix/loader_ios.c').read_text()

# Wiring: slot 2 of the unix-call table (dbg_write) asks the cap first, and a
# line it keeps still goes through the unchanged wrapper and write().
wrap = loader[loader.index('static NTSTATUS ios_wrap_2(void *a)\n{'):]
wrap = wrap[:wrap.index('\n}\n') + 3]
assert wrap.index('if (!ios_rtcs_admit( p->str, p->len ))') < wrap.index(
    'return ios_wrap_unix_call(2, a, unixcall_wine_dbg_write);')
assert 'return p->len;' in wrap and 'g_wine_unix_call_count++;' in wrap
assert loader.count('static NTSTATUS ios_wrap_2(') == 1
table = loader[loader.index('static const unixlib_entry_t unix_call_funcs[] =\n{\n    ios_wrap_0'):]
assert table.index('ios_wrap_0, ios_wrap_1, ios_wrap_2, ios_wrap_3,') < table.index('};')
assert '#include <time.h>' in loader
assert 'memmem' not in loader, 'builds with -Wno-implicit-function-declaration: keep to declared libc'

start = loader.index('#define IOS_RTCS_SLOTS 64')
end = loader.index('static NTSTATUS ios_wrap_2(void *a)')
block = loader[start:end]

harness = r'''
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
static long long fake_now;
static int fake_clock(struct timespec *ts) { ts->tv_sec = fake_now; ts->tv_nsec = 0; return 0; }
static long fake_write(int fd, const void *buf, size_t n) { printf("NOTE %d %.*s", fd, (int)n, (const char *)buf); return (long)n; }
#define clock_gettime(clock, ts) fake_clock(ts)
#define write fake_write
''' + block + r'''
int main(void)
{
    char line[512];
    while (fgets(line, sizeof(line), stdin))
    {
        char *text = strchr(line, ' ');
        size_t len;
        if (!text) continue;
        *text++ = 0;
        fake_now = atoll(line);
        len = strlen(text);
        if (len && text[len - 1] == '\n') text[--len] = 0;
        text[len++] = '\n';  /* dbg_write lines end in a newline, not NUL */
        printf("%d\n", ios_rtcs_admit(text, (unsigned int)len));
    }
    return 0;
}
'''

PRE = ('{tid}:err:seh:prepare_exception_arm64ec [rtcs] pre: code=c0000005 addr=0000000133BED10C '
       'armPc=0000000133BED10C ecRip=0000000133BED10C rtcs=000000015638CD60 insim=1')
POST = '{tid}:err:seh:prepare_exception_arm64ec [rtcs] post: code=c0000005 addr=0000000133BED10C'
OTHER = '{tid}:err:seh:dispatch_exception [ki-path] code=c0000005 ctx=0 -> direct dispatch'


def slot(tid):
    h = 2166136261
    for c in tid.encode()[:16]:
        h = ((h ^ c) * 16777619) & 0xFFFFFFFF
    return h % 64


assert slot('00f4') != slot('0420') and slot('00f4') != slot('03e0')

with tempfile.TemporaryDirectory() as tmp:
    source = os.path.join(tmp, 'rtcs.c')
    binary = os.path.join(tmp, 'rtcs')
    Path(source).write_text(harness)
    subprocess.run([os.environ.get('CC', 'cc'), '-std=gnu11', '-O1', '-Wall', '-Werror', source, '-o', binary],
                   check=True)

    def run(lines, env_value=None):
        env = dict(os.environ)
        env.pop('MADEIRA_RTCS_LOG', None)
        if env_value is not None:
            env['MADEIRA_RTCS_LOG'] = env_value
        out = subprocess.run([binary], input=''.join(f'{s} {t}\n' for s, t in lines), capture_output=True,
                             text=True, check=True, env=env).stdout
        notes = [l for l in out.splitlines() if l.startswith('NOTE ')]
        verdicts = [int(l) for l in out.splitlines() if not l.startswith('NOTE ')]
        assert len(verdicts) == len(lines)
        return verdicts, notes

    # A storm on one thread: 10 per second kept, the rest counted and noted
    # once in the next second; other threads and other lines are untouched.
    storm = [(5, PRE.format(tid='00f4'))] * 300
    mixed = storm + [(5, PRE.format(tid='0420'))] * 3 + [(5, POST.format(tid='00f4'))] * 50 \
        + [(5, OTHER.format(tid='00f4'))] * 50 + [(6, PRE.format(tid='00f4'))] * 300
    verdicts, notes = run(mixed)
    assert sum(verdicts[:300]) == 10 and verdicts[:10] == [1] * 10
    assert verdicts[300:303] == [1, 1, 1], 'another thread keeps its own budget'
    assert all(verdicts[303:403]), 'only [rtcs] pre lines are capped'
    assert sum(verdicts[403:]) == 10
    assert len(notes) == 1 and "NOTE 2 [rtcs-cap] madeira-bcd v1: 290 '[rtcs] pre' lines left out" in notes[0], notes
    assert '(304 seen, 290 left out; 10 per second per thread kept;' in notes[0]  # 303 + the line that prints it
    assert 'MADEIRA_RTCS_LOG=all prints every line' in notes[0]

    # Opt-out, explicit limits, junk values and short lines.
    assert sum(run(storm, 'all')[0]) == 300 and not run(storm, 'all')[1]
    assert sum(run(storm, '0')[0]) == 0
    assert sum(run(storm, '25')[0]) == 25
    assert sum(run(storm, 'lots')[0]) == 10 and sum(run(storm, '-3')[0]) == 10
    assert run([(5, '[rtcs] pre: x')], '0')[0] == [0]
    assert run([(5, '[rtcs] pre')], '0')[0] == [1]
    assert run([(5, 'x')], '0')[0] == [1]
    # The tag must sit near the start (it follows the debug header); a long
    # line that only mentions it far later is not a prepare_exception line.
    assert run([(5, 'y' * 200 + ' [rtcs] pre: ')], '0')[0] == [1]

print('rtcs cap: 10/s per thread by default, other lines and threads untouched, notes counted, '
      'MADEIRA_RTCS_LOG=all|N honoured')
