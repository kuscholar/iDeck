/* Recursive Fibonacci — built as x86_64 PE (mingw), runs under FEX on iOS.
 *
 * Tests:
 *   - Deep CALL/RET chains (FEX call-ret-stack stress)
 *   - Integer arithmetic
 *   - WriteFile to stdout
 *
 * No printf — we write the result manually via WriteFile so we don't pull
 * in ucrtbase's full printf machinery (and the more x86 instructions it
 * exercises means more chances of hitting an unimplemented one). Plain
 * itoa-equivalent + WriteFile keeps the surface tight.
 */
#include <windows.h>

static unsigned long long fib(int n) {
    if (n < 2) return (unsigned long long)n;
    return fib(n - 1) + fib(n - 2);
}

static int format_u64(char *buf, unsigned long long v) {
    char tmp[32];
    int n = 0;
    if (v == 0) { buf[0] = '0'; return 1; }
    while (v) { tmp[n++] = '0' + (char)(v % 10); v /= 10; }
    /* reverse */
    for (int i = 0; i < n; i++) buf[i] = tmp[n - 1 - i];
    return n;
}

int main(void) {
    HANDLE h = GetStdHandle(STD_OUTPUT_HANDLE);
    DWORD written = 0;

    const char *prefix = "fib(30) = ";
    WriteFile(h, prefix, 10, &written, NULL);

    unsigned long long result = fib(30);

    char num[32];
    int len = format_u64(num, result);
    WriteFile(h, num, len, &written, NULL);
    WriteFile(h, "\n", 1, &written, NULL);

    /* fib(30) = 832040. Use it as the exit code (mod 256) so we can verify
     * via the process exit code in the log: 832040 % 256 = 232 = 0xE8. */
    return (int)(result & 0xFF);
}
