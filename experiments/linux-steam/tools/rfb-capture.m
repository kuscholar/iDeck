/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * Host-only real-frame control using the pinned LinuxRunner RFB client.
 * Password and image artifacts stay private. This does not prove Steam paint.
 */
#import <Foundation/Foundation.h>
#import <ImageIO/ImageIO.h>
#import <CoreGraphics/CoreGraphics.h>
#import "RFBClient.h"
#include <stdatomic.h>

int main(int argc, char **argv) {
    @autoreleasepool {
        if (argc != 4) return 2;
        char *end = NULL;
        long port = strtol(argv[1], &end, 10);
        if (!end || *end || port < 1024 || port > 65535) return 2;
        NSString *password = [NSString stringWithContentsOfFile:@(argv[2]) encoding:NSUTF8StringEncoding error:nil];
        password = [password stringByTrimmingCharactersInSet:NSCharacterSet.newlineCharacterSet];
        if (!password || [password lengthOfBytesUsingEncoding:NSUTF8StringEncoding] != 8) return 2;
        NSURL *destination = [NSURL fileURLWithPath:@(argv[3])];
        if ([NSFileManager.defaultManager fileExistsAtPath:destination.path]) return 2;
        dispatch_semaphore_t done = dispatch_semaphore_create(0);
        __block atomic_bool captured = false;
        __block BOOL saved = NO;
        LRRFBClient *client = [[LRRFBClient alloc] initWithPort:(uint16_t)port password:password];
        client.frameHandler = ^(NSData *pixels, uint16_t width, uint16_t height, uint64_t count, uint64_t bytes) {
            if (atomic_exchange(&captured, true)) return;
            CGColorSpaceRef color = CGColorSpaceCreateDeviceRGB();
            CGDataProviderRef provider = CGDataProviderCreateWithCFData((__bridge CFDataRef)pixels);
            CGImageRef frame = CGImageCreate(width, height, 8, 32, width * 4, color,
                kCGBitmapByteOrder32Little | kCGImageAlphaNoneSkipFirst, provider, NULL, false, kCGRenderingIntentDefault);
            CGImageDestinationRef output = frame ? CGImageDestinationCreateWithURL((__bridge CFURLRef)destination, CFSTR("public.png"), 1, NULL) : NULL;
            if (output) {
                CGImageDestinationAddImage(output, frame, NULL);
                saved = CGImageDestinationFinalize(output);
                CFRelease(output);
            }
            if (frame) CGImageRelease(frame);
            CGDataProviderRelease(provider);
            CGColorSpaceRelease(color);
            printf("RFB_FRAME width=%u height=%u frames=%llu bytes=%llu saved=%d steam_ui=UNVERIFIED\n",
                width, height, (unsigned long long)count, (unsigned long long)bytes, saved);
            dispatch_semaphore_signal(done);
        };
        client.statusHandler = ^(NSString *status) {
            if([status hasPrefix:@"Display error:"] && !atomic_exchange(&captured,true)) {
                puts("RFB_ERROR frame_unavailable");dispatch_semaphore_signal(done);
            }
        };
        [client start];
        long timedOut = dispatch_semaphore_wait(done, dispatch_time(DISPATCH_TIME_NOW, 45 * NSEC_PER_SEC));
        [client stop];
        return timedOut || !saved;
    }
}
