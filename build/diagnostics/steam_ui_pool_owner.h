/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Bounded, read-only PE data scan. Emit only exact known pool base matches;
 * no arbitrary data, stack contents, strings or authentication payloads.
 */
#ifndef MADEIRA_STEAM_UI_POOL_OWNER_H
#define MADEIRA_STEAM_UI_POOL_OWNER_H
#include <stdint.h>
#include <stddef.h>
#include <string.h>

static int steam_ui_pool_guarded(size_t size) { return size == 0x400010000ULL; }

typedef int (*steam_ui_pool_read_fn)(void *, uint64_t, void *, size_t);
typedef void (*steam_ui_pool_emit_fn)(void *, uint32_t, uint64_t, uint32_t, uint64_t);
static uint32_t steam_ui_pool_u32(const unsigned char *p) { uint32_t v; memcpy(&v,p,4); return v; }
static uint16_t steam_ui_pool_u16(const unsigned char *p) { uint16_t v; memcpy(&v,p,2); return v; }

static unsigned steam_ui_scan_pool_owner(uint64_t base, size_t image_size,
    steam_ui_pool_read_fn read, steam_ui_pool_emit_fn emit, void *context,
    const uint64_t *wanted, unsigned nwanted)
{
    unsigned char dos[64], nt[26], section[40], bytes[16384];
    unsigned matches = 0;
    size_t budget = 8u * 1024u * 1024u;
    if (!base || image_size < 4096 || base > UINT64_MAX-image_size || !nwanted || nwanted>8) return 0;
    if (!read(context,base,dos,sizeof(dos)) || dos[0]!='M' || dos[1]!='Z') return 0;
    uint32_t pe = steam_ui_pool_u32(dos+60);
    if (pe < 64 || pe > image_size-sizeof(nt) || !read(context,base+pe,nt,sizeof(nt)) ||
        memcmp(nt,"PE\0\0",4) || steam_ui_pool_u16(nt+4)!=0x8664 || steam_ui_pool_u16(nt+24)!=0x20b) return 0;
    unsigned nsections=steam_ui_pool_u16(nt+6), optional=steam_ui_pool_u16(nt+20);
    uint64_t table=(uint64_t)pe+24+optional;
    if (!nsections || nsections>96 || optional<2 || table>image_size || nsections*40>image_size-table) return 0;
    for (unsigned i=0;i<nsections && matches<8 && budget;i++) {
        if (!read(context,base+table+i*40,section,sizeof(section))) continue;
        uint32_t rva=steam_ui_pool_u32(section+12), length=steam_ui_pool_u32(section+8);
        if (!(steam_ui_pool_u32(section+36)&0x80000000u) || rva<4096 || rva>image_size || length>image_size-rva) continue;
        uint32_t last_rva=0;uint64_t last_value=0;
        for (uint64_t off=(rva+7ull)&~7ull; off+8<=(uint64_t)rva+length && matches<8 && budget;) {
            size_t count=(size_t)((uint64_t)rva+length-off);
            if(count>sizeof(bytes))count=sizeof(bytes);
            if(count>budget)count=budget;
            if(count<8)break;
            budget-=count;
            if (!read(context,base+off,bytes,count)) {last_value=0;off+=count;continue;}
            for (size_t b=0;b+8<=count && matches<8;b+=8) {
                uint64_t value;memcpy(&value,bytes+b,8);
                for (unsigned w=0;w<nwanted;w++) if (value==wanted[w]) {
                    uint32_t here=(uint32_t)(off+b);
                    if(last_value && value!=last_value && here-last_rva<=512) {
                        emit(context,last_rva,last_value,here,value);matches++;
                    }
                    last_rva=here;last_value=value;break;
                }
            }
            off+=count;
        }
    }
    return matches;
}
#endif
