// SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
#import "MetalFramebufferView.h"
// Only link against the explicit generated framebuffer with LabMetalDrain.
@interface LRMetalFramebufferView (LabMetalFramebufferDrain)
- (void)ideckCloseMetalWithCompletion:(dispatch_block_t)completion;
- (BOOL)ideckReopenMetal;
@end
