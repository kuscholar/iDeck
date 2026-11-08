/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#include "LaunchProtocol.h"
#include <string.h>
static int path(const char *s, size_t size, int empty) {
    const char *end = memchr(s, 0, size);
    if (!end) return 0;
    size_t n = (size_t)(end - s);
    if (!n) {
        for (size_t i = 1; i < size; i++) if (s[i]) return 0;
        return empty;
    }
    if (*s != '/' || s[n - 1] == '/') return 0;
    for (size_t i = 0; i < n; i++) {
        if ((unsigned char)s[i] < 32 || (unsigned char)s[i] > 126 || s[i] == '\\') return 0;
        if ((i == 0 || s[i - 1] == '/') &&
            (s[i] == '/' && i != 0)) return 0;
        if ((i == 0 || s[i - 1] == '/') && s[i] == '.' &&
            (s[i + 1] == '/' || s[i + 1] == 0 || (s[i + 1] == '.' && (s[i + 2] == '/' || s[i + 2] == 0)))) return 0;
    }
    for (size_t i = n + 1; i < size; i++) if (s[i]) return 0;
    return 1;
}
static int inside(const char *candidate, const char *root, int same) {
    size_t n = strlen(root);
    return !strncmp(candidate, root, n) && (candidate[n] == '/' || (same && candidate[n] == 0));
}
int ideck_launch_validate(const void *frame, size_t size) {
    if (!frame || size != sizeof(struct ideck_launch_request)) return -1;
    struct ideck_launch_request r;
    memcpy(&r, frame, sizeof r);
    if (r.magic != IDECK_LAUNCH_MAGIC || r.version != IDECK_LAUNCH_VERSION || !r.appid ||
        (r.verb != 1 && r.verb != 2) || !r.argc || r.argc > IDECK_LAUNCH_MAX_ARGS ||
        !r.argument_bytes || r.argument_bytes > sizeof r.arguments) return -1;
    if (!path(r.install, sizeof r.install, 0) || !path(r.executable, sizeof r.executable, 0) ||
        !path(r.working, sizeof r.working, 0) || !path(r.compatdata, sizeof r.compatdata, 1)) return -1;
    if (strncmp(r.install, IDECK_LAUNCH_ROOT, sizeof IDECK_LAUNCH_ROOT - 1) ||
        !r.install[sizeof IDECK_LAUNCH_ROOT - 1] ||
        !inside(r.executable, r.install, 0) || !inside(r.working, r.install, 1)) return -1;
    size_t p = 0;
    for (unsigned i = 0; i < r.argc; i++) {
        const char *end = memchr(r.arguments + p, 0, r.argument_bytes - p);
        if (!end) return -1;
        for (const char *s = r.arguments + p; s < end; s++)
            if ((unsigned char)*s < 32 || (unsigned char)*s > 126) return -1;
        if (i == 0 && strcmp(r.arguments, r.executable)) return -1;
        p = (size_t)(end - r.arguments) + 1;
        if (p == r.argument_bytes && i + 1 != r.argc) return -1;
    }
    if (p != r.argument_bytes) return -1;
    for (; p < sizeof r.arguments; p++) if (r.arguments[p]) return -1;
    return 0;
}
