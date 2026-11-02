/* SPDX-License-Identifier: GPL-3.0-or-later
 * Madeira Converter Exception: see LICENSE-EXCEPTION.md */
#ifndef IDECK_HYBRID_ARGS_H
#define IDECK_HYBRID_ARGS_H
#include <wchar.h>
/* Windows argv[0] quoting: quote marks delimit executable name, backslashes
 * are literal here. Return the untouched suffix so Chromium quoting survives. */
static const wchar_t *hybrid_args_tail(const wchar_t *cmd)
{
    if (!cmd) return L"";
    int quoted = 0;
    for (; *cmd; ++cmd) {
        if (*cmd == L'"') quoted = !quoted;
        else if (!quoted && (*cmd == L' ' || *cmd == L'\t')) break;
    }
    while (*cmd == L' ' || *cmd == L'\t') ++cmd;
    return cmd;
}
#endif
