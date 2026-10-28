// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
#import <CoreText/CoreText.h>
#import <math.h>
// Horizontal maximum over actual advances of every glyph of the supplied font.
// No fabricated constant or bounding-box substitution. No font/account logging.
CGSize IDeckFontMaximumAdvancement(CTFontRef font) {
    if (!font) return CGSizeZero;
    CFIndex count=CTFontGetGlyphCount(font);
    if (count<0 || count>65536) return CGSizeZero;
    CGSize result=CGSizeZero;
    for (CFIndex base=0;base<count;base+=256) {
        CGGlyph glyphs[256];CGSize advances[256];CFIndex n=(count-base<256?count-base:256);
        for (CFIndex j=0;j<n;++j) glyphs[j]=(CGGlyph)(base+j);
        CTFontGetAdvancesForGlyphs(font,kCTFontOrientationHorizontal,glyphs,advances,n);
        for (CFIndex j=0;j<n;++j) {
            if (isfinite(advances[j].width)) result.width=fmax(result.width,advances[j].width);
            if (isfinite(advances[j].height)) result.height=fmax(result.height,advances[j].height);
        }
    }
    return result;
}
