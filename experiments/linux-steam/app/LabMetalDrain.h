// SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
#import <Foundation/Foundation.h>
#import <Metal/Metal.h>

// Main-queue admission plus actual command-completion bodies. This does not
// claim driver teardown, all GPU resources reclaimed or permission to run Wine.
@interface LabMetalDrain : NSObject
@property(nonatomic,readonly) BOOL closed;
@property(nonatomic,readonly) NSUInteger pending;
- (BOOL)trackCommand:(id<MTLCommandBuffer>)command completion:(void (^)(id<MTLCommandBuffer>))body;
- (void)closeWithCompletion:(dispatch_block_t)completion;
- (BOOL)reopen;
@end
