/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * Real interpreter coherence control: cached adjacent reads across private CoW.
 * Shared coordination is separate from the private data and fork sibling.
 */
typedef unsigned long u64;
#define PAGES 128
struct control {u64 warmed,changed,ack,stop,done,child_ok,failed;};
static struct control *control;
static volatile u64 *pages;
static int logfd;
extern long probe_clone(long,void *,void (*)(void));
static long call(long n,long a,long b,long c,long d,long e,long f){
    register long x0 __asm__("x0")=a,x1 __asm__("x1")=b,x2 __asm__("x2")=c;
    register long x3 __asm__("x3")=d,x4 __asm__("x4")=e,x5 __asm__("x5")=f,x8 __asm__("x8")=n;
    __asm__ volatile("svc #0":"+r"(x0):"r"(x1),"r"(x2),"r"(x3),"r"(x4),"r"(x5),"r"(x8):"memory","cc");return x0;
}
static void end(int status){call(93,status,0,0,0,0,0);__builtin_unreachable();}
static void mark(const char *s){unsigned n=0;while(s[n])n++;call(64,logfd,(long)s,n,0,0,0);}
static void delay(void){struct {long sec,nsec;} t={0,1000000};call(101,(long)&t,0,0,0,0,0);}
static int wait_at_least(u64 *p,u64 value){
    for(unsigned i=0;i<5000;i++){
        if(__atomic_load_n(p,__ATOMIC_ACQUIRE)>=value)return 1;
        delay();
    }
    return 0;
}
static volatile u64 *at(unsigned i){return pages+(u64)i*4096/sizeof(u64);}
static void reader(void){
    for(unsigned i=0;i<PAGES;i+=2){
        /* Warm the adjacent page before another thread changes its backing. */
        if(*at(i+1)!=i+2)end(31);
        __atomic_store_n(&control->warmed,i+2,__ATOMIC_RELEASE);
        if(!wait_at_least(&control->changed,i+2))end(32);
        if(*at(i+1)!=i+1002 || *at(i)!=i+1001){
            __atomic_store_n(&control->failed,1,__ATOMIC_RELEASE);end(33);
        }
        __atomic_store_n(&control->ack,i+2,__ATOMIC_RELEASE);
    }
    end(0);
}
void _start(void){
    logfd=call(56,-100,(long)"/cow-adjacent-results.txt",0x241,0600,0,0);if(logfd<0)end(2);
    long c=call(222,0,4096,3,0x21,-1,0),p=call(222,0,PAGES*4096,3,0x22,-1,0);
    if((c<0&&c>=-4095)||(p<0&&p>=-4095))end(3);
    control=(struct control *)c;pages=(volatile u64 *)p;
    for(unsigned i=0;i<PAGES;i++)*at(i)=i+1;
    long sibling=call(220,17,0,0,0,0,0);if(sibling<0)end(4);
    if(!sibling){
        if(!wait_at_least(&control->done,1))end(41);
        for(unsigned i=0;i<PAGES;i++)if(*at(i)!=i+1)end(42);
        __atomic_store_n(&control->child_ok,1,__ATOMIC_RELEASE);end(0);
    }
    long stack=call(222,0,65536,3,0x22,-1,0);if(stack<0&&stack>=-4095)end(5);
    long worker=probe_clone(0x100|17,(void *)(stack+65536),reader);if(worker<0)end(6);
    for(unsigned i=0;i<PAGES;i+=2){
        if(!wait_at_least(&control->warmed,i+2))end(7);
        *at(i)=i+1001;*at(i+1)=i+1002;
        __atomic_store_n(&control->changed,i+2,__ATOMIC_RELEASE);
        if(!wait_at_least(&control->ack,i+2))end(8);
    }
    __atomic_store_n(&control->done,1,__ATOMIC_RELEASE);
    int status=-1;if(call(260,worker,(long)&status,0,0,0,0)!=worker||status||control->failed)end(9);
    mark("adjacent-cached-read-across-CoW=PASS\n");
    if(call(260,sibling,(long)&status,0,0,0,0)!=sibling||status||!control->child_ok)end(10);
    mark("fork-sibling-isolation=PASS\n");
    for(unsigned i=0;i<PAGES;i++)if(*at(i)!=i+1001)end(11);
    if(call(215,p,PAGES*4096,0,0,0,0)||call(215,stack,65536,0,0,0,0))end(12);
    mark("joins-and-unmap=PASS\ncomplete=PASS\n");end(0);
}
