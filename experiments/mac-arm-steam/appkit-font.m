// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
// Narrow compatibility for the observed Steam updater font request.
#import <UIKit/UIKit.h>
#import <objc/runtime.h>

static id IDeckLabelFont(id cls, SEL selector, CGFloat size) {
    (void)cls; (void)selector;
    return [UIFont systemFontOfSize:size > 0 ? size : [UIFont labelFontSize]];
}
__attribute__((constructor)) static void InstallLabelFont(void) {
    Class font = NSClassFromString(@"NSFont");
    SEL selector = NSSelectorFromString(@"labelFontOfSize:");
    if (font && !class_getClassMethod(font, selector)) {
        BOOL added = class_addMethod(object_getClass(font), selector, (IMP)IDeckLabelFont, "@@:d");
        NSLog(@"[ideck-mac-font] labelFontOfSize bridge=%d", added);
    }
}
