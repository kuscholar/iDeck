/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * Freestanding ARM64 Linux X11 wire control, no Xlib/Steam/auth dependency.
 * Layout reference: X.Org Xproto.h (protocol definitions, not copied code):
 * https://cgit.freedesktop.org/xorg/proto/xproto/tree/Xproto.h
 * Only its own :97 windows are created/mapped/read/destroyed. Two clients use
 * separate connections. BadWindow on a DESTROYED window is expected evidence,
 * not a browser crash. No unrelated X display or installed app is touched.
 */
typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef unsigned long u64;
static long call(long n,long a,long b,long c,long d,long e,long f){
    register long x0 __asm__("x0")=a,x1 __asm__("x1")=b,x2 __asm__("x2")=c;
    register long x3 __asm__("x3")=d,x4 __asm__("x4")=e,x5 __asm__("x5")=f,x8 __asm__("x8")=n;
    __asm__ volatile("svc #0":"+r"(x0):"r"(x1),"r"(x2),"r"(x3),"r"(x4),"r"(x5),"r"(x8):"memory","cc");return x0;
}
static void zero(void *p,unsigned n){u8 *b=p;while(n--)*b++=0;}
static unsigned length(const char *p){unsigned n=0;while(p[n])n++;return n;}
static u16 get16(const u8 *p){return (u16)p[0]|(u16)p[1]<<8;}
static u32 get32(const u8 *p){return (u32)p[0]|(u32)p[1]<<8|(u32)p[2]<<16|(u32)p[3]<<24;}
static void put16(u8 *p,u16 v){p[0]=(u8)v;p[1]=(u8)(v>>8);}
static void put32(u8 *p,u32 v){for(unsigned i=0;i<4;i++)p[i]=(u8)(v>>(8*i));}
static u8 reply[65536];
static unsigned stage,wire_error,live_attributes,bad_windows,images;
static u64 image_bytes,pixel_checks;
static u32 image_hash=2166136261U;
static long deadline;
static long seconds(void){struct {long sec,nsec;} t;if(call(113,1,(long)&t,0,0,0,0))return -1;return t.sec;}
static int transfer(long fd,void *buffer,unsigned bytes,int writing){
    unsigned done=0;
    while(done<bytes){
        if(seconds()>deadline){wire_error=110;return -1;}
        struct {int fd;short events,revents;} poll={(int)fd,writing?4:1,0};
        struct {long sec,nsec;} timeout={1,0};long ready=call(73,(long)&poll,1,(long)&timeout,0,0,0);
        if(ready==-4||ready==0)continue;if(ready<0){wire_error=(unsigned)-ready;return -1;}
        long n=call(writing?64:63,fd,(long)((u8 *)buffer+done),bytes-done,0,0,0);
        if(n==-4||n==-11)continue;if(n<=0){wire_error=n<0?(unsigned)-n:32;return -1;}done+=(unsigned)n;
    }
    return 0;
}
static int response(long fd,unsigned sequence,int expected_error,unsigned expected_size){
    for(unsigned i=0;i<128;i++){
        if(transfer(fd,reply,32,0))return -1;
        if(reply[0]==0){if(expected_error&&reply[1]==expected_error&&get16(reply+2)==sequence&&reply[10]==3)return 0;wire_error=1000+reply[1];return -1;}
        if(reply[0]!=1){if((reply[0]&127)==35){unsigned extra=get32(reply+4);if(extra>(sizeof reply-32)/4||transfer(fd,reply+32,extra*4,0))return -1;}continue;}
        unsigned extra=get32(reply+4);if(extra>(sizeof reply-32)/4){wire_error=100;return -1;}
        if(transfer(fd,reply+32,extra*4,0))return -1;
        if(expected_error||get16(reply+2)!=sequence||32+extra*4!=expected_size){wire_error=101;return -1;}
        return 0;
    }
    wire_error=102;return -1;
}
static int resource(long fd,unsigned opcode,u32 window,unsigned *sequence){
    u8 request[8]={0};request[0]=(u8)opcode;put16(request+2,2);put32(request+4,window);(*sequence)++;return transfer(fd,request,sizeof request,1);
}
static int worker(unsigned role){
    stage=1;deadline=seconds()+45;
    struct {u16 family;char path[108];} address={1,"/tmp/.X11-unix/X97"};
    long fd=call(198,1,1|0x80000,0,0,0,0);if(fd<0){wire_error=(unsigned)-fd;return 1;}
    long result=call(203,fd,(long)&address,2+length(address.path)+1,0,0,0);
    if(result<0){wire_error=(unsigned)-result;return 1;}
    long flags=call(25,fd,3,0,0,0,0);if(flags<0||call(25,fd,4,flags|0x800,0,0,0)<0)return 1;
    stage=2;u8 setup[12]={0};setup[0]='l';put16(setup+2,11);
    if(transfer(fd,setup,sizeof setup,1)||transfer(fd,reply,8,0))return 1;
    unsigned setup_bytes=get16(reply+6)*4;if(reply[0]!=1||setup_bytes<32||setup_bytes>sizeof reply){wire_error=103;return 1;}
    if(transfer(fd,reply,setup_bytes,0))return 1;
    u32 base=get32(reply+4),mask=get32(reply+8);unsigned formats=reply[21];
    unsigned root_offset=32+((get16(reply+16)+3)&~3U)+formats*8;
    if(!base||(mask&31)!=31||!reply[20]||reply[22]!=0||formats>32||root_offset+40>setup_bytes){wire_error=104;return 1;}
    int format=0;for(unsigned i=0;i<formats;i++){const u8 *p=reply+32+((get16(reply+16)+3)&~3U)+i*8;if(p[0]==24&&p[1]==32&&p[2]==32)format=1;}
    u32 root=get32(reply+root_offset);if(!format||reply[root_offset+38]!=24){wire_error=105;return 1;}
    unsigned sequence=0;u32 color=role?0x327ac4:0x194e83;
    for(unsigned i=1;i<=16;i++){
        u32 window=base|i;u8 create[36];zero(create,sizeof create);create[0]=1;put16(create+2,9);put32(create+4,window);put32(create+8,root);
        put16(create+12,(u16)(role?128:16));put16(create+14,16);put16(create+16,64);put16(create+18,32);put16(create+22,1);put32(create+28,2);put32(create+32,color);
        stage=3;sequence++;if(transfer(fd,create,sizeof create,1))return 1;
        stage=4;if(resource(fd,3,window,&sequence)||response(fd,sequence,0,44)||get16(reply+12)!=1||reply[26]!=0)return 1;live_attributes++;
        stage=5;if(resource(fd,8,window,&sequence)||resource(fd,3,window,&sequence)||response(fd,sequence,0,44)||reply[26]!=2)return 1;live_attributes++;
        stage=6;if(resource(fd,14,window,&sequence)||response(fd,sequence,0,32)||get16(reply+16)!=64||get16(reply+18)!=32)return 1;
        u8 image[20];zero(image,sizeof image);image[0]=73;image[1]=2;put16(image+2,5);put32(image+4,window);put16(image+12,64);put16(image+14,32);put32(image+16,0xffffffffU);
        stage=7;sequence++;if(transfer(fd,image,sizeof image,1)||response(fd,sequence,0,32+64*32*4)||reply[1]!=24)return 1;
        for(unsigned p=32;p<32+64*32*4;p+=4){if((get32(reply+p)&0xffffff)!=color){wire_error=106;return 1;}pixel_checks++;}
        for(unsigned p=32;p<32+64*32*4;p++){image_hash^=reply[p];image_hash*=16777619U;}image_bytes+=64*32*4;images++;
        stage=8;if(resource(fd,4,window,&sequence)||resource(fd,3,window,&sequence)||response(fd,sequence,3,32))return 1;bad_windows++;
    }
    call(57,fd,0,0,0,0,0);stage=0;return 0;
}
static char report[1024];static unsigned used;
static void append(const char *p){while(*p&&used<sizeof report-1)report[used++]=*p++;}
static void number(u64 n){char value[24];unsigned size=0;do{value[size++]=(char)('0'+n%10);n/=10;}while(n);while(size)report[used++]=value[--size];}
static void field(const char *name,u64 value){append(name);append("=");number(value);append("\n");}
static void finish(unsigned code,unsigned role){
    field("status",code);field("failure_stage",stage);field("wire_error",wire_error);field("live_attributes",live_attributes);field("expected_bad_windows",bad_windows);field("images",images);field("image_bytes",image_bytes);field("pixel_comparisons",pixel_checks);field("framebuffer_fnv1a32",image_hash);
    append("scope=real_ARM64_X11_wire_own_windows_not_Steam_or_iPad_success\n");
    const char *path=role?"/x11-window-child.txt":"/x11-window-parent.txt";long fd=call(56,-100,(long)path,0x241,0600,0,0);
    if(fd<0||call(64,fd,(long)report,used,0,0,0)!=(long)used)code=90;
    if(fd>=0)call(57,fd,0,0,0,0,0);call(94,code,0,0,0,0,0);__builtin_unreachable();
}
void _start(void){
    long child=call(220,17,0,0,0,0,0);if(child<0){stage=9;wire_error=(unsigned)-child;finish(1,0);}
    unsigned role=child==0;unsigned code=(unsigned)worker(role);
    if(!role){int status=-1;long waited=call(260,child,(long)&status,0,0,0,0);if(waited!=child||status){stage=10;wire_error=status<0?999:(unsigned)status;code=1;}}
    finish(code,role);
}
