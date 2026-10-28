// SPDX-License-Identifier: GPL-3.0-or-later
#import <Foundation/Foundation.h>
#include <assert.h>
extern CFStringRef CGDisplayModeCopyPixelEncoding(const void *);
int main(void) {
    @autoreleasepool {
        assert(CGDisplayModeCopyPixelEncoding(NULL) == NULL);
        int mode = 1;
        for (int i = 0; i < 1000; ++i) {
            CFStringRef encoding = CGDisplayModeCopyPixelEncoding(&mode);
            assert(encoding && CFGetTypeID(encoding) == CFStringGetTypeID());
            assert(CFEqual(encoding, CFSTR("--------RRRRRRRRGGGGGGGGBBBBBBBB")));
            CFRelease(encoding);
        }
    }
    puts("pixel encoding: retained CFString, SDL comparison and null contract PASS");
}
