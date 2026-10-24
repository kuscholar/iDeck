/*
 * ml731 clock regression test (x86-64 PE, runs under the emulator).
 *
 * Asserts the Windows time contract that KUSER_SHARED_DATA is supposed to
 * provide. It was silently broken on iOS for the whole life of the port:
 * the server never copied its clock into the shared page, so SystemTime,
 * InterruptTime and TickCount were frozen at their init values. Native
 * titles pace frames with QueryPerformanceCounter, which reads
 * clock_gettime and is unaffected, so nothing failed loudly -- managed
 * titles just sat forever on transitions that wait for time to pass.
 *
 * Verifying that by hand cost a five-minute game run and a comparison
 * against a control log. This does it in one second.
 *
 * Each clock is checked independently so a partial failure names itself:
 * QPC alone advancing (with the others frozen) is exactly the signature of
 * the shared-page bug, and is far more informative than "time is broken".
 */
#include <windows.h>
#include <stdio.h>

static int failures;

static void check(const char *name, unsigned long long before,
                  unsigned long long after, unsigned long long min_delta)
{
    unsigned long long d = after - before;
    if (after < before)          /* unsigned wrap reads as an enormous delta */
    {
        printf("FAIL %-18s went BACKWARDS: %llu -> %llu\n", name, before, after);
        failures++;
        return;
    }
    if (d < min_delta)
    {
        printf("FAIL %-18s advanced %llu, expected >= %llu (frozen?)\n",
               name, d, min_delta);
        failures++;
        return;
    }
    printf("ok   %-18s advanced %llu\n", name, d);
}

int main(void)
{
    const DWORD nap = 1000;                 /* sleep long enough that even a
                                             * coarse 15.6ms tick must move */
    ULONGLONG tick0, tick1, unbiased0 = 0, unbiased1 = 0;
    FILETIME  ft0, ft1;
    LARGE_INTEGER qpc0, qpc1, qpf;
    ULARGE_INTEGER u0, u1;

    printf("=== ml731 clock regression test ===\n");

    tick0 = GetTickCount64();
    GetSystemTimeAsFileTime(&ft0);
    QueryPerformanceCounter(&qpc0);
    QueryPerformanceFrequency(&qpf);
    QueryUnbiasedInterruptTime(&unbiased0);

    Sleep(nap);

    tick1 = GetTickCount64();
    GetSystemTimeAsFileTime(&ft1);
    QueryPerformanceCounter(&qpc1);
    QueryUnbiasedInterruptTime(&unbiased1);

    u0.LowPart = ft0.dwLowDateTime; u0.HighPart = ft0.dwHighDateTime;
    u1.LowPart = ft1.dwLowDateTime; u1.HighPart = ft1.dwHighDateTime;

    /* Deliberately loose lower bounds: this is a frozen-clock test, not a
     * timing-accuracy test, and the emulator's Sleep may overshoot badly
     * under load. Half the requested nap is far above any tick granularity
     * and far below anything a working clock would fail. */
    check("GetTickCount64",   tick0,       tick1,       nap / 2);
    check("SystemTime",       u0.QuadPart, u1.QuadPart, (nap / 2) * 10000ULL);
    check("UnbiasedInterrupt",unbiased0,   unbiased1,   (nap / 2) * 10000ULL);
    check("QueryPerfCounter", (unsigned long long)qpc0.QuadPart,
                              (unsigned long long)qpc1.QuadPart,
                              (unsigned long long)(qpf.QuadPart / 2));

    if (failures)
        printf("=== %d FAILED. If only QueryPerfCounter passed, the server is not "
               "updating KUSER_SHARED_DATA (see MADEIRA_USD_TIME). ===\n", failures);
    else
        printf("=== all clocks advance ===\n");
    return failures ? 1 : 0;
}
