/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * Opt-in ARM64 Linux diagnostic interposer; NOT a Valve binary patch or a fix.
 * Forward exact arguments/return/output and preserve errno. No error handler,
 * retry, title/property/pixel/account read, shell or authentication operation.
 * Numeric events only, bounded512KiB/counter instance to the caller's existing
 * private diagnostic stderr. No additional fd/lock or fork-time fd ownership.
 * Failed logging is omitted, never a substitute for the real Xlib call.
 * Explicit diagnostic build AND startup only, never an ordinary Steam launch.
 */
typedef unsigned long word;
typedef int (*get_attributes_fn)(void *,word,void *);
typedef int (*destroy_window_fn)(void *,word);
extern void *dlsym(void *,const char *);
extern void *dlopen(const char *,int);
extern int dlclose(void *);
extern int *__errno_location(void);
static get_attributes_fn original_get;
static destroy_window_fn original_destroy;
static unsigned log_bytes,cap_noted;
static word calls;
static void *held_xlib;
static long call(long n,long a,long b,long c,long d,long e,long f){
    register long x0 __asm__("x0")=a,x1 __asm__("x1")=b,x2 __asm__("x2")=c;
    register long x3 __asm__("x3")=d,x4 __asm__("x4")=e,x5 __asm__("x5")=f,x8 __asm__("x8")=n;
    __asm__ volatile("svc #0":"+r"(x0):"r"(x1),"r"(x2),"r"(x3),"r"(x4),"r"(x5),"r"(x8):"memory","cc");return x0;
}
static unsigned append(char *body,unsigned used,const char *text){while(*text&&used<255)body[used++]=*text++;return used;}
static unsigned number(char *body,unsigned used,word value){char digits[24];unsigned n=0;do{digits[n++]=(char)('0'+value%10);value/=10;}while(value);while(n&&used<255)body[used++]=digits[--n];return used;}
static void emit(unsigned operation,unsigned phase,word id,word window,int result){
    long pid=call(172,0,0,0,0,0,0);if(pid<=0)return;
    struct {long seconds,nanos;} now={0};int clock_ok=call(113,1,(long)&now,0,0,0,0)==0;
    char row[256];unsigned n=append(row,0,"X11_WINDOW_TRACE_V1 pid=");n=number(row,n,(word)pid);n=append(row,n," tid=");n=number(row,n,(word)call(178,0,0,0,0,0,0));
    n=append(row,n," op=");n=number(row,n,operation);n=append(row,n," phase=");n=number(row,n,phase);n=append(row,n," call=");n=number(row,n,id);
    n=append(row,n," window=");n=number(row,n,window);n=append(row,n," result=");if(result<0)n=append(row,n,"-");n=number(row,n,result<0?(word)-(long)result:(word)result);
    n=append(row,n," mono_ns=");n=number(row,n,clock_ok?(word)now.seconds*1000000000+(word)now.nanos:0);n=append(row,n,"\n");
    unsigned bytes=__atomic_load_n(&log_bytes,__ATOMIC_RELAXED);
    do {
        if(n>=255||bytes+n+96>512U*1024U){
            if(!__atomic_exchange_n(&cap_noted,1,__ATOMIC_RELAXED)){
                char note[256];unsigned size=append(note,0,"X11_WINDOW_TRACE_CAPPED pid=");size=number(note,size,(word)pid);size=append(note,size," omitted=1\n");
                call(64,2,(long)note,size,0,0,0);
            }
            return;
        }
    }while(!__atomic_compare_exchange_n(&log_bytes,&bytes,bytes+n,0,__ATOMIC_RELAXED,__ATOMIC_RELAXED));
    // One small write, no retry/blocking mutex and no owned descriptor to
    // corrupt when fork/CLONE_VM/exec/close-range changes descriptor tables.
    // stderr must be the host's private diagnostic sink for this experiment.
    // Short/failed/interleaved output is incomplete evidence, not UI success.
    call(64,2,(long)row,n,0,0,0);
}
static void missing_symbol(unsigned operation){
    // Diagnostic configuration is invalid; never fabricate Xlib success or
    // an error in place of an unavailable original. No Steam result claimed.
    emit(operation,2,0,0,-125);call(94,125,0,0,0,0,0);__builtin_unreachable();
}
static void *resolve(const char *name,unsigned operation){
    void *symbol=dlsym((void *)-1L,name);int scope=1;
    if(!symbol){
        /* Linux glibc flags: NOW=2, NOLOAD=4, LOCAL=0. A real plugin may
         * load libX11 LOCAL, outside RTLD_NEXT's global search. Refer ONLY
         * to the already-loaded soname; never load new dependencies or
         * promote the client/plugin to GLOBAL/DEEPBIND. Keep one reference
         * for this diagnostic's cached function pointers. This deliberately
         * extends Xlib lifetime and must not be called a transparent unload
         * test or a runtime fix. Concurrent losing references are closed.
         */
        void *library=__atomic_load_n(&held_xlib,__ATOMIC_ACQUIRE);
        if(!library){
            void *opened=dlopen("libX11.so.6",2|4);
            if(opened){
                void *expected=0;
                if(__atomic_compare_exchange_n(&held_xlib,&expected,opened,0,__ATOMIC_ACQ_REL,__ATOMIC_ACQUIRE))library=opened;
                else {library=expected;dlclose(opened);}
            }
        }
        if(library)symbol=dlsym(library,name);
        scope=2;
    }
    if(!symbol)missing_symbol(operation);
    emit(operation,2,0,0,scope);return symbol;
}
int XGetWindowAttributes(void *display,word window,void *attributes){
    int *error=__errno_location(),before=*error;
    get_attributes_fn original=__atomic_load_n(&original_get,__ATOMIC_ACQUIRE);
    if(!original){original=(get_attributes_fn)resolve("XGetWindowAttributes",1);__atomic_store_n(&original_get,original,__ATOMIC_RELEASE);}
    word id=__atomic_add_fetch(&calls,1,__ATOMIC_RELAXED);emit(1,0,id,window,0);*error=before;
    int result=original(display,window,attributes),after=*error;
    emit(1,1,id,window,result);*error=after;return result;
}
int XDestroyWindow(void *display,word window){
    int *error=__errno_location(),before=*error;
    destroy_window_fn original=__atomic_load_n(&original_destroy,__ATOMIC_ACQUIRE);
    if(!original){original=(destroy_window_fn)resolve("XDestroyWindow",2);__atomic_store_n(&original_destroy,original,__ATOMIC_RELEASE);}
    word id=__atomic_add_fetch(&calls,1,__ATOMIC_RELAXED);emit(2,0,id,window,0);*error=before;
    int result=original(display,window),after=*error;
    emit(2,1,id,window,result);*error=after;return result;
}
