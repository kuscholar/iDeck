/*
 * wineios.drv — minimal iOS audio driver PE stub for Madeira.
 *
 * Just exists to satisfy mmdevapi's __wine_load_unix_lib at the PE-load
 * stage. All real driver behavior is on the unix side, statically linked
 * into Madeira.app via libntdll_unix.a (see audio_null_ios.c).
 *
 * No windows.h includes to avoid mingw/Wine header collisions with the
 * cross-compile toolchain.
 */

typedef int BOOL;
typedef void *HINSTANCE;
typedef void *LPVOID;
typedef unsigned long DWORD;

#define DLL_PROCESS_ATTACH 1

__attribute__((visibility("default")))
BOOL __stdcall DllMain(HINSTANCE inst, DWORD reason, LPVOID reserved)
{
    (void)inst; (void)reason; (void)reserved;
    return 1;
}
