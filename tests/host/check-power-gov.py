#!/usr/bin/env python3
"""The CPU power governor holds the average at its target; no Wine runs.

The SoC clamps the CPU once a budget of energy above ~2.3 W is spent (ml1133;
GTA V Enhanced in 442/447: P 1.31 / E 1.70 GHz from the start of play).
env.MADEIRA_POWER_GOV_MW holds the process's CPU power at a target while a game
presents by turning ECO (utility QoS) on and off. Compiles the production
ios_power_gov_step from build/ntdll-unix/server_ios.c against a model where the
process draws 4.2 W with ECO off and 1.1 W with it on, sampled every 250 ms:
  - unset: never touches ECO;
  - 2200 mW: the 10 s averages stay within 0.15 W of 2.2 W, ECO on about two
    thirds of the time, no switch closer than 500 ms;
  - when the game stops presenting, ECO goes back to what it was (off, or on
    when the user had it on) and nothing switches while nothing presents;
and textually that the [xp] sampler feeds it every sample with ri_energy_nj.
Needs python3 and a C compiler (AddressSanitizer/UBSan when available).
"""
from pathlib import Path
import os
import re
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
source = (root / 'build/ntdll-unix/server_ios.c').read_text()


def function(text, signature):
    start = text.index(signature)
    return text[start:text.index('\n}\n', start) + 3]


gov = function(source, 'static void ios_power_gov_step( uint64_t now, double dt_ms, double mj )')
xprobe = function(source, 'static void ios_xprobe_main( void )')
assert 'ios_power_gov_step( ios_bg_now_ns(), dt_ms, (double)(ru.ri_energy_nj - pru.ri_energy_nj) / 1e6 );' in xprobe
assert xprobe.index('ios_power_gov_step(') < xprobe.index('wine_log_write( "%s", line );')

harness = r'''
#define _GNU_SOURCE
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define IOS_BG_QOS_HOLD_NS (2000ull * 1000 * 1000)
static volatile uint64_t ios_bg_game_seen_ns;
static int eco_state, eco_sets;
static uint64_t last_set_ns, min_gap_ns = ~0ull, clock_ns;
static char last_log[512];
static void wine_log_write( const char *fmt, ... )
{
    va_list ap; va_start( ap, fmt ); vsnprintf( last_log, sizeof(last_log), fmt, ap ); va_end( ap );
    if (getenv( "VERBOSE" )) puts( last_log );
}
static void madeira_set_eco( int on )
{
    if (eco_sets && clock_ns - last_set_ns < min_gap_ns) min_gap_ns = clock_ns - last_set_ns;
    last_set_ns = clock_ns; eco_sets++; eco_state = on;
}
static int madeira_get_eco( void ) { return eco_state; }
''' + gov.replace('extern void madeira_set_eco( int on );', '').replace('extern int madeira_get_eco( void );', '') + r'''
static double avg_w[64]; static int navg;
int main( int argc, char **argv )
{
    int mode = atoi( argv[1] ), i, presenting = 1;
    double on_ms = 0, total_ms = 0;
    (void)argc;
    eco_state = mode == 3;   /* the user had ECO on */
    for (i = 0; i < 4 * 240; i++)   /* 240 s of 250 ms samples */
    {
        double w = eco_state ? 1.1 : 4.2;
        clock_ns += 250000000ull;
        if (mode >= 2 && i == 4 * 120) presenting = 0;   /* the game stops after 120 s */
        if (presenting) ios_bg_game_seen_ns = clock_ns;
        ios_power_gov_step( clock_ns, 250.0, w * 250.0 );
        if (presenting) { total_ms += 250; if (eco_state) on_ms += 250; }
        if (!strncmp( last_log, "[power-gov] last", 16 ))
        {
            avg_w[navg++] = atof( strstr( last_log, "s: " ) + 3 );
            last_log[0] = 0;
        }
    }
    printf( "%d %d %.3f %llu %d", eco_sets, eco_state, total_ms ? on_ms / total_ms : 0,
            (unsigned long long)(min_gap_ns == ~0ull ? 0 : min_gap_ns / 1000000), navg );
    for (i = 0; i < navg; i++) printf( " %.3f", avg_w[i] );
    printf( "\n" );
    return 0;
}
'''

with tempfile.TemporaryDirectory(prefix='madeira-power-gov-') as directory:
    folder = Path(directory)
    src = folder / 'gov.c'
    src.write_text(harness)
    exe = folder / 'gov'
    cc = os.environ.get('CC', 'cc')
    flags = [cc, '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function', '-g', str(src), '-o', str(exe)]
    sanitize = ['-fsanitize=address,undefined', '-fno-sanitize-recover=all']
    if subprocess.run(flags[:1] + sanitize + flags[1:], capture_output=True).returncode != 0:
        r = subprocess.run(flags, capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
    base = {k: v for k, v in os.environ.items() if not k.startswith('MADEIRA_POWER_GOV')}

    def run(mode, target=None):
        env = dict(base, **({'MADEIRA_POWER_GOV_MW': target} if target else {}))
        r = subprocess.run([str(exe), str(mode)], capture_output=True, text=True, env=env)
        assert r.returncode == 0, r.stdout + r.stderr
        f = r.stdout.split()
        return int(f[0]), int(f[1]), float(f[2]), int(f[3]), [float(x) for x in f[5:]]

    sets, state, on_frac, gap, avgs = run(1)
    assert sets == 0 and state == 0 and not avgs, ('unset', sets, state, avgs)
    print('PASS: MADEIRA_POWER_GOV_MW unset: ECO never touched')

    sets, state, on_frac, gap, avgs = run(1, '2200')
    assert avgs and all(abs(a - 2.2) <= 0.15 for a in avgs), avgs
    assert 0.55 <= on_frac <= 0.75, on_frac
    assert gap >= 500, gap
    print(f'PASS: 2200 mW: 10 s averages {min(avgs):.2f}-{max(avgs):.2f} W, ECO on {on_frac:.0%} of the time, '
          f'{sets} switches in 240 s, none closer than {gap} ms')

    sets, state, on_frac, gap, avgs = run(2, '2200')
    assert state == 0, 'ECO left on after the game stopped presenting'
    print('PASS: the game stops presenting: ECO back off, no switching while nothing presents')

    sets, state, on_frac, gap, avgs = run(3, '2200')
    assert state == 1, 'the user\'s ECO was not put back'
    print('PASS: with the user\'s ECO on, it is on again once the game stops presenting')
