/* dxchkmsaa — isolates the Thumper wall.
 *
 * Calls D3D11CreateDevice → ID3D11Device::CheckMultisampleQualityLevels.
 * If this PE crashes the same way as Thumper at vtable[30], we've isolated
 * the ARM64EC dispatch bug outside the game.
 * If this PE succeeds, the wall is Thumper-specific (state corruption via
 * steam_api64 indirection).
 *
 * Built x86_64 mingw → runs via FEX on iOS → DXMT/Metal stack same as cube.
 */
#include <windows.h>

typedef HRESULT (WINAPI *D3D11CreateDeviceFn)(
    void *pAdapter,
    UINT DriverType,
    HMODULE Software,
    UINT Flags,
    const UINT *pFeatureLevels,
    UINT FeatureLevels,
    UINT SDKVersion,
    void **ppDevice,
    UINT *pFeatureLevel,
    void **ppImmediateContext);

#define D3D11_SDK_VERSION 7
#define D3D_DRIVER_TYPE_HARDWARE 1
#define DXGI_FORMAT_R8G8B8A8_UNORM 28

/* ID3D11Device vtable layout (Microsoft). Slot 30 = CheckMultisampleQualityLevels.
 * IUnknown(3) + ID3D11Device starts at 3. */
typedef struct ID3D11DeviceVtbl {
    void *QueryInterface;       /* 0 */
    void *AddRef;               /* 1 */
    void *Release;              /* 2 */
    void *CreateBuffer;         /* 3 */
    void *CreateTexture1D;
    void *CreateTexture2D;
    void *CreateTexture3D;
    void *CreateShaderResourceView;
    void *CreateUnorderedAccessView;
    void *CreateRenderTargetView;
    void *CreateDepthStencilView;
    void *CreateInputLayout;
    void *CreateVertexShader;
    void *CreateGeometryShader;
    void *CreateGeometryShaderWithStreamOutput;
    void *CreatePixelShader;
    void *CreateHullShader;
    void *CreateDomainShader;
    void *CreateComputeShader;
    void *CreateClassLinkage;
    void *CreateBlendState;
    void *CreateDepthStencilState;
    void *CreateRasterizerState;
    void *CreateSamplerState;
    void *CreateQuery;
    void *CreatePredicate;
    void *CreateCounter;
    void *CreateDeferredContext;
    void *OpenSharedResource;
    void *CheckFormatSupport;
    HRESULT (WINAPI *CheckMultisampleQualityLevels)(  /* slot 30 */
        void *This, UINT Format, UINT SampleCount, UINT *pNumQualityLevels);
    /* ... rest not used here ... */
} ID3D11DeviceVtbl;

typedef struct ID3D11Device {
    ID3D11DeviceVtbl *lpVtbl;
} ID3D11Device;

static HANDLE g_stdout;

static int strlen_c(const char *s) { int n = 0; while (s[n]) n++; return n; }

static void put_str(const char *s) {
    DWORD w; WriteFile(g_stdout, s, strlen_c(s), &w, NULL);
}

static void put_hex(unsigned long long v) {
    char buf[20]; int n = 0;
    if (v == 0) { put_str("0x0"); return; }
    char tmp[18];
    while (v) { int d = v & 0xf; tmp[n++] = d < 10 ? '0' + d : 'a' + d - 10; v >>= 4; }
    buf[0]='0'; buf[1]='x';
    for (int i = 0; i < n; i++) buf[2+i] = tmp[n-1-i];
    buf[2+n] = 0;
    DWORD w; WriteFile(g_stdout, buf, 2+n, &w, NULL);
}

int main(void) {
    g_stdout = GetStdHandle(STD_OUTPUT_HANDLE);
    put_str("=== dxchkmsaa: Thumper vtable[30] isolation test ===\n");

    /* Load d3d11.dll dynamically to avoid linker-time import. */
    HMODULE d3d11 = LoadLibraryA("d3d11.dll");
    if (!d3d11) { put_str("LoadLibrary d3d11.dll FAILED\n"); ExitProcess(1); }
    put_str("d3d11.dll loaded at "); put_hex((unsigned long long)d3d11); put_str("\n");

    D3D11CreateDeviceFn pD3D11CreateDevice =
        (D3D11CreateDeviceFn)GetProcAddress(d3d11, "D3D11CreateDevice");
    if (!pD3D11CreateDevice) { put_str("GetProcAddress D3D11CreateDevice FAILED\n"); ExitProcess(2); }
    put_str("D3D11CreateDevice at "); put_hex((unsigned long long)pD3D11CreateDevice); put_str("\n");

    ID3D11Device *device = NULL;
    void *context = NULL;
    UINT featureLevel = 0;
    HRESULT hr = pD3D11CreateDevice(
        NULL,                                /* default adapter */
        D3D_DRIVER_TYPE_HARDWARE,
        NULL,                                /* Software */
        0,                                   /* Flags */
        NULL, 0,                             /* default feature levels */
        D3D11_SDK_VERSION,
        (void **)&device,
        &featureLevel,
        &context);

    put_str("D3D11CreateDevice hr="); put_hex((unsigned)hr);
    put_str(" device="); put_hex((unsigned long long)device);
    put_str(" featureLevel="); put_hex(featureLevel); put_str("\n");

    if (hr != 0 || !device) { put_str("D3D11 device creation failed\n"); ExitProcess(3); }

    /* Dump vtable layout around slot 30 — does it match expectations? */
    put_str("device->lpVtbl="); put_hex((unsigned long long)device->lpVtbl); put_str("\n");
    put_str("vtable[28]="); put_hex((unsigned long long)device->lpVtbl->OpenSharedResource); put_str("\n");
    put_str("vtable[29]="); put_hex((unsigned long long)device->lpVtbl->CheckFormatSupport); put_str("\n");
    put_str("vtable[30]="); put_hex((unsigned long long)device->lpVtbl->CheckMultisampleQualityLevels);
    put_str(" (CheckMultisampleQualityLevels)\n");

    /* The actual call — same args Thumper uses */
    UINT quality = 0xCAFE;  /* sentinel */
    put_str("Calling CheckMultisampleQualityLevels(R8G8B8A8_UNORM, 4, &q)...\n");
    HRESULT q_hr = device->lpVtbl->CheckMultisampleQualityLevels(
        device, DXGI_FORMAT_R8G8B8A8_UNORM, 4, &quality);
    put_str("  hr="); put_hex((unsigned)q_hr);
    put_str(" quality="); put_hex(quality); put_str("\n");

    put_str("=== test SUCCEEDED — bug is Thumper-specific ===\n");
    ExitProcess(0);
}
