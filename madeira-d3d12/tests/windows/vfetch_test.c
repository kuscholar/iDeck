/*  Vertex-path differential test (ml914): does the production D3D12 runtime
 *  put a triangle on screen through each of the binding patterns a UE5 base
 *  pass uses, and if not, which one breaks?
 *
 *  Cases (each into a freshly cleared 64x64 RGBA8 target, read back, counted):
 *    1  vertex stream + identity matrix from a root CBV that is NOT root param 0
 *    2  same, matrix = 0.5 scale  (coverage must shrink; which corner stays
 *       uncovered tells the Y convention)
 *    3  positions + ID through typed Buffer<float>/Buffer<uint> SRVs at
 *       non-zero FirstElement, table at a non-zero heap offset
 *    4  constant-step (stride 0) ID stream with sentinel neighbours; the
 *       pixel colour IS the ID the vertex stage read
 *    5  depth: draw near, stencil-only clear (must keep depth), draw far with
 *       LESS -> far must be rejected
 *    6  case 1 through ExecuteIndirect with the args at byte offset 100
 *    7  compute probe: the same CBV / typed buffers read by a compute shader
 *       and written out verbatim
 *
 *  Every line is printed to stdout AND stderr so it reaches the app log.
 */
#define COBJMACROS
#define INITGUID
#include <initguid.h>
#include <windows.h>
#include <d3d12.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include "vfetch_dxil.h"

static int checks, fails;
static volatile ULONG g_probe_code;
static LONG WINAPI probe_veh(EXCEPTION_POINTERS *ep) {
    ULONG code = ep->ExceptionRecord->ExceptionCode;
    /* OutputDebugString raises DBG_PRINTEXCEPTION_C/W as its normal operation;
     * those are not failures and must not hide a real code recorded earlier. */
    if (code == 0x40010006 || code == 0x4001000a) return EXCEPTION_CONTINUE_SEARCH;
    g_probe_code = code;
    return EXCEPTION_CONTINUE_EXECUTION;
}
static void say(const char *fmt, ...) {
    char b[512]; va_list ap; va_start(ap, fmt); vsnprintf(b, sizeof b, fmt, ap); va_end(ap);
    printf("%s\n", b); fprintf(stderr, "[vfetch] %s\n", b); fflush(stdout); fflush(stderr);
}
#define CHECK(cond, ...) do { checks++; if (!(cond)) { fails++; say("  FAIL  " __VA_ARGS__); } else say("  ok    " __VA_ARGS__); } while (0)

typedef HRESULT (WINAPI *pfn_create)(IUnknown *, D3D_FEATURE_LEVEL, REFIID, void **);
typedef HRESULT (WINAPI *pfn_serialize)(const D3D12_ROOT_SIGNATURE_DESC1 *, unsigned char *, SIZE_T *);
typedef const char *(*pfn_marker)(void);

enum { RT_W = 64, RT_H = 64 };
static ID3D12Device *dev; static ID3D12CommandQueue *queue; static ID3D12CommandAllocator *alloc;
static ID3D12GraphicsCommandList *list; static ID3D12Fence *fence; static UINT64 fence_v;
static ID3D12Resource *rt, *ds, *pix, *cbuf, *vbuf, *idbuf, *posbuf, *indbuf, *probe, *proberb, *zero, *ibuf;
static ID3D12DescriptorHeap *rtvh, *dsvh, *cbvh; static D3D12_CPU_DESCRIPTOR_HANDLE rtv, dsv;
static ID3D12RootSignature *rs; static ID3D12CommandSignature *csig;
static UINT cbv_inc;

static ID3D12Resource *make_buffer(D3D12_HEAP_TYPE heap, UINT64 size, D3D12_RESOURCE_STATES st, D3D12_RESOURCE_FLAGS fl) {
    D3D12_HEAP_PROPERTIES hp; ZeroMemory(&hp, sizeof hp); hp.Type = heap;
    D3D12_RESOURCE_DESC d; ZeroMemory(&d, sizeof d);
    d.Dimension = D3D12_RESOURCE_DIMENSION_BUFFER; d.Width = size; d.Height = 1; d.DepthOrArraySize = 1; d.MipLevels = 1;
    d.Format = DXGI_FORMAT_UNKNOWN; d.SampleDesc.Count = 1; d.Layout = D3D12_TEXTURE_LAYOUT_ROW_MAJOR; d.Flags = fl;
    ID3D12Resource *r = NULL;
    ID3D12Device_CreateCommittedResource(dev, &hp, D3D12_HEAP_FLAG_NONE, &d, st, NULL, &IID_ID3D12Resource, (void **)&r);
    return r;
}
static ID3D12Resource *make_tex(DXGI_FORMAT f, D3D12_RESOURCE_FLAGS fl, D3D12_RESOURCE_STATES st, const D3D12_CLEAR_VALUE *cv) {
    D3D12_HEAP_PROPERTIES hp; ZeroMemory(&hp, sizeof hp); hp.Type = D3D12_HEAP_TYPE_DEFAULT;
    D3D12_RESOURCE_DESC d; ZeroMemory(&d, sizeof d);
    d.Dimension = D3D12_RESOURCE_DIMENSION_TEXTURE2D; d.Width = RT_W; d.Height = RT_H; d.DepthOrArraySize = 1; d.MipLevels = 1;
    d.Format = f; d.SampleDesc.Count = 1; d.Flags = fl;
    ID3D12Resource *r = NULL;
    ID3D12Device_CreateCommittedResource(dev, &hp, D3D12_HEAP_FLAG_NONE, &d, st, cv, &IID_ID3D12Resource, (void **)&r);
    return r;
}
static void upload(ID3D12Resource *r, UINT64 off, const void *src, size_t n) {
    BYTE *p = NULL; ID3D12Resource_Map(r, 0, NULL, (void **)&p);
    if (p) { memcpy(p + off, src, n); ID3D12Resource_Unmap(r, 0, NULL); }
}
static void submit_and_wait(void) {
    ID3D12CommandList *lists[1] = { (ID3D12CommandList *)list };
    ID3D12GraphicsCommandList_Close(list);
    ID3D12CommandQueue_ExecuteCommandLists(queue, 1, lists);
    HANDLE ev = CreateEventA(NULL, FALSE, FALSE, NULL);
    fence_v++;
    ID3D12Fence_SetEventOnCompletion(fence, fence_v, ev);
    ID3D12CommandQueue_Signal(queue, fence, fence_v);
    if (WaitForSingleObject(ev, 15000) != WAIT_OBJECT_0) say("  !! fence wait timed out");
    CloseHandle(ev);
    ID3D12CommandAllocator_Reset(alloc);
    ID3D12GraphicsCommandList_Reset(list, alloc, NULL);
}
static void copy_rt_to_readback(void) {
    D3D12_TEXTURE_COPY_LOCATION dl, sl; ZeroMemory(&dl, sizeof dl); ZeroMemory(&sl, sizeof sl);
    dl.pResource = pix; dl.Type = D3D12_TEXTURE_COPY_TYPE_PLACED_FOOTPRINT;
    dl.PlacedFootprint.Footprint.Format = DXGI_FORMAT_R8G8B8A8_UNORM;
    dl.PlacedFootprint.Footprint.Width = RT_W; dl.PlacedFootprint.Footprint.Height = RT_H;
    dl.PlacedFootprint.Footprint.Depth = 1; dl.PlacedFootprint.Footprint.RowPitch = RT_W * 4;
    sl.pResource = rt; sl.Type = D3D12_TEXTURE_COPY_TYPE_SUBRESOURCE_INDEX;
    ID3D12GraphicsCommandList_CopyTextureRegion(list, &dl, 0, 0, 0, &sl, NULL);
}
/* count pixels equal to (r,g,b); print the four corners and the centre */
static unsigned count_colour(const char *what, BYTE r, BYTE g, BYTE b) {
    BYTE *p = NULL; unsigned n = 0, x, y;
    ID3D12Resource_Map(pix, 0, NULL, (void **)&p);
    if (!p) { say("  !! readback map failed"); return 0; }
    for (y = 0; y < RT_H; y++) for (x = 0; x < RT_W; x++) {
        const BYTE *q = p + (y * RT_W + x) * 4;
        if (q[0] == r && q[1] == g && q[2] == b) n++;
    }
#define PX(x, y) p[((y) * RT_W + (x)) * 4], p[((y) * RT_W + (x)) * 4 + 1], p[((y) * RT_W + (x)) * 4 + 2]
    say("  %s: %u/%u pixels are (%u,%u,%u); TL=(%u,%u,%u) TR=(%u,%u,%u) BL=(%u,%u,%u) BR=(%u,%u,%u) C=(%u,%u,%u)",
        what, n, RT_W * RT_H, r, g, b, PX(2, 2), PX(RT_W - 3, 2), PX(2, RT_H - 3), PX(RT_W - 3, RT_H - 3), PX(RT_W / 2, RT_H / 2));
    ID3D12Resource_Unmap(pix, 0, NULL);
    return n;
}

struct params { float xform[16]; float colour[4]; UINT misc[4]; };
static void set_params(const float *xform, float r, float g, float b, UINT mode) {
    struct params p; memset(&p, 0, sizeof p);
    memcpy(p.xform, xform, sizeof p.xform);
    p.colour[0] = r; p.colour[1] = g; p.colour[2] = b; p.colour[3] = 1.0f; p.misc[0] = mode;
    upload(cbuf, 256, &p, sizeof p);            /* the CBV lives 256 bytes INTO the buffer */
}
static const float IDENT[16] = { 1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1 };
static const float HALF[16]  = { 0.5f,0,0,0, 0,0.5f,0,0, 0,0,1,0, 0,0,0,1 };

static ID3D12PipelineState *make_pso(const unsigned char *vs, size_t vsn, int with_layout, int depth, D3D12_COMPARISON_FUNC dfunc) {
    D3D12_INPUT_ELEMENT_DESC il[2];
    D3D12_GRAPHICS_PIPELINE_STATE_DESC pd; ZeroMemory(&pd, sizeof pd);
    ZeroMemory(il, sizeof il);
    il[0].SemanticName = "POSITION"; il[0].Format = DXGI_FORMAT_R32G32B32_FLOAT; il[0].InputSlot = 0;
    il[0].AlignedByteOffset = 0; il[0].InputSlotClass = D3D12_INPUT_CLASSIFICATION_PER_VERTEX_DATA;
    il[1].SemanticName = "INSTID"; il[1].Format = DXGI_FORMAT_R32_UINT; il[1].InputSlot = 1;
    il[1].AlignedByteOffset = 0; il[1].InputSlotClass = D3D12_INPUT_CLASSIFICATION_PER_VERTEX_DATA;
    pd.pRootSignature = rs;
    pd.VS.pShaderBytecode = vs; pd.VS.BytecodeLength = vsn;
    pd.PS.pShaderBytecode = vfetch_ps_dxil; pd.PS.BytecodeLength = sizeof vfetch_ps_dxil;
    if (with_layout) { pd.InputLayout.pInputElementDescs = il; pd.InputLayout.NumElements = 2; }
    pd.NumRenderTargets = 1; pd.RTVFormats[0] = DXGI_FORMAT_R8G8B8A8_UNORM;
    pd.SampleDesc.Count = 1; pd.SampleMask = 0xffffffff;
    pd.PrimitiveTopologyType = D3D12_PRIMITIVE_TOPOLOGY_TYPE_TRIANGLE;
    pd.RasterizerState.FillMode = D3D12_FILL_MODE_SOLID; pd.RasterizerState.CullMode = D3D12_CULL_MODE_NONE;
    pd.RasterizerState.DepthClipEnable = TRUE;
    pd.BlendState.RenderTarget[0].RenderTargetWriteMask = D3D12_COLOR_WRITE_ENABLE_ALL;
    if (depth) {
        pd.DSVFormat = DXGI_FORMAT_D32_FLOAT_S8X24_UINT;
        pd.DepthStencilState.DepthEnable = TRUE; pd.DepthStencilState.DepthWriteMask = D3D12_DEPTH_WRITE_MASK_ALL;
        pd.DepthStencilState.DepthFunc = dfunc;
    }
    ID3D12PipelineState *pso = NULL;
    HRESULT hr = ID3D12Device_CreateGraphicsPipelineState(dev, &pd, &IID_ID3D12PipelineState, (void **)&pso);
    if (FAILED(hr) || !pso) say("  !! pipeline creation failed %#lx", hr);
    return pso;
}

static void begin_frame(ID3D12PipelineState *pso, int with_depth) {
    const FLOAT clear[4] = { 1.0f, 0.0f, 0.0f, 1.0f };
    D3D12_VIEWPORT vp = { 0, 0, (FLOAT)RT_W, (FLOAT)RT_H, 0.0f, 1.0f };
    D3D12_RECT sc = { 0, 0, RT_W, RT_H };
    D3D12_GPU_DESCRIPTOR_HANDLE gh; UINT64 base;
    ID3D12GraphicsCommandList_OMSetRenderTargets(list, 1, &rtv, FALSE, with_depth ? &dsv : NULL);
    ID3D12GraphicsCommandList_ClearRenderTargetView(list, rtv, clear, 0, NULL);
    ID3D12GraphicsCommandList_SetGraphicsRootSignature(list, rs);
    ID3D12GraphicsCommandList_SetPipelineState(list, pso);
    ID3D12GraphicsCommandList_SetDescriptorHeaps(list, 1, &cbvh);
    ID3D12GraphicsCommandList_SetGraphicsRoot32BitConstant(list, 0, 0xDEADBEEF, 0);
    ID3D12GraphicsCommandList_SetGraphicsRootConstantBufferView(list, 1, ID3D12Resource_GetGPUVirtualAddress(cbuf) + 256);
    cbvh->lpVtbl->GetGPUDescriptorHandleForHeapStart(cbvh, &gh); base = gh.ptr;
    gh.ptr = base + (UINT64)5 * cbv_inc; ID3D12GraphicsCommandList_SetGraphicsRootDescriptorTable(list, 2, gh);
    gh.ptr = base + (UINT64)9 * cbv_inc; ID3D12GraphicsCommandList_SetGraphicsRootDescriptorTable(list, 3, gh);
    ID3D12GraphicsCommandList_RSSetViewports(list, 1, &vp);
    ID3D12GraphicsCommandList_RSSetScissorRects(list, 1, &sc);
    ID3D12GraphicsCommandList_IASetPrimitiveTopology(list, D3D_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
}
static void bind_streams(UINT id_byte_offset, UINT id_stride) {
    D3D12_VERTEX_BUFFER_VIEW vb[2];
    vb[0].BufferLocation = ID3D12Resource_GetGPUVirtualAddress(vbuf) + 64;   /* positions 64 bytes into the buffer */
    vb[0].SizeInBytes = 3 * 12; vb[0].StrideInBytes = 12;
    vb[1].BufferLocation = ID3D12Resource_GetGPUVirtualAddress(idbuf) + id_byte_offset;
    vb[1].SizeInBytes = 4; vb[1].StrideInBytes = id_stride;
    ID3D12GraphicsCommandList_IASetVertexBuffers(list, 0, 2, vb);
}

int main(void) {
    HRESULT hr;
    say("madeira-d3d12 vertex-path differential test (ml914)");
    HMODULE dll = LoadLibraryA("madeira_d3d12.dll");
    CHECK(dll != NULL, "madeira_d3d12.dll loaded (err %lu)", dll ? 0UL : GetLastError());
    if (!dll) return 1;
    pfn_create create = (pfn_create)GetProcAddress(dll, "MadeiraD3D12CreateDevice");
    pfn_serialize serialize = (pfn_serialize)GetProcAddress(dll, "MadeiraD3D12SerializeRootSignature");
    pfn_marker marker = (pfn_marker)GetProcAddress(dll, "MadeiraD3D12GetBuildMarker");
    CHECK(create && serialize, "exports resolved");
    if (!create || !serialize) return 1;
    if (marker) say("  implementation: %s", marker());

    hr = create(NULL, D3D_FEATURE_LEVEL_12_0, &IID_ID3D12Device, (void **)&dev);
    CHECK(SUCCEEDED(hr) && dev, "device (%#lx)", hr); if (!dev) return 1;
    D3D12_COMMAND_QUEUE_DESC qd; ZeroMemory(&qd, sizeof qd);
    ID3D12Device_CreateCommandQueue(dev, &qd, &IID_ID3D12CommandQueue, (void **)&queue);
    ID3D12Device_CreateCommandAllocator(dev, D3D12_COMMAND_LIST_TYPE_DIRECT, &IID_ID3D12CommandAllocator, (void **)&alloc);
    ID3D12Device_CreateCommandList(dev, 0, D3D12_COMMAND_LIST_TYPE_DIRECT, alloc, NULL, &IID_ID3D12GraphicsCommandList, (void **)&list);
    ID3D12Device_CreateFence(dev, 0, D3D12_FENCE_FLAG_NONE, &IID_ID3D12Fence, (void **)&fence);
    CHECK(queue && alloc && list && fence, "queue/allocator/list/fence");
    if (!(queue && alloc && list && fence)) return 1;

    /* ---- root signature: constants(b1), CBV(b0), SRV table t0-1, UAV table u0 ---- */
    {
        D3D12_DESCRIPTOR_RANGE1 rg[2]; D3D12_ROOT_PARAMETER1 rp[5]; D3D12_ROOT_SIGNATURE_DESC1 rd;
        static unsigned char blob[1024]; SIZE_T n = sizeof blob;
        ZeroMemory(rg, sizeof rg); ZeroMemory(rp, sizeof rp); ZeroMemory(&rd, sizeof rd);
        rg[0].RangeType = D3D12_DESCRIPTOR_RANGE_TYPE_SRV; rg[0].NumDescriptors = 2; rg[0].BaseShaderRegister = 0;
        rg[1].RangeType = D3D12_DESCRIPTOR_RANGE_TYPE_UAV; rg[1].NumDescriptors = 1; rg[1].BaseShaderRegister = 0;
        rp[0].ParameterType = D3D12_ROOT_PARAMETER_TYPE_32BIT_CONSTANTS; rp[0].Constants.ShaderRegister = 1; rp[0].Constants.Num32BitValues = 1;
        rp[1].ParameterType = D3D12_ROOT_PARAMETER_TYPE_CBV; rp[1].Descriptor.ShaderRegister = 0;
        rp[2].ParameterType = D3D12_ROOT_PARAMETER_TYPE_DESCRIPTOR_TABLE; rp[2].DescriptorTable.NumDescriptorRanges = 1; rp[2].DescriptorTable.pDescriptorRanges = &rg[0];
        rp[3].ParameterType = D3D12_ROOT_PARAMETER_TYPE_DESCRIPTOR_TABLE; rp[3].DescriptorTable.NumDescriptorRanges = 1; rp[3].DescriptorTable.pDescriptorRanges = &rg[1];
        rp[4].ParameterType = D3D12_ROOT_PARAMETER_TYPE_UAV; rp[4].Descriptor.ShaderRegister = 1;   /* ml907: root UAV */
        { int i; for (i = 0; i < 5; i++) rp[i].ShaderVisibility = D3D12_SHADER_VISIBILITY_ALL; }
        rd.NumParameters = 5; rd.pParameters = rp; rd.Flags = D3D12_ROOT_SIGNATURE_FLAG_ALLOW_INPUT_ASSEMBLER_INPUT_LAYOUT;
        hr = serialize(&rd, blob, &n);
        if (SUCCEEDED(hr)) hr = ID3D12Device_CreateRootSignature(dev, 0, blob, n, &IID_ID3D12RootSignature, (void **)&rs);
        CHECK(SUCCEEDED(hr) && rs, "root signature: constants(b1), CBV(b0) as param 1, SRV table, UAV table, root UAV u1 (%#lx)", hr);
        if (!rs) return 1;
    }

    /* ---- resources ---- */
    rt = make_tex(DXGI_FORMAT_R8G8B8A8_UNORM, D3D12_RESOURCE_FLAG_ALLOW_RENDER_TARGET, D3D12_RESOURCE_STATE_RENDER_TARGET, NULL);
    {
        D3D12_CLEAR_VALUE cv; ZeroMemory(&cv, sizeof cv); cv.Format = DXGI_FORMAT_D32_FLOAT_S8X24_UINT; cv.DepthStencil.Depth = 1.0f;
        ds = make_tex(DXGI_FORMAT_D32_FLOAT_S8X24_UINT, D3D12_RESOURCE_FLAG_ALLOW_DEPTH_STENCIL, D3D12_RESOURCE_STATE_DEPTH_WRITE, &cv);
    }
    pix   = make_buffer(D3D12_HEAP_TYPE_READBACK, RT_W * RT_H * 4, D3D12_RESOURCE_STATE_COPY_DEST, 0);
    cbuf  = make_buffer(D3D12_HEAP_TYPE_UPLOAD, 1024, D3D12_RESOURCE_STATE_GENERIC_READ, 0);
    vbuf  = make_buffer(D3D12_HEAP_TYPE_UPLOAD, 1024, D3D12_RESOURCE_STATE_GENERIC_READ, 0);
    idbuf = make_buffer(D3D12_HEAP_TYPE_UPLOAD, 1024, D3D12_RESOURCE_STATE_GENERIC_READ, 0);
    posbuf= make_buffer(D3D12_HEAP_TYPE_UPLOAD, 4096, D3D12_RESOURCE_STATE_GENERIC_READ, 0);
    indbuf= make_buffer(D3D12_HEAP_TYPE_UPLOAD, 1024, D3D12_RESOURCE_STATE_GENERIC_READ, 0);
    probe = make_buffer(D3D12_HEAP_TYPE_DEFAULT, 256, D3D12_RESOURCE_STATE_UNORDERED_ACCESS, D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS);
    proberb = make_buffer(D3D12_HEAP_TYPE_READBACK, 256, D3D12_RESOURCE_STATE_COPY_DEST, 0);
    zero    = make_buffer(D3D12_HEAP_TYPE_UPLOAD, 256, D3D12_RESOURCE_STATE_GENERIC_READ, 0);
    ibuf    = make_buffer(D3D12_HEAP_TYPE_UPLOAD, 1024, D3D12_RESOURCE_STATE_GENERIC_READ, 0);   /* ml914: 16-bit indices */
    { USHORT ix[512]; int i; for (i = 0; i < 512; i++) ix[i] = 0x7777; ix[8] = 0; ix[9] = 1; ix[10] = 2; upload(ibuf, 0, ix, sizeof ix); }
    { BYTE z[256]; memset(z, 0, sizeof z); upload(zero, 0, z, sizeof z); }
    CHECK(rt && ds && pix && cbuf && vbuf && idbuf && posbuf && indbuf && probe && proberb, "resources created");
    if (!(rt && ds && pix && cbuf && vbuf && idbuf && posbuf && indbuf && probe && proberb)) return 1;

    /* geometry: one oversized clip-space triangle covering the whole target */
    static const float tri[9] = { -1.0f, -1.0f, 0.5f,   3.0f, -1.0f, 0.5f,   -1.0f, 3.0f, 0.5f };
    { float junk[16]; int i; for (i = 0; i < 16; i++) junk[i] = 9.0f; upload(vbuf, 0, junk, sizeof junk); }   /* sentinels before */
    upload(vbuf, 64, tri, sizeof tri);
    /* id stream: sentinels around the intended value at byte 4 */
    { UINT ids[8] = { 0xAAAA, 0x0102, 0xBBBB, 0xCCCC, 0xDDDD, 0xEEEE, 0x1111, 0x2222 }; upload(idbuf, 0, ids, sizeof ids); }
    /* typed fetch: positions at element 64 (byte 256), ids at element 16 (byte 64) of posbuf, sentinels elsewhere */
    { float f[1024]; int i; for (i = 0; i < 1024; i++) f[i] = 7.0f; memcpy(f + 64, tri, sizeof tri);
      UINT *u = (UINT *)f; for (i = 0; i < 64; i++) u[i] = 0x9999; u[16] = 0x0304; u[17] = 0x0304; u[18] = 0x0304;
      upload(posbuf, 0, f, sizeof f); }
    /* indirect args (DrawInstanced: vcount, icount, vstart, istart) at byte 100 */
    { UINT junk[25]; int i; for (i = 0; i < 25; i++) junk[i] = 0x7777; upload(indbuf, 0, junk, sizeof junk);
      UINT args[4] = { 3, 1, 0, 0 }; upload(indbuf, 100, args, sizeof args); }

    /* descriptor heaps: RTV, DSV, and a shader-visible heap with SRVs at 5,6 and the UAV at 9 */
    {
        D3D12_DESCRIPTOR_HEAP_DESC hd; ZeroMemory(&hd, sizeof hd);
        hd.Type = D3D12_DESCRIPTOR_HEAP_TYPE_RTV; hd.NumDescriptors = 1;
        ID3D12Device_CreateDescriptorHeap(dev, &hd, &IID_ID3D12DescriptorHeap, (void **)&rtvh);
        hd.Type = D3D12_DESCRIPTOR_HEAP_TYPE_DSV;
        ID3D12Device_CreateDescriptorHeap(dev, &hd, &IID_ID3D12DescriptorHeap, (void **)&dsvh);
        hd.Type = D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV; hd.NumDescriptors = 16; hd.Flags = D3D12_DESCRIPTOR_HEAP_FLAG_SHADER_VISIBLE;
        ID3D12Device_CreateDescriptorHeap(dev, &hd, &IID_ID3D12DescriptorHeap, (void **)&cbvh);
        CHECK(rtvh && dsvh && cbvh, "descriptor heaps");
        if (!(rtvh && dsvh && cbvh)) return 1;
        rtvh->lpVtbl->GetCPUDescriptorHandleForHeapStart(rtvh, &rtv); ID3D12Device_CreateRenderTargetView(dev, rt, NULL, rtv);
        dsvh->lpVtbl->GetCPUDescriptorHandleForHeapStart(dsvh, &dsv);
        { D3D12_DEPTH_STENCIL_VIEW_DESC dd; ZeroMemory(&dd, sizeof dd); dd.Format = DXGI_FORMAT_D32_FLOAT_S8X24_UINT; dd.ViewDimension = D3D12_DSV_DIMENSION_TEXTURE2D;
          ID3D12Device_CreateDepthStencilView(dev, ds, &dd, dsv); }
        cbv_inc = ID3D12Device_GetDescriptorHandleIncrementSize(dev, D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV);
        D3D12_CPU_DESCRIPTOR_HANDLE ch; cbvh->lpVtbl->GetCPUDescriptorHandleForHeapStart(cbvh, &ch);
        D3D12_SHADER_RESOURCE_VIEW_DESC sd; ZeroMemory(&sd, sizeof sd);
        sd.ViewDimension = D3D12_SRV_DIMENSION_BUFFER; sd.Shader4ComponentMapping = D3D12_DEFAULT_SHADER_4_COMPONENT_MAPPING;
        sd.Format = DXGI_FORMAT_R32_FLOAT; sd.Buffer.FirstElement = 64; sd.Buffer.NumElements = 9;
        { D3D12_CPU_DESCRIPTOR_HANDLE h = ch; h.ptr += (SIZE_T)5 * cbv_inc; ID3D12Device_CreateShaderResourceView(dev, posbuf, &sd, h); }
        sd.Format = DXGI_FORMAT_R32_UINT; sd.Buffer.FirstElement = 16; sd.Buffer.NumElements = 3;
        { D3D12_CPU_DESCRIPTOR_HANDLE h = ch; h.ptr += (SIZE_T)6 * cbv_inc; ID3D12Device_CreateShaderResourceView(dev, posbuf, &sd, h); }
        /* ml914: wide views (heap 7,8) so a base vertex of 64 stays in bounds */
        sd.Format = DXGI_FORMAT_R32_FLOAT; sd.Buffer.FirstElement = 64; sd.Buffer.NumElements = 1024 - 64;
        { D3D12_CPU_DESCRIPTOR_HANDLE h = ch; h.ptr += (SIZE_T)7 * cbv_inc; ID3D12Device_CreateShaderResourceView(dev, posbuf, &sd, h); }
        sd.Format = DXGI_FORMAT_R32_UINT; sd.Buffer.FirstElement = 16; sd.Buffer.NumElements = 1024 - 16;
        { D3D12_CPU_DESCRIPTOR_HANDLE h = ch; h.ptr += (SIZE_T)8 * cbv_inc; ID3D12Device_CreateShaderResourceView(dev, posbuf, &sd, h); }
        D3D12_UNORDERED_ACCESS_VIEW_DESC ud; ZeroMemory(&ud, sizeof ud);
        ud.ViewDimension = D3D12_UAV_DIMENSION_BUFFER; ud.Format = DXGI_FORMAT_UNKNOWN; ud.Buffer.NumElements = 16; ud.Buffer.StructureByteStride = 16;
        { D3D12_CPU_DESCRIPTOR_HANDLE h = ch; h.ptr += (SIZE_T)9 * cbv_inc; ID3D12Device_CreateUnorderedAccessView(dev, probe, NULL, &ud, h); }
    }

    ID3D12PipelineState *pso_stream = make_pso(vfetch_vs_stream_dxil, sizeof vfetch_vs_stream_dxil, 1, 0, D3D12_COMPARISON_FUNC_ALWAYS);
    ID3D12PipelineState *pso_fetch  = make_pso(vfetch_vs_fetch_dxil,  sizeof vfetch_vs_fetch_dxil,  0, 0, D3D12_COMPARISON_FUNC_ALWAYS);
    ID3D12PipelineState *pso_depth  = make_pso(vfetch_vs_stream_dxil, sizeof vfetch_vs_stream_dxil, 1, 1, D3D12_COMPARISON_FUNC_LESS);
    ID3D12PipelineState *pso_inst   = make_pso(vfetch_vs_inst_dxil,   sizeof vfetch_vs_inst_dxil,   1, 0, D3D12_COMPARISON_FUNC_ALWAYS);   /* ml914 */
    CHECK(pso_stream && pso_fetch && pso_depth, "pipelines converted (stream, fetch, depth)");
    if (!(pso_stream && pso_fetch && pso_depth)) return 1;
    ID3D12PipelineState *pso_probe = NULL, *pso_write = NULL, *pso_root = NULL;
    { D3D12_COMPUTE_PIPELINE_STATE_DESC cd; ZeroMemory(&cd, sizeof cd); cd.pRootSignature = rs;
      cd.CS.pShaderBytecode = vfetch_cs_dxil; cd.CS.BytecodeLength = sizeof vfetch_cs_dxil;
      ID3D12Device_CreateComputePipelineState(dev, &cd, &IID_ID3D12PipelineState, (void **)&pso_probe);
      cd.CS.pShaderBytecode = vfetch_cs_write_dxil; cd.CS.BytecodeLength = sizeof vfetch_cs_write_dxil;
      ID3D12Device_CreateComputePipelineState(dev, &cd, &IID_ID3D12PipelineState, (void **)&pso_write);
      cd.CS.pShaderBytecode = vfetch_cs_root_dxil; cd.CS.BytecodeLength = sizeof vfetch_cs_root_dxil;
      ID3D12Device_CreateComputePipelineState(dev, &cd, &IID_ID3D12PipelineState, (void **)&pso_root);
      CHECK(pso_probe && pso_write && pso_root, "compute pipelines (probe, write-only, root-UAV)"); }
    { D3D12_INDIRECT_ARGUMENT_DESC ia; D3D12_COMMAND_SIGNATURE_DESC csd; ZeroMemory(&ia, sizeof ia); ZeroMemory(&csd, sizeof csd);
      ia.Type = D3D12_INDIRECT_ARGUMENT_TYPE_DRAW; csd.ByteStride = 16; csd.NumArgumentDescs = 1; csd.pArgumentDescs = &ia;
      ID3D12Device_CreateCommandSignature(dev, &csd, NULL, &IID_ID3D12CommandSignature, (void **)&csig);
      CHECK(csig != NULL, "command signature (draw)"); }

    /* ---- case 1: stream + identity ---- */
    set_params(IDENT, 0.0f, 0.25f, 1.0f, 0);
    begin_frame(pso_stream, 0); bind_streams(4, 0);
    ID3D12GraphicsCommandList_DrawInstanced(list, 3, 1, 0, 0);
    copy_rt_to_readback(); submit_and_wait();
    { unsigned n = count_colour("case1 stream+identity", 0, 64, 255);
      CHECK(n == RT_W * RT_H, "case1: whole target is the CBV colour (%u/%u)", n, RT_W * RT_H); }

    /* ---- case 2: stream + half scale ---- */
    set_params(HALF, 0.0f, 0.25f, 1.0f, 0);
    begin_frame(pso_stream, 0); bind_streams(4, 0);
    ID3D12GraphicsCommandList_DrawInstanced(list, 3, 1, 0, 0);
    copy_rt_to_readback(); submit_and_wait();
    { unsigned n = count_colour("case2 stream+half", 0, 64, 255);
      CHECK(n > RT_W * RT_H / 3 && n < RT_W * RT_H * 3 / 4 + RT_W * 2, "case2: coverage shrank to about 9/16 (%u/%u)", n, RT_W * RT_H); }

    /* ---- case 3: typed buffer fetch ---- */
    set_params(IDENT, 0.0f, 0.25f, 1.0f, 1);
    begin_frame(pso_fetch, 0);
    ID3D12GraphicsCommandList_DrawInstanced(list, 3, 1, 0, 0);
    copy_rt_to_readback(); submit_and_wait();
    { unsigned n = count_colour("case3 typed fetch (colour = id 0x0304 -> (4,3,0))", 4, 3, 0);
      CHECK(n == RT_W * RT_H, "case3: whole target shows the fetched id (%u/%u)", n, RT_W * RT_H); }

    /* ---- case 4: constant-step id stream ---- */
    set_params(IDENT, 0.0f, 0.25f, 1.0f, 1);
    begin_frame(pso_stream, 0); bind_streams(4, 0);
    ID3D12GraphicsCommandList_DrawInstanced(list, 3, 1, 0, 0);
    copy_rt_to_readback(); submit_and_wait();
    { unsigned n = count_colour("case4 constant stream (id 0x0102 -> (2,1,0))", 2, 1, 0);
      CHECK(n == RT_W * RT_H, "case4: every pixel shows the stride-0 id, not a neighbour (%u/%u)", n, RT_W * RT_H); }

    /* ---- case 5: depth. 5a and 5b have NO clear between the two draws, so
     * they say whether the depth test works at all; 5c is the stencil-only
     * clear in between (the UE5 pattern). Near = z 0.5 colour A; far = z 0.75
     * colour B; pipeline is LESS with depth writes. ---- */
    { static const float far_tri[9] = { -1.0f, -1.0f, 0.75f,   3.0f, -1.0f, 0.75f,   -1.0f, 3.0f, 0.75f };
      struct params pb; upload(vbuf, 128, far_tri, sizeof far_tri);
      memset(&pb, 0, sizeof pb); memcpy(pb.xform, IDENT, sizeof pb.xform); pb.colour[0] = 1.0f; pb.colour[1] = 1.0f; pb.colour[2] = 0.0f; pb.colour[3] = 1.0f;
      upload(cbuf, 512, &pb, sizeof pb); }
#define BIND_NEAR() do { bind_streams(4, 0); ID3D12GraphicsCommandList_SetGraphicsRootConstantBufferView(list, 1, ID3D12Resource_GetGPUVirtualAddress(cbuf) + 256); } while (0)
#define BIND_FAR() do { D3D12_VERTEX_BUFFER_VIEW vb[2]; \
      vb[0].BufferLocation = ID3D12Resource_GetGPUVirtualAddress(vbuf) + 128; vb[0].SizeInBytes = 36; vb[0].StrideInBytes = 12; \
      vb[1].BufferLocation = ID3D12Resource_GetGPUVirtualAddress(idbuf) + 4; vb[1].SizeInBytes = 4; vb[1].StrideInBytes = 0; \
      ID3D12GraphicsCommandList_IASetVertexBuffers(list, 0, 2, vb); \
      ID3D12GraphicsCommandList_SetGraphicsRootConstantBufferView(list, 1, ID3D12Resource_GetGPUVirtualAddress(cbuf) + 512); } while (0)

    /* 5a: near then far, one pass, no clear between -> far must lose */
    set_params(IDENT, 0.0f, 0.25f, 1.0f, 0);
    begin_frame(pso_depth, 1);
    ID3D12GraphicsCommandList_ClearDepthStencilView(list, dsv, D3D12_CLEAR_FLAG_DEPTH | D3D12_CLEAR_FLAG_STENCIL, 1.0f, 0, 0, NULL);
    BIND_NEAR(); ID3D12GraphicsCommandList_DrawInstanced(list, 3, 1, 0, 0);
    BIND_FAR();  ID3D12GraphicsCommandList_DrawInstanced(list, 3, 1, 0, 0);
    copy_rt_to_readback(); submit_and_wait();
    { unsigned a = count_colour("case5a near-then-far, no clear between (A)", 0, 64, 255);
      unsigned b = count_colour("case5a far colour B, must be 0", 255, 255, 0);
      CHECK(a == RT_W * RT_H && b == 0, "case5a: depth test rejects the far draw in the same pass (A=%u B=%u)", a, b); }

    /* 5b: far then near, one pass -> near must win (LESS passes, writes land) */
    begin_frame(pso_depth, 1);
    ID3D12GraphicsCommandList_ClearDepthStencilView(list, dsv, D3D12_CLEAR_FLAG_DEPTH | D3D12_CLEAR_FLAG_STENCIL, 1.0f, 0, 0, NULL);
    BIND_FAR();  ID3D12GraphicsCommandList_DrawInstanced(list, 3, 1, 0, 0);
    BIND_NEAR(); ID3D12GraphicsCommandList_DrawInstanced(list, 3, 1, 0, 0);
    copy_rt_to_readback(); submit_and_wait();
    { unsigned a = count_colour("case5b far-then-near (A must win)", 0, 64, 255);
      CHECK(a == RT_W * RT_H, "case5b: near draw passes LESS over the far one (A=%u)", a); }

    /* 5c: near, stencil-only clear, far -> the clear must not touch depth */
    begin_frame(pso_depth, 1);
    ID3D12GraphicsCommandList_ClearDepthStencilView(list, dsv, D3D12_CLEAR_FLAG_DEPTH | D3D12_CLEAR_FLAG_STENCIL, 1.0f, 0, 0, NULL);
    BIND_NEAR(); ID3D12GraphicsCommandList_DrawInstanced(list, 3, 1, 0, 0);
    ID3D12GraphicsCommandList_ClearDepthStencilView(list, dsv, D3D12_CLEAR_FLAG_STENCIL, 1.0f, 0, 0, NULL);   /* must NOT touch depth */
    BIND_FAR();  ID3D12GraphicsCommandList_DrawInstanced(list, 3, 1, 0, 0);
    copy_rt_to_readback(); submit_and_wait();
    { unsigned a = count_colour("case5c near, stencil-only clear, far (A)", 0, 64, 255);
      unsigned b = count_colour("case5c far colour B, must be 0", 255, 255, 0);
      CHECK(a == RT_W * RT_H && b == 0, "case5c: depth survives a stencil-only clear (A=%u B=%u)", a, b); }
#undef BIND_NEAR
#undef BIND_FAR

    /* ---- case 6: indirect draw ---- */
    set_params(IDENT, 0.0f, 0.25f, 1.0f, 0);
    begin_frame(pso_stream, 0); bind_streams(4, 0);
    ID3D12GraphicsCommandList_ExecuteIndirect(list, csig, 1, indbuf, 100, NULL, 0);
    copy_rt_to_readback(); submit_and_wait();
    { unsigned n = count_colour("case6 indirect draw", 0, 64, 255);
      CHECK(n == RT_W * RT_H, "case6: ExecuteIndirect with args at byte 100 covers the target (%u/%u)", n, RT_W * RT_H); }

    /* ---- case 7: compute. 7a writes constants through the table UAV (no
     * reads); 7b is the full probe through the table UAV; 7c is the same
     * probe through the ROOT UAV (param 4). The probe buffer is zeroed
     * before each so stale rows cannot pass. ---- */
#define RUN_CS(pso_) do { D3D12_GPU_DESCRIPTOR_HANDLE gh; UINT64 base; \
        set_params(HALF, 0.0f, 0.25f, 1.0f, 0); \
        ID3D12GraphicsCommandList_CopyBufferRegion(list, probe, 0, zero, 0, 256); \
        ID3D12GraphicsCommandList_SetComputeRootSignature(list, rs); \
        ID3D12GraphicsCommandList_SetPipelineState(list, (pso_)); \
        ID3D12GraphicsCommandList_SetDescriptorHeaps(list, 1, &cbvh); \
        ID3D12GraphicsCommandList_SetComputeRoot32BitConstant(list, 0, 0xDEADBEEF, 0); \
        ID3D12GraphicsCommandList_SetComputeRootConstantBufferView(list, 1, ID3D12Resource_GetGPUVirtualAddress(cbuf) + 256); \
        cbvh->lpVtbl->GetGPUDescriptorHandleForHeapStart(cbvh, &gh); base = gh.ptr; \
        gh.ptr = base + (UINT64)5 * cbv_inc; ID3D12GraphicsCommandList_SetComputeRootDescriptorTable(list, 2, gh); \
        gh.ptr = base + (UINT64)9 * cbv_inc; ID3D12GraphicsCommandList_SetComputeRootDescriptorTable(list, 3, gh); \
        ID3D12GraphicsCommandList_SetComputeRootUnorderedAccessView(list, 4, ID3D12Resource_GetGPUVirtualAddress(probe)); \
        ID3D12GraphicsCommandList_Dispatch(list, 1, 1, 1); \
        ID3D12GraphicsCommandList_CopyBufferRegion(list, proberb, 0, probe, 0, 64); \
        submit_and_wait(); } while (0)
#define ROW(f_, i_) (f_)[(i_) * 4], (f_)[(i_) * 4 + 1], (f_)[(i_) * 4 + 2], (f_)[(i_) * 4 + 3]
    if (pso_write) {
        float *f = NULL;
        RUN_CS(pso_write);
        ID3D12Resource_Map(proberb, 0, NULL, (void **)&f);
        if (f) {
            say("  7a write-only row0 = (%g, %g, %g, %g) expected (1, 2, 3, 4)", ROW(f, 0));
            say("  7a write-only row1 = (%g, %g, %g, %g) expected (5, 6, 7, 8)", ROW(f, 1));
            CHECK(f[0] == 1.0f && f[3] == 4.0f && f[4] == 5.0f && f[7] == 8.0f, "case7a: a compute write through the table UAV lands and reads back");
            ID3D12Resource_Unmap(proberb, 0, NULL);
        } else CHECK(0, "case7a: probe readback map");
    }
    if (pso_probe) {
        float *f = NULL;
        RUN_CS(pso_probe);
        ID3D12Resource_Map(proberb, 0, NULL, (void **)&f);
        if (f) {
            UINT *u = (UINT *)f;
            say("  7b probe colour   = (%g, %g, %g, %g) expected (0, 0.25, 1, 1)", ROW(f, 0));
            say("  7b probe xform[0] = (%g, %g, %g, %g) expected (0.5, 0, 0, 0)", ROW(f, 1));
            say("  7b probe PosBuf   = (%g, %g, %g, %g) expected (-1, -1, 0.5, 3)", ROW(f, 2));
            say("  7b probe IdBuf    = (%#x, %#x, %#x, %#x) expected (0x304, 0x304, 0x304, ...)", u[12], u[13], u[14], u[15]);
            CHECK(f[1] == 0.25f && f[2] == 1.0f, "case7b: compute sees the CBV through root parameter 1");
            CHECK(f[4] == 0.5f, "case7b: compute sees the matrix");
            CHECK(f[8] == -1.0f && f[10] == 0.5f && f[11] == 3.0f, "case7b: compute sees the typed float buffer at FirstElement 64");
            CHECK(u[12] == 0x0304 && u[13] == 0x0304, "case7b: compute sees the typed uint buffer at FirstElement 16");
            ID3D12Resource_Unmap(proberb, 0, NULL);
        } else CHECK(0, "case7b: probe readback map");
    }
    if (pso_root) {
        float *f = NULL;
        RUN_CS(pso_root);
        ID3D12Resource_Map(proberb, 0, NULL, (void **)&f);
        if (f) {
            say("  7c root-UAV colour   = (%g, %g, %g, %g) expected (0, 0.25, 1, 1)", ROW(f, 0));
            say("  7c root-UAV PosBuf   = (%g, %g, %g, %g) expected (-1, -1, 0.5, 3)", ROW(f, 1));
            say("  7c root-UAV constant = (%g, %g, %g, %g) expected (1, 2, 3, 4)", ROW(f, 2));
            say("  7c root-UAV xform[0] = (%g, %g, %g, %g) expected (0.5, 0, 0, 0)", ROW(f, 3));
            CHECK(f[8] == 1.0f && f[11] == 4.0f, "case7c: a compute write through the ROOT UAV lands");
            CHECK(f[1] == 0.25f && f[2] == 1.0f && f[12] == 0.5f, "case7c: compute sees the CBV (colour + matrix) via root UAV output");
            CHECK(f[4] == -1.0f && f[6] == 0.5f && f[7] == 3.0f, "case7c: compute sees the typed float buffer via root UAV output");
            ID3D12Resource_Unmap(proberb, 0, NULL);
        } else CHECK(0, "case7c: probe readback map");
    }
    /* 7d: the ml906 shape that read back zeros -- the dispatch is the FIRST
     * thing in its command list (no blit before it) and root param 4 is left
     * unset. The probe still holds 7c's rows, so row 2 == (1,2,3,4) would be
     * stale; CSWrite puts (5,6,7,8) in row 1 where 7c wrote PosBuf. */
    if (pso_write) {
        float *f = NULL; D3D12_GPU_DESCRIPTOR_HANDLE gh; UINT64 base;
        ID3D12GraphicsCommandList_SetComputeRootSignature(list, rs);
        ID3D12GraphicsCommandList_SetPipelineState(list, pso_write);
        ID3D12GraphicsCommandList_SetDescriptorHeaps(list, 1, &cbvh);
        ID3D12GraphicsCommandList_SetComputeRoot32BitConstant(list, 0, 0xDEADBEEF, 0);
        ID3D12GraphicsCommandList_SetComputeRootConstantBufferView(list, 1, ID3D12Resource_GetGPUVirtualAddress(cbuf) + 256);
        cbvh->lpVtbl->GetGPUDescriptorHandleForHeapStart(cbvh, &gh); base = gh.ptr;
        gh.ptr = base + (UINT64)5 * cbv_inc; ID3D12GraphicsCommandList_SetComputeRootDescriptorTable(list, 2, gh);
        gh.ptr = base + (UINT64)9 * cbv_inc; ID3D12GraphicsCommandList_SetComputeRootDescriptorTable(list, 3, gh);
        ID3D12GraphicsCommandList_Dispatch(list, 1, 1, 1);
        ID3D12GraphicsCommandList_CopyBufferRegion(list, proberb, 0, probe, 0, 64);
        submit_and_wait();
        ID3D12Resource_Map(proberb, 0, NULL, (void **)&f);
        if (f) {
            say("  7d first-in-list row1 = (%g, %g, %g, %g) expected (5, 6, 7, 8)", ROW(f, 1));
            CHECK(f[4] == 5.0f && f[7] == 8.0f, "case7d: a dispatch that opens the command buffer (ml906 shape) still lands");
            ID3D12Resource_Unmap(proberb, 0, NULL);
        } else CHECK(0, "case7d: probe readback map");
    }
#undef RUN_CS
#undef ROW

    /* ---- case 8 (ml914): the production logger must survive oversized,
     * newline-less records. ntdll's debug line buffer is 1020 bytes and
     * raises STATUS_BUFFER_OVERFLOW (0x80000005) when fragments without a
     * newline accumulate past it -- which is what killed the game's
     * submission thread during the draw census. ---- */
    {
        typedef void (*pfn_probe)(const char *, unsigned);
        pfn_probe probe = (pfn_probe)GetProcAddress(dll, "MadeiraD3D12LogProbe");
        if (probe) {
            static char big[3000]; int i; PVOID veh;
            for (i = 0; i < (int)sizeof big - 1; i++) big[i] = 'a' + (i % 26);
            big[sizeof big - 1] = 0;
            g_probe_code = 0;
            veh = AddVectoredExceptionHandler(1, probe_veh);   /* records the code, resumes */
            probe(big, 40); probe("short, no newline", 300);
            if (veh) RemoveVectoredExceptionHandler(veh);
            CHECK(g_probe_code == 0, "case8: 40 x 3000-byte + 300 x short newline-less log records raise nothing (code %#lx)", g_probe_code);
        } else CHECK(0, "case8: MadeiraD3D12LogProbe export present");
    }

    /* ---- case 9 (ml914): D3D draw-parameter semantics the converter derives
     * from the bind-point-4/5 block. 9a: indexed draw with a non-zero index
     * buffer offset, non-zero StartIndexLocation and BaseVertexLocation 64:
     * SV_VertexID must be index + 64. 9b: 3 instances starting at instance 5:
     * SV_InstanceID must run 0..2 (D3D excludes StartInstanceLocation). ---- */
    {
        static const float tri9[9] = { -1.0f, -1.0f, 0.5f,   3.0f, -1.0f, 0.5f,   -1.0f, 3.0f, 0.5f };
        UINT ids9[3] = { 0x0506, 0x0506, 0x0506 };
        D3D12_GPU_DESCRIPTOR_HANDLE gh; UINT64 base; D3D12_INDEX_BUFFER_VIEW ibv;
        upload(posbuf, (64 + 64 * 3) * 4, tri9, sizeof tri9);      /* PosBuf[vid*3] for vid 64..66, view starts at element 64 */
        upload(posbuf, (16 + 64) * 4, ids9, sizeof ids9);          /* IdBuf[64], view starts at element 16 */
        set_params(IDENT, 0.0f, 0.25f, 1.0f, 1);
        begin_frame(pso_fetch, 0);
        cbvh->lpVtbl->GetGPUDescriptorHandleForHeapStart(cbvh, &gh); base = gh.ptr;
        gh.ptr = base + (UINT64)7 * cbv_inc; ID3D12GraphicsCommandList_SetGraphicsRootDescriptorTable(list, 2, gh);
        ibv.BufferLocation = ID3D12Resource_GetGPUVirtualAddress(ibuf) + 8; ibv.SizeInBytes = 1000; ibv.Format = DXGI_FORMAT_R16_UINT;
        ID3D12GraphicsCommandList_IASetIndexBuffer(list, &ibv);
        ID3D12GraphicsCommandList_DrawIndexedInstanced(list, 3, 1, 4, 64, 0);   /* bytes 8 + 4*2 = 16 -> indices {0,1,2}; base vertex 64 */
        copy_rt_to_readback(); submit_and_wait();
        /* D3D semantics (and DXVK's emulation of them): SV_VertexID is the raw
         * index value, EXCLUDING BaseVertexLocation. So the fetch shader must
         * see vertex ids 0..2 -> the original triangle and id 0x0304. */
        { unsigned n = count_colour("case9a1 indexed fetch: ib offset 8, start 4, base vertex 64 (SV_VertexID = index -> id 0x0304 -> (4,3,0))", 4, 3, 0);
          unsigned m = count_colour("case9a1 wrong if base vertex leaked into SV_VertexID (6,5,0)", 6, 5, 0);
          CHECK(n == RT_W * RT_H && m == 0, "case9a1: SV_VertexID excludes BaseVertexLocation with a non-zero index buffer offset (%u right, %u leaked)", n, m); }
        /* ...while the STREAM fetch must apply the base vertex: the triangle
         * lives at vertex 64 of the position stream, sentinels elsewhere. */
        { float junk[16]; int i; for (i = 0; i < 16; i++) junk[i] = 9.0f; upload(vbuf, 64 * 12 - 64, junk, sizeof junk); }
        upload(vbuf, 64 * 12, tri9, sizeof tri9);
        set_params(IDENT, 0.0f, 0.25f, 1.0f, 0);
        begin_frame(pso_stream, 0); bind_streams(4, 0);
        { D3D12_VERTEX_BUFFER_VIEW vb[2];
          vb[0].BufferLocation = ID3D12Resource_GetGPUVirtualAddress(vbuf); vb[0].SizeInBytes = 1024; vb[0].StrideInBytes = 12;
          vb[1].BufferLocation = ID3D12Resource_GetGPUVirtualAddress(idbuf) + 4; vb[1].SizeInBytes = 4; vb[1].StrideInBytes = 0;
          ID3D12GraphicsCommandList_IASetVertexBuffers(list, 0, 2, vb); }
        ID3D12GraphicsCommandList_IASetIndexBuffer(list, &ibv);
        ID3D12GraphicsCommandList_DrawIndexedInstanced(list, 3, 1, 4, 64, 0);
        copy_rt_to_readback(); submit_and_wait();
        { unsigned n = count_colour("case9a2 indexed stream: base vertex 64 selects vertices 64..66 of the stream", 0, 64, 255);
          CHECK(n == RT_W * RT_H, "case9a2: BaseVertexLocation offsets the vertex stream fetch (%u/%u)", n, RT_W * RT_H); }
    }
    if (pso_inst) {
        set_params(IDENT, 0.0f, 0.25f, 1.0f, 0);
        begin_frame(pso_inst, 0); bind_streams(4, 0);
        ID3D12GraphicsCommandList_DrawInstanced(list, 3, 3, 0, 5);            /* instances 5,6,7 -> SV_InstanceID 0,1,2; last one wins */
        copy_rt_to_readback(); submit_and_wait();
        { unsigned n = count_colour("case9b 3 instances from StartInstanceLocation 5 (last SV_InstanceID 2 -> (2,0,0))", 2, 0, 0);
          unsigned m = count_colour("case9b wrong if (7,0,0)", 7, 0, 0);
          CHECK(n == RT_W * RT_H && m == 0, "case9b: SV_InstanceID excludes StartInstanceLocation (%u right, %u include-start)", n, m); }
    } else CHECK(0, "case9b: instance-id pipeline");

    say("vfetch: %d checks, %d failed", checks, fails);
    return fails;
}
