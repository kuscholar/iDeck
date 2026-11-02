/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Isolated layout experiment; no synthetic/overlapping pool grants.
 */
#ifndef MADEIRA_STEAM64_LAYOUT_H
#define MADEIRA_STEAM64_LAYOUT_H
#include <stdint.h>
#include <string.h>
static int steam64_layout_enabled(const char *session, const char *layout)
{
    return session && !strcmp(session, "1") && layout && !strcmp(layout, "1");
}
#define STEAM64_FEX_BASE UINT64_C(0x7100000000)
#define STEAM64_FEX_SIZE UINT64_C(0x100000000)
#define STEAM64_FURNITURE_END STEAM64_FEX_BASE
#endif
