/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
static long call(long n,long a,long b,long c,long d,long e,long f) {
    register long x0 __asm__("x0")=a,x1 __asm__("x1")=b,x2 __asm__("x2")=c;
    register long x3 __asm__("x3")=d,x4 __asm__("x4")=e,x5 __asm__("x5")=f,x8 __asm__("x8")=n;
    __asm__ volatile("svc #0":"+r"(x0):"r"(x1),"r"(x2),"r"(x3),"r"(x4),"r"(x5),"r"(x8):"memory","cc");return x0;
}
static int output,failures;
static void report(const char *s,int ok) {
    unsigned n=0;while(s[n])n++;
    call(64,output,(long)s,n,0,0,0);call(64,output,(long)(ok?"=PASS\n":"=FAIL\n"),6,0,0,0);failures+=!ok;
}
void _start(void) {
    output=(int)call(56,-100,(long)"/lazy-results.txt",0101|01000,0600,0,0);
    long source=call(56,-100,(long)"/source",0102|01000,0600,0,0);
    call(64,source,(long)"Q",1,0,0,0);
    const long base=0x4100001000L,size=512L*1024*1024+8192;
    long address=call(222,base,size,3,0x32,-1,0); // Private anonymous FIXED, unaligned native group.
    report("unaligned-reservation",address==base);
    if(address==base) {
        volatile unsigned char *p=(volatile unsigned char *)address;
        report("demand-zero-edges",p[0]==0&&p[4096]==0&&p[8192]==0&&p[size-1]==0);
        p[0]=17;p[4096]=23;p[8192]=31;p[size-1]=47;
        report("independent-page-bytes",p[0]==17&&p[4096]==23&&p[8192]==31&&p[size-1]==47);
        report("protect-first-readonly",call(226,base,4096,1,0,0,0)==0);
        call(62,source,0,0,0,0,0);
        report("readonly-kernel-write-refused",call(63,source,base,1,0,0,0)==-14);
        report("protect-middle-none",call(226,base+4096,4096,0,0,0,0)==0);
        report("none-kernel-read-refused",call(64,source,base+4096,1,0,0,0)==-14);
        p[8192]=37;report("neighbor-after-protection",p[0]==17&&p[8192]==37);
        report("partial-unmap",call(215,base+8192,4096,0,0,0,0)==0);
        report("hole-kernel-read-refused",call(64,source,base+8192,1,0,0,0)==-14);
        report("fixed-replace-hole",call(222,base+8192,4096,3,0x32,-1,0)==base+8192&&p[8192]==0);
        report("restore-protection",call(226,base,8192,3,0,0,0)==0&&p[0]==17&&p[4096]==23);
        p[8192]=61;
        long pid=call(220,17,0,0,0,0,0);
        if(pid==0){p[0]=99;p[8192]=101;p[size-1]=103;call(94,29,0,0,0,0,0);__builtin_unreachable();}
        int status=0;long waited=call(260,pid,(long)&status,0,0,0,0);
        report("fork-child-wait",pid>0&&waited==pid&&status==(29<<8));
        report("private-cow-survives",p[0]==17&&p[8192]==61&&p[size-1]==47);
        report("full-unmap-after-split",call(215,base,size,0,0,0,0)==0);
        report("lazy-none-reservation",call(222,base,size,0,0x32,-1,0)==base);
        int first=call(226,base,4096,3,0,0,0)==0;
        if(first)p[0]=73;
        report("enable-only-first-page",first&&p[0]==73);
        report("adjacent-lazy-none-stays-inaccessible",call(64,source,base+4096,1,0,0,0)==-14);
        int tail=call(226,base+size-4096,4096,3,0,0,0)==0;
        report("enable-only-tail-and-free",tail&&p[size-1]==0&&p[0]==73&&call(215,base,size,0,0,0,0)==0);
    }
    report("complete",failures==0);
    call(94,failures?1:0,0,0,0,0,0);__builtin_unreachable();
}
