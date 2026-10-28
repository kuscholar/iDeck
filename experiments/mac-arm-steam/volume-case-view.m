// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
// Report the verified process-local casefold view, never a changed physical FS.
// Only the experimental app's bundle/data roots participate. No permissions,
// ownership, signatures, security/authentication properties are altered.
#import <Foundation/Foundation.h>
#import <objc/runtime.h>
extern int IDeckCaseViewReady(void);
extern int IDeckCaseViewContains(const char *);
static BOOL (*OriginalGetResource)(id, SEL, id *, NSURLResourceKey, NSError **);
static BOOL ViewGetResource(id object, SEL selector, id *value, NSURLResourceKey key, NSError **error) {
    BOOL result = OriginalGetResource(object, selector, value, key, error);
    if (![key isEqualToString:NSURLVolumeSupportsCaseSensitiveNamesKey]) return result;
    BOOL enabled = [NSBundle.mainBundle.infoDictionary[@"IDeckCaseView"] boolValue];
    BOOL ready = IDeckCaseViewReady();
    BOOL scoped = IDeckCaseViewContains([(NSURL *)object fileSystemRepresentation]);
    if (result && value && enabled && ready && scoped) {
        *value = @NO;
        NSLog(@"[ideck-mac-case] resource-query view=casefold selftest=passed");
    } else {
        NSLog(@"[ideck-mac-case] resource-query unchanged result=%d enabled=%d ready=%d scoped=%d", result, enabled, ready, scoped);
    }
    return result;
}
__attribute__((constructor)) static void InstallCaseView(void) {
    Class concrete = object_getClass([NSURL fileURLWithPath:NSHomeDirectory()]);
    SEL selector = @selector(getResourceValue:forKey:error:);
    Method method = class_getInstanceMethod(concrete, selector);
    if (!method) return;
    OriginalGetResource = (void *)method_getImplementation(method);
    if (!class_addMethod(concrete, selector, (IMP)ViewGetResource, method_getTypeEncoding(method))) {
        class_replaceMethod(concrete, selector, (IMP)ViewGetResource, method_getTypeEncoding(method));
    }
}
