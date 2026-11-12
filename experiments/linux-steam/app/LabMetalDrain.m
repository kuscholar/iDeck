// SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
#import "LabMetalDrain.h"
@interface LabMetalDrain ()
@property(nonatomic,readwrite) BOOL closed;
@property(nonatomic,readwrite) NSUInteger pending;
@property(nonatomic,strong) NSMutableArray *waiters;
@property(nonatomic) BOOL notifying;
@end
@implementation LabMetalDrain
- (instancetype)init { if((self=[super init])) _waiters=[NSMutableArray new]; return self; }
- (void)assertQueue { NSAssert(NSThread.isMainThread || dispatch_get_specific((const void *)&LabMetalDrainQueueKey), @"Metal admission belongs to main thread/queue"); }
static char LabMetalDrainQueueKey;
+ (void)initialize {
    if(self==LabMetalDrain.class) dispatch_queue_set_specific(dispatch_get_main_queue(),&LabMetalDrainQueueKey,&LabMetalDrainQueueKey,NULL);
}
- (void)notifyIfDrained {
    [self assertQueue];
    if(!self.closed || self.pending || self.notifying) return;
    NSArray *ready=[self.waiters copy]; [self.waiters removeAllObjects];
    self.notifying=YES;
    for(dispatch_block_t callback in ready) callback();
    self.notifying=NO;
    if(self.waiters.count) dispatch_async(dispatch_get_main_queue(), ^{[self notifyIfDrained];});
}
- (BOOL)trackCommand:(id<MTLCommandBuffer>)command completion:(void (^)(id<MTLCommandBuffer>))body {
    [self assertQueue];
    if(self.closed || !command || command.status!=MTLCommandBufferStatusNotEnqueued) return NO;
    self.pending++;
    [command addCompletedHandler:^(id<MTLCommandBuffer> completed){
        dispatch_async(dispatch_get_main_queue(), ^{
            body(completed); // Existing per-view resource accounting first.
            NSAssert(self.pending>0,@"Unbalanced tracked Metal command");
            self.pending--;
            [self notifyIfDrained]; // Last tracked main-queue work, never before body.
        });
    }];
    return YES; // Caller must commit; absent completion stays pending, never faked.
}
- (void)closeWithCompletion:(dispatch_block_t)completion {
    [self assertQueue]; self.closed=YES;
    [self.waiters addObject:[completion copy]]; [self notifyIfDrained];
}
- (BOOL)reopen {
    [self assertQueue];
    if(self.pending || self.waiters.count || self.notifying) return NO;
    self.closed=NO; return YES;
}
@end
