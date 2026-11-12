// SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
#import "LabMetalDrain.h"
#include <stdlib.h>
#include <stdio.h>
static void check(BOOL value,const char *name) {if(!value){fprintf(stderr,"FAIL %s\n",name);exit(1);}}
int main(void){@autoreleasepool{
 id<MTLDevice> device=MTLCreateSystemDefaultDevice();
 if(!device){fprintf(stderr,"No physical Metal device; test unavailable\n");return 77;}
 id<MTLCommandQueue> queue=[device newCommandQueue];check(queue!=nil,"queue");
 dispatch_async(dispatch_get_main_queue(), ^{
  LabMetalDrain *drain=[LabMetalDrain new];__block unsigned bodies=0,closes=0;
  id<MTLCommandBuffer> a=[queue commandBuffer],b=[queue commandBuffer];
  id<MTLBuffer> buffer=[device newBufferWithLength:4096 options:MTLResourceStorageModeShared];check(buffer!=nil,"buffer");
  id<MTLBlitCommandEncoder> blit=[a blitCommandEncoder];[blit fillBuffer:buffer range:NSMakeRange(0,4096) value:0x5a];[blit endEncoding];
  check([drain trackCommand:a completion:^(id<MTLCommandBuffer> c){check(c.status==MTLCommandBufferStatusCompleted,"actual GPU complete");check(((unsigned char *)buffer.contents)[0]==0x5a,"actual GPU data");bodies++;}],"admit a");
  check([drain trackCommand:b completion:^(id<MTLCommandBuffer> c){check(c.status==MTLCommandBufferStatusCompleted,"second actual command");bodies++;}],"admit b");
  check(drain.pending==2,"two pending precommit");
  [drain closeWithCompletion:^{
   closes++;check(bodies==2&&drain.pending==0&&drain.closed,"body before drain callback");
   check(closes==1,"single callback");check(![drain reopen],"no reentrant reopen inside callback");
   dispatch_async(dispatch_get_main_queue(), ^{check(closes==2,"all original drain callbacks returned");check([drain reopen],"reopen after actual drain");
   id<MTLCommandBuffer> c=[queue commandBuffer];
   check([drain trackCommand:c completion:^(id<MTLCommandBuffer> done){check(done.status==MTLCommandBufferStatusCompleted,"wave2 actual command");bodies++;}],"wave2 admission");
   [drain closeWithCompletion:^{check(bodies==3&&drain.pending==0,"wave2 drained");puts("PASS actual Metal commands, closed admission, completion body, drain and reopen");exit(0);}];
   [c commit];
   });
  }];
  [drain closeWithCompletion:^{closes++;check(bodies==2&&drain.pending==0,"second subscriber actual completion");}];
  check(closes==0&&! [drain reopen],"no premature callback/reopen");
  check(![drain trackCommand:[queue commandBuffer] completion:^(id<MTLCommandBuffer> c){(void)c;exit(2);}],"closed admission refused");
  [a commit];[b commit];
 });
 dispatch_after(dispatch_time(DISPATCH_TIME_NOW,10*NSEC_PER_SEC),dispatch_get_main_queue(),^{fputs("FAIL bounded actual GPU drain timeout\n",stderr);exit(3);});
 dispatch_main();
}}
