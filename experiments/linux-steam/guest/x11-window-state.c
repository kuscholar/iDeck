/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * Read-only, one-shot Linux AArch64 X11 state discriminator, fixed display :99.
 * Own implementation from X.Org core protocol definitions, not copied code:
 * https://www.x.org/releases/X11R7.7/doc/xproto/x11protocol.html
 * Queries ONLY setup, attributes, geometry, tree and input focus. No property,
 * title, pixel, key, selection, auth, client mutation or WM replacement. Output
 * is numeric metadata; a successful query is NOT Steam/UI/WM health proof.
 * A window may disappear between requests; record BadWindow/BadDrawable rather
 * than inventing an unmapped window or claiming an atomic server snapshot.
 */
typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef unsigned long u64;
#define WINDOW_LIMIT 32U
#define WIRE_LIMIT 65536U
#ifdef IDECK_X11_STATE_CONTROL
extern long ideck_x11_call(long,long,long,long,long,long,long);
#define call ideck_x11_call
#else
static long call(long n,long a,long b,long c,long d,long e,long f){
    register long x0 __asm__("x0")=a,x1 __asm__("x1")=b,x2 __asm__("x2")=c;
    register long x3 __asm__("x3")=d,x4 __asm__("x4")=e,x5 __asm__("x5")=f,x8 __asm__("x8")=n;
    __asm__ volatile("svc #0":"+r"(x0):"r"(x1),"r"(x2),"r"(x3),"r"(x4),"r"(x5),"r"(x8):"memory","cc");return x0;
}
#endif
static u16 get16(const u8 *p){return (u16)p[0]|(u16)p[1]<<8;}
static u32 get32(const u8 *p){return (u32)p[0]|(u32)p[1]<<8|(u32)p[2]<<16|(u32)p[3]<<24;}
static void put16(u8 *p,u16 n){p[0]=(u8)n;p[1]=(u8)(n>>8);}
static void put32(u8 *p,u32 n){for(unsigned i=0;i<4;i++)p[i]=(u8)(n>>(8*i));}
static u8 reply[WIRE_LIMIT];
struct window_state {u32 id,error,event_mask;unsigned attributes_valid,geometry_valid,map_state,override_redirect,window_class,width,height;int x,y;};
static struct {
    u32 root,focus;unsigned width,height,children,recorded,focus_extra,revert,sequence,error;
    struct window_state root_state,windows[WINDOW_LIMIT+1];
    long begin_ms,end_ms,deadline;
} state;
static long now_ms(void){
    struct {long sec,nsec;} t;long r=call(113,1,(long)&t,0,0,0,0);
    if(r<0){state.error=(unsigned)-r;return -1;}return t.sec*1000+t.nsec/1000000;
}
static int transfer(long fd,void *buffer,unsigned count,int writing){
    unsigned done=0;
    while(done<count){
        long now=now_ms();if(now<0)return -1;
        if(now>=state.deadline){state.error=110;return -1;}
        long left=state.deadline-now;if(left>250)left=250;
        struct {int fd;short events,revents;} poll={(int)fd,writing?4:1,0};
        struct {long sec,nsec;} timeout={0,left*1000000};
        long r=call(73,(long)&poll,1,(long)&timeout,0,0,0);
        if(r==-4||r==0)continue;if(r<0){state.error=(unsigned)-r;return -1;}
        r=call(writing?64:63,fd,(long)((u8 *)buffer+done),count-done,0,0,0);
        if(r==-4||r==-11)continue;
        if(r<=0){state.error=r<0?(unsigned)-r:32;return -1;}
        if((unsigned long)r>count-done){state.error=71;return -1;}done+=(unsigned)r;
    }
    return 0;
}
/* Returns X error as a positive code, transport/protocol error as -1. */
static int query(long fd,unsigned opcode,u32 window,unsigned bytes){
    u8 request[8]={0};request[0]=(u8)opcode;put16(request+2,(u16)(bytes/4));put32(request+4,window);
    state.sequence++;
    if(transfer(fd,request,bytes,1)||transfer(fd,reply,32,0))return -1;
    /* No events are selected by this connection. Unexpected packets, lengths,
     * sequences and opcodes fail closed rather than consuming an endless log. */
    if(get16(reply+2)!=state.sequence){state.error=71;return -1;}
    if(reply[0]==0){
        if(!reply[1]||reply[10]!=opcode||get32(reply+4)!=window){state.error=71;return -1;}
        return reply[1];
    }
    if(reply[0]!=1){state.error=71;return -1;}
    u32 extra=get32(reply+4);if(extra>(WIRE_LIMIT-32)/4){state.error=75;return -1;}
    if(transfer(fd,reply+32,extra*4,0))return -1;
    return 0;
}
static int attributes(long fd,struct window_state *w){
    int r=query(fd,3,w->id,8);if(r<0)return -1;
    if(r){w->error=(u32)r;if(r==3)return 0;state.error=1000+(unsigned)r;return -1;}
    if(get32(reply+4)!=3||reply[26]>2||reply[27]>1){state.error=71;return -1;}
    w->window_class=get16(reply+12);w->map_state=reply[26];w->override_redirect=reply[27];w->event_mask=get32(reply+32);w->attributes_valid=1;
    r=query(fd,14,w->id,8);if(r<0)return -1;
    if(r){w->error=(u32)r;if(r==3||r==9)return 0;state.error=1000+(unsigned)r;return -1;}
    if(get32(reply+4)!=0||get32(reply+8)!=state.root){state.error=71;return -1;}
    w->x=(short)get16(reply+12);w->y=(short)get16(reply+14);w->width=get16(reply+16);w->height=get16(reply+18);w->geometry_valid=1;return 0;
}
static int collect(long fd){
    u8 setup[12]={0};setup[0]='l';put16(setup+2,11);
    if(transfer(fd,setup,12,1)||transfer(fd,reply,8,0))return -1;
    unsigned size=get16(reply+6)*4;
    if(reply[0]!=1||get16(reply+2)!=11||size<32||size>WIRE_LIMIT){state.error=71;return -1;}
    if(transfer(fd,reply,size,0))return -1;
    unsigned root_offset=32+((get16(reply+16)+3)&~3U)+reply[21]*8;
    if(!reply[20]||root_offset+40>size){state.error=71;return -1;}
    state.root=get32(reply+root_offset);state.width=get16(reply+root_offset+20);state.height=get16(reply+root_offset+22);
    if(!state.root||!state.width||!state.height){state.error=71;return -1;}
    state.root_state.id=state.root;if(attributes(fd,&state.root_state))return -1;
    if(state.root_state.error){state.error=1000+state.root_state.error;return -1;}
    int r=query(fd,43,0,4);if(r){if(r>0)state.error=1000+(unsigned)r;return -1;}
    if(get32(reply+4)||reply[1]>2){state.error=71;return -1;}
    state.focus=get32(reply+8);state.revert=reply[1];
    r=query(fd,15,state.root,8);if(r){if(r>0)state.error=1000+(unsigned)r;return -1;}
    state.children=get16(reply+16);
    if(get32(reply+4)!=state.children||get32(reply+8)!=state.root){state.error=71;return -1;}
    /* Retain TOPMOST children if truncated. QueryTree returns bottom-to-top.
     * Copy IDs before another reply reuses the buffer. Focus is independent. */
    state.recorded=state.children<WINDOW_LIMIT?state.children:WINDOW_LIMIT;
    unsigned first=state.children-state.recorded,found=state.focus==state.root||state.focus<=1;
    for(unsigned i=0;i<state.recorded;i++){
        state.windows[i].id=get32(reply+32+4*(first+i));
        if(state.windows[i].id==state.focus)found=1;
    }
    if(!found){state.focus_extra=1;state.windows[state.recorded].id=state.focus;}
    for(unsigned i=0;i<state.recorded+state.focus_extra;i++)if(attributes(fd,&state.windows[i]))return -1;
    return 0;
}
static int snapshot(void){
    state.begin_ms=now_ms();if(state.begin_ms<0)return -1;state.deadline=state.begin_ms+20000;
    struct {u16 family;char path[108];} address={1,"/tmp/.X11-unix/X99"};
    long fd=call(198,1,1|0x800|0x80000,0,0,0,0);if(fd<0){state.error=(unsigned)-fd;return -1;}
    long r=call(203,fd,(long)&address,21,0,0,0);
    if(r==-115||r==-11){
        struct {int fd;short events,revents;} poll={(int)fd,4,0};struct {long sec,nsec;} timeout={2,0};
        r=call(73,(long)&poll,1,(long)&timeout,0,0,0);
        if(r<=0){state.error=r<0?(unsigned)-r:110;call(57,fd,0,0,0,0,0);return -1;}
        int error=0;unsigned size=4;r=call(209,fd,1,4,(long)&error,(long)&size,0);
        if(r<0||size!=4||error){state.error=r<0?(unsigned)-r:error?(unsigned)error:71;call(57,fd,0,0,0,0,0);return -1;}
    }else if(r<0){state.error=(unsigned)-r;call(57,fd,0,0,0,0,0);return -1;}
    int result=collect(fd);call(57,fd,0,0,0,0,0);state.end_ms=now_ms();return result;
}
static char output[16384];static unsigned used,overflow;
static void text(const char *p){while(*p){if(used>=sizeof output-1){overflow=1;return;}output[used++]=*p++;}}
static void number(u64 n){char b[24];unsigned size=0;do{b[size++]=(char)('0'+n%10);n/=10;}while(n);while(size){char p[2]={b[--size],0};text(p);}}
static void field(const char *name,u64 n){text(",\"");text(name);text("\":");number(n);}
static void signed_field(const char *name,int n){text(",\"");text(name);text("\":");if(n<0){text("-");number((u64)-(long)n);}else number((unsigned)n);}
static void window_json(const struct window_state *w){
    text("{\"id\":");number(w->id);field("x_error",w->error);field("attributes_valid",w->attributes_valid);field("geometry_valid",w->geometry_valid);field("map_state",w->map_state);
    field("override_redirect",w->override_redirect);field("class",w->window_class);field("event_mask",w->event_mask);
    signed_field("x",w->x);signed_field("y",w->y);field("width",w->width);field("height",w->height);text("}");
}
static int report(int status){
    text("{\"schema\":1,\"status\":");number(status!=0);field("error",state.error);field("requests",state.sequence);
    field("root",state.root);field("root_width",state.width);field("root_height",state.height);field("focus",state.focus);field("revert_to",state.revert);
    field("children_total",state.children);field("children_recorded",state.recorded);field("focus_extra",state.focus_extra);
    field("elapsed_ms",state.end_ms>=state.begin_ms?(u64)(state.end_ms-state.begin_ms):0);
    text(",\"atomic_snapshot\":false,\"Steam_UI_qualified\":false,\"root_attributes\":");window_json(&state.root_state);
    text(",\"windows_bottom_to_top_then_extra_focus\":[");
    for(unsigned i=0;i<state.recorded+state.focus_extra;i++){if(i)text(",");window_json(&state.windows[i]);}
    text("]}\n");if(overflow)return 90;
    /* stdout is the caller's private artifact, never an app credential log. */
    unsigned done=0;while(done<used){long r=call(64,1,(long)(output+done),used-done,0,0,0);if(r==-4)continue;if(r<=0||(u64)r>used-done)return 91;done+=(unsigned)r;}
    return status?1:0;
}
#ifndef IDECK_X11_STATE_CONTROL
void _start(void){int result=report(snapshot());call(94,result,0,0,0,0,0);__builtin_unreachable();}
#endif
