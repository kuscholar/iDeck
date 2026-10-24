/* fib2 — exercises 64-bit integer math harder than fib-x64.c.
 *
 * Tests:
 *   - 64-bit integer arithmetic past 2^32 (fib(85) ≈ 2.6 × 10^17 ≈ 2^58)
 *   - 64-bit division/modulo (decimal formatting requires u64 div/mod)
 *   - Multiple recursive call branches (recursive fib(30) for call-ret stack)
 *   - Sign-extending 32→64 (multiplication patterns)
 *   - Mixing iterative and recursive paths
 *
 * Output is verifiable: each line shows fib(N) = <decimal>. The known values
 * are baked in as a table for self-check at the end.
 */
#include <windows.h>

static unsigned long long fib_rec(int n) {
    if (n < 2) return (unsigned long long)n;
    return fib_rec(n - 1) + fib_rec(n - 2);
}

static unsigned long long fib_iter(int n) {
    if (n < 2) return (unsigned long long)n;
    unsigned long long a = 0, b = 1;
    for (int i = 2; i <= n; i++) {
        unsigned long long t = a + b;
        a = b;
        b = t;
    }
    return b;
}

static int format_u64(char *buf, unsigned long long v) {
    char tmp[32];
    int n = 0;
    if (v == 0) { buf[0] = '0'; return 1; }
    while (v) { tmp[n++] = '0' + (char)(v % 10); v /= 10; }
    for (int i = 0; i < n; i++) buf[i] = tmp[n - 1 - i];
    return n;
}

static void put_line(HANDLE h, const char *prefix, int prefix_len,
                     unsigned long long val) {
    char num[32];
    int len = format_u64(num, val);
    DWORD written = 0;
    WriteFile(h, prefix, (DWORD)prefix_len, &written, NULL);
    WriteFile(h, num, (DWORD)len, &written, NULL);
    WriteFile(h, "\n", 1, &written, NULL);
}

/* Known reference values for self-check. */
static const struct { int n; unsigned long long expected; } known[] = {
    { 10,                    55ULL },
    { 20,                  6765ULL },
    { 30,                832040ULL },
    { 40,             102334155ULL },
    { 50,           12586269025ULL },
    { 60,         1548008755920ULL },
    { 70,       190392490709135ULL },
    { 80,     23416728348467685ULL },
    { 85,    259695496911122585ULL },
};
#define KNOWN_COUNT (sizeof(known) / sizeof(known[0]))

int main(void) {
    HANDLE h = GetStdHandle(STD_OUTPUT_HANDLE);
    DWORD written = 0;
    int passed = 0;
    int total = (int)KNOWN_COUNT;

    /* Iterative path: tests 64-bit arithmetic at increasing magnitudes. */
    for (size_t i = 0; i < KNOWN_COUNT; i++) {
        char prefix[32] = "iter fib(";
        int p = 9;
        char nbuf[8];
        int nlen = format_u64(nbuf, (unsigned long long)known[i].n);
        for (int j = 0; j < nlen; j++) prefix[p++] = nbuf[j];
        prefix[p++] = ')';
        prefix[p++] = ' '; prefix[p++] = '='; prefix[p++] = ' ';
        unsigned long long got = fib_iter(known[i].n);
        put_line(h, prefix, p, got);
        if (got == known[i].expected) passed++;
    }

    /* Recursive path: stresses call-ret stack with 2.7M calls for fib(30). */
    unsigned long long rec30 = fib_rec(30);
    put_line(h, "rec  fib(30) = ", 15, rec30);
    if (rec30 == 832040ULL) passed++;
    total++;

    /* Verdict line. */
    char verdict[64];
    int vp = 0;
    const char *p1 = "verdict: ";
    while (p1[vp]) { verdict[vp] = p1[vp]; vp++; }
    char nb[8];
    int nl = format_u64(nb, (unsigned long long)passed);
    for (int j = 0; j < nl; j++) verdict[vp++] = nb[j];
    verdict[vp++] = '/';
    nl = format_u64(nb, (unsigned long long)total);
    for (int j = 0; j < nl; j++) verdict[vp++] = nb[j];
    const char *p2 = " passed\n";
    for (int j = 0; p2[j]; j++) verdict[vp++] = p2[j];
    WriteFile(h, verdict, (DWORD)vp, &written, NULL);

    /* Exit code: number of failures (0 = all pass). */
    return total - passed;
}
