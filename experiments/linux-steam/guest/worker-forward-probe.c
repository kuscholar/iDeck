/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * Runs only a registered, harmless native worker-control handler. */
static long call(long number,long a,long b,long c){
    register long x0 __asm__("x0")=a,x1 __asm__("x1")=b,x2 __asm__("x2")=c,x8 __asm__("x8")=number;
    __asm__ volatile("svc #0":"+r"(x0):"r"(x1),"r"(x2),"r"(x8):"memory","cc");return x0;
}
void _start(void){
    const char *argv[]={"/worker-control",0},*env[]={0};
    call(221,(long)argv[0],(long)argv,(long)env);
    call(94,91,0,0);__builtin_unreachable();
}
