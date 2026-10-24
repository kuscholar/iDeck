#!/usr/bin/env python3
"""The opt-in power probe (env.MADEIRA_POWER_PROBE = 1); no Wine runs.

The CPU clamp follows the whole chip's energy, and [xp] logs only the
process's CPU energy (proc_pid_rusage ri_energy_nj). What else can a
developer-signed app read? From xnu's sources:
  - task_info(TASK_POWER_INFO_V2)'s gpu_energy.task_gpu_utilisation is
    task_gpu_ns + ml_gpu_stat(thread), and ml_gpu_stat returns 0 on arm64
    (osfmk/arm64/machine_routines.c): always 0 on the phone;
  - the GPU driver charges GPU time and energy to the task's RESOURCE
    COALITION (ml_gpu_stat_update -> task_coalition_update_gpu_stats,
    coalition_add_to_gpu_energy); coalition_info() has no privilege check
    ("TODO: priv check?"), PROC_PIDCOALITIONINFO is NO_CHECK_SAME_USER;
  - rusage v6 also has ri_penergy_nj and the voucher-billed
    ri_billed_energy / ri_serviced_energy;
  - IOReport's "Energy Model" group and the battery's IORegistry entry are
    private / sandbox-dependent: tried once, named "unavailable" once.
server_ios.c's ios_power_probe_tick logs a [power] line every 5 s with
these, and [power-t] with the energy of the hungriest threads (the [xp]
sampler's per-thread PROC_PIDTHREADCOUNTS energy, never printed before).

Checks (unset = nothing resolved, nothing logged, byte-identical [xp]):
  - the switch is read where the samplers are armed; the per-thread hook and
    the 5 s tick only run with it;
  - compiled on this host against stand-in CoreFoundation, IOKit, IOReport
    and coalition readers:
      * every source missing: one [power] line every 5 s with the rusage
        numbers, each source named "unavailable" exactly once;
      * a coalition charging 6 J of GPU energy and 2.5 s of GPU time in 5 s:
        "gpu 1.20 W, busy 50%"; IOReport GPU/CPU/DRAM channels in mJ, uJ
        and nJ: 0.80 / 1.50 / 0.30 W, and the channel list once; a battery
        at 3.85 V and -1250 mA: 4.81 W of device power;
      * [power-t] lists the threads by energy, with the role or m<tid>;
  - the catalog documents the switch and CI runs this check.
"""
from pathlib import Path
import os
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SERVER = ROOT / "build/ntdll-unix/server_ios.c"
CAT = ROOT / "app/Madeira/ConfigCatalog.generated.swift"
GEN = ROOT / "build/tools/gen-config-catalog.py"
CI = ROOT / ".github/workflows/build-ipa.yml"

failures = []


def check(cond, what):
    print(("PASS " if cond else "FAIL ") + what)
    if not cond:
        failures.append(what)


def func_body(src, signature):
    i = src.find(signature)
    if i < 0:
        return ""
    j = src.find("{", i)
    depth = 0
    for k in range(j, len(src)):
        if src[k] == "{":
            depth += 1
        elif src[k] == "}":
            depth -= 1
            if depth == 0:
                return src[i:k + 1]
    return ""


server = SERVER.read_text(encoding="utf-8")
start = server.find("static int ios_power_probe_on;")
end = server.find("static void ios_xprobe_main( void )")
probe = server[start:end]
check(start > 0 and end > start and "static void ios_power_probe_tick(" in probe, "the probe block is found before the xprobe")

arm_at = server.find("if (__sync_bool_compare_and_swap(&ios_ts_armed, 0, 1))")
arm = server[arm_at:arm_at + 1500]
check('const char *probe_env = getenv("MADEIRA_POWER_PROBE");' in arm
      and 'ios_power_probe_on = probe_env && *probe_env && strcmp(probe_env, "0") != 0;' in arm,
      "MADEIRA_POWER_PROBE is read where the samplers are armed; unset, empty or 0 = off")
xprobe = func_body(server, "static void ios_xprobe_main( void )")
check("if (ios_power_probe_on)   /* madeira-bcd power probe: this thread's energy on P and E cores */" in xprobe
      and xprobe.count("ios_pp_thread(") == 1, "the per-thread energy hook only runs with the switch")
check("if (ios_power_probe_on)   /* madeira-bcd power probe: every 5 s;" in xprobe and xprobe.count("ios_power_probe_tick(") == 1,
      "the 5 s tick only runs with the switch")
check(xprobe.index("ios_power_probe_tick(") > xprobe.index('n = snprintf( line, sizeof(line), "[xp-t] %s", wall );'),
      "the probe logs after [xp] and [xp-t], which keep their format")
check("ios_pp_init()" in probe and probe.count("ios_pp_init();") == 1 and "if (!ios_pp.inited)" in probe,
      "nothing is resolved before the first tick with the switch on")

harness = r'''
#define _GNU_SOURCE
#include <errno.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
typedef unsigned int mach_port_t;
#define MACH_PORT_NULL 0
#define RTLD_DEFAULT ((void *)0)
#define RTLD_LAZY 1
static int scenario;
static void wine_log_write( const char *fmt, ... ) __attribute__((format(printf, 1, 2)));
static void wine_log_write( const char *fmt, ... )
{
    va_list ap; va_start( ap, fmt ); vprintf( fmt, ap ); va_end( ap ); putchar( '\n' );
}
/* ---- stand-in CoreFoundation: tagged objects ---- */
enum { T_STR = 1, T_NUM, T_DICT, T_ARR };
struct obj { int type; const char *s; long long v; int n; struct obj *k[8], *val[8]; };
static struct obj pool[256]; static int npool;
static struct obj *mk( int type ) { struct obj *o = &pool[npool++]; memset( o, 0, sizeof(*o) ); o->type = type; return o; }
static const void *f_str( const void *a, const char *s, uint32_t e ) { struct obj *o = mk( T_STR ); (void)a; (void)e; o->s = strdup( s ); return o; }
static unsigned char f_num_get( const void *n, long t, void *out ) { (void)t; if (((const struct obj *)n)->type != T_NUM) return 0; *(long long *)out = ((const struct obj *)n)->v; return 1; }
static unsigned long f_type_id( const void *o ) { return ((const struct obj *)o)->type; }
static unsigned long f_num_type( void ) { return T_NUM; }
static int releases;
static void f_release( const void *o ) { (void)o; releases++; }
static const void *f_dict_get( const void *d, const void *k )
{
    const struct obj *dd = d; int i;
    for (i = 0; i < dd->n; i++) if (!strcmp( dd->k[i]->s, ((const struct obj *)k)->s )) return dd->val[i];
    return NULL;
}
static const void *f_dict_mcopy( const void *a, long c, const void *d ) { (void)a; (void)c; return d; }
static long f_arr_count( const void *a ) { return ((const struct obj *)a)->n; }
static const void *f_arr_at( const void *a, long i ) { return ((const struct obj *)a)->val[i]; }
static unsigned char f_str_get( const void *s, char *buf, long size, uint32_t e ) { (void)e; snprintf( buf, size, "%s", ((const struct obj *)s)->s ); return 1; }
/* ---- stand-in IOKit (battery) ---- */
static const void *f_io_matching( const char *n ) { return f_str( 0, n, 0 ); }
static mach_port_t f_io_service( mach_port_t m, const void *match ) { (void)m; return !strcmp( ((const struct obj *)match)->s, "AppleSmartBattery" ) ? 77 : 0; }
static const void *f_io_prop( mach_port_t e, const void *key, const void *a, uint32_t o )
{
    struct obj *n; (void)a; (void)o;
    if (e != 77) return NULL;
    n = mk( T_NUM );
    if (!strcmp( ((const struct obj *)key)->s, "Voltage" )) n->v = 3850;
    else if (!strcmp( ((const struct obj *)key)->s, "InstantAmperage" )) n->v = -1250;
    else return NULL;
    return n;
}
/* ---- stand-in IOReport: one sample = 3 channels, energy grows by fixed steps ---- */
static int samples;
struct chan { const char *name, *unit; long long step; };
static const struct chan chans[] = { { "GPU Energy", "mJ", 4000 }, { "CPU Energy", "uJ", 7500000 }, { "DRAM Energy", "nJ", 1500000000 } };
static const void *f_ior_channels( const void *g, const void *s, uint64_t a, uint64_t b, uint64_t c ) { (void)s; (void)a; (void)b; (void)c; return !strcmp( ((const struct obj *)g)->s, "Energy Model" ) ? mk( T_DICT ) : NULL; }
static const void *f_ior_subscribe( const void *a, const void *ch, const void **subbed, uint64_t b, const void *c ) { (void)a; (void)ch; (void)b; (void)c; *subbed = mk( T_DICT ); return mk( T_DICT ); }
static const void *f_ior_samples( const void *sub, const void *subbed, const void *a ) { struct obj *o = mk( T_NUM ); (void)sub; (void)subbed; (void)a; o->v = ++samples; return o; }
static const void *f_ior_delta( const void *p, const void *c, const void *a )
{
    struct obj *d = mk( T_DICT ), *arr = mk( T_ARR ); int i; long long k = ((const struct obj *)c)->v - ((const struct obj *)p)->v; (void)a;
    d->k[0] = (struct obj *)f_str( 0, "IOReportChannels", 0 ); d->val[0] = arr; d->n = 1;
    for (i = 0; i < 3; i++) { struct obj *ch = mk( T_NUM ); ch->s = chans[i].name; ch->v = chans[i].step * k; ch->n = i; arr->val[i] = ch; }
    arr->n = 3;
    return d;
}
static const void *f_ior_name( const void *ch ) { return f_str( 0, ((const struct obj *)ch)->s, 0 ); }
static const void *f_ior_unit( const void *ch ) { return f_str( 0, chans[((const struct obj *)ch)->n].unit, 0 ); }
static int64_t f_ior_int( const void *ch, int32_t i ) { (void)i; return ((const struct obj *)ch)->v; }
/* ---- stand-in coalition ---- */
static uint64_t coal_calls;
static int f_cru( uint64_t cid, void *cru, size_t size )
{
    uint64_t *u = cru; (void)size;
    if (cid != 0x1234) { errno = ESRCH; return -1; }
    coal_calls++;
    u[8] = coal_calls * 2500000000ull;    /* gpu_time: 2.5 s of GPU time per 5 s */
    u[11] = coal_calls * 9000000000ull;   /* energy (CPU), nJ: 1.8 W */
    u[41] = coal_calls * 6000000000ull;   /* gpu_energy_nj: 6 J per 5 s = 1.2 W */
    return 0;
}
static int proc_pidinfo( int pid, int flavor, uint64_t arg, void *buf, int size )
{
    (void)pid; (void)arg;
    if (flavor != 20 || scenario == 0) return 0;
    memset( buf, 0, size ); ((uint64_t *)buf)[0] = 0x1234; return size;
}
static void *fake_dlsym( void *h, const char *n )
{
    if (scenario == 0) return NULL;
    (void)h;
#define F(name, fn) if (!strcmp( n, name )) return (void *)fn;
    F("coalition_info_resource_usage", f_cru) F("CFStringCreateWithCString", f_str) F("CFNumberGetValue", f_num_get)
    F("CFGetTypeID", f_type_id) F("CFNumberGetTypeID", f_num_type) F("CFRelease", f_release) F("CFDictionaryGetValue", f_dict_get)
    F("CFDictionaryCreateMutableCopy", f_dict_mcopy) F("CFArrayGetCount", f_arr_count) F("CFArrayGetValueAtIndex", f_arr_at)
    F("CFStringGetCString", f_str_get) F("IOServiceMatching", f_io_matching) F("IOServiceGetMatchingService", f_io_service)
    F("IORegistryEntryCreateCFProperty", f_io_prop) F("IOReportCopyChannelsInGroup", f_ior_channels)
    F("IOReportCreateSubscription", f_ior_subscribe) F("IOReportCreateSamples", f_ior_samples) F("IOReportCreateSamplesDelta", f_ior_delta)
    F("IOReportChannelGetChannelName", f_ior_name) F("IOReportChannelGetUnitLabel", f_ior_unit) F("IOReportSimpleGetIntegerValue", f_ior_int)
#undef F
    return NULL;
}
static void *fake_dlopen( const char *p, int f ) { (void)f; return scenario == 0 ? NULL : (void *)p; }
#define dlsym fake_dlsym
#define dlopen fake_dlopen
''' + probe + r'''
int main( int argc, char **argv )
{
    uint64_t now = 0; int i;
    scenario = atoi( argv[1] );
    for (i = 0; i < 4 * 16; i++)   /* 16 s of 250 ms samples */
    {
        now += 250000000ull;
        struct ios_pp_thr *nat = ios_pp_thread( 3270754, 0, NULL, 150.0, 2.0 );   /* a native thread: 0.6 W on P cores */
        struct ios_pp_thr *game = ios_pp_thread( 4242, 0x24, "EP", 30.0, 45.0 );  /* the game's presenting thread */
        ios_pp_thread( 4243, 0xf8, NULL, 0.0, 20.0 );
        if (!nat || !game || game->pri != -1) return 3;   /* a Wine thread is never asked for its priority */
        if (nat->pri == -2) nat->pri = 47;                 /* what the xprobe's THREAD_EXTENDED_INFO gives */
        ios_power_probe_tick( "12:00:00.000", now, 250.0, 500.0, 400.0, 25.0, 0.0 );
    }
    return 0;
}
'''

with tempfile.TemporaryDirectory(prefix="madeira-power-probe-") as tmp:
    c = Path(tmp) / "probe.c"
    exe = Path(tmp) / "probe"
    c.write_text(harness)
    cc = os.environ.get("CC", "cc")
    base = [cc, "-std=gnu11", "-O1", "-Wall", "-Werror", "-Wno-unused-function", "-Wno-unused-variable", str(c), "-o", str(exe)]
    r = subprocess.run(base[:1] + ["-fsanitize=address,undefined", "-fno-sanitize-recover=all"] + base[1:], capture_output=True, text=True)
    if r.returncode != 0:
        r = subprocess.run(base, capture_output=True, text=True)
    check(r.returncode == 0, "the probe compiles on this host against stand-ins" + ("" if r.returncode == 0 else ": " + r.stderr[-1500:]))
    if r.returncode == 0:
        none = subprocess.run([str(exe), "0"], capture_output=True, text=True)
        allx = subprocess.run([str(exe), "1"], capture_output=True, text=True)
        check(none.returncode == 0 and allx.returncode == 0, "both runs exit cleanly" + none.stderr[-500:] + allx.stderr[-500:])
        nl = [l for l in none.stdout.splitlines() if l.startswith("[power] 12:")]
        check(len(nl) == 3, "nothing available: one [power] line every 5 s (%d in 16 s)" % len(nl))
        check(nl and "cpu 2.00 W (P 1.60; rusage), billed 0.10 W" in nl[0], "the rusage numbers: cpu 2.00 W, P 1.60 W, billed 0.10 W")
        joined = "\n".join(nl)
        for src in ("coalition unavailable", "IOReport unavailable", "battery unavailable"):
            check(joined.count(src) == 1, "%s is said once" % src)
        al = [l for l in allx.stdout.splitlines() if l.startswith("[power] 12:")]
        check(len(al) == 3 and "unavailable" not in "\n".join(al[1:]), "everything available: no unavailable after the first line")
        last = al[-1] if al else ""
        check("coalition: gpu 1.20 W, busy 50%, cpu 1.80 W" in last, "coalition: 6 J and 2.5 s of GPU in 5 s = 1.20 W, 50 %% busy (%s)" % last[:400])
        check("IOReport: gpu 0.80 W, cpu 1.50 W, dram 0.30 W" in last, "IOReport channels in mJ, uJ and nJ scaled to W")
        check("battery 3.85 V x -1250 mA = 4.81 W (discharging: the whole device)" in last, "battery: 3.85 V x 1.25 A = 4.81 W")
        check(allx.stdout.count("[power] IOReport Energy Model channels") == 1, "the IOReport channel list is logged once")
        pt = [l for l in allx.stdout.splitlines() if l.startswith("[power-t] ")]
        check(len(pt) == 3 and pt[-1].endswith("top threads, W (P/E): m3270754/47:0.608(0.600/0.008) EP0024:0.300(0.120/0.180) -00f8:0.080(0.000/0.080)"),
              "[power-t]: threads by energy in W with the P/E split, a native thread with its base priority (%s)" % (pt[-1] if pt else ""))
xp_hook = xprobe[xprobe.find("if (ios_power_probe_on)   /* madeira-bcd power probe: this thread's energy"):]
xp_hook = xp_hook[:xp_hook.find("sum_thr_ms += pt + et;")]
check("if (pp && pp->pri == -2)" in xp_hook and "THREAD_EXTENDED_INFO" in xp_hook and "xi.pth_priority" in xp_hook,
      "the xprobe asks a native thread for its base priority once per 5 s window (THREAD_EXTENDED_INFO)")

gen = GEN.read_text(encoding="utf-8")
cat = CAT.read_text(encoding="utf-8")
check('"env.MADEIRA_POWER_PROBE"' in gen and "env.MADEIRA_POWER_PROBE" in cat, "the catalog documents env.MADEIRA_POWER_PROBE")
# The CI step exists only in the fork's workflow; upstream has no .github.
if CI.exists():
    ci = CI.read_text(encoding="utf-8")
    check("- name: Check power-probe" in ci and "python3 tests/host/check-power-probe.py" in ci, "CI runs this check")

if failures:
    print("FAILED: %d" % len(failures))
    sys.exit(1)
print("OK")
