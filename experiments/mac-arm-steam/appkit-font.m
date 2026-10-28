// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
// Narrow compatibility for the observed Steam updater font request.
#import <UIKit/UIKit.h>
#import <objc/runtime.h>
#import <math.h>
#import <CoreText/CoreText.h>
extern CGSize IDeckFontMaximumAdvancement(CTFontRef);
static CGSize IDeckMaximumAdvancement(UIFont *font, SEL selector) {
    (void)selector;
    CTFontRef named=CTFontCreateWithName((__bridge CFStringRef)font.fontName,font.pointSize,NULL);
    CGSize result=IDeckFontMaximumAdvancement(named);
    if (named) CFRelease(named);
    return result;
}


static id IDeckLabelFont(id cls, SEL selector, CGFloat size) {
    (void)cls; (void)selector;
    return [UIFont systemFontOfSize:size > 0 ? size : [UIFont labelFontSize]];
}
// Only the unrotated, uniformly scaled matrix used for ordinary UI fonts.
// Unsupported affine transforms return nil instead of pretending to render them.
static id IDeckMatrixFont(id cls, SEL selector, NSString *name, const CGFloat *matrix) {
    (void)cls; (void)selector;
    CGFloat size = matrix ? matrix[0] : 12;
    if (!isfinite(size) || size <= 0 || size > 1024) return nil;
    if (matrix && (matrix[1] != 0 || matrix[2] != 0 || matrix[3] != size || matrix[4] != 0 || matrix[5] != 0)) return nil;
    return [UIFont fontWithName:name size:size];
}
__attribute__((constructor)) static void InstallLabelFont(void) {
    // The current shim returns real UIFont objects for NSFont. The observed
    // request is horizontal named-font metrics, not arbitrary variation axes.
    SEL advance=NSSelectorFromString(@"maximumAdvancement");
    if (!class_getInstanceMethod([UIFont class],advance)) {
        BOOL added=class_addMethod([UIFont class],advance,(IMP)IDeckMaximumAdvancement,"{CGSize=dd}@:");
        NSLog(@"[ideck-mac-font] maximumAdvancement real-glyph-metrics bridge=%d",added);
    }
    Class font = NSClassFromString(@"NSFont");
    SEL selector = NSSelectorFromString(@"labelFontOfSize:");
    if (font && !class_getClassMethod(font, selector)) {
        BOOL added = class_addMethod(object_getClass(font), selector, (IMP)IDeckLabelFont, "@@:d");
        NSLog(@"[ideck-mac-font] labelFontOfSize bridge=%d", added);
    }
    SEL matrix = NSSelectorFromString(@"fontWithName:matrix:");
    if (font && !class_getClassMethod(font, matrix)) {
        BOOL added = class_addMethod(object_getClass(font), matrix, (IMP)IDeckMatrixFont, "@@:@^d");
        NSLog(@"[ideck-mac-font] uniform matrix font bridge=%d", added);
    }
}
