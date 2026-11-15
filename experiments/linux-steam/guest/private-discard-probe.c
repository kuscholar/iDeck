/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * Real ARM64 SVC-path control; no libc, Steam, credentials or file payload. */
static long call(long n,long a,long b,long c,long d,long e,long f){
    register long x0 __asm__("x0")=a,x1 __asm__("x1")=b,x2 __asm__("x2")=c;
    register long x3 __asm__("x3")=d,x4 __asm__("x4")=e,x5 __asm__("x5")=f,x8 __asm__("x8")=n;
    __asm__ volatile("svc #0":"+r"(x0):"r"(x1),"r"(x2),"r"(x3),"r"(x4),"r"(x5),"r"(x8):"memory","cc");return x0;
}
static int fd,failed;
static void report(const char *s,int good){unsigned n=0;while(s[n])n++;call(64,fd,(long)s,n,0,0,0);call(64,fd,(long)(good?"=PASS\n":"=FAIL\n"),6,0,0,0);failed+=!good;}
void _start(void){
    fd=call(56,-100,(long)"/private-discard-results.txt",0x241,0600,0,0);
    const long length=65536,base=0x4100000000L;
    long mapped=call(222,base,length,3,0x32,-1,0);report("private-map",mapped==base);
    if(mapped==base){
        volatile unsigned char *p=(volatile unsigned char *)mapped;
        for(long i=0;i<length;i+=4096){p[i]=53;p[i+4095]=79;}
        report("real-svc-DONTNEED",call(233,base,length,4,0,0,0)==0);
        int zero=1;for(long i=0;i<length;i+=4096)if(p[i]||p[i+4095])zero=0;
        report("discard-zero-edges",zero);
        report("unmap",call(215,base,length,0,0,0,0)==0);
    }
    call(94,failed?1:0,0,0,0,0,0);__builtin_unreachable();
}
