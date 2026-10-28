// SPDX-License-Identifier: GPL-3.0-or-later
#import <Foundation/Foundation.h>
#include <assert.h>
@interface NSBitmapImageRep : NSObject @end
@implementation NSBitmapImageRep @end
@interface NSBitmapImageRep (TestAPI)
- (instancetype)initWithBitmapDataPlanes:(unsigned char **)planes pixelsWide:(NSInteger)w pixelsHigh:(NSInteger)h bitsPerSample:(NSInteger)b samplesPerPixel:(NSInteger)s hasAlpha:(BOOL)a isPlanar:(BOOL)p colorSpaceName:(NSString *)n bytesPerRow:(NSInteger)r bitsPerPixel:(NSInteger)pixel;
- (unsigned char *)bitmapData;
- (NSInteger)bytesPerRow;
@end
int main(void) {
    @autoreleasepool {
        NSBitmapImageRep *rep=[[NSBitmapImageRep alloc] initWithBitmapDataPlanes:NULL pixelsWide:32 pixelsHigh:32 bitsPerSample:8 samplesPerPixel:4 hasAlpha:YES isPlanar:NO colorSpaceName:@"NSDeviceRGBColorSpace" bytesPerRow:128 bitsPerPixel:32];
        assert(rep && rep.bitmapData && rep.bytesPerRow==128);
        for(int i=0;i<4096;++i) assert(rep.bitmapData[i]==0);
        memset(rep.bitmapData,0x5a,4096); assert(rep.bitmapData[4095]==0x5a);
        assert(![[NSBitmapImageRep alloc] initWithBitmapDataPlanes:NULL pixelsWide:32 pixelsHigh:32 bitsPerSample:8 samplesPerPixel:4 hasAlpha:YES isPlanar:NO colorSpaceName:@"NSDeviceRGBColorSpace" bytesPerRow:127 bitsPerPixel:32]);
        assert(![[NSBitmapImageRep alloc] initWithBitmapDataPlanes:NULL pixelsWide:NSIntegerMax pixelsHigh:32 bitsPerSample:8 samplesPerPixel:4 hasAlpha:YES isPlanar:NO colorSpaceName:@"NSDeviceRGBColorSpace" bytesPerRow:0 bitsPerPixel:32]);
        assert(![[NSBitmapImageRep alloc] initWithBitmapDataPlanes:NULL pixelsWide:32 pixelsHigh:32 bitsPerSample:16 samplesPerPixel:4 hasAlpha:YES isPlanar:NO colorSpaceName:@"NSDeviceRGBColorSpace" bytesPerRow:0 bitsPerPixel:64]);
    }
    puts("RGBA8 bitmap: zeroed writable storage, row bounds, overflow and unsupported format PASS");
}
