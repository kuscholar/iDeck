/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * Real ARM64 Linux syscall integration, not a host mock or device claim.
 */
static long call(long n,long a,long b,long c,long d,long e,long f) {
    register long x0 __asm__("x0")=a,x1 __asm__("x1")=b,x2 __asm__("x2")=c;
    register long x3 __asm__("x3")=d,x4 __asm__("x4")=e,x5 __asm__("x5")=f,x8 __asm__("x8")=n;
    __asm__ volatile("svc #0" : "+r"(x0) : "r"(x1),"r"(x2),"r"(x3),"r"(x4),"r"(x5),"r"(x8) : "memory","cc");
    return x0;
}
static long c3(long n,long a,long b,long c) {return call(n,a,b,c,0,0,0);}
static int failures;
static void out(const char *s) {unsigned n=0;while(s[n])n++;c3(64,1,(long)s,n);}
static void number(long n) {char b[24];unsigned at=sizeof b;unsigned long v=n<0?(unsigned long)-n:(unsigned long)n;do{b[--at]=(char)('0'+v%10);v/=10;}while(v);if(n<0)b[--at]='-';c3(64,1,(long)(b+at),sizeof b-at);out("\n");}
static void report(const char *name,int ok) {out(name);out(ok ? "=PASS\n":"=FAIL\n");if(!ok)failures++;}
static int make(int p[2],int flags) {return c3(59,(long)p,flags,0)==0;}
static void closefd(int fd) {c3(57,fd,0,0);}
static void closepair(int p[2]) {closefd(p[0]);closefd(p[1]);}
struct pollfd {int fd;short events,revents;};
struct timespec {long sec,nsec;};
static int ready(int fd,short events) {
    struct pollfd p={fd,events,0};struct timespec zero={0,0};
    long n=call(73,(long)&p,1,(long)&zero,0,8,0);
    return n>=0?p.revents:-1;
}
struct epoll_event {unsigned events,padding;unsigned long data;};
static long epwait(int ep,struct epoll_event *event,int ms) {return call(22,ep,(long)event,1,ms,0,8);}
static char payload[8193],buffer[8193];
__attribute__((noreturn)) void _start(void) {
    int p[2]={-1,-1};int flags=0x90800;
    for(unsigned i=0;i<sizeof payload;i++)payload[i]=(char)(i%97+1);
    int ok=make(p,flags);
    if(!ok){report("packet-create",0);c3(94,1,0,0);__builtin_unreachable();}
    ok=c3(64,p[1],(long)payload,8193)==8193 && c3(63,p[0],(long)buffer,sizeof buffer)==4096;
    for(unsigned i=0;i<4096&&ok;i++)ok=buffer[i]==payload[i];
    ok=ok&&c3(63,p[0],(long)buffer,sizeof buffer)==4096;
    for(unsigned i=0;i<4096&&ok;i++)ok=buffer[i]==payload[i+4096];
    ok=ok&&c3(63,p[0],(long)buffer,sizeof buffer)==1&&buffer[0]==payload[8192];
    report("packet-large-write-split",ok);closepair(p);

    ok=make(p,flags)&&c3(64,p[1],(long)"abc",3)==3&&c3(64,p[1],(long)"de",2)==2&&
        c3(63,p[0],(long)buffer,1)==1&&buffer[0]=='a'&&c3(63,p[0],(long)buffer,8)==2&&buffer[0]=='d'&&
        c3(64,p[1],(long)"",0)==0&&c3(63,p[0],(long)buffer,1)==-11;
    report("packet-short-read-discard-zero-nonblock",ok);closepair(p);

    int available=-1;
    ok=make(p,flags)&&c3(64,p[1],(long)"abc",3)==3&&c3(64,p[1],(long)"de",2)==2&&
        c3(29,p[0],0x541b,(long)&available)==0&&available==5&&c3(63,p[0],(long)buffer,1)==1&&
        c3(29,p[1],0x541b,(long)&available)==0&&available==2&&c3(63,p[0],(long)buffer,8)==2&&
        c3(29,p[0],0x541b,(long)&available)==0&&available==0;
    report("packet-fionread-payload-not-native-overhead",ok);closepair(p);

    ok=make(p,flags);long copy=c3(23,p[1],0,0);closefd(p[1]);
    ok=ok&&copy>=0&&!(ready(p[0],1)&16)&&c3(64,copy,(long)"x",1)==1;
    closefd((int)copy);
    ok=ok&&(ready(p[0],1)&16)&&c3(63,p[0],(long)buffer,8)==1&&c3(63,p[0],(long)buffer,8)==0;
    report("packet-dup-queued-eof-hup",ok);closefd(p[0]);

    ok=make(p,flags)&&c3(25,p[0],1,0)==1;
    long old=c3(25,p[1],3,0);
    ok=ok&&(old&0x10000)&&!(c3(25,p[0],3,0)&0x10000)&&c3(25,p[1],4,old&~0x800)==0&&!(c3(25,p[1],3,0)&0x800)&&
        c3(25,p[1],4,old)==0&&c3(25,p[1],4,old&~0x10000)==-95&&(c3(25,p[1],3,0)&0x10000);
    report("packet-fcntl-flags-explicit-conversion-limit",ok);closepair(p);

    ok=make(p,flags);long ep=c3(20,0,0,0);struct epoll_event event={1,0,0x12345678};
    ok=ok&&ep>=0&&call(21,ep,1,p[0],(long)&event,0,0)==0&&epwait((int)ep,&event,0)==0&&
        c3(64,p[1],(long)"a",1)==1&&epwait((int)ep,&event,100)==1&&event.data==0x12345678&&(event.events&1)&&
        c3(63,p[0],(long)buffer,8)==1&&epwait((int)ep,&event,0)==0;
    closefd(p[1]);ok=ok&&epwait((int)ep,&event,100)==1&&(event.events&16);
    report("packet-epoll-read-drain-hup",ok);closefd((int)ep);closefd(p[0]);

    ok=make(p,flags);unsigned count=0;long written=0;
    do{written=c3(64,p[1],(long)payload,4096);if(written==4096)count++;}while(written==4096&&count<1024);
    long drained=c3(63,p[0],(long)buffer,sizeof buffer);int writable=ready(p[1],4);long refilled=c3(64,p[1],(long)payload,4096);
    out("capacity-count=");number(count);out("capacity-error=");number(written);out("capacity-drained=");number(drained);out("capacity-ready=");number(writable);out("capacity-refill=");number(refilled);
    ok=ok&&count>0&&count<1024&&written==-11&&drained==4096&&(writable&4)&&refilled==4096;
    report("packet-bounded-backpressure-refill",ok);closepair(p);

    struct {unsigned long handler,flags,restorer,mask;} ignore={1,0,0,0};
    ok=call(134,13,(long)&ignore,0,8,0,0)==0&&make(p,flags);closefd(p[0]);
    ok=ok&&(ready(p[1],4)&8)&&c3(64,p[1],(long)"x",1)==-32;
    report("packet-closed-reader-epipe",ok);closefd(p[1]);

    ok=make(p,flags);
    for(unsigned i=0;i<16;i++)ok=ok&&c3(64,p[1],(long)payload,4096)==4096;
    closefd(p[0]);int closed_ready=ready(p[1],4);
    ok=ok&&(closed_ready&8)&&!(closed_ready&4)&&c3(64,p[1],(long)"x",1)==-32;
    report("packet-full-closed-reader-poll-mask",ok);closefd(p[1]);

    ok=make(p,0x90000);long pid=call(220,17,0,0,0,0,0);
    if(pid==0){closefd(p[0]);c3(64,p[1],(long)"f",1);closefd(p[1]);c3(94,0,0,0);__builtin_unreachable();}
    closefd(p[1]);int status=-1;
    ok=ok&&pid>0&&c3(63,p[0],(long)buffer,8)==1&&buffer[0]=='f'&&c3(63,p[0],(long)buffer,8)==0&&
        call(260,pid,(long)&status,0,0,0,0)==pid&&status==0;
    report("packet-fork-shared-lifetime",ok);closefd(p[0]);

    ok=make(p,flags);ep=c3(20,0,0,0);event=(struct epoll_event){1,0,0xabc};
    ok=ok&&ep>=0&&call(21,ep,1,p[0],(long)&event,0,0)==0;
    pid=call(220,17,0,0,0,0,0);
    if(pid==0){closefd(p[0]);closefd((int)ep);struct timespec pause={0,30000000};c3(101,(long)&pause,0,0);c3(64,p[1],(long)"w",1);closefd(p[1]);c3(94,0,0,0);__builtin_unreachable();}
    closefd(p[1]);status=-1;
    ok=ok&&pid>0&&epwait((int)ep,&event,1000)==1&&(event.events&1)&&c3(63,p[0],(long)buffer,8)==1&&buffer[0]=='w'&&
        call(260,pid,(long)&status,0,0,0,0)==pid&&status==0;
    report("packet-blocked-epoll-wakeup",ok);closefd((int)ep);closefd(p[0]);

    ok=make(p,0x90000);
    for(unsigned i=0;i<16;i++)ok=ok&&c3(64,p[1],(long)payload,4096)==4096;
    pid=call(220,17,0,0,0,0,0);
    if(pid==0){closefd(p[1]);struct timespec pause={0,30000000};c3(101,(long)&pause,0,0);int child_ok=1;for(unsigned i=0;i<17;i++)child_ok=child_ok&&c3(63,p[0],(long)buffer,8193)==4096;closefd(p[0]);c3(94,child_ok?0:1,0,0);__builtin_unreachable();}
    closefd(p[0]);status=-1;
    ok=ok&&pid>0&&c3(64,p[1],(long)payload,4096)==4096&&call(260,pid,(long)&status,0,0,0,0)==pid&&status==0;
    report("packet-blocked-writer-space-wakeup",ok);closefd(p[1]);

    ok=make(p,0x90000);
    for(unsigned i=0;i<16;i++)ok=ok&&c3(64,p[1],(long)payload,4096)==4096;
    pid=call(220,17,0,0,0,0,0);
    if(pid==0){closefd(p[0]);c3(64,p[1],(long)payload,4096);c3(94,9,0,0);__builtin_unreachable();}
    struct timespec pause={0,30000000};c3(101,(long)&pause,0,0);status=-1;
    ok=ok&&pid>0&&c3(129,pid,15,0)==0&&call(260,pid,(long)&status,0,0,0,0)==pid&&(status&127)==15;
    report("packet-blocked-writer-signal-cancel",ok);closepair(p);

    ok=1;
    for(unsigned i=0;i<32;i++)ok=ok&&c3(59,1,flags,0)==-14;
    ok=ok&&make(p,flags)&&p[0]==3&&p[1]==4;
    report("packet-failed-create-cleanup",ok);closepair(p);

    struct {unsigned long soft,hard;} original_limit={0,0},limited={4,0};
    ok=c3(163,7,(long)&original_limit,0)==0;limited.hard=original_limit.hard;
    ok=ok&&c3(164,7,(long)&limited,0)==0;
    for(unsigned i=0;i<16;i++)ok=ok&&c3(59,(long)p,flags,0)==-24;
    ok=ok&&c3(164,7,(long)&original_limit,0)==0&&make(p,flags)&&p[0]==3&&p[1]==4;
    report("packet-partial-install-emfile-cleanup",ok);closepair(p);
    report("complete",failures==0);
    c3(94,failures?1:0,0,0);__builtin_unreachable();
}
