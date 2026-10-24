/* fib3 — reads N from argv[1] and computes both iterative and recursive fib(N).
 *
 * Tests:
 *   - argv handling end-to-end (wine command line → __argc/__argv → main(argc, argv))
 *   - String → int parsing
 *   - Variable input (no compile-time-fixed N)
 *
 * Usage: fib3-x64.exe N    (default 30 if no arg)
 * Output:
 *   argc = N
 *   argv[0] = ...
 *   argv[1] = ... (if present)
 *   iter fib(N) = ...
 *   rec  fib(N) = ...    (skipped if N > 35 to avoid runaway recursion)
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

static int parse_int(const char *s) {
    if (!s) return -1;
    int v = 0;
    int i = 0;
    if (s[0] == '-' || s[0] == '+') i = 1;  /* skip sign, treat as positive */
    while (s[i]) {
        if (s[i] < '0' || s[i] > '9') return v;  /* stop at first non-digit */
        v = v * 10 + (s[i] - '0');
        i++;
    }
    return v;
}

static int format_u64(char *buf, unsigned long long v) {
    char tmp[32];
    int n = 0;
    if (v == 0) { buf[0] = '0'; return 1; }
    while (v) { tmp[n++] = '0' + (char)(v % 10); v /= 10; }
    for (int i = 0; i < n; i++) buf[i] = tmp[n - 1 - i];
    return n;
}

static void put_str(HANDLE h, const char *s, int len) {
    DWORD w = 0;
    WriteFile(h, s, (DWORD)len, &w, NULL);
}

static int strlen_c(const char *s) {
    int n = 0;
    while (s[n]) n++;
    return n;
}

static void put_line_u64(HANDLE h, const char *prefix, int prefix_len,
                         unsigned long long val) {
    char num[32];
    int len = format_u64(num, val);
    put_str(h, prefix, prefix_len);
    put_str(h, num, len);
    put_str(h, "\n", 1);
}

int main(int argc, char **argv) {
    HANDLE h = GetStdHandle(STD_OUTPUT_HANDLE);

    /* Echo argc/argv. */
    put_line_u64(h, "argc = ", 7, (unsigned long long)argc);
    for (int i = 0; i < argc && i < 8; i++) {
        char prefix[32] = "argv[";
        int p = 5;
        char nbuf[8];
        int nlen = format_u64(nbuf, (unsigned long long)i);
        for (int j = 0; j < nlen; j++) prefix[p++] = nbuf[j];
        prefix[p++] = ']'; prefix[p++] = ' '; prefix[p++] = '='; prefix[p++] = ' ';
        put_str(h, prefix, p);
        if (argv[i]) {
            int slen = strlen_c(argv[i]);
            put_str(h, argv[i], slen);
        } else {
            put_str(h, "(null)", 6);
        }
        put_str(h, "\n", 1);
    }

    int n = 30;
    if (argc > 1 && argv[1]) {
        int parsed = parse_int(argv[1]);
        if (parsed > 0 && parsed <= 90) n = parsed;
    }

    unsigned long long iter_result = fib_iter(n);
    {
        char prefix[32] = "iter fib(";
        int p = 9;
        char nbuf[8];
        int nlen = format_u64(nbuf, (unsigned long long)n);
        for (int j = 0; j < nlen; j++) prefix[p++] = nbuf[j];
        prefix[p++] = ')'; prefix[p++] = ' '; prefix[p++] = '='; prefix[p++] = ' ';
        put_line_u64(h, prefix, p, iter_result);
    }

    /* Recursive only if N reasonable — fib(35) is ~24M calls already. */
    if (n <= 35) {
        unsigned long long rec_result = fib_rec(n);
        char prefix[32] = "rec  fib(";
        int p = 9;
        char nbuf[8];
        int nlen = format_u64(nbuf, (unsigned long long)n);
        for (int j = 0; j < nlen; j++) prefix[p++] = nbuf[j];
        prefix[p++] = ')'; prefix[p++] = ' '; prefix[p++] = '='; prefix[p++] = ' ';
        put_line_u64(h, prefix, p, rec_result);
    } else {
        put_str(h, "rec skipped (N too large)\n", 26);
    }

    /* Exit code = N % 256 — easy to verify the right N was parsed. */
    return n & 0xFF;
}
