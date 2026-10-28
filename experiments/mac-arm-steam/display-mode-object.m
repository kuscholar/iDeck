// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
// The reference has one emulated SDR mode. Its token must be a genuine CF
// object: SDL stores modes in arrays with kCFTypeArrayCallBacks.
#import <Foundation/Foundation.h>
typedef const void *IDeckDisplayMode;
static CFDictionaryRef Mode(void) {
    static CFDictionaryRef mode;
    static dispatch_once_t once;
    dispatch_once(&once, ^{
        const void *keys[] = {CFSTR("IDeckSingleScreenMode")};
        const void *values[] = {kCFBooleanTrue};
        mode = CFDictionaryCreate(kCFAllocatorDefault, keys, values, 1,
                                  &kCFTypeDictionaryKeyCallBacks, &kCFTypeDictionaryValueCallBacks);
    });
    return mode;
}
IDeckDisplayMode CGDisplayCopyDisplayMode(uint32_t display) {
    if (display != 1) return NULL;
    return CFRetain(Mode());
}
CFArrayRef CGDisplayCopyAllDisplayModes(uint32_t display, CFDictionaryRef options) {
    (void)options;
    if (display != 1) return NULL;
    const void *mode = Mode();
    return CFArrayCreate(kCFAllocatorDefault, &mode, 1, &kCFTypeArrayCallBacks);
}
void CGDisplayModeRelease(IDeckDisplayMode mode) { if (mode) CFRelease(mode); }
IDeckDisplayMode CGDisplayModeRetain(IDeckDisplayMode mode) { return mode ? CFRetain(mode) : NULL; }
