/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * Minimal Linux ARM64 connect/accept ordering discriminator. No Steam, UI,
 * network access, credentials or game. Abstract AF_UNIX namespace only.
 */
static long call(long n,long a,long b,long c,long d,long e,long f){
    register long x0 __asm__("x0")=a,x1 __asm__("x1")=b,x2 __asm__("x2")=c;
    register long x3 __asm__("x3")=d,x4 __asm__("x4")=e,x5 __asm__("x5")=f,x8 __asm__("x8")=n;
    __asm__ volatile("svc #0":"+r"(x0):"r"(x1),"r"(x2),"r"(x3),"r"(x4),"r"(x5),"r"(x8):"memory","cc");return x0;
}
static int logfd;
static void mark(const char *s){unsigned long n=0;while(s[n])n++;call(64,logfd,(long)s,n,0,0,0);}
static void end(int code){call(94,code,0,0,0,0,0);__builtin_unreachable();}
void _start(void){
    logfd=call(56,-100,(long)"/connect-order.txt",0101|01000|1,0600,0,0);if(logfd<0)end(2);
    struct {unsigned short family;char path[108];} address={1,"\0ideck-late-accept"};
    long length=2+sizeof("\0ideck-late-accept")-1;
    long server=call(198,1,1,0,0,0,0),client=call(198,1,1,0,0,0,0);
    if(server<0||client<0||call(200,server,(long)&address,length,0,0,0)||call(201,server,4,0,0,0,0)){mark("setup=FAIL\n");end(3);}
    mark("listen-ready=PASS\n");
#if SERVER_ACCEPT_EARLY
    long child=call(220,17,0,0,0,0,0);if(child<0)end(4);
    if(!child){
        call(57,client,0,0,0,0,0);long accepted=call(202,server,0,0,0,0,0);if(accepted<0)end(5);
        char byte=0;if(call(63,accepted,(long)&byte,1,0,0,0)!=1||byte!='x')end(6);
        mark("acceptor-roundtrip=PASS\n");end(0);
    }
#endif
    mark("before-connect\n");
    long connected=call(203,client,(long)&address,length,0,0,0);
    if(connected){mark("connect=FAIL\n");end(7);}
    mark("connect-returned=PASS\n");
#if SERVER_ACCEPT_EARLY
    if(call(64,client,(long)"x",1,0,0,0)!=1)end(8);
    int status=-1;if(call(260,child,(long)&status,0,0,0,0)!=child||status)end(9);
#else
    mark("before-late-accept\n");
    if(call(202,server,0,0,0,0,0)<0)end(10);
#endif
    mark("complete=PASS\n");end(0);
}
