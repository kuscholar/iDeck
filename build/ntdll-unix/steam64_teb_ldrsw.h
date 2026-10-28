/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Narrow native iOS TEB adaptation; never changes FEX or a guest binary.
 */
#ifndef MADEIRA_STEAM64_TEB_LDRSW_H
#define MADEIRA_STEAM64_TEB_LDRSW_H
#include <stdint.h>
#include <string.h>
static int steam64_teb_ldrsw_matches(const char *session, const char *prefix,
                                    uint32_t insn, uint64_t x18, uint64_t fault)
{
    static const char suffix[]="/wine-steam64";
    size_t n=prefix?strlen(prefix):0;
    return session&&!strcmp(session,"1")&&n>=sizeof(suffix)-1&&
           !strcmp(prefix+n-(sizeof(suffix)-1),suffix)&&x18==0&&fault==0x180c&&
           (insn&0xffc00000)==0xb9800000&&((insn>>5)&31)==18&&
           (((insn>>10)&4095)*4)==fault;
}
static uint64_t steam64_teb_ldrsw_value(int32_t value)
{
    return (uint64_t)(int64_t)value;
}
#endif
