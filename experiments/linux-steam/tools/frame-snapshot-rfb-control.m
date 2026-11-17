/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * HOST real copied RFB update method, local protocol fixture, no authentication
 * or Steam claim. Existing handshake is not invoked or modified by this test. */
#import "RFBClient.h"
#import "CheckedFrameSnapshot.h"
#include <sys/socket.h>
#include <unistd.h>
#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
@interface LRRFBClient (HostControl)
- (BOOL)update;
@end
static int inject;
void *ideck_frame_test_alloc(size_t n){return inject?NULL:malloc(n);}
void ideck_frame_test_free(void *p){free(p);}
static void put(int fd,const void *p,size_t n){const char *s=p;while(n){ssize_t r=write(fd,s,n);assert(r>0);s+=r;n-=r;}}
static void raw(int fd,unsigned x,unsigned y,unsigned w,unsigned h,unsigned char value){
    uint8_t header[]={0,0,0,1,(uint8_t)(x>>8),(uint8_t)x,(uint8_t)(y>>8),(uint8_t)y,(uint8_t)(w>>8),(uint8_t)w,(uint8_t)(h>>8),(uint8_t)h,0,0,0,0};
    put(fd,header,sizeof header);unsigned char pixels[16*16*4];assert(w*h*4<=sizeof pixels);memset(pixels,value,w*h*4);put(fd,pixels,w*h*4);
}
int main(void){@autoreleasepool{
    int fds[2];assert(!socketpair(AF_UNIX,SOCK_STREAM,0,fds));
    LRRFBClient *client=[[LRRFBClient alloc]initWithPort:0 password:@"fixture"];
    [client setValue:@(fds[0]) forKey:@"socket"];[client setValue:@16 forKey:@"width"];[client setValue:@16 forKey:@"height"];
    [client setValue:[NSMutableData dataWithLength:16*16*4] forKey:@"pixels"];[client setValue:[NSMutableData new] forKey:@"raw"];
    __block NSData *first=nil,*latest=nil;__block unsigned calls=0,errors=0;
    client.frameHandler=^(NSData *p,uint16_t w,uint16_t h,uint64_t frames,uint64_t bytes){(void)bytes;assert(w==16&&h==16&&frames==calls+1);if(!calls)first=p;latest=p;calls++;};
    client.statusHandler=^(NSString *s){assert([s containsString:@"snapshot allocation failed"]);errors++;};
    uint8_t request[10];raw(fds[1],0,0,16,16,7);assert([client update]&&read(fds[1],request,10)==10&&calls==1);
    raw(fds[1],8,9,3,4,43);assert([client update]&&read(fds[1],request,10)==10&&calls==2);
    for(unsigned y=0;y<16;y++)for(unsigned x=0;x<16;x++)for(unsigned c=0;c<4;c++){
        size_t at=(y*16+x)*4+c;assert(((const uint8_t *)first.bytes)[at]==7);
        assert(((const uint8_t *)latest.bytes)[at]==((x>=8&&x<11&&y>=9&&y<13)?43:7));
    }
    inject=1;raw(fds[1],0,0,16,16,99);assert(![client update]&&calls==2&&errors==1);inject=0;
    /* Failed snapshot emitted no callback and retained consumers remain exact. */
    for(size_t i=0;i<first.length;i++)assert(((const uint8_t *)first.bytes)[i]==7);
    first=nil;latest=nil;client.frameHandler=nil;client.statusHandler=nil;
    close(fds[0]);close(fds[1]);[client setValue:@(-1) forKey:@"socket"];
}
    struct ideck_frame_snapshot_stats s;ideck_frame_snapshot_stats_read(&s);assert(s.calls==3&&s.failures==1&&!s.live_frames&&!s.live_bytes&&s.releases==2);
    puts("HOST actual RFB raw full+partial decode retains immutable bytes; allocNULL emits no frame and returns existing display-error path PASS");
return 0;}
