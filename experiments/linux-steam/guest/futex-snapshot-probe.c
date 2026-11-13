/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
static long call(long n,long a,long b,long c,long d,long e,long f){
    register long x0 __asm__("x0")=a,x1 __asm__("x1")=b,x2 __asm__("x2")=c,x3 __asm__("x3")=d;
    register long x4 __asm__("x4")=e,x5 __asm__("x5")=f,x8 __asm__("x8")=n;
    __asm__ volatile("svc #0":"+r"(x0):"r"(x1),"r"(x2),"r"(x3),"r"(x4),"r"(x5),"r"(x8):"memory","cc");return x0;
}
static int word;
static char stack[65536] __attribute__((aligned(16)));
extern long probe_clone(long,void *,void (*)(void));
static void worker(void){
    struct {long sec,nsec;} interval={0,1000000};
    for(unsigned i=0;i<20000;i++){
        long fd=call(56,-100,(long)"/release",0,0,0,0);
        if(fd>=0){call(57,fd,0,0,0,0,0);__atomic_store_n(&word,1,__ATOMIC_SEQ_CST);call(98,(long)&word,129,1,0,0,0);call(93,0,0,0,0,0,0);__builtin_unreachable();}
        call(101,(long)&interval,0,0,0,0,0);
    }
    call(94,91,0,0,0,0,0);__builtin_unreachable();
}
void _start(void){
    long child=probe_clone(0x10f00,stack+sizeof stack,worker);
    if(child<0){call(94,92,0,0,0,0,0);__builtin_unreachable();}
    long ready=call(56,-100,(long)"/wait-ready",0100|1|0200,0600,0,0);
    if(ready>=0)call(57,ready,0,0,0,0,0);
    long result=call(98,(long)&word,128,0,0,0,0);
    // Host releases only AFTER a real blocked-futex snapshot was captured.
    int success=result==0&&__atomic_load_n(&word,__ATOMIC_SEQ_CST)==1;
    call(94,success?0:93,0,0,0,0,0);__builtin_unreachable();
}
