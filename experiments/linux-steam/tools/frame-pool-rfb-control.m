/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * Actual generated RFB update decoder, protocol fixture; no handshake/auth/UI. */
#import "RFBClient.h"
#import "FrameSnapshotPool.h"
#include <sys/socket.h>
#include <unistd.h>
#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
@interface LRRFBClient (IDECKPoolControl)
@property(nonatomic,strong) IDECKFrameSnapshotPool *ideckFramePool;
- (BOOL)update;
@end
static BOOL denyAlloc;
static unsigned allocs,frees;
void *ideck_frame_pool_test_alloc(size_t n){allocs++;return denyAlloc?NULL:malloc(n);}
void ideck_frame_pool_test_free(void *p){frees++;free(p);}
static void put(int fd,const void *p,size_t n){const char *s=p;while(n){ssize_t r=write(fd,s,n);assert(r>0);s+=r;n-=r;}}
static void raw(int fd,unsigned x,unsigned y,unsigned w,unsigned h,unsigned char value){
    uint8_t header[]={0,0,0,1,0,(uint8_t)x,0,(uint8_t)y,0,(uint8_t)w,0,(uint8_t)h,0,0,0,0};
    put(fd,header,sizeof header);unsigned char pixels[16*16*4];assert(w*h*4<=sizeof pixels);memset(pixels,value,w*h*4);put(fd,pixels,w*h*4);
}
int main(void){@autoreleasepool{
    int fds[2];assert(!socketpair(AF_UNIX,SOCK_STREAM,0,fds));
    LRRFBClient *client=[[LRRFBClient alloc]initWithPort:0 password:@"fixture"];
    client.ideckFramePool=[[IDECKFrameSnapshotPool alloc]initWithWidth:16 height:16];assert(client.ideckFramePool&&allocs==4);
    denyAlloc=YES; // late allocator failure must not prevent pool snapshots
    [client setValue:@(fds[0]) forKey:@"socket"];[client setValue:@16 forKey:@"width"];[client setValue:@16 forKey:@"height"];
    [client setValue:[NSMutableData dataWithLength:16*16*4] forKey:@"pixels"];[client setValue:[NSMutableData new] forKey:@"raw"];
    NSMutableArray<NSData *> *held=[NSMutableArray new];__block unsigned errors=0;
    client.frameHandler=^(NSData *p,uint16_t w,uint16_t h,uint64_t frames,uint64_t bytes){(void)bytes;assert(w==16&&h==16&&frames==held.count+1);[held addObject:p];};
    client.statusHandler=^(NSString *s){assert([s containsString:@"snapshot pool unavailable"]);errors++;};
    uint8_t request[10];
    @autoreleasepool{raw(fds[1],0,0,16,16,7);assert([client update]&&read(fds[1],request,10)==10);}
    @autoreleasepool{raw(fds[1],8,9,3,4,43);assert([client update]&&read(fds[1],request,10)==10);}
    for(unsigned y=0;y<16;y++)for(unsigned x=0;x<16;x++)for(unsigned c=0;c<4;c++){
        size_t at=(y*16+x)*4+c;assert(((const uint8_t *)held[0].bytes)[at]==7);
        assert(((const uint8_t *)held[1].bytes)[at]==((x>=8&&x<11&&y>=9&&y<13)?43:7));
    }
    for(unsigned i=0;i<2;i++){@autoreleasepool{raw(fds[1],0,0,16,16,(unsigned char)(51+i));assert([client update]&&read(fds[1],request,10)==10);}}
    raw(fds[1],0,0,16,16,99);assert(![client update]&&held.count==4&&errors==1&&allocs==4);
    for(size_t i=0;i<held[0].length;i++)assert(((const uint8_t *)held[0].bytes)[i]==7);
    [held removeAllObjects];client.frameHandler=nil;client.statusHandler=nil;client.ideckFramePool=nil;
    close(fds[0]);close(fds[1]);[client setValue:@(-1) forKey:@"socket"];
}
    struct ideck_frame_pool_stats s;ideck_frame_pool_stats_read(&s);
    assert(s.calls==5&&s.exhausted==1&&s.releases==4&&!s.live_slots&&!s.native_buffers&&!s.native_bytes&&frees==4);
    puts("HOST actual generated RFB full/partial immutable bytes with lateallocator unavailable; bounded exhaustion fails no callback, all slots freed PASS");return 0;
}
