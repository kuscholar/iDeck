/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#include "../app/LaunchProtocol.h"
typedef unsigned long usize;
static long call(long n, long a, long b, long c, long d, long e, long f) {
    register long x0 __asm__("x0") = a, x1 __asm__("x1") = b;
    register long x2 __asm__("x2") = c, x3 __asm__("x3") = d;
    register long x4 __asm__("x4") = e, x5 __asm__("x5") = f;
    register long x8 __asm__("x8") = n;
    __asm__ volatile("svc #0" : "+r"(x0) : "r"(x1), "r"(x2), "r"(x3),
                     "r"(x4), "r"(x5), "r"(x8) : "memory", "cc");
    return x0;
}
static usize length(const char *p) { usize n = 0; while (p[n]) n++; return n; }
static int fd, failures;
static void report(const char *name, int pass) {
    call(64, fd, (long)name, length(name), 0, 0, 0);
    const char *result = pass ? "=PASS\n" : "=FAIL\n";
    call(64, fd, (long)result, length(result), 0, 0, 0);
    if (!pass) failures++;
}
static volatile int child_done;
static char stack[65536] __attribute__((aligned(16)));
extern long probe_clone(long flags, void *stack, void (*entry)(void));
static void thread(void) {
    __atomic_store_n(&child_done, 1, __ATOMIC_RELEASE);
    call(98, (long)&child_done, 1, 1, 0, 0, 0);
    call(93, 0, 0, 0, 0, 0, 0);
    __builtin_unreachable();
}
void _start(void) {
    fd = (int)call(56, -100, (long)"/probe-results.txt", 0101 | 01000 | 1, 0600, 0, 0);
    if (fd < 0) { call(94, 90, 0, 0, 0, 0, 0); __builtin_unreachable(); }
    report("elf-arm64", 1);
    char bytes[8] = {0};
    long entropy = call(56, -100, (long)"/dev/urandom", 0, 0, 0, 0);
    report("urandom-device", entropy >= 0 && call(63, entropy, (long)bytes, sizeof bytes, 0, 0, 0) == sizeof bytes);
    if (entropy >= 0) call(57, entropy, 0, 0, 0, 0, 0);
    long file = call(56, -100, (long)"/filesystem-control", 0100 | 2 | 01000, 0600, 0, 0);
    int ok = file >= 0 && call(64, file, (long)"iDeck", 5, 0, 0, 0) == 5;
    ok = ok && call(62, file, 0, 0, 0, 0, 0) == 0;
    ok = ok && call(63, file, (long)bytes, 5, 0, 0, 0) == 5 && bytes[0] == 'i' && bytes[4] == 'k';
    report("utimensat-file-null", file >= 0 && call(88, file, 0, 0, 0, 0, 0) == 0);
    if (file >= 0) call(57, file, 0, 0, 0, 0, 0);
    report("filesystem", ok);
    long map = call(222, 0, 4096, 3, 0x21, -1, 0);
    report("shared-mmap", map > 0);
    if (map > 0) *(volatile int *)map = 1;
    long pid = call(220, 17, 0, 0, 0, 0, 0);
    if (pid == 0) {
        if (map > 0) *(volatile int *)map = 7;
        call(94, 23, 0, 0, 0, 0, 0); __builtin_unreachable();
    }
    int status = 0;
    long waited = pid > 0 ? call(260, pid, (long)&status, 0, 0, 0, 0) : -1;
    report("clone-wait", waited == pid && pid > 0 && status == (23 << 8));
    report("shared-across-clone", map > 0 && *(volatile int *)map == 7);
    if (map > 0) call(215, map, 4096, 0, 0, 0, 0);
    int sockets[2] = {-1, -1};
    ok = call(199, 1, 1, 0, (long)sockets, 0, 0) == 0;
    ok = ok && call(64, sockets[0], (long)"IPC", 3, 0, 0, 0) == 3;
    ok = ok && call(63, sockets[1], (long)bytes, 3, 0, 0, 0) == 3 && bytes[2] == 'C';
    report("unix-socketpair", ok);
    report("openat-nondirectory", sockets[0] >= 0 && call(56, sockets[0], (long)"./.writable", 0, 0, 0, 0) == -20);
    report("faccessat2-nondirectory", sockets[0] >= 0 && call(439, sockets[0], (long)"./.writable", 0, 0, 0, 0) == -20);
    report("faccessat2-absolute-ignores-dirfd", call(439, sockets[0], (long)"/filesystem-control", 0, 0, 0, 0) == 0);
    long absolute = call(56, sockets[0], (long)"/filesystem-control", 0, 0, 0, 0);
    report("openat-absolute-ignores-dirfd", absolute >= 0);
    if (absolute >= 0) call(57, absolute, 0, 0, 0, 0, 0);
    for (int i = 0; i < 2; i++) if (sockets[i] >= 0) call(57, sockets[i], 0, 0, 0, 0, 0);
    long sock = call(198, 2, 1, 0, 0, 0, 0);
    report("ipv4-socket", sock >= 0);
    if (sock >= 0) call(57, sock, 0, 0, 0, 0, 0);
    /* CLONE_VM|FS|FILES|SIGHAND|THREAD|SYSVSEM; no libc/TLS in this fixture. */
    long tid = probe_clone(0x50f00, stack + sizeof stack, thread);
    struct { long sec, nsec; } timeout = {2, 0};
    while (tid > 0 && !__atomic_load_n(&child_done, __ATOMIC_ACQUIRE)) {
        long r = call(98, (long)&child_done, 0, 0, (long)&timeout, 0, 0);
        if (r == -110 || (r < 0 && r != -11 && r != -4)) break;
    }
    report("thread-futex", tid > 0 && child_done == 1);
    static struct ideck_launch_request request = {
        .magic=IDECK_LAUNCH_MAGIC, .version=IDECK_LAUNCH_VERSION, .appid=480,
        .verb=1, .argc=1, .argument_bytes=sizeof(IDECK_LAUNCH_ROOT "Control/control.exe"),
        .install=IDECK_LAUNCH_ROOT "Control", .working=IDECK_LAUNCH_ROOT "Control",
        .executable=IDECK_LAUNCH_ROOT "Control/control.exe",
        .arguments=IDECK_LAUNCH_ROOT "Control/control.exe"
    };
    struct ideck_launch_response response = {0};
    long bridge = call(56, -100, (long)"/dev/ideck-madeira", 2, 0, 0, 0);
    ok = bridge >= 0 && call(64, bridge, (long)&request, sizeof request, 0, 0, 0) == sizeof request;
    ok = ok && call(63, bridge, (long)&response, sizeof response, 0, 0, 0) == sizeof response;
    ok = ok && response.magic == IDECK_LAUNCH_MAGIC && response.appid == 480 && response.result == 125;
    ok = ok && call(64, bridge, (long)&request, sizeof request, 0, 0, 0) == -16;
    report("native-bridge-roundtrip", ok);
    if (bridge >= 0) call(57, bridge, 0, 0, 0, 0, 0);
    report("complete", failures == 0);
    call(57, fd, 0, 0, 0, 0, 0);
    call(94, failures ? 1 : 0, 0, 0, 0, 0, 0);
    __builtin_unreachable();
}
