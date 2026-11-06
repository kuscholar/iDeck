/* SPDX-License-Identifier: GPL-3.0-or-later
 * Madeira Converter Exception: see LICENSE-EXCEPTION.md.
 * Owned AMD64 image: real code, writable data, large BSS and native Windows TLS. */
#include <windows.h>
#include <stdint.h>
_Static_assert(sizeof(void *)==8,"AMD64 only");
static volatile unsigned char payload[24*1024*1024];
static volatile uint64_t calls;
static _Thread_local uint64_t tls_value=UINT64_C(0x123456789abcdef0);
__declspec(dllexport) uint64_t image_tls(uint64_t value)
{
    uint64_t old=tls_value;tls_value=value;return old;
}
__declspec(dllexport) uint64_t image_step(uint64_t seed,uint64_t (*callback)(uint64_t))
{
    if (!calls && (payload[0] || payload[sizeof(payload)-1])) return 0;
    payload[0]=(unsigned char)seed;payload[sizeof(payload)-1]=(unsigned char)(seed>>8);
    calls++;
    return callback(seed)+calls+payload[0]+payload[sizeof(payload)-1];
}
BOOL WINAPI DllMain(HINSTANCE instance,DWORD reason,void *reserved)
{
    (void)instance;(void)reason;(void)reserved;return TRUE;
}
