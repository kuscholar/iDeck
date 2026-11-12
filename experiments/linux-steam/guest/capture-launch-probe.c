/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * Actual ARM64 device-write/read control, NOT a game or Steam login. */
#include "LaunchProtocol.h"
static long call(long n,long a,long b,long c,long d,long e,long f){
 register long x0 __asm__("x0")=a,x1 __asm__("x1")=b,x2 __asm__("x2")=c;
 register long x3 __asm__("x3")=d,x4 __asm__("x4")=e,x5 __asm__("x5")=f,x8 __asm__("x8")=n;
 __asm__ volatile("svc #0":"+r"(x0):"r"(x1),"r"(x2),"r"(x3),"r"(x4),"r"(x5),"r"(x8):"memory","cc");return x0;
}
static void finish(int code){call(94,code,0,0,0,0,0);__builtin_unreachable();}
static unsigned copy(char *out,const char *in){unsigned n=0;do{out[n]=in[n];}while(in[n++]);return n;}
static struct ideck_launch_request r={.magic=IDECK_LAUNCH_MAGIC,.version=IDECK_LAUNCH_VERSION,.appid=0x70000001,.verb=1,.argc=3};
void _start(void){
 copy(r.install,IDECK_LAUNCH_ROOT "Bridge Probe");copy(r.executable,IDECK_LAUNCH_ROOT "Bridge Probe/probe.exe");copy(r.working,r.install);
 unsigned n=copy(r.arguments,r.executable);n+=copy(r.arguments+n,"--level");n+=copy(r.arguments+n,"1 2");r.argument_bytes=n;
 long fd=call(56,-100,(long)"/dev/ideck-madeira",2,0,0,0);if(fd<0)finish(1);
 if(call(64,fd,(long)&r,sizeof r,0,0,0)!=sizeof r)finish(2);
 struct ideck_launch_response response;
 if(call(63,fd,(long)&response,sizeof response,0,0,0)!=sizeof response)finish(3);
 if(response.magic!=IDECK_LAUNCH_MAGIC||response.version!=IDECK_LAUNCH_VERSION||response.appid!=r.appid||response.result!=125)finish(4);
 if(call(57,fd,0,0,0,0,0))finish(5);
 finish(0);
}
