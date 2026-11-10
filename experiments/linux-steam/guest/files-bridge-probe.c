/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * HOST control: real ARM64 exec into the actual compatibility wrapper. Synthetic
 * AppID480 and PE identity fixtures only; no Steam login, owned game or launch.
 */
static long call(long n,long a,long b,long c){register long x0 __asm__("x0")=a,x1 __asm__("x1")=b,x2 __asm__("x2")=c,x8 __asm__("x8")=n;__asm__ volatile("svc #0":"+r"(x0):"r"(x1),"r"(x2),"r"(x8):"memory","cc");return x0;}
#if PROBE_SHARED
#define INSTALL "/mnt/ideck/SteamLibrary/steamapps/common/Control Game"
#else
#define INSTALL "/Steam/steamapps/common/Control Game"
#endif
void _start(void){
    if(call(49,(long)INSTALL,0,0)<0){call(94,41,0,0);__builtin_unreachable();}
    const char *args[]={"/ideck-madeira","waitforexitandrun",INSTALL "/control.exe",0};
    const char *env[]={"STEAM_COMPAT_APP_ID=480","STEAM_COMPAT_INSTALL_PATH=" INSTALL,0};
    call(221,(long)"/ideck-madeira",(long)args,(long)env);call(94,42,0,0);__builtin_unreachable();
}
