/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * Freestanding ARM64 control: identical 64 MiB write/verify, two reservation sizes.
 * No Steam files, account state, JIT, or native allocator changes. */
#ifndef RESERVE_MIB
#error explicit RESERVE_MIB required
#endif
static long call(long n,long a,long b,long c,long d,long e,long f) {
    register long x0 __asm__("x0")=a,x1 __asm__("x1")=b,x2 __asm__("x2")=c;
    register long x3 __asm__("x3")=d,x4 __asm__("x4")=e,x5 __asm__("x5")=f,x8 __asm__("x8")=n;
    __asm__ volatile("svc #0":"+r"(x0):"r"(x1),"r"(x2),"r"(x3),"r"(x4),"r"(x5),"r"(x8):"memory","cc");
    return x0;
}
static void finish(long status) __attribute__((noreturn));
static void finish(long status) {call(94,status,0,0,0,0,0);__builtin_unreachable();}
static void marker(const char *path) {
    long fd=call(56,-100,(long)path,0100|0200|1,0600,0,0);
    if(fd<0)finish(10);
    if(call(64,fd,(long)"1",1,0,0,0)!=1)finish(11);
    call(57,fd,0,0,0,0,0);
}
static void await(const char *path) {
    for(unsigned i=0;i<15000;i++) {
        long fd=call(56,-100,(long)path,0,0,0,0);
        if(fd>=0) {call(57,fd,0,0,0,0,0);return;}
        if(fd!=-2)finish(12);
        struct {long sec,nsec;} delay={0,2000000};
        call(101,(long)&delay,0,0,0,0,0);
    }
    finish(13);
}
void _start(void) {
    const long size=(long)RESERVE_MIB*1024*1024;
    long address=call(222,0x4100000000L,size,3,0x32,-1,0);
    if(address<0 && address>=-4095)finish(14);
    volatile unsigned char *p=(volatile unsigned char *)address;
    marker("/memory-reserved");await("/start-touch");
    for(unsigned i=0;i<16384;i++) p[(long)i*4096]=(unsigned char)(5+i%241);
    for(unsigned i=0;i<16384;i++) if(p[(long)i*4096]!=(unsigned char)(5+i%241))finish(15);
    marker("/memory-ready");
#if TEST_DISCARD
    await("/start-discard");
    if(call(233,address,64L*1024*1024,4,0,0,0)!=0)finish(17);
    marker("/memory-discarded");await("/release");
    for(unsigned i=0;i<16384;i++)if(p[(long)i*4096]!=0)finish(18);
#else
    await("/release");
#endif
    if(call(215,address,size,0,0,0,0)!=0)finish(16);
    marker("/memory-unmapped");finish(0);
}
