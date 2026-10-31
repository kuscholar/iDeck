// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
#import <Foundation/Foundation.h>
#include <assert.h>
#include <stdio.h>
extern void IDeckWindowMakeMain(id);
@interface Window : NSObject
@property(weak) id delegate;
- (void)makeMainWindow;
- (void)makeKeyAndOrderFront:(id)sender;
@end
@implementation Window
- (void)makeMainWindow { IDeckWindowMakeMain(self); }
- (void)makeKeyAndOrderFront:(id)sender { (void)sender; }
@end
// Same callback direction as the observed Steam subclass: order-front asks the
// base to become main. A base implementation that calls order-front recurses.
@interface ReentrantWindow : Window
@property unsigned orderCalls;
@end
@implementation ReentrantWindow
- (void)makeKeyAndOrderFront:(id)sender {
    (void)sender; ++self.orderCalls; assert(self.orderCalls<3);
    [self makeMainWindow];
}
@end
@interface Delegate : NSObject
@property unsigned became,resigned;
@end
@implementation Delegate
- (void)windowDidBecomeMain:(NSNotification*)event {
    ++self.became; [(Window*)event.object makeMainWindow];
}
- (void)windowDidResignMain:(NSNotification*)event {
    (void)event; ++self.resigned;
}
@end
int main(void) { @autoreleasepool {
    Delegate* a=[Delegate new];Delegate* b=[Delegate new];
    ReentrantWindow* first=[ReentrantWindow new];first.delegate=a;
    ReentrantWindow* second=[ReentrantWindow new];second.delegate=b;
    __block unsigned notifications=0;
    id observer=[NSNotificationCenter.defaultCenter addObserverForName:@"NSWindowDidBecomeMainNotification" object:nil queue:nil usingBlock:^(NSNotification* event){
        ++notifications;[(Window*)event.object makeMainWindow];
    }];
    [first makeMainWindow];[first makeMainWindow];
    assert(first.orderCalls==0 && a.became==1 && notifications==1);
    [first makeKeyAndOrderFront:nil];assert(first.orderCalls==1 && a.became==1);
    [second makeMainWindow];assert(a.resigned==1 && b.became==1 && notifications==2);
    [first makeMainWindow];assert(b.resigned==1 && a.became==2 && notifications==3);
    IDeckWindowMakeMain(nil);assert(notifications==3);
    [NSNotificationCenter.defaultCenter removeObserver:observer];
    puts("window main PASS: no order-front dispatch, delegate/observer reentry idempotent, focus transition notifications preserved");
} return 0; }
