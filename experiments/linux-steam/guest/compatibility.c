/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#include "../app/LaunchProtocol.h"
static long call(long n, long a, long b, long c, long d) {
    register long x0 __asm__("x0") = a, x1 __asm__("x1") = b;
    register long x2 __asm__("x2") = c, x3 __asm__("x3") = d;
    register long x8 __asm__("x8") = n;
    __asm__ volatile("svc #0" : "+r"(x0) : "r"(x1), "r"(x2), "r"(x3), "r"(x8) : "memory", "cc");
    return x0;
}
static int copy(char *out, size_t cap, const char *in) {
    if (!in) return -1;
    for (size_t i = 0; i < cap; i++) { out[i] = in[i]; if (!in[i]) return (int)i; }
    return -1;
}
static int equal(const char *a, const char *b) { while (*a && *a == *b) {a++; b++;} return *a == *b; }
static const char *env(char **vars, const char *key) {
    for (unsigned i = 0; vars[i] && i < 512; i++) {
        unsigned n = 0; while (key[n] && key[n] == vars[i][n]) n++;
        if (!key[n] && vars[i][n] == '=') return vars[i] + n + 1;
    }
    return 0;
}
int compatibility_main(unsigned long *stack) {
    unsigned long argc = *stack;
    if (argc < 3 || argc > IDECK_LAUNCH_MAX_ARGS + 2) return 126;
    char **argv = (char **)(stack + 1), **vars = argv + argc + 1;
    static struct ideck_launch_request r;
    r.magic = IDECK_LAUNCH_MAGIC; r.version = IDECK_LAUNCH_VERSION;
    r.verb = equal(argv[1], "waitforexitandrun") ? 1 : equal(argv[1], "run") ? 2 : 0;
    if (!r.verb) return 126;
    const char *id = env(vars, "STEAM_COMPAT_APP_ID");
    if (!id) id = env(vars, "SteamAppId");
    if (!id || !*id) return 126;
    uint64_t appid = 0;
    for (unsigned i = 0; id[i]; i++) {
        if (i >= 10 || id[i] < '0' || id[i] > '9') return 126;
        appid = appid * 10 + (unsigned)(id[i] - '0');
        if (appid > 0xffffffffu) return 126;
    }
    r.appid = (uint32_t)appid;
    if (!r.appid || copy(r.install, sizeof r.install, env(vars, "STEAM_COMPAT_INSTALL_PATH")) < 0 ||
        copy(r.executable, sizeof r.executable, argv[2]) < 0 ||
        call(17, (long)r.working, sizeof r.working, 0, 0) < 0) return 126;
    const char *compat = env(vars, "STEAM_COMPAT_DATA_PATH");
    if (compat && copy(r.compatdata, sizeof r.compatdata, compat) < 0) return 126;
    r.argc = (uint32_t)argc - 2;
    for (unsigned i = 2; i < argc; i++) {
        int n = copy(r.arguments + r.argument_bytes, sizeof r.arguments - r.argument_bytes, argv[i]);
        if (n < 0) return 126;
        r.argument_bytes += (unsigned)n + 1;
    }
    long fd = call(56, -100, (long)"/dev/ideck-madeira", 2, 0);
    if (fd < 0) return 126;
    if (call(64, fd, (long)&r, sizeof r, 0) != sizeof r) { call(57, fd, 0, 0, 0); return 126; }
    struct ideck_launch_response response;
    long count = call(63, fd, (long)&response, sizeof response, 0);
    call(57, fd, 0, 0, 0);
    if (count != sizeof response || response.magic != IDECK_LAUNCH_MAGIC ||
        response.version != IDECK_LAUNCH_VERSION || response.appid != r.appid) return 126;
    return (int)(response.result <= 255 ? response.result : 126);
}
