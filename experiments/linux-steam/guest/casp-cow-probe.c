/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * Real ARM64 CASPAL64 + fork CoW + CLONE_VM contenders. No Steam/rootfs/login.
 * Link with the existing freestanding clone.S trampoline. A native timeout is
 * failure evidence, never a clean guest teardown result.
 */
#define PAGES 128
typedef unsigned long u64;
struct pair {u64 lo,hi;} __attribute__((aligned(16)));
struct control {u64 done,stop,child_ok,failed,ready[3];struct pair hot;};
static struct control *control;
static volatile struct pair *pages;
static int logfd;
extern long probe_clone(long flags,void *stack,void (*entry)(void));
static long call(long n,long a,long b,long c,long d,long e,long f){
    register long x0 __asm__("x0")=a,x1 __asm__("x1")=b,x2 __asm__("x2")=c;
    register long x3 __asm__("x3")=d,x4 __asm__("x4")=e,x5 __asm__("x5")=f,x8 __asm__("x8")=n;
    __asm__ volatile("svc #0":"+r"(x0):"r"(x1),"r"(x2),"r"(x3),"r"(x4),"r"(x5),"r"(x8):"memory","cc");return x0;
}
static void mark(const char *s){unsigned n=0;while(s[n])n++;call(64,logfd,(long)s,n,0,0,0);}
static void end(int status){call(93,status,0,0,0,0,0);__builtin_unreachable();}
static void delay(void){struct {long sec,nsec;} tick={0,2000000};call(101,(long)&tick,0,0,0,0,0);}
static void casp(volatile struct pair *address,u64 *oldlo,u64 *oldhi,u64 newlo,u64 newhi){
    register u64 x0 __asm__("x0")=*oldlo,x1 __asm__("x1")=*oldhi;
    register u64 x2 __asm__("x2")=newlo,x3 __asm__("x3")=newhi,x4 __asm__("x4")=(u64)address;
    __asm__ volatile("caspal x0, x1, x2, x3, [x4]":"+r"(x0),"+r"(x1):"r"(x2),"r"(x3),"r"(x4):"memory","cc");
    *oldlo=x0;*oldhi=x1;
}
static volatile struct pair *at(unsigned i){return (volatile struct pair *)((unsigned char *)pages+(u64)i*4096);}
static void spinner(unsigned n){
    __atomic_store_n(&control->ready[n],1,__ATOMIC_RELEASE);
    while(!__atomic_load_n(&control->stop,__ATOMIC_ACQUIRE)){
        u64 lo=0,hi=0;casp(&control->hot,&lo,&hi,0,0);
        if(lo||hi){__atomic_store_n(&control->failed,1,__ATOMIC_RELEASE);end(21);}
    }
    end(0);
}
static void spin0(void){spinner(0);}static void spin1(void){spinner(1);}static void spin2(void){spinner(2);}
static void writer(void){
    for(unsigned i=0;i<3;i++)while(!__atomic_load_n(&control->ready[i],__ATOMIC_ACQUIRE))delay();
    mark("cow-casp-start\n");
    for(unsigned i=0;i<PAGES;i++){
        u64 lo=i+1,hi=~(u64)i;casp(at(i),&lo,&hi,i+1000,i+2000);
        if(lo!=i+1||hi!=~(u64)i){__atomic_store_n(&control->failed,1,__ATOMIC_RELEASE);end(22);}
    }
    mark("cow-casp-complete=PASS\n");__atomic_store_n(&control->done,1,__ATOMIC_RELEASE);end(0);
}
static long clone_worker(void (*entry)(void)){
    long stack=call(222,0,65536,3,0x22,-1,0);if(stack<0&&stack>=-4095)return stack;
    /* Separate guest PIDs sharing one mm; parent can use real wait4. */
    return probe_clone(0x100|17,(void *)(stack+65536),entry);
}
void _start(void){
    logfd=call(56,-100,(long)"/casp-cow.txt",0x241,0600,0,0);if(logfd<0)end(2);
    long c=call(222,0,4096,3,0x21,-1,0),p=call(222,0,PAGES*4096,3,0x22,-1,0);
    if((c<0&&c>=-4095)||(p<0&&p>=-4095))end(3);
    control=(struct control *)c;pages=(volatile struct pair *)p;
    for(unsigned i=0;i<PAGES;i++){at(i)->lo=i+1;at(i)->hi=~(u64)i;}
    u64 lo=0,hi=0;casp(&control->hot,&lo,&hi,7,8);
    if(lo||hi||control->hot.lo!=7||control->hot.hi!=8)end(4);
    lo=0;hi=0;casp(&control->hot,&lo,&hi,9,10);
    if(lo!=7||hi!=8||control->hot.lo!=7||control->hot.hi!=8)end(5);
    lo=7;hi=8;casp(&control->hot,&lo,&hi,0,0);if(lo!=7||hi!=8)end(6);
    mark("real-casp64-serial=PASS\n");
    long child=call(220,17,0,0,0,0,0);if(child<0)end(7);
    if(!child){
        while(!__atomic_load_n(&control->done,__ATOMIC_ACQUIRE))delay();
        for(unsigned i=0;i<PAGES;i++)if(at(i)->lo!=i+1||at(i)->hi!=~(u64)i)end(8);
        __atomic_store_n(&control->child_ok,1,__ATOMIC_RELEASE);end(0);
    }
    long workers[4];workers[0]=clone_worker(spin0);workers[1]=clone_worker(spin1);
    workers[2]=clone_worker(spin2);workers[3]=clone_worker(writer);
    for(unsigned i=0;i<4;i++)if(workers[i]<0)end(9);
    mark("real-fork-clone-contenders-started\n");
    for(unsigned i=0;i<10000&&!__atomic_load_n(&control->done,__ATOMIC_ACQUIRE);i++)delay();
    if(!__atomic_load_n(&control->done,__ATOMIC_ACQUIRE))end(10);
    __atomic_store_n(&control->stop,1,__ATOMIC_RELEASE);
    for(unsigned i=0;i<4;i++){int status=-1;if(call(260,workers[i],(long)&status,0,0,0,0)!=workers[i]||status)end(11);}
    int status=-1;if(call(260,child,(long)&status,0,0,0,0)!=child||status||!control->child_ok||control->failed)end(12);
    for(unsigned i=0;i<PAGES;i++)if(at(i)->lo!=i+1000||at(i)->hi!=i+2000)end(13);
    mark("real-cow-isolation-and-joins=PASS\ncomplete=PASS\n");end(0);
}
