/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * OWN synthetic ARM64 VM coherence control, not a Chromium allocator or fix.
 * Untouched metadata + protected guards beside a changing private payload.
 */
typedef unsigned long u64;
enum { PAGE=4096,SPAN=2*1024*1024,ROUNDS=16 };
struct control {u64 warmed,changed,ack,done;};
static struct control *control;
static volatile u64 *metadata,*payload;
static int logfd;
extern long probe_clone(long,void *,void (*)(void));
static long call(long n,long a,long b,long c,long d,long e,long f){
    register long x0 __asm__("x0")=a,x1 __asm__("x1")=b,x2 __asm__("x2")=c;
    register long x3 __asm__("x3")=d,x4 __asm__("x4")=e,x5 __asm__("x5")=f,x8 __asm__("x8")=n;
    __asm__ volatile("svc #0":"+r"(x0):"r"(x1),"r"(x2),"r"(x3),"r"(x4),"r"(x5),"r"(x8):"memory","cc");return x0;
}
static void end(int status){call(93,status,0,0,0,0,0);__builtin_unreachable();}
static void mark(const char *s){unsigned n=0;while(s[n])n++;if(call(64,logfd,(long)s,n,0,0,0)!=n)end(90);}
static int wait_at_least(u64 *p,u64 value){
#if IDECK_METADATA_PURE_SPIN
    // Keep the translated reader in userspace across the writer's remapping;
    // nanosleep would return through the syscall loop and refresh its TLB.
    for(unsigned i=0;i<100000000;i++)if(__atomic_load_n(p,__ATOMIC_ACQUIRE)>=value)return 1;
#else
    for(unsigned i=0;i<5000;i++){
        if(__atomic_load_n(p,__ATOMIC_ACQUIRE)>=value)return 1;
        struct {long s,ns;} delay={0,1000000};call(101,(long)&delay,0,0,0,0,0);
    }
#endif
    return 0;
}
static u64 sentinel(unsigned i){return 0x57681234e90a0000UL+i*17;}
static int metadata_ok(void){for(unsigned i=0;i<PAGE/8;i++)if(metadata[i]!=sentinel(i))return 0;return 1;}
static volatile u64 *round_payload(unsigned round){return payload+(u64)round*16384/8;}
static int edges(volatile u64 *p,unsigned pages,u64 value){
    for(unsigned i=0;i<pages;i++)if(p[i*PAGE/8]!=value||p[(i+1)*PAGE/8-1]!=value)return 0;
    return 1;
}
static void fill(volatile u64 *p,unsigned pages,u64 value){
    for(unsigned i=0;i<pages;i++){p[i*PAGE/8]=value;p[(i+1)*PAGE/8-1]=value;}
}
static void reader(void){
    for(unsigned round=0;round<ROUNDS;round++){
        volatile u64 *p=round_payload(round);
        if(!metadata_ok()||!edges(p,4,71))end(31);
        __atomic_store_n(&control->warmed,round+1,__ATOMIC_RELEASE);
        if(!wait_at_least(&control->changed,round+1))end(32);
        if(!metadata_ok()||!edges(p,4,round+0x100))end(33);
        __atomic_store_n(&control->ack,round+1,__ATOMIC_RELEASE);
    }end(0);
}
void _start(void){
    logfd=call(56,-100,(long)"/metadata-payload-results.txt",0x241,0600,0,0);if(logfd<0)end(2);
    const long base=0x4c20000000UL;
    long mapped=call(222,base,SPAN,0,0x32,-1,0);
    if(mapped!=base||call(226,base+PAGE,PAGE,3,0,0,0)||call(226,base+4*PAGE,SPAN-4*PAGE,3,0,0,0))end(3);
    metadata=(volatile u64 *)(base+PAGE);payload=(volatile u64 *)(base+4*PAGE);
    for(unsigned i=0;i<PAGE/8;i++)metadata[i]=sentinel(i);
    fill(payload,(SPAN-4*PAGE)/PAGE,71);mark("private-superpage-layout=PASS\n");
    long shared=call(222,0,PAGE,3,0x21,-1,0);if(shared<0&&shared>=-4095)end(4);control=(struct control *)shared;
    long sibling=call(220,17,0,0,0,0,0);if(sibling<0)end(5);
    if(!sibling){
        if(!wait_at_least(&control->done,1)||!metadata_ok()||!edges(payload,(SPAN-4*PAGE)/PAGE,71))end(41);
        end(0);
    }
    long stack=call(222,0,65536,3,0x22,-1,0);if(stack<0&&stack>=-4095)end(6);
    long worker=probe_clone(0x100|17,(void *)(stack+65536),reader);if(worker<0)end(7);
    for(unsigned round=0;round<ROUNDS;round++){
        volatile u64 *p=round_payload(round);
        if(!wait_at_least(&control->warmed,round+1))end(8);
        if(call(233,(long)p,16384,4,0,0,0)||!edges(p,4,0)||!metadata_ok())end(9);
        if(call(226,(long)p,PAGE,0,0,0,0)||call(226,(long)p,PAGE,3,0,0,0))end(10);
        fill(p,4,round+0x100);if(!metadata_ok())end(11);
        __atomic_store_n(&control->changed,round+1,__ATOMIC_RELEASE);
        if(!wait_at_least(&control->ack,round+1))end(12);
        // Retire an already-private previous block while another broker slot
        // remains live. The next new CoW block can reuse that released native
        // slot. The reader is now warming a DIFFERENT payload block.
        if(round){volatile u64 *previous=round_payload(round-1);
            if(call(233,(long)previous,16384,4,0,0,0)||!edges(previous,4,0)||!metadata_ok())end(18);
        }
    }
    mark("metadata-independent-of-discard-and-protection=PASS\ncached-reader-sees-current-payload=PASS\n");
    __atomic_store_n(&control->done,1,__ATOMIC_RELEASE);
    int status=-1;
    if(call(260,worker,(long)&status,0,0,0,0)!=worker||status)end(13);
    if(call(260,sibling,(long)&status,0,0,0,0)!=sibling||status)end(14);
    mark("fork-sibling-private-isolation=PASS\n");
    for(unsigned guard=0;guard<2;guard++){
        long child=call(220,17,0,0,0,0,0);if(child<0)end(15);
        if(!child){volatile u64 *p=(volatile u64 *)(base+(guard?2*PAGE:0));
            if(guard)*p=19;else{volatile u64 value=*p;(void)value;}
            end(99); // Any successful access to the guard fails the control.
        }
        if(call(260,child,(long)&status,0,0,0,0)!=child||(status&127)!=11)end(16);
    }
    mark("translated-guard-read-and-write-refused=PASS\n");
    if(!metadata_ok()||call(215,base,SPAN,0,0,0,0)||call(215,stack,65536,0,0,0,0))end(17);
    mark("joined-and-cleaned=PASS\ncomplete=PASS\n");end(0);
}
