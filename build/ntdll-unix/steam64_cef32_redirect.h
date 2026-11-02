/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Private AMD64 Steam / i386 CEF process-identity discriminator.
 * No proprietary image modification or synthetic allocation grants. */
#ifndef MADEIRA_STEAM64_CEF32_REDIRECT_H
#define MADEIRA_STEAM64_CEF32_REDIRECT_H
#include <stdint.h>
#include <stddef.h>
#include <string.h>

static int steam64_cef32_enabled(const char *session, const char *experiment, const char *prefix)
{
    static const char suffix[] = "/wine-steam64";
    size_t n;
    if (!session || strcmp(session, "1") || !experiment || strcmp(experiment, "1") || !prefix) return 0;
    n = strlen(prefix);
    return n >= sizeof(suffix) - 1 && !strcmp(prefix + n - (sizeof(suffix) - 1), suffix);
}

/* Exact experiment install path only, optionally prefixed with NT \??\.
 * command=1 rewrites argv[0] only and preserves the argument suffix verbatim.
 * Output length is one UTF-16 unit shorter (win64 -> win7), or zero on refusal. */
static size_t steam64_cef32_path(uint16_t *out, size_t cap, const uint16_t *in, size_t len, int command)
{
    static const char from[] = "C:\\Program Files\\Steam\\bin\\cef\\cef.win64\\steamwebhelper.exe";
    static const char to[] = "C:\\Program Files\\Steam\\bin\\cef\\cef.win7\\steamwebhelper.exe";
    size_t begin = 0, end, nt = 0, i, tail, n;
    if (!in || !len) return 0;
    if (command && in[0] == '"') begin = 1;
    if (len >= begin + 4 && in[begin] == '\\' && in[begin+1] == '?' &&
        in[begin+2] == '?' && in[begin+3] == '\\') nt = 4;
    end = begin + nt + sizeof(from) - 1;
    if (end > len) return 0;
    for (i = 0; i < sizeof(from) - 1; ++i) {
        unsigned c = in[begin + nt + i], want = (unsigned char)from[i];
        if (c == '/') c = '\\';
        if (c >= 'A' && c <= 'Z') c += 'a' - 'A';
        if (want >= 'A' && want <= 'Z') want += 'a' - 'A';
        if (c != want) return 0;
    }
    tail = end;
    if (!command) { if (end != len) return 0; }
    else if (begin) { if (end == len || in[end] != '"') return 0; }
    else if (end < len && in[end] != ' ' && in[end] != '\t') return 0;
    n = len - 1;
    if (!out) return cap ? 0 : n; /* checked sizing query */
    if (cap <= n) return 0;
    for (i = 0; i < begin + nt; ++i) out[i] = in[i];
    for (i = 0; i < sizeof(to) - 1; ++i) out[begin + nt + i] = (unsigned char)to[i];
    for (i = tail; i < len; ++i) out[i - 1] = in[i];
    out[n] = 0;
    return n;
}
#endif
