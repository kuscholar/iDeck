/*  M2 gate: an x86-64 Windows executable driving the ARM64EC D3D12 runtime.
 *
 *  This is the milestone the design describes: create the device, queue,
 *  allocator, list and fence; record and close an empty list; execute it; signal
 *  a fence; and wake an event waiter. It also checks the things that are easy to
 *  get wrong and invisible until much later: reference identity, refcounts,
 *  rejected interfaces, and the state rules around Close, Reset and allocator
 *  reuse.
 *
 *  The executable is x86-64 and runs under FEX; the DLL is ARM64EC. So a pass
 *  also proves the architecture transition actually happened rather than an x64
 *  fallback being loaded, which the build marker reports explicitly.
 */

#define COBJMACROS
#define INITGUID
#include <initguid.h>
#include <windows.h>
#include <d3d12.h>
#include <stdio.h>
#include <math.h>
#include "tri_dxil.h"
#include "cube_geom.h"
#include "root_sig.h"

static int checks, fails;
#define CHECK(cond, ...) do {                                                  \
    checks++;                                                                  \
    if (!(cond)) { fails++; printf("  FAIL  " __VA_ARGS__); printf("\n"); }     \
    else         { printf("  ok    " __VA_ARGS__); printf("\n"); }             \
} while (0)

typedef HRESULT (WINAPI *pfn_create)(IUnknown *, D3D_FEATURE_LEVEL, REFIID, void **);
typedef const char *(*pfn_marker)(void);
typedef void (*pfn_stats)(ID3D12CommandQueue *, UINT64 *, UINT64 *);

static pfn_stats g_stats;
static void stats(ID3D12CommandQueue *q, UINT64 *e, UINT64 *r) {
    *e = *r = 0;
    if (g_stats) g_stats(q, e, r);
}

/* Advances the fence from another thread so the blocking wait has something to
 * wake it.
 *
 * It waits on `ready` first so the main thread controls the ordering: without
 * that, the signal can land before the main thread even reaches the call, and
 * the wait then returns immediately having blocked on nothing. That is exactly
 * what happened on one of the two devices, and elapsed time could not tell the
 * difference because a coarse clock also reads zero. The check that actually
 * settles it is the fence value observed immediately before the call. */
struct blocker_args { ID3D12Fence *fence; UINT64 value; DWORD delay_ms; HANDLE ready; };
static DWORD WINAPI blocker(LPVOID p) {
    struct blocker_args *a = (struct blocker_args *)p;
    WaitForSingleObject(a->ready, INFINITE);
    Sleep(a->delay_ms);
    ID3D12Fence_Signal(a->fence, a->value);
    return 0;
}

int main(void) {
    printf("madeira-d3d12 M2: x64 caller -> ARM64EC D3D12 runtime\n\n");

    HMODULE dll = LoadLibraryA("madeira_d3d12.dll");
    CHECK(dll != NULL, "madeira_d3d12.dll loaded (err %lu)", dll ? 0UL : GetLastError());
    if (!dll) return 1;

    pfn_marker marker = (pfn_marker)GetProcAddress(dll, "MadeiraD3D12GetBuildMarker");
    pfn_create create = (pfn_create)GetProcAddress(dll, "MadeiraD3D12CreateDevice");
    g_stats = (pfn_stats)GetProcAddress(dll, "MadeiraD3D12GetQueueStats");
    pfn_serialize serialize = (pfn_serialize)GetProcAddress(dll, "MadeiraD3D12SerializeRootSignature");
    CHECK(marker && create && g_stats, "exports resolved");
    if (!marker || !create) return 1;

    /* Names the implementation actually reached. The design asks for a module
     * marker precisely so "did the x64 caller reach ARM64EC code" is answered by
     * evidence rather than by assuming the loader did the right thing. */
    printf("\n  implementation: %s\n\n", marker());

    /* Support probe: a null out-pointer must report support without creating. */
    HRESULT hr = create(NULL, D3D_FEATURE_LEVEL_11_0, &IID_ID3D12Device, NULL);
    CHECK(hr == S_FALSE, "null-device support probe returns S_FALSE (got %#lx)", hr);

    /* A level we do not claim must be refused, not silently accepted. */
    ID3D12Device *bogus = NULL;
    hr = create(NULL, D3D_FEATURE_LEVEL_12_1, &IID_ID3D12Device, (void **)&bogus);
    CHECK(FAILED(hr) && bogus == NULL, "unclaimed feature level 12_1 refused (%#lx)", hr);

    ID3D12Device *dev = NULL;
    hr = create(NULL, D3D_FEATURE_LEVEL_11_0, &IID_ID3D12Device, (void **)&dev);
    CHECK(SUCCEEDED(hr) && dev, "device created (%#lx)", hr);
    if (!dev) return 1;

    /* Reference identity: QueryInterface for IUnknown must return the same
     * pointer, and an interface we are not must be refused. */
    IUnknown *unk = NULL;
    hr = ID3D12Device_QueryInterface(dev, &IID_IUnknown, (void **)&unk);
    CHECK(SUCCEEDED(hr) && (void *)unk == (void *)dev, "QueryInterface(IUnknown) returns the same pointer");
    if (unk) IUnknown_Release(unk);

    void *nope = NULL;
    hr = ID3D12Device_QueryInterface(dev, &IID_ID3D12Fence, &nope);
    CHECK(hr == E_NOINTERFACE && nope == NULL, "device refuses IID_ID3D12Fence (%#lx)", hr);

    ULONG r1 = ID3D12Device_AddRef(dev);
    ULONG r2 = ID3D12Device_Release(dev);
    CHECK(r1 == 2 && r2 == 1, "refcount round-trips (AddRef %lu, Release %lu)", r1, r2);

    CHECK(ID3D12Device_GetNodeCount(dev) == 1, "GetNodeCount reports a single node");

    /* ---- the M2 sequence ---- */
    D3D12_COMMAND_QUEUE_DESC qd;
    ZeroMemory(&qd, sizeof qd);
    qd.Type = D3D12_COMMAND_LIST_TYPE_DIRECT;
    ID3D12CommandQueue *queue = NULL;
    hr = ID3D12Device_CreateCommandQueue(dev, &qd, &IID_ID3D12CommandQueue, (void **)&queue);
    CHECK(SUCCEEDED(hr) && queue, "command queue created (%#lx)", hr);

    ID3D12CommandAllocator *alloc = NULL;
    hr = ID3D12Device_CreateCommandAllocator(dev, D3D12_COMMAND_LIST_TYPE_DIRECT,
                                             &IID_ID3D12CommandAllocator, (void **)&alloc);
    CHECK(SUCCEEDED(hr) && alloc, "command allocator created (%#lx)", hr);

    ID3D12GraphicsCommandList *list = NULL;
    hr = ID3D12Device_CreateCommandList(dev, 0, D3D12_COMMAND_LIST_TYPE_DIRECT, alloc, NULL,
                                        &IID_ID3D12GraphicsCommandList, (void **)&list);
    CHECK(SUCCEEDED(hr) && list, "command list created (%#lx)", hr);
    if (!queue || !alloc || !list) return 1;

    CHECK(ID3D12GraphicsCommandList_GetType(list) == D3D12_COMMAND_LIST_TYPE_DIRECT,
          "list reports DIRECT type");

    /* A list is created recording, so resetting its allocator now must fail. */
    hr = ID3D12CommandAllocator_Reset(alloc);
    CHECK(FAILED(hr), "allocator reset refused while a list records into it (%#lx)", hr);

    hr = ID3D12GraphicsCommandList_Close(list);
    CHECK(SUCCEEDED(hr), "empty list closed (%#lx)", hr);
    hr = ID3D12GraphicsCommandList_Close(list);
    CHECK(FAILED(hr), "second Close refused (%#lx)", hr);

    ID3D12CommandList *lists[1] = { (ID3D12CommandList *)list };
    UINT64 executed = 0, rejected = 0;

    /* Execute while the recording is still valid. Resetting the allocator first
     * and then executing this same list -- which an earlier version of this test
     * did -- submits storage the allocator has already taken back, and real
     * D3D12 rejects it. The order here is the legal one. */
    ID3D12CommandQueue_ExecuteCommandLists(queue, 1, lists);
    stats(queue, &executed, &rejected);
    CHECK(executed == 1 && rejected == 0, "valid list executed (executed %llu, rejected %llu)",
          (unsigned long long)executed, (unsigned long long)rejected);

    hr = ID3D12CommandAllocator_Reset(alloc);
    CHECK(SUCCEEDED(hr), "allocator reset accepted once the list is closed (%#lx)", hr);

    /* The list is now stale: it was recorded against storage that has been
     * handed back. Submitting it must be refused, not silently replayed. */
    ID3D12CommandQueue_ExecuteCommandLists(queue, 1, lists);
    stats(queue, &executed, &rejected);
    CHECK(executed == 1 && rejected == 1,
          "list recorded before the allocator reset is rejected (executed %llu, rejected %llu)",
          (unsigned long long)executed, (unsigned long long)rejected);

    /* Re-recording against the reset allocator makes it valid again. */
    hr = ID3D12GraphicsCommandList_Reset(list, alloc, NULL);
    CHECK(SUCCEEDED(hr), "list reset against the reset allocator (%#lx)", hr);
    hr = ID3D12GraphicsCommandList_Close(list);
    CHECK(SUCCEEDED(hr), "re-recorded list closed (%#lx)", hr);
    ID3D12CommandQueue_ExecuteCommandLists(queue, 1, lists);
    stats(queue, &executed, &rejected);
    CHECK(executed == 2 && rejected == 1, "re-recorded list executes (executed %llu, rejected %llu)",
          (unsigned long long)executed, (unsigned long long)rejected);

    ID3D12Fence *fence = NULL;
    hr = ID3D12Device_CreateFence(dev, 0, D3D12_FENCE_FLAG_NONE, &IID_ID3D12Fence, (void **)&fence);
    CHECK(SUCCEEDED(hr) && fence, "fence created at 0 (%#lx)", hr);
    if (!fence) return 1;
    CHECK(ID3D12Fence_GetCompletedValue(fence) == 0, "fence starts at 0");

    HANDLE ev = CreateEventA(NULL, FALSE, FALSE, NULL);
    CHECK(ev != NULL, "event created");

    /* Late registration for a value already reached must signal immediately;
     * queueing it would hang the caller forever. */
    hr = ID3D12Fence_SetEventOnCompletion(fence, 0, ev);
    CHECK(SUCCEEDED(hr) && WaitForSingleObject(ev, 0) == WAIT_OBJECT_0,
          "waiting on an already-reached value signals at once");

    /* The real sequence: register, execute, signal, wake. */
    hr = ID3D12Fence_SetEventOnCompletion(fence, 1, ev);
    CHECK(SUCCEEDED(hr), "registered for fence value 1 (%#lx)", hr);
    CHECK(WaitForSingleObject(ev, 0) == WAIT_TIMEOUT, "not signalled before the queue signals");

    ID3D12CommandQueue_ExecuteCommandLists(queue, 1, lists);
    hr = ID3D12CommandQueue_Signal(queue, fence, 1);
    CHECK(SUCCEEDED(hr), "queue signalled the fence (%#lx)", hr);
    CHECK(WaitForSingleObject(ev, 5000) == WAIT_OBJECT_0, "event waiter woke");
    CHECK(ID3D12Fence_GetCompletedValue(fence) == 1, "completed value advanced to 1");

    /* A null event means block until the value is reached. Another thread
     * advances the fence while this one is inside the call, which also proves
     * the wait is not holding the fence lock: if it were, the signalling thread
     * could not get in and this would deadlock rather than return. */
    {
        struct blocker_args ba;
        ba.fence = fence;
        ba.value = 42;
        ba.delay_ms = 150;
        ba.ready = CreateEventA(NULL, TRUE, FALSE, NULL);
        HANDLE th = CreateThread(NULL, 0, blocker, &ba, 0, NULL);
        CHECK(th != NULL && ba.ready != NULL, "signalling thread started");

        /* Observed before the call, so a pass cannot be an artefact of the
         * clock: the value is provably below the target at this point. */
        UINT64 before = ID3D12Fence_GetCompletedValue(fence);
        CHECK(before < 42, "fence is below the target before the wait (%llu)",
              (unsigned long long)before);

        DWORD t0 = GetTickCount();
        SetEvent(ba.ready);                       /* the blocker may now sleep and signal */
        hr = ID3D12Fence_SetEventOnCompletion(fence, 42, NULL);
        DWORD waited = GetTickCount() - t0;
        UINT64 after = ID3D12Fence_GetCompletedValue(fence);

        CHECK(SUCCEEDED(hr), "null-event wait returned success (%#lx)", hr);
        CHECK(before < 42 && after >= 42,
              "null-event wait blocked until the value was reached: %llu -> %llu (%lu ms elapsed)",
              (unsigned long long)before, (unsigned long long)after, waited);
        if (th) { WaitForSingleObject(th, 5000); CloseHandle(th); }
        if (ba.ready) CloseHandle(ba.ready);
    }

    /* Repeated cycles: reset, record, close, execute, signal again. */
    int cycles_ok = 1;
    for (UINT64 n = 43; n <= 46; n++) {
        if (FAILED(ID3D12GraphicsCommandList_Reset(list, alloc, NULL))) { cycles_ok = 0; break; }
        if (FAILED(ID3D12GraphicsCommandList_Close(list))) { cycles_ok = 0; break; }
        ID3D12CommandQueue_ExecuteCommandLists(queue, 1, lists);
        if (FAILED(ID3D12CommandQueue_Signal(queue, fence, n))) { cycles_ok = 0; break; }
        if (ID3D12Fence_GetCompletedValue(fence) != n) { cycles_ok = 0; break; }
    }
    CHECK(cycles_ok && ID3D12Fence_GetCompletedValue(fence) == 46,
          "four more record/close/execute/signal cycles");

    /* ---- M3a: real GPU buffer copy and readback ----
     *
     * Upload -> default -> readback, every hop at a DIFFERENT offset, so a copy
     * that is shifted, truncated or silently skipped produces wrong bytes rather
     * than plausible ones. The readback buffer is pre-filled with a sentinel and
     * the regions outside the copied range are checked afterwards, because a
     * copy that writes too much is as wrong as one that writes too little. */
    {
        const UINT64 BUF = 4096, LEN = 1024;
        const UINT64 SRC_OFF = 256, MID_OFF = 512, DST_OFF = 128;
        const BYTE SENTINEL = 0xCD;

        D3D12_HEAP_PROPERTIES hp; ZeroMemory(&hp, sizeof hp);
        D3D12_RESOURCE_DESC rd;  ZeroMemory(&rd, sizeof rd);
        rd.Dimension = D3D12_RESOURCE_DIMENSION_BUFFER;
        rd.Width = BUF; rd.Height = 1; rd.DepthOrArraySize = 1; rd.MipLevels = 1;
        rd.Format = DXGI_FORMAT_UNKNOWN; rd.SampleDesc.Count = 1;
        rd.Layout = D3D12_TEXTURE_LAYOUT_ROW_MAJOR;

        ID3D12Resource *up = NULL, *mid = NULL, *rb = NULL;
        hp.Type = D3D12_HEAP_TYPE_UPLOAD;
        hr = ID3D12Device_CreateCommittedResource(dev, &hp, D3D12_HEAP_FLAG_NONE, &rd,
                D3D12_RESOURCE_STATE_GENERIC_READ, NULL, &IID_ID3D12Resource, (void **)&up);
        CHECK(SUCCEEDED(hr) && up, "upload buffer created (%#lx)", hr);
        hp.Type = D3D12_HEAP_TYPE_DEFAULT;
        hr = ID3D12Device_CreateCommittedResource(dev, &hp, D3D12_HEAP_FLAG_NONE, &rd,
                D3D12_RESOURCE_STATE_COPY_DEST, NULL, &IID_ID3D12Resource, (void **)&mid);
        CHECK(SUCCEEDED(hr) && mid, "default (GPU-private) buffer created (%#lx)", hr);
        hp.Type = D3D12_HEAP_TYPE_READBACK;
        hr = ID3D12Device_CreateCommittedResource(dev, &hp, D3D12_HEAP_FLAG_NONE, &rd,
                D3D12_RESOURCE_STATE_COPY_DEST, NULL, &IID_ID3D12Resource, (void **)&rb);
        CHECK(SUCCEEDED(hr) && rb, "readback buffer created (%#lx)", hr);

        if (up && mid && rb) {
            /* A GPU-private resource must not be mappable. */
            void *nope2 = NULL;
            hr = ID3D12Resource_Map(mid, 0, NULL, &nope2);
            CHECK(FAILED(hr), "Map refused on the DEFAULT-heap buffer (%#lx)", hr);

            BYTE *src = NULL, *dst = NULL;
            hr = ID3D12Resource_Map(up, 0, NULL, (void **)&src);
            CHECK(SUCCEEDED(hr) && src, "upload buffer mapped (%#lx)", hr);
            hr = ID3D12Resource_Map(rb, 0, NULL, (void **)&dst);
            CHECK(SUCCEEDED(hr) && dst, "readback buffer mapped (%#lx)", hr);

            if (src && dst) {
                /* Deliberately not a constant or a ramp: a byte-shifted copy
                 * must not be able to look correct. */
                for (UINT64 i = 0; i < BUF; i++)
                    src[i] = (BYTE)((i * 31u + (i >> 3) * 17u + 0x5Au) & 0xFF);
                memset(dst, SENTINEL, (size_t)BUF);

                hr = ID3D12GraphicsCommandList_Reset(list, alloc, NULL);
                CHECK(SUCCEEDED(hr), "list reset for the copy (%#lx)", hr);
                ID3D12GraphicsCommandList_CopyBufferRegion(list, mid, MID_OFF, up, SRC_OFF, LEN);
                ID3D12GraphicsCommandList_CopyBufferRegion(list, rb, DST_OFF, mid, MID_OFF, LEN);
                hr = ID3D12GraphicsCommandList_Close(list);
                CHECK(SUCCEEDED(hr), "copy list closed (%#lx)", hr);

                UINT64 before_exec = ID3D12Fence_GetCompletedValue(fence);
                ID3D12CommandQueue_ExecuteCommandLists(queue, 1, lists);
                HANDLE done = CreateEventA(NULL, FALSE, FALSE, NULL);
                ID3D12Fence_SetEventOnCompletion(fence, before_exec + 1, done);
                hr = ID3D12CommandQueue_Signal(queue, fence, before_exec + 1);
                CHECK(SUCCEEDED(hr), "queue signalled after the copy (%#lx)", hr);
                CHECK(WaitForSingleObject(done, 10000) == WAIT_OBJECT_0,
                      "waiter woke for the copy fence");
                CloseHandle(done);

                /* Everything below is read only AFTER the waiter woke, which is
                 * the ordering guarantee being tested. */
                int payload_ok = 1;
                UINT64 first_bad = 0;
                for (UINT64 i = 0; i < LEN; i++) {
                    if (dst[DST_OFF + i] != src[SRC_OFF + i]) {
                        payload_ok = 0; first_bad = i; break;
                    }
                }
                CHECK(payload_ok, "%llu copied bytes match byte-for-byte%s",
                      (unsigned long long)LEN,
                      payload_ok ? "" : " -- first mismatch at offset shown next");
                if (!payload_ok)
                    printf("        first mismatch at %llu: got %02X expected %02X\n",
                           (unsigned long long)first_bad,
                           dst[DST_OFF + first_bad], src[SRC_OFF + first_bad]);

                int before_ok = 1, after_ok = 1;
                for (UINT64 i = 0; i < DST_OFF; i++)
                    if (dst[i] != SENTINEL) { before_ok = 0; break; }
                for (UINT64 i = DST_OFF + LEN; i < BUF; i++)
                    if (dst[i] != SENTINEL) { after_ok = 0; break; }
                CHECK(before_ok, "the %llu sentinel bytes before the copy are untouched",
                      (unsigned long long)DST_OFF);
                CHECK(after_ok, "the %llu sentinel bytes after the copy are untouched",
                      (unsigned long long)(BUF - DST_OFF - LEN));

                ID3D12Resource_Unmap(up, 0, NULL);
                ID3D12Resource_Unmap(rb, 0, NULL);
            }
        }
        if (rb) ID3D12Resource_Release(rb);
        if (mid) ID3D12Resource_Release(mid);
        if (up) ID3D12Resource_Release(up);
    }

    /* ---- M3b: offscreen triangle through the D3D12 runtime ----
     *
     * Every drawing call goes through our D3D12 interfaces. The viewport covers
     * the LEFT half only, so a correct frame has the shader's constant-buffer
     * colour on the left and the clear colour on the right. A draw that silently
     * did nothing leaves the whole target the clear colour; one that ignored the
     * viewport covers all of it. Both are distinguishable from success. */
    {
        const UINT RT_W = 64, RT_H = 64;
        const UINT64 RB_SIZE = (UINT64)RT_W * RT_H * 4;

        /* Nothing is registered any more. The DXIL handed to the pipeline below
         * is converted on this machine at creation time, so there is no
         * embedded library that could stand in for it. */
        CHECK(serialize != NULL, "root signature serializer export present");

        /* A real serialized container now, produced by the runtime's own
         * serializer and read back by its parser. The old call handed four
         * bytes of shader bytecode to CreateRootSignature, which only worked
         * because nothing looked at it. */
        static unsigned char rs_blob[512];
        ID3D12RootSignature *rs = make_root_sig(dev, serialize, rs_blob, sizeof rs_blob);
        hr = rs ? S_OK : E_FAIL;
        CHECK(SUCCEEDED(hr) && rs, "root signature created (%#lx)", hr);

        D3D12_GRAPHICS_PIPELINE_STATE_DESC pd; ZeroMemory(&pd, sizeof pd);
        pd.pRootSignature = rs;
        pd.VS.pShaderBytecode = tri_vs_dxil; pd.VS.BytecodeLength = sizeof tri_vs_dxil;
        pd.PS.pShaderBytecode = tri_ps_dxil; pd.PS.BytecodeLength = sizeof tri_ps_dxil;
        pd.NumRenderTargets = 1;
        pd.RTVFormats[0] = DXGI_FORMAT_R8G8B8A8_UNORM;
        pd.SampleDesc.Count = 1;
        pd.PrimitiveTopologyType = D3D12_PRIMITIVE_TOPOLOGY_TYPE_TRIANGLE;

        ID3D12PipelineState *pso = NULL;
        hr = ID3D12Device_CreateGraphicsPipelineState(dev, &pd, &IID_ID3D12PipelineState, (void **)&pso);
        CHECK(SUCCEEDED(hr) && pso, "pipeline built by converting the supplied DXIL at run time (%#lx)", hr);

        /* A shader the runtime has no library for must be REFUSED, not quietly
         * served from a fixture. */
        D3D12_GRAPHICS_PIPELINE_STATE_DESC bad = pd;
        static const unsigned char junk_dxil[64] = { 'D','X','B','C' };
        bad.VS.pShaderBytecode = junk_dxil; bad.VS.BytecodeLength = sizeof junk_dxil;
        ID3D12PipelineState *bad_pso = NULL;
        hr = ID3D12Device_CreateGraphicsPipelineState(dev, &bad, &IID_ID3D12PipelineState, (void **)&bad_pso);
        CHECK(FAILED(hr) && bad_pso == NULL,
              "bytecode that is not real DXIL fails conversion rather than rendering something (%#lx)", hr);

        D3D12_DESCRIPTOR_HEAP_DESC hd; ZeroMemory(&hd, sizeof hd);
        hd.Type = D3D12_DESCRIPTOR_HEAP_TYPE_RTV; hd.NumDescriptors = 1;
        ID3D12DescriptorHeap *rtvh = NULL;
        hr = ID3D12Device_CreateDescriptorHeap(dev, &hd, &IID_ID3D12DescriptorHeap, (void **)&rtvh);
        CHECK(SUCCEEDED(hr) && rtvh, "RTV descriptor heap created (%#lx)", hr);

        D3D12_HEAP_PROPERTIES hp2; ZeroMemory(&hp2, sizeof hp2);
        D3D12_RESOURCE_DESC td;  ZeroMemory(&td, sizeof td);
        td.Dimension = D3D12_RESOURCE_DIMENSION_TEXTURE2D;
        td.Width = RT_W; td.Height = RT_H; td.DepthOrArraySize = 1; td.MipLevels = 1;
        td.Format = DXGI_FORMAT_R8G8B8A8_UNORM; td.SampleDesc.Count = 1;
        td.Flags = D3D12_RESOURCE_FLAG_ALLOW_RENDER_TARGET;
        hp2.Type = D3D12_HEAP_TYPE_DEFAULT;
        ID3D12Resource *rt = NULL;
        hr = ID3D12Device_CreateCommittedResource(dev, &hp2, D3D12_HEAP_FLAG_NONE, &td,
                D3D12_RESOURCE_STATE_RENDER_TARGET, NULL, &IID_ID3D12Resource, (void **)&rt);
        CHECK(SUCCEEDED(hr) && rt, "render target created (%#lx)", hr);

        D3D12_RESOURCE_DESC bd2; ZeroMemory(&bd2, sizeof bd2);
        bd2.Dimension = D3D12_RESOURCE_DIMENSION_BUFFER;
        bd2.Width = RB_SIZE; bd2.Height = 1; bd2.DepthOrArraySize = 1; bd2.MipLevels = 1;
        bd2.Format = DXGI_FORMAT_UNKNOWN; bd2.SampleDesc.Count = 1;
        bd2.Layout = D3D12_TEXTURE_LAYOUT_ROW_MAJOR;
        hp2.Type = D3D12_HEAP_TYPE_READBACK;
        ID3D12Resource *pix = NULL;
        hr = ID3D12Device_CreateCommittedResource(dev, &hp2, D3D12_HEAP_FLAG_NONE, &bd2,
                D3D12_RESOURCE_STATE_COPY_DEST, NULL, &IID_ID3D12Resource, (void **)&pix);
        CHECK(SUCCEEDED(hr) && pix, "pixel readback buffer created (%#lx)", hr);

        hp2.Type = D3D12_HEAP_TYPE_UPLOAD;
        bd2.Width = 256;
        ID3D12Resource *cbv = NULL;
        hr = ID3D12Device_CreateCommittedResource(dev, &hp2, D3D12_HEAP_FLAG_NONE, &bd2,
                D3D12_RESOURCE_STATE_GENERIC_READ, NULL, &IID_ID3D12Resource, (void **)&cbv);
        CHECK(SUCCEEDED(hr) && cbv, "constant buffer created (%#lx)", hr);

        if (rs && pso && rtvh && rt && pix && cbv) {
            D3D12_CPU_DESCRIPTOR_HANDLE rtv;
            /* The COBJMACROS wrapper for this one is deliberately disabled in the
             * header because it returns an aggregate, so call through the vtable. */
            rtvh->lpVtbl->GetCPUDescriptorHandleForHeapStart(rtvh, &rtv);
            ID3D12Device_CreateRenderTargetView(dev, rt, NULL, rtv);

            float *cb = NULL;
            ID3D12Resource_Map(cbv, 0, NULL, (void **)&cb);
            if (cb) { cb[0] = 0.0f; cb[1] = 0.25f; cb[2] = 1.0f; cb[3] = 1.0f; }   /* shader colour */
            ID3D12Resource_Unmap(cbv, 0, NULL);

            BYTE *px = NULL;
            ID3D12Resource_Map(pix, 0, NULL, (void **)&px);
            if (px) memset(px, 0xCD, (size_t)RB_SIZE);

            const FLOAT clear[4] = { 1.0f, 0.0f, 0.0f, 1.0f };                     /* clear colour */
            D3D12_VIEWPORT vp; vp.TopLeftX = 0; vp.TopLeftY = 0;
            vp.Width = (FLOAT)(RT_W / 2); vp.Height = (FLOAT)RT_H;
            vp.MinDepth = 0.0f; vp.MaxDepth = 1.0f;

            hr = ID3D12GraphicsCommandList_Reset(list, alloc, NULL);
            CHECK(SUCCEEDED(hr), "list reset for the draw (%#lx)", hr);
            ID3D12GraphicsCommandList_OMSetRenderTargets(list, 1, &rtv, FALSE, NULL);
            ID3D12GraphicsCommandList_ClearRenderTargetView(list, rtv, clear, 0, NULL);
            ID3D12GraphicsCommandList_SetGraphicsRootSignature(list, rs);
            ID3D12GraphicsCommandList_SetPipelineState(list, pso);
            ID3D12GraphicsCommandList_SetGraphicsRootConstantBufferView(list, 0,
                    ID3D12Resource_GetGPUVirtualAddress(cbv));
            ID3D12GraphicsCommandList_RSSetViewports(list, 1, &vp);
            ID3D12GraphicsCommandList_IASetPrimitiveTopology(list, D3D_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
            ID3D12GraphicsCommandList_DrawInstanced(list, 3, 1, 0, 0);

            D3D12_TEXTURE_COPY_LOCATION dstl, srcl;
            ZeroMemory(&dstl, sizeof dstl); ZeroMemory(&srcl, sizeof srcl);
            dstl.pResource = pix; dstl.Type = D3D12_TEXTURE_COPY_TYPE_PLACED_FOOTPRINT;
            srcl.pResource = rt;  srcl.Type = D3D12_TEXTURE_COPY_TYPE_SUBRESOURCE_INDEX;
            ID3D12GraphicsCommandList_CopyTextureRegion(list, &dstl, 0, 0, 0, &srcl, NULL);

            hr = ID3D12GraphicsCommandList_Close(list);
            CHECK(SUCCEEDED(hr), "draw list closed (%#lx)", hr);

            UINT64 base = ID3D12Fence_GetCompletedValue(fence);
            ID3D12CommandQueue_ExecuteCommandLists(queue, 1, lists);
            HANDLE dn = CreateEventA(NULL, FALSE, FALSE, NULL);
            ID3D12Fence_SetEventOnCompletion(fence, base + 1, dn);
            ID3D12CommandQueue_Signal(queue, fence, base + 1);
            CHECK(WaitForSingleObject(dn, 10000) == WAIT_OBJECT_0, "waiter woke for the draw fence");
            CloseHandle(dn);

            if (px) {
                /* Sample well inside each half so rasterisation edges cannot
                 * decide the result. */
                const BYTE *L = px + ((RT_H / 2) * RT_W + RT_W / 4) * 4;
                const BYTE *R = px + ((RT_H / 2) * RT_W + (RT_W * 3) / 4) * 4;
                CHECK(L[0] == 0 && L[1] == 64 && L[2] == 255 && L[3] == 255,
                      "drawn half is the shader's constant-buffer colour: (%u,%u,%u,%u) expected (0,64,255,255)",
                      L[0], L[1], L[2], L[3]);
                CHECK(R[0] == 255 && R[1] == 0 && R[2] == 0 && R[3] == 255,
                      "undrawn half kept the clear colour: (%u,%u,%u,%u) expected (255,0,0,255)",
                      R[0], R[1], R[2], R[3]);
                CHECK(memcmp(L, R, 4) != 0, "the two halves differ, so the draw and the clear are distinguishable");
                ID3D12Resource_Unmap(pix, 0, NULL);
            }
        }
        if (cbv) ID3D12Resource_Release(cbv);
        if (pix) ID3D12Resource_Release(pix);
        if (rt) ID3D12Resource_Release(rt);
        if (rtvh) ID3D12DescriptorHeap_Release(rtvh);
        if (pso) ID3D12PipelineState_Release(pso);
        if (rs) ID3D12RootSignature_Release(rs);
    }

    /* ---- M4: indexed cube with depth and a changing transform ----
     *
     * Real index buffer, real DrawIndexed, depth attachment and depth state. The
     * index order draws the FRONT face first and the BACK face after it, and both
     * cover the centre at angle zero. So the centre pixel says which one won:
     * blue means depth testing kept the nearer face, red means the later draw
     * simply overwrote it. That makes depth a checkable property rather than
     * something assumed to be on. */
    {
        const UINT RT_W = 64, RT_H = 64;
        const UINT64 RB_SIZE = (UINT64)RT_W * RT_H * 4;

        /* Its own root signature, built and parsed the same way. The pipeline
         * must carry one: the converter compiles the shaders against it, so a
         * missing signature is a different binding layout, not a small
         * omission. */
        static unsigned char crs_blob[512];
        ID3D12RootSignature *crs = make_root_sig(dev, serialize, crs_blob, sizeof crs_blob);
        CHECK(crs != NULL, "cube root signature created from a serialized blob");

        D3D12_GRAPHICS_PIPELINE_STATE_DESC cpd; ZeroMemory(&cpd, sizeof cpd);
        cpd.pRootSignature = crs;
        cpd.VS.pShaderBytecode = cube_vs_dxil; cpd.VS.BytecodeLength = sizeof cube_vs_dxil;
        cpd.PS.pShaderBytecode = cube_ps_dxil; cpd.PS.BytecodeLength = sizeof cube_ps_dxil;
        cpd.NumRenderTargets = 1;
        cpd.RTVFormats[0] = DXGI_FORMAT_R8G8B8A8_UNORM;
        cpd.DSVFormat = DXGI_FORMAT_D32_FLOAT;
        cpd.SampleDesc.Count = 1;
        cpd.PrimitiveTopologyType = D3D12_PRIMITIVE_TOPOLOGY_TYPE_TRIANGLE;
        ID3D12PipelineState *cpso = NULL;
        hr = ID3D12Device_CreateGraphicsPipelineState(dev, &cpd, &IID_ID3D12PipelineState, (void **)&cpso);
        CHECK(SUCCEEDED(hr) && cpso, "cube pipeline created with a depth format (%#lx)", hr);

        D3D12_HEAP_PROPERTIES hp3; ZeroMemory(&hp3, sizeof hp3);
        D3D12_RESOURCE_DESC td3; ZeroMemory(&td3, sizeof td3);
        td3.Dimension = D3D12_RESOURCE_DIMENSION_TEXTURE2D;
        td3.Width = RT_W; td3.Height = RT_H; td3.DepthOrArraySize = 1; td3.MipLevels = 1;
        td3.SampleDesc.Count = 1;

        hp3.Type = D3D12_HEAP_TYPE_DEFAULT;
        td3.Format = DXGI_FORMAT_R8G8B8A8_UNORM;
        td3.Flags = D3D12_RESOURCE_FLAG_ALLOW_RENDER_TARGET;
        ID3D12Resource *crt = NULL;
        hr = ID3D12Device_CreateCommittedResource(dev, &hp3, D3D12_HEAP_FLAG_NONE, &td3,
                D3D12_RESOURCE_STATE_RENDER_TARGET, NULL, &IID_ID3D12Resource, (void **)&crt);
        CHECK(SUCCEEDED(hr) && crt, "cube render target created (%#lx)", hr);

        td3.Format = DXGI_FORMAT_D32_FLOAT;
        td3.Flags = D3D12_RESOURCE_FLAG_ALLOW_DEPTH_STENCIL;
        ID3D12Resource *dsb = NULL;
        hr = ID3D12Device_CreateCommittedResource(dev, &hp3, D3D12_HEAP_FLAG_NONE, &td3,
                D3D12_RESOURCE_STATE_DEPTH_WRITE, NULL, &IID_ID3D12Resource, (void **)&dsb);
        CHECK(SUCCEEDED(hr) && dsb, "depth buffer created (%#lx)", hr);

        D3D12_DESCRIPTOR_HEAP_DESC hd2; ZeroMemory(&hd2, sizeof hd2);
        hd2.Type = D3D12_DESCRIPTOR_HEAP_TYPE_RTV; hd2.NumDescriptors = 1;
        ID3D12DescriptorHeap *crtvh = NULL;
        ID3D12Device_CreateDescriptorHeap(dev, &hd2, &IID_ID3D12DescriptorHeap, (void **)&crtvh);
        hd2.Type = D3D12_DESCRIPTOR_HEAP_TYPE_DSV;
        ID3D12DescriptorHeap *dsvh = NULL;
        hr = ID3D12Device_CreateDescriptorHeap(dev, &hd2, &IID_ID3D12DescriptorHeap, (void **)&dsvh);
        CHECK(SUCCEEDED(hr) && crtvh && dsvh, "RTV and DSV heaps created (%#lx)", hr);

        D3D12_RESOURCE_DESC bd3; ZeroMemory(&bd3, sizeof bd3);
        bd3.Dimension = D3D12_RESOURCE_DIMENSION_BUFFER;
        bd3.Height = 1; bd3.DepthOrArraySize = 1; bd3.MipLevels = 1;
        bd3.Format = DXGI_FORMAT_UNKNOWN; bd3.SampleDesc.Count = 1;
        bd3.Layout = D3D12_TEXTURE_LAYOUT_ROW_MAJOR;

        hp3.Type = D3D12_HEAP_TYPE_READBACK; bd3.Width = RB_SIZE;
        ID3D12Resource *cpix = NULL;
        ID3D12Device_CreateCommittedResource(dev, &hp3, D3D12_HEAP_FLAG_NONE, &bd3,
                D3D12_RESOURCE_STATE_COPY_DEST, NULL, &IID_ID3D12Resource, (void **)&cpix);
        hp3.Type = D3D12_HEAP_TYPE_UPLOAD; bd3.Width = 1024;
        ID3D12Resource *ccb = NULL, *cib = NULL;
        ID3D12Device_CreateCommittedResource(dev, &hp3, D3D12_HEAP_FLAG_NONE, &bd3,
                D3D12_RESOURCE_STATE_GENERIC_READ, NULL, &IID_ID3D12Resource, (void **)&ccb);
        bd3.Width = 128;
        hr = ID3D12Device_CreateCommittedResource(dev, &hp3, D3D12_HEAP_FLAG_NONE, &bd3,
                D3D12_RESOURCE_STATE_GENERIC_READ, NULL, &IID_ID3D12Resource, (void **)&cib);
        CHECK(cpix && ccb && cib, "cube readback, constant and index buffers created (%#lx)", hr);

        if (cpso && crt && dsb && crtvh && dsvh && cpix && ccb && cib) {
            D3D12_CPU_DESCRIPTOR_HANDLE crtv, dsv;
            crtvh->lpVtbl->GetCPUDescriptorHandleForHeapStart(crtvh, &crtv);
            dsvh->lpVtbl->GetCPUDescriptorHandleForHeapStart(dsvh, &dsv);
            ID3D12Device_CreateRenderTargetView(dev, crt, NULL, crtv);
            ID3D12Device_CreateDepthStencilView(dev, dsb, NULL, dsv);

            /* Shared geometry so the offscreen check and the visible demo cannot
             * drift apart: 24 vertices, front face (+Z) first, back face second,
             * so the centre pixel reports whether depth kept the nearer one. */
            unsigned short *ibp = NULL;
            ID3D12Resource_Map(cib, 0, NULL, (void **)&ibp);
            if (ibp) memcpy(ibp, cube_idx, sizeof cube_idx);
            ID3D12Resource_Unmap(cib, 0, NULL);

            D3D12_INDEX_BUFFER_VIEW ibv;
            ibv.BufferLocation = ID3D12Resource_GetGPUVirtualAddress(cib);
            ibv.SizeInBytes = (UINT)sizeof cube_idx;
            ibv.Format = DXGI_FORMAT_R16_UINT;

            BYTE *cpx = NULL;
            ID3D12Resource_Map(cpix, 0, NULL, (void **)&cpx);
            BYTE frame0[4] = {0}, frame1[4] = {0}, corner0[4] = {0};
            unsigned long long differing = 0;

            for (int frame = 0; frame < 2; frame++) {
                float ang = frame ? 0.9f : 0.0f;
                float *cb2 = NULL;
                ID3D12Resource_Map(ccb, 0, NULL, (void **)&cb2);
                if (cb2) {
                    /* cos/sin computed here so the shader needs no matrix and no
                     * row/column-major convention has to be agreed. Pitch stays
                     * at zero for frame 0 so the +Z face is square to the camera
                     * and the depth check has a definite expected colour. */
                    cb2[0] = (float)cos((double)ang); cb2[1] = (float)sin((double)ang);
                    cb2[2] = 1.0f;                    cb2[3] = 0.0f;
                    memcpy(cb2 + 4, cube_pos, sizeof cube_pos);
                    memcpy(cb2 + 4 + 24 * 4, cube_col, sizeof cube_col);
                }
                ID3D12Resource_Unmap(ccb, 0, NULL);
                if (cpx) memset(cpx, 0xCD, (size_t)RB_SIZE);

                const FLOAT cclear[4] = { 0.0f, 0.0f, 0.0f, 1.0f };
                D3D12_VIEWPORT cvp; cvp.TopLeftX = 0; cvp.TopLeftY = 0;
                cvp.Width = (FLOAT)RT_W; cvp.Height = (FLOAT)RT_H;
                cvp.MinDepth = 0; cvp.MaxDepth = 1;

                ID3D12GraphicsCommandList_Reset(list, alloc, NULL);
                ID3D12GraphicsCommandList_OMSetRenderTargets(list, 1, &crtv, FALSE, &dsv);
                ID3D12GraphicsCommandList_ClearRenderTargetView(list, crtv, cclear, 0, NULL);
                ID3D12GraphicsCommandList_ClearDepthStencilView(list, dsv, D3D12_CLEAR_FLAG_DEPTH, 1.0f, 0, 0, NULL);
                ID3D12GraphicsCommandList_SetPipelineState(list, cpso);
                ID3D12GraphicsCommandList_SetGraphicsRootSignature(list, crs);
                ID3D12GraphicsCommandList_SetGraphicsRootConstantBufferView(list, 0,
                        ID3D12Resource_GetGPUVirtualAddress(ccb));
                ID3D12GraphicsCommandList_RSSetViewports(list, 1, &cvp);
                ID3D12GraphicsCommandList_IASetPrimitiveTopology(list, D3D_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
                ID3D12GraphicsCommandList_IASetIndexBuffer(list, &ibv);
                ID3D12GraphicsCommandList_DrawIndexedInstanced(list,
                        (UINT)(sizeof cube_idx / sizeof cube_idx[0]), 1, 0, 0, 0);

                D3D12_TEXTURE_COPY_LOCATION cd, cs;
                ZeroMemory(&cd, sizeof cd); ZeroMemory(&cs, sizeof cs);
                cd.pResource = cpix; cs.pResource = crt;
                ID3D12GraphicsCommandList_CopyTextureRegion(list, &cd, 0, 0, 0, &cs, NULL);

                hr = ID3D12GraphicsCommandList_Close(list);
                if (frame == 0) CHECK(SUCCEEDED(hr), "cube frame list closed (%#lx)", hr);

                UINT64 b2 = ID3D12Fence_GetCompletedValue(fence);
                ID3D12CommandQueue_ExecuteCommandLists(queue, 1, lists);
                HANDLE e2 = CreateEventA(NULL, FALSE, FALSE, NULL);
                ID3D12Fence_SetEventOnCompletion(fence, b2 + 1, e2);
                ID3D12CommandQueue_Signal(queue, fence, b2 + 1);
                WaitForSingleObject(e2, 10000);
                CloseHandle(e2);

                if (cpx) {
                    const BYTE *C = cpx + ((RT_H / 2) * RT_W + RT_W / 2) * 4;
                    memcpy(frame ? frame1 : frame0, C, 4);
                    if (frame == 0) memcpy(corner0, cpx, 4);
                    else {
                        for (UINT64 i = 0; i < RB_SIZE; i += 4)
                            if (cpx[i] != frame0[0] || cpx[i+1] != frame0[1]) { differing++; }
                    }
                }
            }

            /* +Z face is the palette's blue; the -Z face drawn after it is
             * orange. Blue at the centre means depth testing decided it. */
            CHECK(frame0[2] > 200 && frame0[0] < 80,
                  "depth kept the near +Z face at the centre: (%u,%u,%u) expected blue-dominant; "
                  "an orange centre would mean the later back-face draw overwrote it",
                  frame0[0], frame0[1], frame0[2]);
            CHECK(corner0[0] == 0 && corner0[1] == 0 && corner0[2] == 0,
                  "a corner outside the cube kept the clear colour: (%u,%u,%u)",
                  corner0[0], corner0[1], corner0[2]);
            CHECK(memcmp(frame0, frame1, 4) != 0 || differing > 0,
                  "rotating the transform changed the image (%llu differing pixels)", differing);
            if (cpx) ID3D12Resource_Unmap(cpix, 0, NULL);
        }
        if (cib) ID3D12Resource_Release(cib);
        if (ccb) ID3D12Resource_Release(ccb);
        if (cpix) ID3D12Resource_Release(cpix);
        if (dsvh) ID3D12DescriptorHeap_Release(dsvh);
        if (crtvh) ID3D12DescriptorHeap_Release(crtvh);
        if (dsb) ID3D12Resource_Release(dsb);
        if (crt) ID3D12Resource_Release(crt);
        if (cpso) ID3D12PipelineState_Release(cpso);
        if (crs) ID3D12RootSignature_Release(crs);
    }

    /* ---- M5: a textured quad through a real descriptor table ----
     *
     * The first draw here whose shader reads something it was not handed
     * directly: a texture and a sampler reached through descriptor tables. The
     * texture is uploaded with CopyTextureRegion from an upload buffer, exactly
     * as an application would, rather than written by a back door.
     *
     * The texel colour and the constant-buffer tint are both non-trivial and
     * different from each other, so the expected pixel is a product neither one
     * could produce alone. A binding that silently missed would show the clear
     * colour, the untinted texel, or black -- all distinguishable. */
    {
        const UINT TW = 64, TH = 64;
        const UINT64 TRB = (UINT64)TW * TH * 4;
        static unsigned char trs_blob[512];
        ID3D12RootSignature *trs = make_textured_root_sig(dev, serialize, trs_blob, sizeof trs_blob);
        CHECK(trs != NULL, "textured root signature (CBV + SRV table + sampler table) created");

        D3D12_GRAPHICS_PIPELINE_STATE_DESC tpd; ZeroMemory(&tpd, sizeof tpd);
        tpd.pRootSignature = trs;
        tpd.VS.pShaderBytecode = tex_vs_dxil; tpd.VS.BytecodeLength = sizeof tex_vs_dxil;
        tpd.PS.pShaderBytecode = tex_ps_dxil; tpd.PS.BytecodeLength = sizeof tex_ps_dxil;
        tpd.NumRenderTargets = 1;
        tpd.RTVFormats[0] = DXGI_FORMAT_R8G8B8A8_UNORM;
        tpd.SampleDesc.Count = 1;
        tpd.PrimitiveTopologyType = D3D12_PRIMITIVE_TOPOLOGY_TYPE_TRIANGLE;
        ID3D12PipelineState *tpso = NULL;
        hr = ID3D12Device_CreateGraphicsPipelineState(dev, &tpd, &IID_ID3D12PipelineState, (void **)&tpso);
        CHECK(SUCCEEDED(hr) && tpso, "textured pipeline created from converted DXIL (%#lx)", hr);

        D3D12_HEAP_PROPERTIES thp; ZeroMemory(&thp, sizeof thp);
        D3D12_RESOURCE_DESC ttd; ZeroMemory(&ttd, sizeof ttd);
        ttd.Dimension = D3D12_RESOURCE_DIMENSION_TEXTURE2D;
        ttd.Width = TW; ttd.Height = TH; ttd.DepthOrArraySize = 1; ttd.MipLevels = 1;
        ttd.Format = DXGI_FORMAT_R8G8B8A8_UNORM; ttd.SampleDesc.Count = 1;
        thp.Type = D3D12_HEAP_TYPE_DEFAULT;
        ID3D12Resource *srctex = NULL, *trt = NULL, *tpix = NULL, *tup = NULL, *tcb = NULL;
        ID3D12Device_CreateCommittedResource(dev, &thp, D3D12_HEAP_FLAG_NONE, &ttd,
                D3D12_RESOURCE_STATE_COMMON, NULL, &IID_ID3D12Resource, (void **)&srctex);
        ID3D12Device_CreateCommittedResource(dev, &thp, D3D12_HEAP_FLAG_NONE, &ttd,
                D3D12_RESOURCE_STATE_COMMON, NULL, &IID_ID3D12Resource, (void **)&trt);
        CHECK(srctex && trt, "sampled texture and render target created");

        D3D12_RESOURCE_DESC tbd; ZeroMemory(&tbd, sizeof tbd);
        tbd.Dimension = D3D12_RESOURCE_DIMENSION_BUFFER;
        tbd.Height = 1; tbd.DepthOrArraySize = 1; tbd.MipLevels = 1;
        tbd.SampleDesc.Count = 1; tbd.Layout = D3D12_TEXTURE_LAYOUT_ROW_MAJOR;
        D3D12_HEAP_PROPERTIES up; ZeroMemory(&up, sizeof up);

        up.Type = D3D12_HEAP_TYPE_READBACK; tbd.Width = TRB;
        ID3D12Device_CreateCommittedResource(dev, &up, D3D12_HEAP_FLAG_NONE, &tbd,
                D3D12_RESOURCE_STATE_COMMON, NULL, &IID_ID3D12Resource, (void **)&tpix);
        up.Type = D3D12_HEAP_TYPE_UPLOAD; tbd.Width = TRB;
        ID3D12Device_CreateCommittedResource(dev, &up, D3D12_HEAP_FLAG_NONE, &tbd,
                D3D12_RESOURCE_STATE_COMMON, NULL, &IID_ID3D12Resource, (void **)&tup);
        tbd.Width = 256;
        ID3D12Device_CreateCommittedResource(dev, &up, D3D12_HEAP_FLAG_NONE, &tbd,
                D3D12_RESOURCE_STATE_COMMON, NULL, &IID_ID3D12Resource, (void **)&tcb);
        CHECK(tpix && tup && tcb, "readback, upload and constant buffers created");

        /* A uniform texel colour, so the check does not depend on filtering or
         * on exactly which texel the centre UV lands in. */
        const BYTE TEX_R = 200, TEX_G = 100, TEX_B = 50;
        BYTE *texels = NULL;
        ID3D12Resource_Map(tup, 0, NULL, (void **)&texels);
        if (texels) for (UINT64 i = 0; i < TRB; i += 4) {
            texels[i+0] = TEX_R; texels[i+1] = TEX_G; texels[i+2] = TEX_B; texels[i+3] = 255;
        }
        ID3D12Resource_Unmap(tup, 0, NULL);

        /* Tint halves red and leaves green alone, so neither channel can match
         * by accident if the constant buffer failed to bind. */
        const float TINT_R = 0.5f, TINT_G = 1.0f, TINT_B = 1.0f;
        float *tint = NULL;
        ID3D12Resource_Map(tcb, 0, NULL, (void **)&tint);
        if (tint) { tint[0] = TINT_R; tint[1] = TINT_G; tint[2] = TINT_B; tint[3] = 1.0f; }
        ID3D12Resource_Unmap(tcb, 0, NULL);

        ID3D12DescriptorHeap *srvh = NULL, *smph = NULL, *trtvh = NULL;
        D3D12_DESCRIPTOR_HEAP_DESC hd; ZeroMemory(&hd, sizeof hd);
        hd.Type = D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV; hd.NumDescriptors = 4;
        hd.Flags = D3D12_DESCRIPTOR_HEAP_FLAG_SHADER_VISIBLE;
        hr = ID3D12Device_CreateDescriptorHeap(dev, &hd, &IID_ID3D12DescriptorHeap, (void **)&srvh);
        CHECK(SUCCEEDED(hr) && srvh, "shader-visible SRV heap created (%#lx)", hr);
        hd.Type = D3D12_DESCRIPTOR_HEAP_TYPE_SAMPLER; hd.NumDescriptors = 4;
        hr = ID3D12Device_CreateDescriptorHeap(dev, &hd, &IID_ID3D12DescriptorHeap, (void **)&smph);
        CHECK(SUCCEEDED(hr) && smph, "shader-visible sampler heap created (%#lx)", hr);
        hd.Type = D3D12_DESCRIPTOR_HEAP_TYPE_RTV; hd.NumDescriptors = 1;
        hd.Flags = D3D12_DESCRIPTOR_HEAP_FLAG_NONE;
        ID3D12Device_CreateDescriptorHeap(dev, &hd, &IID_ID3D12DescriptorHeap, (void **)&trtvh);

        UINT inc = ID3D12Device_GetDescriptorHandleIncrementSize(dev, D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV);
        CHECK(inc == 24, "descriptor increment is the real stride (%u, expected 24)", inc);

        if (srvh && smph && trtvh && srctex && trt) {
            D3D12_CPU_DESCRIPTOR_HANDLE sh, mh, rh;
            D3D12_GPU_DESCRIPTOR_HANDLE sg, mg;
            srvh->lpVtbl->GetCPUDescriptorHandleForHeapStart(srvh, &sh);
            smph->lpVtbl->GetCPUDescriptorHandleForHeapStart(smph, &mh);
            trtvh->lpVtbl->GetCPUDescriptorHandleForHeapStart(trtvh, &rh);
            srvh->lpVtbl->GetGPUDescriptorHandleForHeapStart(srvh, &sg);
            smph->lpVtbl->GetGPUDescriptorHandleForHeapStart(smph, &mg);

            /* Deliberately NOT slot zero. A table encoding that ignored the
             * offset would still pass at index 0 and fail everywhere else. */
            const UINT SRV_SLOT = 2, SMP_SLOT = 1;
            sh.ptr += (SIZE_T)SRV_SLOT * inc;  sg.ptr += (UINT64)SRV_SLOT * inc;
            mh.ptr += (SIZE_T)SMP_SLOT * inc;  mg.ptr += (UINT64)SMP_SLOT * inc;

            D3D12_SHADER_RESOURCE_VIEW_DESC svd; ZeroMemory(&svd, sizeof svd);
            svd.Format = DXGI_FORMAT_R8G8B8A8_UNORM;
            svd.ViewDimension = D3D12_SRV_DIMENSION_TEXTURE2D;
            svd.Texture2D.MipLevels = 1;
            ID3D12Device_CreateShaderResourceView(dev, srctex, &svd, sh);

            D3D12_SAMPLER_DESC smd; ZeroMemory(&smd, sizeof smd);
            smd.Filter = D3D12_FILTER_MIN_MAG_MIP_POINT;
            smd.AddressU = smd.AddressV = smd.AddressW = D3D12_TEXTURE_ADDRESS_MODE_CLAMP;
            smd.MaxLOD = 0.0f;
            ID3D12Device_CreateSampler(dev, &smd, mh);
            ID3D12Device_CreateRenderTargetView(dev, trt, NULL, rh);

            ID3D12DescriptorHeap *heaps[2]; heaps[0] = srvh; heaps[1] = smph;
            BYTE px[4] = {0}, corner[4] = {0};

            /* Upload and draw in ONE list, so the ordering between the blit and
             * the render pass is exercised rather than assumed. */
            ID3D12CommandAllocator_Reset(alloc);
            ID3D12GraphicsCommandList_Reset(list, alloc, NULL);
            D3D12_TEXTURE_COPY_LOCATION ud, us;
            ZeroMemory(&ud, sizeof ud); ZeroMemory(&us, sizeof us);
            ud.pResource = srctex; us.pResource = tup;
            us.PlacedFootprint.Footprint.RowPitch = TW * 4;
            ID3D12GraphicsCommandList_CopyTextureRegion(list, &ud, 0, 0, 0, &us, NULL);

            D3D12_VIEWPORT tvp; ZeroMemory(&tvp, sizeof tvp);
            tvp.Width = (FLOAT)TW; tvp.Height = (FLOAT)TH; tvp.MaxDepth = 1.0f;
            const FLOAT tclear[4] = { 0.0f, 0.0f, 1.0f, 1.0f };   /* blue: not a possible result */
            ID3D12GraphicsCommandList_OMSetRenderTargets(list, 1, &rh, FALSE, NULL);
            ID3D12GraphicsCommandList_ClearRenderTargetView(list, rh, tclear, 0, NULL);
            ID3D12GraphicsCommandList_SetPipelineState(list, tpso);
            ID3D12GraphicsCommandList_SetGraphicsRootSignature(list, trs);
            ID3D12GraphicsCommandList_SetDescriptorHeaps(list, 2, heaps);
            ID3D12GraphicsCommandList_SetGraphicsRootConstantBufferView(list, 0,
                    ID3D12Resource_GetGPUVirtualAddress(tcb));
            ID3D12GraphicsCommandList_SetGraphicsRootDescriptorTable(list, 1, sg);
            ID3D12GraphicsCommandList_SetGraphicsRootDescriptorTable(list, 2, mg);
            ID3D12GraphicsCommandList_RSSetViewports(list, 1, &tvp);
            ID3D12GraphicsCommandList_IASetPrimitiveTopology(list, D3D_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
            ID3D12GraphicsCommandList_DrawInstanced(list, 3, 1, 0, 0);

            D3D12_TEXTURE_COPY_LOCATION rd2, rs2;
            ZeroMemory(&rd2, sizeof rd2); ZeroMemory(&rs2, sizeof rs2);
            rd2.pResource = tpix; rs2.pResource = trt;
            ID3D12GraphicsCommandList_CopyTextureRegion(list, &rd2, 0, 0, 0, &rs2, NULL);
            hr = ID3D12GraphicsCommandList_Close(list);
            CHECK(SUCCEEDED(hr), "textured list closed (%#lx)", hr);

            UINT64 base = ID3D12Fence_GetCompletedValue(fence);
            ID3D12CommandList *tl[1]; tl[0] = (ID3D12CommandList *)list;
            ID3D12CommandQueue_ExecuteCommandLists(queue, 1, tl);
            HANDLE te = CreateEventA(NULL, FALSE, FALSE, NULL);
            ID3D12Fence_SetEventOnCompletion(fence, base + 1, te);
            ID3D12CommandQueue_Signal(queue, fence, base + 1);
            CHECK(WaitForSingleObject(te, 10000) == WAIT_OBJECT_0, "textured draw completed");
            CloseHandle(te);

            BYTE *tp = NULL;
            ID3D12Resource_Map(tpix, 0, NULL, (void **)&tp);
            if (tp) {
                memcpy(px, tp + ((TH / 2) * TW + TW / 2) * 4, 4);
                memcpy(corner, tp, 4);
                ID3D12Resource_Unmap(tpix, 0, NULL);
            }

            /* The product of the texel and the tint, to within rounding. */
            int want_r = (int)(TEX_R * TINT_R + 0.5f);
            int want_g = (int)(TEX_G * TINT_G + 0.5f);
            int want_b = (int)(TEX_B * TINT_B + 0.5f);
            CHECK(abs((int)px[0] - want_r) <= 2 && abs((int)px[1] - want_g) <= 2 &&
                  abs((int)px[2] - want_b) <= 2,
                  "sampled texel times tint reached the target: got (%u,%u,%u), expected (%d,%d,%d) -- "
                  "the untinted texel, the clear colour or black would each mean a different binding failed",
                  px[0], px[1], px[2], want_r, want_g, want_b);
            CHECK(!(px[0] == TEX_R && px[1] == TEX_G && px[2] == TEX_B),
                  "the constant buffer really was read: the pixel is not the raw texel");
            CHECK(!(px[0] == 0 && px[1] == 0 && px[2] == 255),
                  "the draw happened at all: the centre is not still the clear colour");
            (void)corner;
        }

        if (tpso) ID3D12PipelineState_Release(tpso);
        if (trs) ID3D12RootSignature_Release(trs);
        if (srvh) ID3D12DescriptorHeap_Release(srvh);
        if (smph) ID3D12DescriptorHeap_Release(smph);
        if (trtvh) ID3D12DescriptorHeap_Release(trtvh);
        if (srctex) ID3D12Resource_Release(srctex);
        if (trt) ID3D12Resource_Release(trt);
        if (tpix) ID3D12Resource_Release(tpix);
        if (tup) ID3D12Resource_Release(tup);
        if (tcb) ID3D12Resource_Release(tcb);
    }

    /* Teardown in an order a real renderer would use. */
    CloseHandle(ev);
    CHECK(ID3D12Fence_Release(fence) == 0, "fence released to zero");
    CHECK(ID3D12GraphicsCommandList_Release(list) == 0, "list released to zero");
    CHECK(ID3D12CommandAllocator_Release(alloc) == 0, "allocator released to zero");
    CHECK(ID3D12CommandQueue_Release(queue) == 0, "queue released to zero");
    CHECK(ID3D12Device_Release(dev) == 0, "device released to zero");

    printf("\n%d checks, %d failures\n", checks, fails);
    return fails != 0;
}
