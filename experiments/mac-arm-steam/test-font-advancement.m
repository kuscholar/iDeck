// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
#import <CoreText/CoreText.h>
#import <assert.h>
#import <math.h>
#import <stdio.h>
extern CGSize IDeckFontMaximumAdvancement(CTFontRef);
int main(void) {
    assert(CGSizeEqualToSize(IDeckFontMaximumAdvancement(NULL),CGSizeZero));
    CTFontRef a=CTFontCreateWithName(CFSTR("Helvetica"),12,NULL);
    CTFontRef b=CTFontCreateWithName(CFSTR("Helvetica"),24,NULL);assert(a&&b);
    CGSize small=IDeckFontMaximumAdvancement(a),large=IDeckFontMaximumAdvancement(b);
    assert(small.width>0 && isfinite(small.width) && fabs(large.width-2*small.width)<0.0001);
    CFIndex count=CTFontGetGlyphCount(a);
    for (CFIndex i=0;i<count;++i) {CGGlyph g=(CGGlyph)i;CGSize v;CTFontGetAdvancesForGlyphs(a,kCTFontOrientationHorizontal,&g,&v,1);assert(v.width<=small.width && v.height<=small.height);}
    CFRelease(a);CFRelease(b);puts("font advancement PASS: actual glyph bounds and font-size scaling, NULL safety");
}
