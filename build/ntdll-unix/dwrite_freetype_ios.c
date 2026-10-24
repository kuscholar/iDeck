/* iOS override for dlls/dwrite/freetype.c  (ml494)
 *
 * WHY THIS EXISTS
 * ---------------
 * dwrite.dll had NO unixlib on iOS at all. Its PE side calls
 * __wine_unix_call() for every glyph operation, so with no unix side every
 * call failed and get_glyph_bbox() never ran — leaving each glyph's bbox
 * empty. ml494 caught the consequence exactly: 12/12
 * [dwrite-bounds] ... bounds=(0,0)-(0,0) EMPTY, and [dwrite-ink] never
 * fired at all, because a caller that is told a glyph run has zero extent
 * has no reason to ask for its alpha texture. That is invisible text with
 * no error reported anywhere — the Steam login page painted its boxes,
 * SVG logo and QR code while every label, placeholder and button caption
 * silently rendered nothing.
 *
 * Same shape as build/win32u-unix/freetype_ios.c: freetype is linked
 * statically on iOS (build/freetype-ios/build/libfreetype.a, merged into
 * libwin32u_unix.a and linked into the same Mach-O), so the upstream
 * dlopen(SONAME_LIBFREETYPE) + dlsym pattern cannot work. Rewrite
 * dlopen/dlsym/dlclose to a direct symbol table resolved by the static
 * linker.
 *
 * config_ios.h force-#undefs HAVE_FT2BUILD_H/SONAME_LIBFREETYPE for every
 * other TU; re-enable them here only.
 */

#undef HAVE_FT2BUILD_H
#undef HAVE_FREETYPE
#undef SONAME_LIBFREETYPE
#define HAVE_FT2BUILD_H 1
#define HAVE_FREETYPE 1
#define SONAME_LIBFREETYPE "libfreetype.a"

/* Rewrites apply to <dlfcn.h>'s prototypes too, which is why the shims are
 * non-static and match dlfcn.h's signatures exactly. */
#define dlopen  ios_dwft_dlopen
#define dlsym   ios_dwft_dlsym
#define dlclose ios_dwft_dlclose

#include "freetype.c"

#undef dlopen
#undef dlsym
#undef dlclose

static void *ios_dwft_sentinel = (void *)&ios_dwft_sentinel;

void *ios_dwft_dlopen( const char *path, int mode )
{
    (void)mode;
    if (path && strstr( path, "freetype" )) return ios_dwft_sentinel;
    return NULL;
}

int ios_dwft_dlclose( void *handle )
{
    (void)handle;
    return 0;
}

/* Exactly the symbols dwrite's MAKE_FUNCPTR block asks for. Kept as a
 * table rather than a chain of strcmp()s so a symbol that upstream adds
 * later fails LOUDLY at its dlsym (the caller's "Can't find symbol" WARN +
 * goto sym_not_found) instead of silently resolving to NULL and
 * reintroducing the empty-bbox failure this file exists to fix. */
#define IOS_DWFT_SYM(f) { #f, (void *)&f }
static const struct { const char *name; void *addr; } ios_dwft_syms[] =
{
    IOS_DWFT_SYM(FT_Activate_Size),
    IOS_DWFT_SYM(FT_Done_Face),
    IOS_DWFT_SYM(FT_Done_FreeType),
    IOS_DWFT_SYM(FT_Done_Glyph),
    IOS_DWFT_SYM(FT_Done_Size),
    IOS_DWFT_SYM(FT_Get_First_Char),
    IOS_DWFT_SYM(FT_Get_Glyph),
    IOS_DWFT_SYM(FT_Get_Kerning),
    IOS_DWFT_SYM(FT_Get_Sfnt_Table),
    IOS_DWFT_SYM(FT_Glyph_Copy),
    IOS_DWFT_SYM(FT_Glyph_Get_CBox),
    IOS_DWFT_SYM(FT_Glyph_Transform),
    IOS_DWFT_SYM(FT_Init_FreeType),
    IOS_DWFT_SYM(FT_Library_Version),
    IOS_DWFT_SYM(FT_Load_Glyph),
    IOS_DWFT_SYM(FT_Matrix_Multiply),
    IOS_DWFT_SYM(FT_MulDiv),
    IOS_DWFT_SYM(FT_New_Memory_Face),
    IOS_DWFT_SYM(FT_New_Size),
    IOS_DWFT_SYM(FT_Outline_Copy),
    IOS_DWFT_SYM(FT_Outline_Decompose),
    IOS_DWFT_SYM(FT_Outline_Done),
    IOS_DWFT_SYM(FT_Outline_EmboldenXY),
    IOS_DWFT_SYM(FT_Outline_Get_Bitmap),
    IOS_DWFT_SYM(FT_Outline_New),
    IOS_DWFT_SYM(FT_Outline_Transform),
    IOS_DWFT_SYM(FT_Outline_Translate),
    IOS_DWFT_SYM(FT_Set_Pixel_Sizes),
};
#undef IOS_DWFT_SYM

void *ios_dwft_dlsym( void *handle, const char *symbol )
{
    unsigned int i;

    if (handle != ios_dwft_sentinel || !symbol) return NULL;
    for (i = 0; i < sizeof(ios_dwft_syms) / sizeof(ios_dwft_syms[0]); i++)
        if (!strcmp( symbol, ios_dwft_syms[i].name )) return ios_dwft_syms[i].addr;
    return NULL;
}
