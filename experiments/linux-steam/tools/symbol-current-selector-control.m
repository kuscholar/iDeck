/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#import <Foundation/Foundation.h>
@interface IDECKNamespaceSelectorControl : NSObject
+ (unsigned)current;
@end
@implementation IDECKNamespaceSelectorControl
+ (unsigned)current { return 17; }
@end
int ideck_test_current_selector(void) {
    @autoreleasepool {
        return [NSStringFromSelector(@selector(current)) isEqualToString:@"current"] &&
               [IDECKNamespaceSelectorControl current] == 17;
    }
}
