/*
 * ml1131 call-cost microbenchmark (x86-64 PE, runs under the emulator).
 *
 * The game's critical threads spend ~35-40 % of their running time inside a
 * handful of Win32 imports (RtlLeaveCriticalSection, QueryPerformanceCounter,
 * SetEvent, GetLastError, HeapFree ...; HANDOFF section 123). This measures what
 * one call of each costs here, from x64 code, so the per-call price of the
 * x64 -> ARM64EC transition and of each sync primitive is known directly
 * instead of being inferred from sample shares.
 *
 * Every figure is the best of three timed runs (least disturbed by the
 * scheduler or by the phone's clock policy). Run it with the phone cool and
 * idle; the [xp] probe lines logged at the same time give the core clock.
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

static LARGE_INTEGER freq;
static volatile LONG sink;
static FILE *out;   /* results also go to C:\\calltest.txt, in case stdout is not captured */

#define XOUT(...) do { printf(__VA_ARGS__); fflush(stdout); if (out) { fprintf(out, __VA_ARGS__); fflush(out); } } while (0)

static double now_ns(void)
{
    LARGE_INTEGER t;
    QueryPerformanceCounter(&t);
    return (double)t.QuadPart * 1e9 / (double)freq.QuadPart;
}

typedef void (*bench_fn)(int n);

static void report(const char *name, bench_fn fn, int n)
{
    double best = 1e30;
    int rep;
    fn(n / 10 + 1);   /* warm up: JIT compile, page in */
    for (rep = 0; rep < 3; rep++)
    {
        double t0 = now_ns();
        fn(n);
        double dt = now_ns() - t0;
        if (dt < best) best = dt;
    }
    XOUT("[calltest] %-34s %9.1f ns/op  (%d ops, best of 3)\n", name, best / n, n);
}

/* ---- baselines ---- */
static void b_empty(int n) { int i; for (i = 0; i < n; i++) sink++; }
static void b_alu(int n)
{
    unsigned long long a = 1, b = 3; int i;
    for (i = 0; i < n; i++) { a = a * 6364136223846793005ull + b; b ^= a >> 17; }
    sink = (LONG)(a ^ b);
}
static void b_atomic(int n) { int i; for (i = 0; i < n; i++) InterlockedIncrement(&sink); }
static int arr[4096];
static void b_stores(int n) { int i; for (i = 0; i < n; i++) arr[i & 4095] = i; }

/* ---- single-thread imports ---- */
static DWORD tls_idx;
static CRITICAL_SECTION cs_uncont, cs_spin4000;
static HANDLE ev_manual_set, ev_manual_unset, ev_auto;
static HANDLE heap;

static void b_getlasterror(int n) { int i; DWORD x = 0; for (i = 0; i < n; i++) x += GetLastError(); sink = x; }
static void b_setlasterror(int n) { int i; for (i = 0; i < n; i++) SetLastError(i); }
static void b_tlsget(int n) { int i; ULONG_PTR x = 0; for (i = 0; i < n; i++) x += (ULONG_PTR)TlsGetValue(tls_idx); sink = (LONG)x; }
static void b_qpc(int n) { int i; LARGE_INTEGER t; LONGLONG x = 0; for (i = 0; i < n; i++) { QueryPerformanceCounter(&t); x += t.QuadPart; } sink = (LONG)x; }
static void b_tid(int n) { int i; DWORD x = 0; for (i = 0; i < n; i++) x += GetCurrentThreadId(); sink = x; }
static void b_cs(int n) { int i; for (i = 0; i < n; i++) { EnterCriticalSection(&cs_uncont); LeaveCriticalSection(&cs_uncont); } }
static void b_setevent_set(int n) { int i; for (i = 0; i < n; i++) SetEvent(ev_manual_set); }
static void b_setevent_auto(int n) { int i; for (i = 0; i < n; i++) SetEvent(ev_auto); }
static void b_resetevent(int n) { int i; for (i = 0; i < n; i++) ResetEvent(ev_manual_unset); }
static void b_wait_signaled(int n) { int i; for (i = 0; i < n; i++) WaitForSingleObject(ev_manual_set, 0); }
static void b_wait_poll_empty(int n) { int i; for (i = 0; i < n; i++) WaitForSingleObject(ev_manual_unset, 0); }
static void b_heap(int n) { int i; for (i = 0; i < n; i++) { void *p = HeapAlloc(heap, 0, 64); HeapFree(heap, 0, p); } }
static void b_malloc(int n) { int i; for (i = 0; i < n; i++) { void *p = malloc(64); free(p); } }
static void b_switch(int n) { int i; for (i = 0; i < n; i++) SwitchToThread(); }
static void b_sleep0(int n) { int i; for (i = 0; i < n; i++) Sleep(0); }

/* ---- cross-thread ---- */
static HANDLE ping, pong;
static volatile LONG stop;
static DWORD WINAPI pong_thread(void *arg)
{
    (void)arg;
    for (;;)
    {
        WaitForSingleObject(ping, INFINITE);
        if (stop) { SetEvent(pong); return 0; }
        SetEvent(pong);
    }
}
static void b_pingpong(int n)
{
    int i;
    for (i = 0; i < n; i++) { SetEvent(ping); WaitForSingleObject(pong, INFINITE); }
}

static volatile LONG cs_go;
static volatile LONGLONG cs_counter;
static DWORD WINAPI cs_contender(void *arg)
{
    CRITICAL_SECTION *cs = arg;
    while (!cs_go) YieldProcessor();
    while (cs_go)
    {
        EnterCriticalSection(cs);
        cs_counter++;
        { volatile int k; for (k = 0; k < 20; k++); }   /* ~a short guarded update */
        LeaveCriticalSection(cs);
    }
    return 0;
}
static CRITICAL_SECTION *cs_target;
static void b_cs_contended(int n)
{
    int i;
    for (i = 0; i < n; i++)
    {
        EnterCriticalSection(cs_target);
        cs_counter++;
        { volatile int k; for (k = 0; k < 20; k++); }
        LeaveCriticalSection(cs_target);
    }
}

static void contended_run(const char *name, CRITICAL_SECTION *cs)
{
    HANDLE t;
    cs_target = cs; cs_go = 0; cs_counter = 0;
    t = CreateThread(NULL, 0, cs_contender, cs, 0, NULL);
    cs_go = 1;
    Sleep(10);
    report(name, b_cs_contended, 200000);
    cs_go = 0;
    WaitForSingleObject(t, INFINITE);
    CloseHandle(t);
    if (cs->DebugInfo && cs->DebugInfo != (void *)-1)
        XOUT("[calltest]   %s: ContentionCount %lu over the run\n", name, cs->DebugInfo->ContentionCount);
}

int main(void)
{
    HANDLE t;
    QueryPerformanceFrequency(&freq);
    out = fopen("C:\\calltest.txt", "w");
    XOUT("[calltest] ml1131 call-cost microbenchmark (x64 under FEX), QPF %lld Hz\n", freq.QuadPart);
    tls_idx = TlsAlloc(); TlsSetValue(tls_idx, (void *)0x1234);
    InitializeCriticalSection(&cs_uncont);
    InitializeCriticalSectionAndSpinCount(&cs_spin4000, 4000);
    ev_manual_set = CreateEventA(NULL, TRUE, TRUE, NULL);
    ev_manual_unset = CreateEventA(NULL, TRUE, FALSE, NULL);
    ev_auto = CreateEventA(NULL, FALSE, FALSE, NULL);
    heap = GetProcessHeap();

    report("empty loop", b_empty, 20000000);
    report("integer mul/xor chain", b_alu, 20000000);
    report("lock inc (InterlockedIncrement)", b_atomic, 5000000);
    report("plain store", b_stores, 20000000);

    report("GetLastError", b_getlasterror, 500000);
    report("SetLastError", b_setlasterror, 500000);
    report("TlsGetValue", b_tlsget, 500000);
    report("GetCurrentThreadId", b_tid, 500000);
    report("QueryPerformanceCounter", b_qpc, 500000);
    report("Enter+LeaveCriticalSection (free)", b_cs, 500000);
    report("SetEvent (manual, already set)", b_setevent_set, 200000);
    report("SetEvent (auto, no waiter)", b_setevent_auto, 200000);
    report("ResetEvent (already reset)", b_resetevent, 200000);
    report("WaitForSingleObject(signaled, 0)", b_wait_signaled, 200000);
    report("WaitForSingleObject(empty, 0) poll", b_wait_poll_empty, 200000);
    report("HeapAlloc+HeapFree 64 B", b_heap, 200000);
    report("malloc+free 64 B", b_malloc, 200000);
    report("SwitchToThread", b_switch, 100000);
    report("Sleep(0)", b_sleep0, 100000);

    ping = CreateEventA(NULL, FALSE, FALSE, NULL);
    pong = CreateEventA(NULL, FALSE, FALSE, NULL);
    t = CreateThread(NULL, 0, pong_thread, NULL, 0, NULL);
    report("event ping-pong round trip (2 threads)", b_pingpong, 20000);
    stop = 1; SetEvent(ping); WaitForSingleObject(t, INFINITE); CloseHandle(t);

    contended_run("contended CS enter/leave (spin 0)", &cs_uncont);
    contended_run("contended CS enter/leave (spin 4000)", &cs_spin4000);

    XOUT("[calltest] done\n");
    if (out) fclose(out);
    return 0;
}
