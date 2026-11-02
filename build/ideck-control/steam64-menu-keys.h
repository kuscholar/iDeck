/* SPDX-License-Identifier: GPL-3.0-or-later
 * Madeira Converter Exception: see LICENSE-EXCEPTION.md
 * Opt-in Big Picture keyboard navigation from an unchanged XInput snapshot.
 * The caller must verify the actual foreground Steam Big Picture window.
 */
#ifndef IDECK_STEAM64_MENU_KEYS_H
#define IDECK_STEAM64_MENU_KEYS_H
#include <stdint.h>
struct steam64_menu_state { uint16_t previous; uint64_t repeat_at; };
enum { MENU_ACCEPT=1, MENU_BACK=2, MENU_LEFT=4, MENU_RIGHT=8, MENU_UP=16, MENU_DOWN=32 };
static unsigned steam64_menu_step(struct steam64_menu_state *state, uint16_t buttons,
                                 int16_t lx, int16_t ly, uint64_t now, int focused, int connected)
{
    if(!focused || !connected){state->previous=0;state->repeat_at=0;return 0;}
    unsigned current=0;
    if(buttons&0x1000)current|=MENU_ACCEPT;
    if(buttons&0x2000)current|=MENU_BACK;
    if((buttons&4)||lx < -16000)current|=MENU_LEFT;
    if((buttons&8)||lx > 16000)current|=MENU_RIGHT;
    if((buttons&1)||ly > 16000)current|=MENU_UP;
    if((buttons&2)||ly < -16000)current|=MENU_DOWN;
    unsigned edges=current&~state->previous;
    unsigned directions=current&(MENU_LEFT|MENU_RIGHT|MENU_UP|MENU_DOWN);
    if(directions && (edges&directions))state->repeat_at=now+400;
    else if(directions && state->repeat_at && now>=state->repeat_at){edges|=directions;state->repeat_at=now+120;}
    else if(!directions)state->repeat_at=0;
    state->previous=(uint16_t)current;
    return edges;
}
#endif
