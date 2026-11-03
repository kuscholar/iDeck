/* SPDX-License-Identifier: GPL-3.0-or-later
 * Madeira Converter Exception: see LICENSE-EXCEPTION.md. */
#ifndef MADEIRA_STEAM_UI_DIAGNOSTICS_H
#define MADEIRA_STEAM_UI_DIAGNOSTICS_H
#include <stdlib.h>
#include <string.h>

/* Apply after config export, before Wine starts. This switch controls only
 * periodic sampling. Never default LEAN_DIAG here: it also changes VM walks
 * and replay cadence. Explicit 1 enables sampling for a controlled test. */
static inline int madeira_steam_ui_diagnostic_defaults(void)
{
    const char *session = getenv("MADEIRA_STEAM_UI_SESSION");
    if (!session || strcmp(session, "1")) return 0;
    if (!getenv("MADEIRA_STEAM_UI_SAMPLING") &&
        setenv("MADEIRA_STEAM_UI_SAMPLING", "0", 0)) return -1;
    return 1;
}

static inline int madeira_steam_ui_sampling_disabled(void)
{
    const char *session = getenv("MADEIRA_STEAM_UI_SESSION");
    const char *sampling = getenv("MADEIRA_STEAM_UI_SAMPLING");
    const char *lean = getenv("MADEIRA_LEAN_DIAG");
    return session && !strcmp(session, "1") &&
        ((sampling && !strcmp(sampling, "0")) ||
         (lean && *lean && strcmp(lean, "0")));
}

/* Actual main-thread-stall evidence remains available independently. */
static inline int madeira_steam_ui_periodic_stacks_enabled(void)
{
    return !madeira_steam_ui_sampling_disabled();
}
#endif
