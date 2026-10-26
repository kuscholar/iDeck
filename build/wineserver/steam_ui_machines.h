/* SPDX-License-Identifier: GPL-3.0-or-later
 * Madeira Converter Exception: see LICENSE-EXCEPTION.md
 * Match machine enumeration to the AMD64 support Wine already accepts on ARM64.
 * Only the isolated Steam UI session opts in; native identity remains ARM64. */
#ifndef IDECK_STEAM_UI_MACHINES_H
#define IDECK_STEAM_UI_MACHINES_H
static int ideck_advertise_amd64_guest(unsigned short *machines, unsigned int *count,
                                      unsigned int capacity, const char *session)
{
    unsigned int i;
    if (!session || session[0] != '1' || session[1] || !*count || *count >= capacity ||
        machines[0] != 0xaa64) return 0;
    for (i = 0; i < *count; i++) if (machines[i] == 0x8664) return 0;
    machines[(*count)++] = 0x8664;
    return 1;
}
#endif
