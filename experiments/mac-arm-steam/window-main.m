// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
// AppKit makeMainWindow changes focus; it must not dispatch order-front again.
// Main-thread contract, like the surrounding UIKit-backed AppKit window shim.
#import <Foundation/Foundation.h>
#import <objc/message.h>
@protocol IDeckWindowDelegateAccess
- (id)delegate;
@end
static __weak id currentMainWindow;
static void Notify(id window, NSString* suffix) {
    if (!window) return;
    NSNotification* event=[NSNotification notificationWithName:
        [NSString stringWithFormat:@"NSWindow%@Notification",suffix] object:window];
    id delegate=[(id<IDeckWindowDelegateAccess>)window delegate];
    SEL selector=NSSelectorFromString([NSString stringWithFormat:@"window%@:",suffix]);
    if ([delegate respondsToSelector:selector])
        ((void(*)(id,SEL,id))objc_msgSend)(delegate,selector,event);
    [NSNotificationCenter.defaultCenter postNotification:event];
}
void IDeckWindowMakeMain(id window) {
    if (!window || currentMainWindow==window) return;
    id previous=currentMainWindow;
    // Commit state before callbacks: repeated requests from delegate/observers
    // are idempotent, rather than another makeKeyAndOrderFront virtual dispatch.
    currentMainWindow=window;
    Notify(previous,@"DidResignMain");
    Notify(window,@"DidBecomeMain");
}
