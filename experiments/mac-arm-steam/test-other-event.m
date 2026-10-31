// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
#import "other-event.h"
#include <assert.h>
#include <limits.h>
typedef NSUInteger NSEventType;
@interface NSEvent : NSObject
@property NSEventType type;
@property CGPoint locationInWindow;
@property NSTimeInterval timestamp;
@property NSUInteger modifierFlags;
IDECK_OTHER_EVENT_FIELDS
@end
@implementation NSEvent
IDECK_OTHER_EVENT_FACTORY
@end
int main(void) { @autoreleasepool {
    _Static_assert(sizeof(NSInteger)==8 && sizeof(short)==2,"LP64 event ABI");
    for(NSUInteger type=13;type<=16;++type) {
        NSEvent* event=[NSEvent otherEventWithType:type location:CGPointMake(-7.25,23.5)
            modifierFlags:1ULL<<40 timestamp:1234.25 windowNumber:-2 context:nil
            subtype:SHRT_MIN data1:LONG_MIN data2:LONG_MAX];
        assert(event && event.type==type && event.locationInWindow.x==-7.25 && event.locationInWindow.y==23.5);
        assert(event.modifierFlags==(1ULL<<40) && event.timestamp==1234.25 && event.windowNumber==-2);
        assert(event.subtype==SHRT_MIN && event.data1==LONG_MIN && event.data2==LONG_MAX);
        NSMutableArray* queue=[NSMutableArray new];[queue insertObject:event atIndex:0];
        assert(queue.firstObject==event && queue.count==1);
    }
    BOOL rejected=NO;
    @try { (void)[NSEvent otherEventWithType:1 location:CGPointZero modifierFlags:0 timestamp:0 windowNumber:0 context:nil subtype:0 data1:0 data2:0]; }
    @catch(NSException* exception) {rejected=[exception.name isEqualToString:NSInternalInconsistencyException];}
    assert(rejected);
    puts("other event PASS: all custom types, signed16/64bit payloads, queue insertion and invalid-type exception");
} return 0; }
