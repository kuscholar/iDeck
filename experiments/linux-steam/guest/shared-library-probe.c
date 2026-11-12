/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * Real ARM64 Linux I/O control only: no Steam, account or game identity. */
static long call(long n,long a,long b,long c,long d,long e,long f){
 register long x0 __asm__("x0")=a,x1 __asm__("x1")=b,x2 __asm__("x2")=c;
 register long x3 __asm__("x3")=d,x4 __asm__("x4")=e,x5 __asm__("x5")=f,x8 __asm__("x8")=n;
 __asm__ volatile("svc #0":"+r"(x0):"r"(x1),"r"(x2),"r"(x3),"r"(x4),"r"(x5),"r"(x8):"memory","cc");return x0;
}
#define ROOT "/mnt/ideck/SteamLibrary/"
static void finish(int code){call(94,code,0,0,0,0,0);__builtin_unreachable();}
static int equal(const char *a,const char *b,unsigned n){for(unsigned i=0;i<n;i++)if(a[i]!=b[i])return 0;return 1;}
static int write_file(const char *path,const char *body){
 long f=call(56,-100,(long)path,0x241,0600,0,0);if(f<0)return 0;
 long n=call(64,f,(long)body,12,0,0,0);long synced=call(82,f,0,0,0,0,0);long closed=call(57,f,0,0,0,0,0);
 return n==12&&!synced&&!closed;
}
void _start(void){
 char data[12];long fd=call(56,-100,(long)ROOT "native-seed",0,0,0,0);if(fd<0)finish(1);
 long n=call(63,fd,(long)data,sizeof data,0,0,0);call(57,fd,0,0,0,0,0);
 int first=n==12&&equal(data,"native-first",12),second=n==12&&equal(data,"native-again",12);if(!first&&!second)finish(2);
 long made=call(34,-100,(long)ROOT "Guest Download",0700,0,0,0);if(made&&made!=-17)finish(3);
 if(!write_file(ROOT "Guest Download/staging",first?"guest-first!":"guest-again!"))finish(4);
 if(call(38,-100,(long)ROOT "Guest Download/staging",-100,(long)ROOT "Guest Download/installed",0,0))finish(5);
 long pid=call(220,17,0,0,0,0,0);if(pid<0)finish(6);
 if(!pid)finish(write_file(ROOT "child-write","child-joined")?0:7);
 int status=-1;if(call(260,pid,(long)&status,0,0,0,0)!=pid||status)finish(8);
 if(!write_file(ROOT "roundtrip-pass",first?"first-pass!!":"again-pass!!"))finish(9);
 finish(0);
}
