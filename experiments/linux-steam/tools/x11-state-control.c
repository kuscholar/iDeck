/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * Exercise actual diagnostic wire/parser/transport with fragmented replies,
 * races, malformed servers and deadlines. No sockets, app, Steam or device.
 */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#define IDECK_X11_STATE_CONTROL 1
#include "../guest/x11-window-state.c"
static u8 pending[WIRE_LIMIT],request_bytes[12];
static unsigned pending_size,pending_read,request_size,requests,closes;
static unsigned mode,tree_count,connect_wait;
static long clock_ms;
static char emitted[sizeof output];static unsigned emitted_size;
enum {NORMAL,FOCUS_NONE,FOCUS_EXTRA,MANY,DISAPPEARED,DRAWABLE_GONE,WRONG_SEQUENCE,
      HUGE_REPLY,TREE_MISMATCH,EOF_REPLY,TIMEOUT_REPLY,BAD_SETUP,WRONG_PACKET,
      CONNECT_FAILURE,CONNECT_ASYNC_FAILURE,ROOT_REDIRECT,SHORT_WRITES,ROOT_GONE,WRONG_ERROR};
static void respond(unsigned opcode,u32 window){
    memset(pending,0,sizeof pending);pending_read=0;pending_size=32;
    if(!requests){
        assert(request_size==12&&request_bytes[0]=='l'&&get16(request_bytes+2)==11);
        pending[0]=1;put16(pending+2,11);put16(pending+6,18);pending_size=80;
        pending[8+20]=1;put32(pending+8+32,0x100);put16(pending+8+32+20,1280);put16(pending+8+32+22,800);
        if(mode==BAD_SETUP)pending[8+21]=255;
    }else{
        /* The control fails if production gains ANY mutating/property/pixel
         * request, or targets a different window/display via hidden payload. */
        assert(opcode==3||opcode==14||opcode==15||opcode==43);
        assert(get16(request_bytes+2)==(opcode==43?1:2));
        pending[0]=1;put16(pending+2,(u16)requests);
        if(opcode==3){
            pending_size=44;put32(pending+4,3);put16(pending+12,1);pending[26]=2;
            if(window==0x200002)pending[26]=0;
            if(window==0x100&&mode==ROOT_REDIRECT)put32(pending+32,1U<<20);
            if(mode==DISAPPEARED&&window==0x200002){pending[0]=0;pending[1]=3;pending[10]=3;put32(pending+4,window);pending_size=32;}
            if(mode==ROOT_GONE&&window==0x100){pending[0]=0;pending[1]=3;pending[10]=3;put32(pending+4,window);pending_size=32;}
            if(mode==WRONG_ERROR&&window==0x200002){pending[0]=0;pending[1]=3;pending[10]=4;put32(pending+4,window);pending_size=32;}
        }else if(opcode==14){
            put32(pending+8,0x100);put16(pending+12,(u16)(short)-9);put16(pending+14,17);put16(pending+16,1280);put16(pending+18,800);
            if(mode==DRAWABLE_GONE&&window==0x200002){pending[0]=0;pending[1]=9;pending[10]=14;put32(pending+4,window);}
        }else if(opcode==43){
            put32(pending+8,mode==FOCUS_NONE?0:mode==FOCUS_EXTRA?0x300001:0x200001);pending[1]=1;
        }else if(opcode==15){
            put32(pending+8,0x100);put16(pending+16,(u16)tree_count);put32(pending+4,tree_count);
            pending_size=32+4*tree_count;for(unsigned i=0;i<tree_count;i++)put32(pending+32+4*i,0x200001+i);
            if(mode==TREE_MISMATCH)put16(pending+16,(u16)(tree_count+1));
        }
        if(requests==1){
            if(mode==WRONG_SEQUENCE)put16(pending+2,9);
            if(mode==HUGE_REPLY)put32(pending+4,0xffffffffU);
            if(mode==WRONG_PACKET)pending[0]=2;
        }
    }
    requests++;request_size=0;
}
long ideck_x11_call(long n,long a,long b,long c,long d,long e,long f){
    (void)d;(void)e;(void)f;
    if(n==113){struct clock_value{long sec,nsec;} *t=(void *)b;clock_ms+=mode==TIMEOUT_REPLY?300:1;t->sec=clock_ms/1000;t->nsec=clock_ms%1000*1000000;return 0;}
    if(n==198){assert(a==1&&b==(1|0x800|0x80000)&&c==0);return 10;}
    if(n==203){assert(a==10&&c==21);assert(!strcmp((const char *)b+2,"/tmp/.X11-unix/X99"));if(mode==CONNECT_FAILURE)return -111;connect_wait=1;return -115;}
    if(n==209){assert(a==10&&b==1&&c==4);*(int *)d=mode==CONNECT_ASYNC_FAILURE?111:0;*(unsigned *)e=4;return 0;}
    if(n==73){if(connect_wait){connect_wait=0;return 1;}return mode==TIMEOUT_REPLY?0:1;}
    if(n==57){assert(a==10);closes++;return 0;}
    if(n==63){
        assert(a==10);if(mode==EOF_REPLY)return 0;
        assert(pending_read<pending_size);unsigned size=pending_size-pending_read;if(size>(unsigned)c)size=(unsigned)c;if(size>3)size=3;
        memcpy((void *)b,pending+pending_read,size);pending_read+=size;return size;
    }
    if(n==64){
        if(a==1){assert(emitted_size+(unsigned)c<sizeof emitted);memcpy(emitted+emitted_size,(void *)b,(size_t)c);emitted_size+=(unsigned)c;return c;}
        assert(a==10);if(mode==SHORT_WRITES&&requests==0&&request_size==0){mode=NORMAL;return -4;}
        unsigned size=(unsigned)c;if(size>2)size=2;assert(request_size+size<=sizeof request_bytes);
        memcpy(request_bytes+request_size,(void *)b,size);request_size+=size;
        unsigned wanted=requests?request_bytes[0]==43?4:8:12;
        if(request_size==wanted)respond(request_bytes[0],requests&&wanted==8?get32(request_bytes+4):0);
        return size;
    }
    assert(!"Unexpected syscall");return -38;
}
static void run(unsigned test,int success){
    memset(&state,0,sizeof state);memset(output,0,sizeof output);memset(emitted,0,sizeof emitted);
    used=overflow=pending_size=pending_read=request_size=requests=closes=emitted_size=connect_wait=0;
    mode=test;clock_ms=1000;tree_count=test==MANY?40:2;
    int result=snapshot();assert((result==0)==success);assert(closes==1);assert(requests<=72);assert(clock_ms-state.begin_ms<=20600);
    assert(report(result)==(success?0:1));assert(strstr(emitted,"\"atomic_snapshot\":false"));assert(strstr(emitted,"\"Steam_UI_qualified\":false"));
    if(success){
        assert(!state.error&&state.root==0x100&&state.width==1280&&state.height==800);
        assert(state.children==tree_count&&state.recorded==(tree_count<WINDOW_LIMIT?tree_count:WINDOW_LIMIT));
        if(test==MANY){assert(state.windows[0].id==0x200009&&state.windows[31].id==0x200028&&state.focus_extra&&state.windows[32].id==0x200001);}
        if(test==FOCUS_NONE)assert(!state.focus&&!state.focus_extra);
        if(test==FOCUS_EXTRA)assert(state.focus_extra&&state.windows[2].id==0x300001);
        if(test==DISAPPEARED)assert(state.windows[1].error==3&&!state.windows[1].attributes_valid&&!state.windows[1].geometry_valid);
        if(test==DRAWABLE_GONE)assert(state.windows[1].error==9&&state.windows[1].attributes_valid&&!state.windows[1].geometry_valid);
        if(test==ROOT_REDIRECT)assert(state.root_state.event_mask==(1U<<20));
        if(test==NORMAL){assert(state.windows[0].x==-9&&state.windows[1].map_state==0);fputs(emitted,stdout);}
    }else assert(state.error);
}
int main(void){
    for(unsigned i=0;i<=WRONG_ERROR;i++)run(i,i<=DRAWABLE_GONE||i==ROOT_REDIRECT||i==SHORT_WRITES);
    puts("PASS actual one-shot X11 protocol: fragmentation/EINTR/focus/map/race/cap/malformed/deadline/read-only whitelist; HOST fixture, not Air/Steam");return 0;
}
