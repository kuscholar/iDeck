#!/usr/bin/env python3
"""eco-native: env.MADEIRA_ECO_NATIVE = 1 moves the runtime's helper threads to utility QoS; no Wine runs.

ECO (sync.c, ml1133) puts guest threads at utility QoS; native threads keep the
QoS they were created with. In Horizon Zero Dawn (hzd486, build 486) the
JIT-pool warmer ran its address-space walks on performance cores at ~2.8 GHz
(~450 ms of CPU for one walk at 11:56:52), and the stale-pointer healer is a
100 ms polling loop. Neither does work a frame waits for. With the switch
each moves itself to utility QoS when it starts.

Checks:
  - ios_eco_native_self (thread_ios.c) compiled on this host with a stand-in
    pthread_set_qos_class_self_np: unset, empty or 0 = no call and no line
    (byte-identical default); 1 = one call with QOS_CLASS_UTILITY and one
    [eco-native] line naming the thread; the env is read once;
  - the warmer and the healer call it first thing, and nothing else does: the
    Mach exception thread keeps USER_INTERACTIVE, the wineserver and the
    samplers are untouched, ECO's ios_eco_apply_self still runs for every
    guest thread at start;
  - the catalog lists the switch and CI runs this check.
"""
from pathlib import Path
import os
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
THREAD = ROOT / "build/ntdll-unix/thread_ios.c"
VIRT = ROOT / "build/ntdll-unix/virtual_ios.c"
SIG = ROOT / "build/ntdll-unix/signal_arm64_ios.c"
SERVER = ROOT / "build/ntdll-unix/server_ios.c"
WS = ROOT / "build/wineserver"
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


thread = THREAD.read_text(encoding="utf-8")
virt = VIRT.read_text(encoding="utf-8")
sig = SIG.read_text(encoding="utf-8")
server = SERVER.read_text(encoding="utf-8")

fn = func_body(thread, "void ios_eco_native_self( const char *who )")
check(bool(fn), "ios_eco_native_self found in thread_ios.c")

harness = r'''
#define _GNU_SOURCE
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef enum { QOS_CLASS_USER_INTERACTIVE = 0x21, QOS_CLASS_USER_INITIATED = 0x19, QOS_CLASS_DEFAULT = 0x15,
               QOS_CLASS_UTILITY = 0x11, QOS_CLASS_BACKGROUND = 0x09 } qos_class_t;
static int calls, last_class = -1, getenvs;
static int pthread_set_qos_class_self_np( qos_class_t c, int rel ) { calls++; last_class = c; return rel; }
static char *h_getenv( const char *n ) { getenvs++; return getenv( n ); }
#define getenv h_getenv
''' + fn + r'''
int main( void )
{
    ios_eco_native_self( "pool-warmer" );
    ios_eco_native_self( "wine-stale-heal" );
    printf( "%d %d %d\n", calls, last_class, getenvs );
    return 0;
}
'''

with tempfile.TemporaryDirectory(prefix="madeira-eco-native-") as t:
    c = Path(t) / "eco.c"
    exe = Path(t) / "eco"
    c.write_text(harness)
    cc = os.environ.get("CC", "cc")
    r = subprocess.run([cc, "-std=gnu11", "-Wall", "-Werror", "-Wno-unused-function", str(c), "-o", str(exe)],
                       capture_output=True, text=True)
    check(r.returncode == 0, "ios_eco_native_self compiles on this host" + ("" if r.returncode == 0 else ": " + r.stderr[-600:]))
    if r.returncode == 0:
        clean = {k: v for k, v in os.environ.items() if not k.startswith("MADEIRA_")}
        res = {}
        for val in (None, "", "0", "1"):
            env = dict(clean, **({"MADEIRA_ECO_NATIVE": val} if val is not None else {}))
            o = subprocess.run([str(exe)], capture_output=True, text=True, env=env)
            res[val] = (o.stdout.split(), o.stderr)
        for val in (None, "", "0"):
            check(res[val][0] == ["0", "-1", "1"] and res[val][1] == "",
                  "MADEIRA_ECO_NATIVE=%r: no QoS call, no line, env read once (%s)" % (val, res[val][0]))
        check(res["1"][0] == ["2", str(0x11), "1"], "MADEIRA_ECO_NATIVE=1: both helpers move to QOS_CLASS_UTILITY (%s)" % res["1"][0])
        check(res["1"][1].count("[eco-native] madeira-bcd pool-warmer thread at utility QoS") == 1
              and res["1"][1].count("[eco-native] madeira-bcd wine-stale-heal thread at utility QoS") == 1,
              "one [eco-native] line per thread")

warm = func_body(virt, "static void *ios_pool_warmer_thread( void *arg )")
check(warm.split("\n")[3].strip() == '{ extern void ios_eco_native_self( const char *who ); ios_eco_native_self( "pool-warmer" ); }   /* madeira-bcd eco-native */',
      "the warmer moves itself before its first cycle")
heal = func_body(sig, "static void *ios_stale_va_scanner( void *arg )")
check('ios_eco_native_self( "wine-stale-heal" );' in heal and heal.index("ios_eco_native_self") < heal.index("for (;;)"),
      "the healer moves itself before its loop")
exc = func_body(sig, "static void *ios_mach_exception_thread")
check("pthread_set_qos_class_self_np( QOS_CLASS_USER_INTERACTIVE, 0 );" in exc and "ios_eco_native_self" not in exc,
      "the Mach exception thread keeps USER_INTERACTIVE")
callers = [p.name for p in (ROOT / "build/ntdll-unix").glob("*.c") if "ios_eco_native_self(" in p.read_text(errors="ignore")]
check(sorted(callers) == ["signal_arm64_ios.c", "thread_ios.c", "virtual_ios.c"], "no other thread is moved (%s)" % callers)
check(not any("ios_eco_native_self" in p.read_text(errors="ignore") for p in WS.glob("*.c")), "the wineserver is untouched")
start = func_body(thread, "static void start_thread( TEB *teb )")
check("ios_eco_apply_self();" in start and "ios_eco_native_self" not in start, "guest threads still start through ECO's ios_eco_apply_self")

gen = GEN.read_text(encoding="utf-8")
cat = CAT.read_text(encoding="utf-8")
check('"env.MADEIRA_ECO_NATIVE"' in gen and "env.MADEIRA_ECO_NATIVE" in cat, "the catalog documents env.MADEIRA_ECO_NATIVE")
# The CI step exists only in the fork's workflow; upstream has no .github.
if CI.exists():
    ci = CI.read_text(encoding="utf-8")
    check("- name: Check eco-native" in ci and "python3 tests/host/check-eco-native.py" in ci, "CI runs this check")

if failures:
    print("FAILED: %d" % len(failures))
    sys.exit(1)
print("OK")
