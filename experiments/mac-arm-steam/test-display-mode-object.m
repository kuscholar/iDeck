// SPDX-License-Identifier: GPL-3.0-or-later
#import <Foundation/Foundation.h>
#include <assert.h>
extern const void *CGDisplayCopyDisplayMode(uint32_t);
extern CFArrayRef CGDisplayCopyAllDisplayModes(uint32_t, CFDictionaryRef);
extern const void *CGDisplayModeRetain(const void *);
extern void CGDisplayModeRelease(const void *);
int main(void) {
    @autoreleasepool {
        assert(!CGDisplayCopyDisplayMode(0));
        assert(!CGDisplayCopyAllDisplayModes(2, NULL));
        assert(!CGDisplayModeRetain(NULL)); CGDisplayModeRelease(NULL);
        for (int i=0; i<1000; ++i) {
            const void *mode = CGDisplayCopyDisplayMode(1);
            CFArrayRef all = CGDisplayCopyAllDisplayModes(1, NULL);
            assert(CFArrayGetCount(all)==1 && CFEqual(mode, CFArrayGetValueAtIndex(all,0)));
            CFMutableArrayRef sdl = CFArrayCreateMutable(NULL,0,&kCFTypeArrayCallBacks);
            CFArrayAppendValue(sdl,mode);
            const void *held=CGDisplayModeRetain(mode);
            CGDisplayModeRelease(mode); CFRelease(all);
            assert(CFEqual(held,CFArrayGetValueAtIndex(sdl,0)));
            CFRelease(sdl); CGDisplayModeRelease(held);
        }
    }
    puts("display mode: SDL CF-array ownership and invalid-display contracts PASS");
}
