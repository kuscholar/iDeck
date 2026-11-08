/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * Freestanding Linux ARM64 reproducer; actual Steam requested flags 0x90000.
 * The packet tests must not be made to pass by silently dropping O_DIRECT.
 */
static long call(long n, long a, long b, long c) {
    register long x0 __asm__("x0") = a, x1 __asm__("x1") = b, x2 __asm__("x2") = c;
    register long x8 __asm__("x8") = n;
    __asm__ volatile("svc #0" : "+r"(x0) : "r"(x1), "r"(x2), "r"(x8) : "memory", "cc");
    return x0;
}
static int report_fd=-1;
static void text(const char *s) {
    unsigned n = 0;
    while (s[n]) n++;
    call(64, 1, (long)s, n);
    if(report_fd>=0) call(64,report_fd,(long)s,n);
}
static void number(long n) {
    char buffer[24]; unsigned at = sizeof buffer;
    unsigned long value = n < 0 ? (unsigned long)(-n) : (unsigned long)n;
    do { buffer[--at] = (char)('0' + value % 10); value /= 10; } while (value);
    if (n < 0) buffer[--at] = '-';
    call(64, 1, (long)(buffer + at), sizeof buffer - at);
    if(report_fd>=0) call(64,report_fd,(long)(buffer+at),sizeof buffer-at);
    text("\n");
}
__attribute__((noreturn)) void _start(void) {
    register long x0 __asm__("x0")=-100,x1 __asm__("x1")=(long)"/packet-probe-results.txt";
    register long x2 __asm__("x2")=0x241,x3 __asm__("x3")=0600,x8 __asm__("x8")=56;
    __asm__ volatile("svc #0" : "+r"(x0) : "r"(x1),"r"(x2),"r"(x3),"r"(x8) : "memory","cc");
    report_fd=x0>=0?(int)x0:-1;
    int fds[2] = {-1, -1}; char bytes[8];
    long status = call(59, (long)fds, 0x80000, 0);
    text("stream-create-status="); number(status);
    int stream = status == 0 && call(64, fds[1], (long)"abc", 3) == 3 &&
        call(63, fds[0], (long)bytes, 3) == 3 && bytes[0] == 'a' && bytes[2] == 'c';
    text(stream ? "stream-roundtrip=PASS\n" : "stream-roundtrip=FAIL\n");
    if (status == 0) { call(57, fds[0], 0, 0); call(57, fds[1], 0, 0); }
    /* ARM64 O_DIRECT=1<<16, O_CLOEXEC=1<<19, NOT the x86 O_DIRECT value. */
    status = call(59, (long)fds, 0x90000, 0);
    text("steam-packet-create-status="); number(status);
    int packets = 0;
    if (status == 0) {
        call(57, fds[0], 0, 0); call(57, fds[1], 0, 0);
        status = call(59, (long)fds, 0x90800, 0);
        if (status == 0) {
            packets = call(25, fds[0], 1, 0) == 1 &&
                !(call(25, fds[0], 3, 0) & 0x10000) &&
                (call(25, fds[1], 3, 0) & 0x10000) &&
                call(64, fds[1], (long)"abc", 3) == 3 &&
                call(64, fds[1], (long)"de", 2) == 2 &&
                call(63, fds[0], (long)bytes, 2) == 2 && bytes[0] == 'a' && bytes[1] == 'b' &&
                call(63, fds[0], (long)bytes, sizeof bytes) == 2 && bytes[0] == 'd' && bytes[1] == 'e' &&
                call(64, fds[1], (long)"", 0) == 0 && call(63, fds[0], (long)bytes, 1) == -11;
            call(57, fds[0], 0, 0); call(57, fds[1], 0, 0);
        }
    }
    text(packets ? "packet-boundaries-short-read-cloexec-nonblock=PASS\n" : "packet-boundaries-short-read-cloexec-nonblock=BLOCKED\n");
    if(report_fd>=0)call(57,report_fd,0,0);
    call(94, stream && packets ? 0 : 1, 0, 0);
    __builtin_unreachable();
}
