/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
typedef unsigned long word;

static long call(long number, word a, word b, word c, word d)
{
    register word x0 __asm__("x0") = a;
    register word x1 __asm__("x1") = b;
    register word x2 __asm__("x2") = c;
    register word x3 __asm__("x3") = d;
    register word x4 __asm__("x4") = 0;
    register long x8 __asm__("x8") = number;
    __asm__ volatile ("svc 0" : "+r"(x0) : "r"(x1), "r"(x2), "r"(x3), "r"(x4), "r"(x8) : "memory");
    return (long)x0;
}

enum {
    READ = 63, WRITE = 64, CLOSE = 57, PIPE2 = 59, EXIT = 93, GETPID = 172,
    GETPPID = 173, PRCTL = 167, CLONE = 220, WAIT4 = 260,
    SET_SUBREAPER = 36, GET_SUBREAPER = 37, SIGCHLD = 17
};

static void __attribute__((noreturn)) finish(int code)
{
    call(EXIT, code, 0, 0, 0);
    __builtin_unreachable();
}

static int enabled(void)
{
    int value = -1;
    return call(PRCTL, GET_SUBREAPER, (word)&value, 0, 0) ? -1 : value;
}

void __attribute__((noreturn)) _start(void)
{
    long supervisor = call(CLONE, SIGCHLD, 0, 0, 0);
    if (supervisor < 0)
        finish(2);
    if (supervisor) {
        int status = -1;
        if (call(WAIT4, supervisor, (word)&status, 0, 0) != supervisor)
            finish(3);
        finish(status >> 8);
    }

    int ids[2], gate[2];
    if (enabled() != 0 || call(PRCTL, SET_SUBREAPER, 1, 0, 0) || enabled() != 1 ||
        call(PRCTL, GET_SUBREAPER, 0, 0, 0) != -14)
        finish(4);
    if (call(PIPE2, (word)ids, 0, 0, 0) || call(PIPE2, (word)gate, 0, 0, 0))
        finish(5);
    long adopter = call(GETPID, 0, 0, 0, 0);
    long middle = call(CLONE, SIGCHLD, 0, 0, 0);
    if (middle < 0)
        finish(6);

    if (!middle) {
        call(CLOSE, ids[0], 0, 0, 0);
        call(CLOSE, gate[1], 0, 0, 0);
        if (enabled() != 0)
            finish(7);
        long descendant = call(CLONE, SIGCHLD, 0, 0, 0);
        if (descendant < 0)
            finish(8);
        if (!descendant) {
            char release;
            call(CLOSE, ids[1], 0, 0, 0);
            if (call(READ, gate[0], (word)&release, sizeof release, 0) != sizeof release)
                finish(9);
            finish(call(GETPPID, 0, 0, 0, 0) == adopter ? 41 : 10);
        }
        if (call(WRITE, ids[1], (word)&descendant, sizeof descendant, 0) != sizeof descendant)
            finish(11);
        finish(0);
    }

    call(CLOSE, ids[1], 0, 0, 0);
    call(CLOSE, gate[0], 0, 0, 0);
    long descendant;
    if (call(READ, ids[0], (word)&descendant, sizeof descendant, 0) != sizeof descendant)
        finish(12);
    int status = -1;
    if (call(WAIT4, middle, (word)&status, 0, 0) != middle || status != 0)
        finish(13);
    if (call(WRITE, gate[1], (word)"x", 1, 0) != 1)
        finish(14);
    if (call(WAIT4, (word)-1, (word)&status, 0, 0) != descendant || status != (41 << 8))
        finish(15);
    if (call(PRCTL, SET_SUBREAPER, 0, 0, 0) || enabled() != 0)
        finish(16);
    static const char ok[]="IDECK_SUBREAPER_ADOPTION_AND_WAIT_PASS\n";
    call(WRITE, 1, (word)ok, sizeof ok - 1, 0);
    finish(0);
}
