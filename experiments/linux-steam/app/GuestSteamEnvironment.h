/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#ifndef IDECK_GUEST_STEAM_ENVIRONMENT_H
#define IDECK_GUEST_STEAM_ENVIRONMENT_H
#ifndef IDECK_LAB_PTHREAD_STACK_CACHE_OFF
#define IDECK_LAB_PTHREAD_STACK_CACHE_OFF 0
#endif
#if IDECK_LAB_PTHREAD_STACK_CACHE_OFF != 0 && IDECK_LAB_PTHREAD_STACK_CACHE_OFF != 1
#error Select only the explicit default-off guest libc policy
#endif
/* Constant guest-only environment. Never import Darwin environment values or
 * change stack sizes, RLIMITs, allocator capacities, Wine/FEX or credentials.
 * The default bytes match the original initial and retained Steam env arrays.
 */
static inline const char *ideck_guest_steam_environment(void){
    static const char env[]="HOME=/root\0PATH=/usr/bin:/bin\0LANG=C\0STEAM_RUNTIME=1\0"
#if IDECK_LAB_PTHREAD_STACK_CACHE_OFF
        "GLIBC_TUNABLES=glibc.pthread.stack_cache_size=0\0"
#endif
        "LD_LIBRARY_PATH=/Steam/steamrtarm64:/Steam/steamrtarm64/libs:/lib/aarch64-linux-gnu\0";
    return env;
}
#endif
