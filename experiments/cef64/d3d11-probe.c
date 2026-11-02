/* SPDX-License-Identifier: GPL-3.0-or-later
 * Madeira Converter Exception: see LICENSE-EXCEPTION.md
 * Own diagnostic program. No Steam, account, game or Valve binary input. */
#define COBJMACROS
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <d3d11.h>
#include <stdio.h>

_Static_assert(sizeof(void *) == 8, "Build this probe for AMD64");

int wmain(void)
{
    FILE *out = _wfopen(L"C:\\ideck-d3d11-results.txt", L"w");
    SYSTEM_INFO info;
    if (!out) return 3;
    GetSystemInfo(&info);
    fprintf(out, "ideck-d3d11-probe version=1 pointer_bits=64 processors=%lu\n",
            (unsigned long)info.dwNumberOfProcessors);
    fflush(out);

    SetLastError(0);
    HMODULE module = LoadLibraryW(L"d3d11.dll");
    DWORD error = GetLastError();
    fprintf(out, "LoadLibrary_d3d11=%d win32_error=%lu module_base=%p\n",
            module != NULL, (unsigned long)error, (void *)module);
    fflush(out);
    if (!module) { fclose(out); return 1; }

    PFN_D3D11_CREATE_DEVICE create =
        (PFN_D3D11_CREATE_DEVICE)(void *)GetProcAddress(module, "D3D11CreateDevice");
    if (!create)
    {
        fprintf(out, "D3D11CreateDevice_export=0 win32_error=%lu\n",
                (unsigned long)GetLastError());
        FreeLibrary(module);
        fclose(out);
        return 2;
    }

    ID3D11Device *device = NULL;
    ID3D11DeviceContext *context = NULL;
    D3D_FEATURE_LEVEL level = 0;
    HRESULT hr = create(NULL, D3D_DRIVER_TYPE_HARDWARE, NULL, 0, NULL, 0,
                        D3D11_SDK_VERSION, &device, &level, &context);
    fprintf(out, "D3D11CreateDevice_hresult=0x%08lx device=%d context=%d feature_level=0x%x\n",
            (unsigned long)(ULONG)hr, device != NULL, context != NULL, (unsigned)level);
    fflush(out);
    int success = SUCCEEDED(hr) && device && context;
    if (context) ID3D11DeviceContext_Release(context);
    if (device) ID3D11Device_Release(device);
    FreeLibrary(module);
    fprintf(out, "result=%s; no rendering/input/gameplay claim\n", success ? "PASS" : "FAIL");
    fclose(out);
    return success ? 0 : 2;
}
