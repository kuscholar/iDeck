/* iOS override for dlls/win32u/freetype.c.
 *
 * On iOS freetype is linked statically (build/freetype-ios/libfreetype.a is
 * merged into libwin32u_unix.a), so the upstream dlopen(SONAME_LIBFREETYPE)
 * + dlsym pattern can't work. We rewrite dlopen/dlsym/dlclose to a direct
 * symbol table resolved by the static linker.
 *
 * config_ios.h force-#undefs HAVE_FT2BUILD_H/SONAME_LIBFREETYPE for every
 * other TU; re-enable them here only. Fontconfig stays disabled.
 */

#define HAVE_FT2BUILD_H 1
#define HAVE_FREETYPE 1
#define SONAME_LIBFREETYPE "libfreetype.a"

/* Rewrites apply to <dlfcn.h>'s prototypes too, which is why the shims are
 * non-static and match dlfcn.h's signatures exactly. */
#define dlopen  ios_ft_dlopen
#define dlsym   ios_ft_dlsym
#define dlclose ios_ft_dlclose

/* Kill the __APPLE__ system-font sweep (load_mac_fonts): enumerating iOS
 * system fonts via CoreText crashed AddFontToList on a font wine can't
 * parse (2026-07-06 log: NULL-name deref → unhandled-fault cascade that
 * corrupted the thread and hung font_init in add_gdi_font_subst). We only
 * want the prefix's C:\windows\fonts anyway. Renaming the collection
 * constructor to a NULL-returning stub makes load_mac_fonts bail on its
 * existing !col early-out; the header's declaration is renamed too, so
 * the stub definition below just implements that prototype. */
#define CTFontCollectionCreateFromAvailableFonts ios_ft_null_collection

#include "freetype.c"

CTFontCollectionRef ios_ft_null_collection( CFDictionaryRef options )
{
    (void)options;
    return NULL;
}

#undef CTFontCollectionCreateFromAvailableFonts

#undef dlopen
#undef dlsym
#undef dlclose

static void *ios_ft_sentinel = (void *)&ios_ft_sentinel;

void *ios_ft_dlopen( const char *path, int mode )
{
    if (path && strstr( path, "freetype" )) return ios_ft_sentinel;
    return NULL;
}

int ios_ft_dlclose( void *handle )
{
    return 0;
}

void *ios_ft_dlsym( void *handle, const char *symbol )
{
    if (handle != ios_ft_sentinel) return NULL;
#define IOS_FT_SYM(f) if (!strcmp( symbol, #f )) return (void *)f;
    IOS_FT_SYM(FT_Done_Face)
    IOS_FT_SYM(FT_Get_Char_Index)
    IOS_FT_SYM(FT_Get_First_Char)
    IOS_FT_SYM(FT_Get_Next_Char)
    IOS_FT_SYM(FT_Get_Sfnt_Name)
    IOS_FT_SYM(FT_Get_Sfnt_Name_Count)
    IOS_FT_SYM(FT_Get_Sfnt_Table)
    IOS_FT_SYM(FT_Get_TrueType_Engine_Type)
    IOS_FT_SYM(FT_Get_WinFNT_Header)
    IOS_FT_SYM(FT_Init_FreeType)
    IOS_FT_SYM(FT_Library_SetLcdFilter)
    IOS_FT_SYM(FT_Library_Version)
    IOS_FT_SYM(FT_Load_Glyph)
    IOS_FT_SYM(FT_Load_Sfnt_Table)
    IOS_FT_SYM(FT_Matrix_Multiply)
    IOS_FT_SYM(FT_MulDiv)
#ifndef FT_MULFIX_INLINED
    IOS_FT_SYM(FT_MulFix)
#endif
    IOS_FT_SYM(FT_New_Face)
    IOS_FT_SYM(FT_New_Memory_Face)
    IOS_FT_SYM(FT_Outline_Embolden)
    IOS_FT_SYM(FT_Outline_Get_Bitmap)
    IOS_FT_SYM(FT_Outline_Get_CBox)
    IOS_FT_SYM(FT_Outline_Transform)
    IOS_FT_SYM(FT_Outline_Translate)
    IOS_FT_SYM(FT_Property_Set)
    IOS_FT_SYM(FT_Render_Glyph)
    IOS_FT_SYM(FT_Set_Charmap)
    IOS_FT_SYM(FT_Set_Pixel_Sizes)
    IOS_FT_SYM(FT_Vector_Length)
    IOS_FT_SYM(FT_Vector_Transform)
    IOS_FT_SYM(FT_Vector_Unit)
#undef IOS_FT_SYM
    return NULL;
}
