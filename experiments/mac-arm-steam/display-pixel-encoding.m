// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
// Single-screen SDR mode contract for the public reference's emulated mode.
// No HDR, display switching, framebuffer capture or CEF rendering is implied.
#import <Foundation/Foundation.h>
CFStringRef CGDisplayModeCopyPixelEncoding(const void *mode) CF_RETURNS_RETAINED;
CFStringRef CGDisplayModeCopyPixelEncoding(const void *mode) {
    if (!mode) return NULL;
    // IO32BitDirectPixels, matching SDL's ARGB8888 display-mode descriptor.
    return CFStringCreateCopy(kCFAllocatorDefault, CFSTR("--------RRRRRRRRGGGGGGGGBBBBBBBB"));
}
