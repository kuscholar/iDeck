// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
// Narrow CPU RGBA8 bitmap storage used by SDL cursor construction. Does not
// implement NSImage drawing, cursor presentation, TIFF, planar or HDR formats.
#import <Foundation/Foundation.h>
#import <objc/runtime.h>
@interface NSBitmapImageRep : NSObject @end
static char StorageKey, RowKey, WidthKey, HeightKey;
@implementation NSBitmapImageRep (IDeckRGBA8)
- (instancetype)initWithBitmapDataPlanes:(unsigned char **)planes
                             pixelsWide:(NSInteger)width pixelsHigh:(NSInteger)height
                          bitsPerSample:(NSInteger)bits samplesPerPixel:(NSInteger)samples
                               hasAlpha:(BOOL)alpha isPlanar:(BOOL)planar
                         colorSpaceName:(NSString *)space bytesPerRow:(NSInteger)row
                           bitsPerPixel:(NSInteger)pixel {
    self = [super init];
    if (!self) return nil;
    if (width<=0 || height<=0 || bits!=8 || samples!=4 || !alpha || planar ||
        (pixel!=0 && pixel!=32) || width>16384 || height>16384 ||
        ![space isEqualToString:@"NSDeviceRGBColorSpace"]) return nil;
    if (row==0) row=width*4;
    if (row<width*4 || row>(64*1024*1024)/height) return nil;
    NSMutableData *data=[NSMutableData dataWithLength:(NSUInteger)(row*height)];
    if (!data) return nil;
    if (planes && planes[0]) memcpy(data.mutableBytes,planes[0],data.length);
    objc_setAssociatedObject(self,&StorageKey,data,OBJC_ASSOCIATION_RETAIN_NONATOMIC);
    objc_setAssociatedObject(self,&RowKey,@(row),OBJC_ASSOCIATION_RETAIN_NONATOMIC);
    objc_setAssociatedObject(self,&WidthKey,@(width),OBJC_ASSOCIATION_RETAIN_NONATOMIC);
    objc_setAssociatedObject(self,&HeightKey,@(height),OBJC_ASSOCIATION_RETAIN_NONATOMIC);
    return self;
}
- (unsigned char *)bitmapData { return [(NSMutableData *)objc_getAssociatedObject(self,&StorageKey) mutableBytes]; }
- (NSInteger)bytesPerRow { return [objc_getAssociatedObject(self,&RowKey) integerValue]; }
- (NSInteger)pixelsWide { return [objc_getAssociatedObject(self,&WidthKey) integerValue]; }
- (NSInteger)pixelsHigh { return [objc_getAssociatedObject(self,&HeightKey) integerValue]; }
@end
