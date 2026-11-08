/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * A real orphan survives its initial process. No account or game data. */
static long call(long n,long a,long b,long c,long d,long e,long f){
    register long x0 __asm__("x0")=a,x1 __asm__("x1")=b,x2 __asm__("x2")=c;
    register long x3 __asm__("x3")=d,x4 __asm__("x4")=e,x5 __asm__("x5")=f,x8 __asm__("x8")=n;
    __asm__ volatile("svc #0":"+r"(x0):"r"(x1),"r"(x2),"r"(x3),"r"(x4),"r"(x5),"r"(x8):"memory","cc");return x0;
}
static int marker(const char *path){long fd=call(56,-100,(long)path,0x241,0600,0,0);if(fd<0)return 0;long n=call(64,fd,(long)"1\n",2,0,0,0);call(57,fd,0,0,0,0,0);return n==2;}
static void finish(int code){call(94,code,0,0,0,0,0);__builtin_unreachable();}
void _start(void){
    long mapping=call(222,0,4096,3,0x21,-1,0);if(mapping<0)finish(1);
    volatile int *ready=(volatile int *)mapping;*ready=0;
    long child=call(220,17,0,0,0,0,0);if(child<0)finish(2);
    if(!child){
        if(!marker("/child-started"))finish(3);__atomic_store_n(ready,1,__ATOMIC_RELEASE);
        struct {long sec,nsec;} delay={2,0};call(101,(long)&delay,0,0,0,0,0);
        finish(marker("/child-after-parent-exit")?0:4);
    }
    struct {long sec,nsec;} tick={0,10000000};
    for(int i=0;i<100&&!__atomic_load_n(ready,__ATOMIC_ACQUIRE);i++)call(101,(long)&tick,0,0,0,0,0);
    finish(__atomic_load_n(ready,__ATOMIC_ACQUIRE)&&marker("/initial-exiting")?0:5);
}
