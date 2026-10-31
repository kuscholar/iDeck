// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
// Shared by the generated NSEvent implementation and the ABI contract fixture.
// No event payload is logged. The obsolete graphics-context argument is unused.
#import <Foundation/Foundation.h>
#import <CoreGraphics/CoreGraphics.h>
#include <stdio.h>
#define IDECK_OTHER_EVENT_FIELDS \
    @property(nonatomic) short subtype; \
    @property(nonatomic) NSInteger data1, data2, windowNumber;
#define IDECK_OTHER_EVENT_FACTORY \
+ (instancetype)otherEventWithType:(NSEventType)type location:(CGPoint)location \
    modifierFlags:(NSUInteger)flags timestamp:(NSTimeInterval)timestamp \
    windowNumber:(NSInteger)number context:(id)context subtype:(short)subtype \
    data1:(NSInteger)first data2:(NSInteger)second { \
    (void)context; \
    if (type<13 || type>16) \
        [NSException raise:NSInternalInconsistencyException format:@"Unsupported custom event type"]; \
    NSEvent* event=[self new]; \
    [event setType:type];[event setLocationInWindow:location]; \
    [event setModifierFlags:flags];[event setTimestamp:timestamp]; \
    [event setWindowNumber:number];[event setSubtype:subtype]; \
    [event setData1:first];[event setData2:second]; \
    static dispatch_once_t once; \
    dispatch_once(&once,^{fprintf(stderr,"[ideck-mac-event] other-event factory=1 fields-preserved=1\n");}); \
    return event; \
}
