#!/usr/bin/env python3
"""The server thread's QoS follows ECO (env.MADEIRA_SRV_ECO_FOLLOW) and its idle tick
(env.MADEIRA_SRV_IDLE_US); both off by default; no Wine runs.

The wineserver thread is created at user-interactive QoS (app/Madeira/WineServerBridge.m),
so it keeps a performance core at full clock even while ECO holds every guest thread on
the efficiency cores: Horizon Zero Dawn's menu with eco = 1 (2026-10-11 11:10) ran it at
0.54 cores, all on P at ~3.9 GHz, while every guest thread ran on E. With
MADEIRA_SRV_ECO_FOLLOW = 1 (build/wineserver/fd_ios.c ios_srv_qos_follow) the server
thread takes ECO's class while ECO is on and user-interactive again when it goes off.
MADEIRA_SRV_IDLE_US (ios_srv_idle_ns) sets the loop's longest sleep, 1 ms by default.

Compiles ios_srv_qos_follow and ios_srv_idle_ns on this host with stand-ins for
pthread_set_qos_class_self_np, madeira_get_eco and ntdll's ECO generation, and checks:
  - switch off: across ECO changes nothing is called at all (no QoS change, and
    madeira_get_eco, which latches madeira.cfg on its first call, is never called);
  - switch on with ECO off: no change; ECO on: utility, once (never background, which
    could stall every request); repeated passes call nothing; ECO off again:
    user-interactive;
  - the switch going off while the thread is lowered restores user-interactive, after
    which nothing is called again;
  - the idle tick: unset 1 ms exactly (unchanged), else 100 us to 50 ms.
Then textually: the loop calls it after every sleep, the loop's exit resets its state for
the next session's server thread, the loop sleeps min(idle tick, next timer), the
bridge sets both switches after the game's env lines and clears them at the session
end, the catalog entries and the CI step.
"""
from pathlib import Path
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
FD = (ROOT / "build/wineserver/fd_ios.c").read_text(encoding="utf-8")
BRIDGE = (ROOT / "app/Madeira/WineProcessBridge.m").read_text(encoding="utf-8")
CAT = (ROOT / "app/Madeira/ConfigCatalog.generated.swift").read_text(encoding="utf-8")
CI_FILE = ROOT / ".github/workflows/build-ipa.yml"   # the fork's CI only; upstream has no .github
CI = CI_FILE.read_text(encoding="utf-8") if CI_FILE.exists() else None

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


follow = func_body(FD, "static void ios_srv_qos_follow(void)")
idle = func_body(FD, "static unsigned long long ios_srv_idle_ns(void)")
exit_ = func_body(FD, "static void ios_srv_loop_exit(void)")
check(bool(follow) and bool(idle) and bool(exit_), "ios_srv_qos_follow, ios_srv_idle_ns and ios_srv_loop_exit are found")
d0 = FD.find("static qos_class_t ios_srv_qos_set;")
check(d0 > 0, "the follow state is found")

harness = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef int qos_class_t;
#define QOS_CLASS_USER_INTERACTIVE 0x21
#define QOS_CLASS_USER_INITIATED 0x19
#define QOS_CLASS_UTILITY 0x11
#define QOS_CLASS_BACKGROUND 0x09
static int qos_now = QOS_CLASS_USER_INTERACTIVE, qos_calls, eco_calls, eco_on;
static int pthread_set_qos_class_self_np( qos_class_t c, int rel ) { (void)rel; qos_now = c; qos_calls++; return 0; }
volatile int ios_eco_gen = 1;
int madeira_get_eco( void ) { eco_calls++; return eco_on; }
volatile int g_madeira_srv_eco_follow, g_madeira_srv_idle_us;
static qos_class_t ios_srv_qos_set;
static int ios_srv_qos_follow_seen, ios_srv_qos_gen_seen;
@FOLLOW@
@IDLE@
static int bad;
static void expect( int ok, const char *what ) { printf( "%s: %s\n", ok ? "PASS" : "FAIL", what ); if (!ok) bad = 1; }
static void passes( int n ) { while (n--) ios_srv_qos_follow(); }
int main(void)
{
    /* switch off: ECO goes on and off, nothing happens */
    passes( 5 ); eco_on = 1; ios_eco_gen++; passes( 5 ); eco_on = 0; ios_eco_gen++; passes( 5 );
    expect( !qos_calls && !eco_calls && qos_now == QOS_CLASS_USER_INTERACTIVE,
            "switch off: no QoS change and madeira_get_eco is never called" );
    /* switch on, ECO off */
    g_madeira_srv_eco_follow = 1;
    passes( 5 );
    expect( !qos_calls && eco_calls == 1, "switch on, ECO off: no change, ECO read once" );
    eco_on = 1; ios_eco_gen++; passes( 5 );
    expect( qos_now == QOS_CLASS_UTILITY && qos_calls == 1 && eco_calls == 2, "ECO on: utility, once" );
    eco_on = 0; ios_eco_gen++; passes( 3 );
    expect( qos_now == QOS_CLASS_USER_INTERACTIVE && qos_calls == 2, "ECO off: user-interactive again" );
    eco_on = 1; ios_eco_gen++; passes( 3 );
    expect( qos_now == QOS_CLASS_UTILITY && qos_calls == 3, "ECO on again: utility (never background)" );
    ios_eco_gen++; passes( 3 );
    expect( qos_calls == 3, "a generation change to the same answer changes nothing" );
    /* the switch goes off while lowered (the session ends) */
    g_madeira_srv_eco_follow = 0; passes( 3 );
    expect( qos_now == QOS_CLASS_USER_INTERACTIVE && qos_calls == 4, "switch off while lowered: user-interactive" );
    {
        int e = eco_calls;
        ios_eco_gen++; passes( 5 );
        expect( qos_calls == 4 && eco_calls == e, "then nothing is called again" );
    }
    /* idle tick */
    g_madeira_srv_idle_us = 0; expect( ios_srv_idle_ns() == 1000000ull, "idle tick unset: 1 ms, as before" );
    g_madeira_srv_idle_us = -5; expect( ios_srv_idle_ns() == 1000000ull, "a negative value: 1 ms" );
    g_madeira_srv_idle_us = 4000; expect( ios_srv_idle_ns() == 4000000ull, "4000 us: 4 ms" );
    g_madeira_srv_idle_us = 20; expect( ios_srv_idle_ns() == 100000ull, "below 100 us: 100 us" );
    g_madeira_srv_idle_us = 900000; expect( ios_srv_idle_ns() == 50000000ull, "above 50 ms: 50 ms" );
    return bad;
}
'''.replace("@FOLLOW@", follow).replace("@IDLE@", idle)

cc = os.environ.get("CC") or shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
if not cc:
    check(False, "a C compiler is available")
else:
    tmp = Path(tempfile.mkdtemp(prefix="srveco-"))
    (tmp / "h.c").write_text(harness)
    b = subprocess.run([cc, "-std=gnu11", "-g", "-O1", "-Wall", "-Wno-unused-function", "-Werror=implicit-function-declaration",
                        "-fsanitize=address,undefined", "-fno-sanitize-recover=all", str(tmp / "h.c"), "-o", str(tmp / "h")],
                       capture_output=True, text=True)
    check(b.returncode == 0, "the harness compiles (ASan + UBSan)" + ("" if not b.returncode else ": " + b.stderr[-1500:]))
    if not b.returncode:
        r = subprocess.run([str(tmp / "h")], capture_output=True, text=True, timeout=60)
        print("\n".join("    " + l for l in r.stdout.strip().splitlines()))
        check(r.returncode == 0 and "FAIL" not in r.stdout, "every behaviour check passes" + ("" if not r.returncode else ": " + r.stderr[-800:]))
    shutil.rmtree(tmp, ignore_errors=True)

# ---- textual ---------------------------------------------------------------------
loop = FD[FD.find("void main_loop(void)"):]
i_sem = loop.find("semaphore_timedwait( ios_srv_wake_sem, wts );")
i_follow = loop.find("ios_srv_qos_follow();    /* madeira-bcd: MADEIRA_SRV_ECO_FOLLOW */")
i_bell = loop.find("ios_doorbell_service();")
check(0 <= i_sem < i_follow < i_bell and loop.count("ios_srv_qos_follow();") == 1,
      "the loop looks at ECO once per pass, after its sleep")
check("unsigned long long sleep_ns = ios_srv_idle_ns();" in loop and
      loop.find("unsigned long long sleep_ns = ios_srv_idle_ns();") < loop.find("if (ios_next_timer_ns < sleep_ns) sleep_ns = ios_next_timer_ns;") < i_sem,
      "the loop sleeps the idle tick or until the next timer, whichever is sooner")
check("ios_srv_qos_set = 0;" in exit_ and "ios_srv_qos_follow_seen = ios_srv_qos_gen_seen = 0;" in exit_,
      "the loop's exit resets the follow state for the next session's server thread")
check("extern volatile int ios_eco_gen;" in FD and "extern int madeira_get_eco( void );" in FD,
      "ECO comes from ntdll's generation counter and madeira_get_eco")
check(follow.find("if (!follow && !ios_srv_qos_set) return;") < follow.find("madeira_get_eco()"),
      "madeira_get_eco is reached only with the switch on (it latches madeira.cfg on its first call)")
check("getenv" not in follow and "getenv" not in idle, "the server reads neither switch from the environment itself")
i_env = BRIDGE.find('fprintf(stderr, "[madeira-env] game %s=%s\\n", k.UTF8String, v.UTF8String);')
i_set = BRIDGE.find("g_madeira_srv_eco_follow = (ef && ef[0] == '1') ? 1 : 0;")
i_idle = BRIDGE.find("g_madeira_srv_idle_us = idle > 0 ? idle : 0;")
i_end = BRIDGE.find('unsetenv("MADEIRA_SRV_ECO_FOLLOW"); unsetenv("MADEIRA_SRV_DIRECT");')
i_clear = BRIDGE.find("g_madeira_srv_eco_follow = 0;", i_end)
i_stop = BRIDGE.find("wineserver_stop();", i_end)
check("volatile int g_madeira_srv_eco_follow = 0;" in BRIDGE and "volatile int g_madeira_srv_idle_us = 0;" in BRIDGE,
      "the bridge defines both globals, off")
check(0 <= i_env < i_set and 0 <= i_env < i_idle, "the bridge sets them after the game's env lines")
check(i_set < i_end < i_clear < i_stop and 'unsetenv("MADEIRA_SRV_IDLE_US");' in BRIDGE[i_end:i_stop] and
      "g_madeira_srv_idle_us = 0;" in BRIDGE[i_end:i_stop], "the session end clears both before the server stops")
check(re.search(r'key: "env.MADEIRA_SRV_ECO_FOLLOW", title: "[^"]+", kind: \.bool, defaultValue: "0"', CAT) is not None,
      "the catalog documents env.MADEIRA_SRV_ECO_FOLLOW, default 0")
check(re.search(r'key: "env.MADEIRA_SRV_IDLE_US", title: "[^"]+", kind: \.int, defaultValue: "1000"', CAT) is not None,
      "the catalog documents env.MADEIRA_SRV_IDLE_US, default 1000")
if CI is not None:
    check("python3 tests/host/check-srv-eco-follow.py" in CI, "CI runs this check")

print()
if failures:
    print("%d check(s) failed" % len(failures))
    sys.exit(1)
print("all checks passed")
