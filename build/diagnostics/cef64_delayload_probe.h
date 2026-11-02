/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Read-only discriminator for the exact pinned CEF126 x64 delay-load trap.
 * Decode documented DelayLoadInfo fields only; never dump stack payloads.
 */
#ifndef IDECK_CEF64_DELAYLOAD_PROBE_H
#define IDECK_CEF64_DELAYLOAD_PROBE_H
#include <stdint.h>
#include <stddef.h>
#include <string.h>

typedef int (*ideck_cef_read)(uint64_t, void *, size_t);
struct ideck_cef_delay_failure {
    uint32_t error, reason, by_name, ordinal;
    char module[96], symbol[128];
};
static uint32_t ideck_cef_u32(const unsigned char *p)
{ uint32_t v; memcpy(&v,p,sizeof(v));return v; }
static uint64_t ideck_cef_u64(const unsigned char *p)
{ uint64_t v; memcpy(&v,p,sizeof(v));return v; }
static int ideck_cef_name(ideck_cef_read read, uint64_t address, char *out, size_t cap, int module)
{
    if(address<0x10000 || address>UINT64_MAX-cap)return 0;
    for(size_t i=0;i<cap;i++){
        unsigned char c;
        if(!read(address+i,&c,1))return 0;
        if(!c){
            if(!i)return 0;
            out[i]=0;
            if (!module) return 1;
            if (i<=4 || out[i-4]!='.') return 0;
            char ext[4]={0};
            for(unsigned j=0;j<3;j++){
                char e=out[i-3+j];ext[j]=e>='A'&&e<='Z'?e+('a'-'A'):e;
            }
            return !strcmp(ext,"dll") || !strcmp(ext,"cpl");
        }
        if(!((c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='_'||
             c=='.'||c=='-'||(!module&&(c=='?'||c=='@'||c=='$'))))return 0;
        out[i]=(char)c;
    }
    return 0;
}
static int ideck_cef_delay_probe(uint64_t rip, uint64_t rsp, ideck_cef_read read,
                               struct ideck_cef_delay_failure *out)
{
    const uint64_t trap=UINT64_C(0x59efb96);
    unsigned char dos[64],pe[88],code[9],saved[16],info[72];
    static const unsigned char expected[]={0xe8,0xcb,0x1a,0xb1,0xfd,0xcc,0xcc,0x0f,0x0b};
    if(rip<trap+0x10000 || rsp<0x10000 || rsp>UINT64_MAX-0x170)return 0;
    uint64_t base=rip-trap;
    if(!read(base,dos,sizeof(dos)) || dos[0]!='M'||dos[1]!='Z')return 0;
    uint32_t off=ideck_cef_u32(dos+60);
    if(off>0x1000 || !read(base+off,pe,sizeof(pe)) || ideck_cef_u32(pe)!=0x4550 ||
       pe[4]!=0x64 || pe[5]!=0x86 || ideck_cef_u32(pe+8)!=0x66956fee ||
       ideck_cef_u32(pe+80)!=0xd3ca000 ||
       !read(rip-6,code,sizeof(code)) || memcmp(code,expected,sizeof(code)))return 0;
    /* This exact prolog saved caller rdi (reason) at+158, rsi (DelayLoadInfo*)
     * at+160. The hook's documented x64 structure has szDll+18, import kind+20,
     * name/ordinal+28, and dwLastError+40. Refuse all other layouts. */
    if(!read(rsp+0x158,saved,sizeof(saved)))return 0;
    uint64_t address=ideck_cef_u64(saved+8);
    if(address<0x10000 || address>UINT64_MAX-sizeof(info) ||
       !read(address,info,sizeof(info)) || ideck_cef_u32(info)!=sizeof(info))return 0;
    struct ideck_cef_delay_failure result={0};
    result.reason=ideck_cef_u32(saved);
    result.error=ideck_cef_u32(info+0x40);
    result.by_name=ideck_cef_u32(info+0x20);
    if((result.reason!=3&&result.reason!=4)||result.by_name>1 ||
       !ideck_cef_name(read,ideck_cef_u64(info+0x18),result.module,sizeof(result.module),1))return 0;
    if(result.by_name){
        if(!ideck_cef_name(read,ideck_cef_u64(info+0x28),result.symbol,sizeof(result.symbol),0))return 0;
    }else result.ordinal=ideck_cef_u32(info+0x28);
    *out=result;
    return 1;
}
#endif
