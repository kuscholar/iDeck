/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * Real ARM64 workload long enough for the native profiler to sample. No Steam.
 */
static long call(long n,long a,long b,long c){
    register long x0 __asm__("x0")=a,x1 __asm__("x1")=b,x2 __asm__("x2")=c,x8 __asm__("x8")=n;
    __asm__ volatile("svc #0":"+r"(x0):"r"(x1),"r"(x2),"r"(x8):"memory","cc");return x0;
}
void _start(void){
    struct {long sec,nsec;} first,last;
    if(call(113,1,(long)&first,0))goto failure;
    do{
        for(volatile unsigned i=0;i<1000;i++){}
        if(call(113,1,(long)&last,0))goto failure;
    }while((last.sec-first.sec)*1000000000L+last.nsec-first.nsec<200000000L);
    call(94,0,0,0);__builtin_unreachable();
failure:
    call(94,1,0,0);__builtin_unreachable();
}
