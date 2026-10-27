// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
// Observe native re-exec without changing its result or printing arguments.
#include <dlfcn.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

int execv(const char *path, char *const arguments[]) {
    typedef int (*Exec)(const char *, char *const []);
    Exec real = (Exec)dlsym(RTLD_NEXT, "execv");
    const char *base = path ? strrchr(path, '/') : NULL;
    base = base ? base + 1 : path;
    fprintf(stderr, "[ideck-mac-exec] request executable=%s\n", base ? base : "<null>");
    if (!real) { errno = ENOSYS; return -1; }
    int result = real(path, arguments), saved = errno;
    fprintf(stderr, "[ideck-mac-exec] returned result=%d errno=%d\n", result, saved);
    errno = saved;
    return result;
}
