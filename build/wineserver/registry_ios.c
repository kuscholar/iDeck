/* SPDX-License-Identifier: GPL-3.0-or-later
 * Madeira Converter Exception: see LICENSE-EXCEPTION.md
 * iDeck-only additions. Included Wine source retains its LGPL notices. */
#define init_registry wine_registry_init_original
#include "../../wine/server/registry.c"
#undef init_registry
#include "steam_ui_machines.h"

void init_registry(void)
{
    wine_registry_init_original();
    if (ideck_advertise_amd64_guest(supported_machines, &supported_machines_count,
                                   ARRAY_SIZE(supported_machines), getenv("MADEIRA_STEAM_UI_SESSION")))
        fprintf(stderr, "[ideck-machines] advertised existing AMD64 guest support; native ARM64 unchanged\n");
}
