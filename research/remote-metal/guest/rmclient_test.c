/* ml762: exercise the control plane through the SHIPPING client header.
 *
 * rmtest.c drives the wire with its own bespoke client, which proves the host
 * but not the code the app runs. This test includes the very header winemetal
 * compiles in, so a defect in wmtr_call() or the mode gate fails HERE rather
 * than one machine away on a phone. */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

typedef int NTSTATUS;
#define STATUS_SUCCESS 0
#define STATUS_NOT_IMPLEMENTED 0xC0000002

#include "../../dxmt/src/winemetal/unix/wmt_remote_client.h"

/* Drive a flush from the test; the client owns the registry. */
static void wmtr_flush_buffers_for_test(uint64_t only) { (void)only; wmtr_flush_buffers(); }

static int fails;
#define CHECK(c, ...) do { if (!(c)) { printf("  FAIL: "); printf(__VA_ARGS__); \
    printf("\n"); fails++; } else { printf("  ok: "); printf(__VA_ARGS__); printf("\n"); } } while (0)

int main(void) {
    if (!wmtr_enabled()) {
        printf("client reports LOCAL mode -- set DXMT_REMOTE_METAL and RMETAL_TOKEN\n");
        return 2;
    }
    printf("client reports REMOTE mode\n");

    struct rm_ret_handle devs = {0};
    uint32_t st = wmtr_call(RM_OP_COPY_ALL_DEVICES, 0, 0, &devs, sizeof devs, 0);
    CHECK(st == RM_OK, "MTLCopyAllDevices -> status %u", st);
    CHECK(devs.handle != 0, "device array handle = 0x%llx", (unsigned long long)devs.handle);
    CHECK(RM_IS_REMOTE(devs.handle), "handle carries the remote tag");

    struct rm_arg_handle a = { devs.handle };
    struct rm_ret_u64 cnt = {0};
    st = wmtr_call(RM_OP_ARRAY_COUNT, &a, sizeof a, &cnt, sizeof cnt, 0);
    CHECK(st == RM_OK && cnt.value >= 1, "NSArray_count -> %llu device(s)",
          (unsigned long long)cnt.value);

    struct rm_arg_handle_u64 ao = { devs.handle, 0 };
    struct rm_ret_handle dev = {0};
    st = wmtr_call(RM_OP_ARRAY_OBJECT, &ao, sizeof ao, &dev, sizeof dev, 0);
    CHECK(st == RM_OK && dev.handle != 0, "NSArray_object(0) -> 0x%llx",
          (unsigned long long)dev.handle);

    /* Capability group: these gate shader and format selection, so they must
     * report the HOST gpu, not the guest's. */
    struct rm_arg_handle da = { dev.handle };
    struct rm_ret_u64 u = {0};
    st = wmtr_call(RM_OP_DEVICE_REGISTRY_ID, &da, sizeof da, &u, sizeof u, 0);
    CHECK(st == RM_OK && u.value != 0, "registryID -> %llu", (unsigned long long)u.value);
    st = wmtr_call(RM_OP_DEVICE_UNIFIED_MEM, &da, sizeof da, &u, sizeof u, 0);
    CHECK(st == RM_OK && u.value == 1, "hasUnifiedMemory -> %llu", (unsigned long long)u.value);
    st = wmtr_call(RM_OP_DEVICE_MAX_WORKING_SET, &da, sizeof da, &u, sizeof u, 0);
    CHECK(st == RM_OK && u.value > (1ull<<30), "recommendedMaxWorkingSetSize -> %llu MB",
          (unsigned long long)(u.value >> 20));
    st = wmtr_call(RM_OP_SUPPORTS_BC, &da, sizeof da, &u, sizeof u, 0);
    CHECK(st == RM_OK && u.value == 1, "supportsBCTextureCompression -> %llu (host is Apple9)",
          (unsigned long long)u.value);
    struct rm_arg_handle_u64 fam = { dev.handle, 1009 };   /* MTLGPUFamilyApple9 */
    st = wmtr_call(RM_OP_SUPPORTS_FAMILY, &fam, sizeof fam, &u, sizeof u, 0);
    CHECK(st == RM_OK && u.value == 1, "supportsFamily(Apple9) -> %llu", (unsigned long long)u.value);
    struct rm_os_version ov = {0};
    st = wmtr_call(RM_OP_OS_VERSION, 0, 0, &ov, sizeof ov, 0);
    CHECK(st == RM_OK && ov.major >= 15, "host OS %u.%u.%u", ov.major, ov.minor, ov.patch);
    char nm[256] = {0}; uint32_t got = 0;
    st = wmtr_call(RM_OP_DEVICE_NAME, &da, sizeof da, nm, sizeof nm - 1, &got);
    CHECK(st == RM_OK && got > 0, "device name -> \"%.*s\"", (int)got, nm);
    struct rm_arg_handle_u64 cc = { dev.handle, 1 };
    st = wmtr_call(RM_OP_DEVICE_SET_MAXCC, &cc, sizeof cc, 0, 0, 0);
    CHECK(st == RM_OK, "setShouldMaximizeConcurrentCompilation -> status %u", st);

    /* Shader path: a REAL metallib crosses as bytes, becomes a host dispatch_data,
     * then a library, then named functions. This is the path DXMT takes; a
     * synthetic blob would not prove the host can actually build a library. */
    FILE *mf = fopen("/private/tmp/claude-501/-Users-willfaust-Documents-ios-pc-game-claude/3356ff92-c226-4913-8afb-99c1e8e39f4d/scratchpad/cube_shader.metallib", "rb");
    if (!mf) { printf("  SKIP: no metallib at /private/tmp/claude-501/-Users-willfaust-Documents-ios-pc-game-claude/3356ff92-c226-4913-8afb-99c1e8e39f4d/scratchpad/cube_shader.metallib\n"); }
    else {
        fseek(mf, 0, SEEK_END); long mlen = ftell(mf); fseek(mf, 0, SEEK_SET);
        uint8_t *mb = malloc((size_t)mlen);
        size_t rd_n = fread(mb, 1, (size_t)mlen, mf); fclose(mf);
        CHECK(rd_n == (size_t)mlen, "read metallib (%ld bytes)", mlen);

        struct rm_ret_handle dd = {0};
        st = wmtr_call(RM_OP_DISPATCH_DATA, mb, (uint32_t)mlen, &dd, sizeof dd, 0);
        CHECK(st == RM_OK && dd.handle, "DISPATCH_DATA -> 0x%llx", (unsigned long long)dd.handle);

        struct rm_arg_handle_u64 la = { dev.handle, dd.handle };
        struct rm_ret_handle lib = {0};
        st = wmtr_call(RM_OP_NEW_LIBRARY_DATA, &la, sizeof la, &lib, sizeof lib, 0);
        CHECK(st == RM_OK && lib.handle, "newLibraryWithData -> 0x%llx", (unsigned long long)lib.handle);

        const char *fn = "cube_vs";
        uint8_t nbuf[sizeof(struct rm_arg_handle) + 64];
        struct rm_arg_handle *na = (void *)nbuf;
        na->handle = lib.handle;
        memcpy(nbuf + sizeof *na, fn, strlen(fn));
        struct rm_ret_handle fh = {0};
        st = wmtr_call(RM_OP_NEW_FUNCTION, nbuf, (uint32_t)(sizeof *na + strlen(fn)), &fh, sizeof fh, 0);
        CHECK(st == RM_OK && fh.handle, "newFunctionWithName(\"%s\") -> 0x%llx", fn,
              (unsigned long long)fh.handle);

        /* A name that does not exist must come back empty, not as some other
         * function -- otherwise a typo in a shader silently binds the wrong one. */
        const char *bad = "not_a_function";
        na->handle = lib.handle;
        memcpy(nbuf + sizeof *na, bad, strlen(bad));
        struct rm_ret_handle bh = {0};
        wmtr_call(RM_OP_NEW_FUNCTION, nbuf, (uint32_t)(sizeof *na + strlen(bad)), &bh, sizeof bh, 0);
        CHECK(bh.handle == 0, "missing function name yields no handle");
        free(mb);
    }

    /* Descriptor path: real Metal state objects built on the host from the
     * guest's verbatim WMT*Info. The render pipeline is the one that must NOT
     * be a subset -- blend state, write masks and formats all have to arrive. */
    {
        uint8_t db[sizeof(struct rm_wmt_info) + 256] = {0};
        struct rm_wmt_info *w = (void *)db;

        /* depth-stencil: zeroed info == always-compare, no write; still a real object */
        w->owner = dev.handle; w->info_len = 24; w->extra_count = 0;
        struct rm_ret_handle dh = {0};
        st = wmtr_call(RM_OP_NEW_DSS_INFO, db, sizeof(struct rm_wmt_info) + w->info_len, &dh, sizeof dh, 0);
        CHECK(st == RM_OK && dh.handle, "newDepthStencilState -> 0x%llx", (unsigned long long)dh.handle);

        /* sampler: WMTSamplerInfo is 32 bytes; lod_max_clamp must be sane */
        memset(db + sizeof *w, 0, 64);
        w->info_len = 32;
        float *lod = (float *)(db + sizeof *w + 8);
        lod[0] = 0.0f; lod[1] = 1000.0f;
        db[sizeof *w + 20] = 1;                  /* normalized_coords */
        struct rm_ret_handle_u64 sh = {0};
        st = wmtr_call(RM_OP_NEW_SAMPLER_INFO, db, sizeof(struct rm_wmt_info) + w->info_len, &sh, sizeof sh, 0);
        CHECK(st == RM_OK && sh.handle, "newSamplerState -> 0x%llx", (unsigned long long)sh.handle);

        /* A bogus device handle must be refused, not crash the daemon. */
        w->owner = 0xdeadbeefull;
        struct rm_ret_handle bad = {0};
        st = wmtr_call(RM_OP_NEW_DSS_INFO, db, sizeof(struct rm_wmt_info) + 24, &bad, sizeof bad, 0);
        CHECK(st != RM_OK && bad.handle == 0, "bogus device refused (status %u)", st);
    }

    /* Buffer ownership: host allocates, guest writes a shadow, upload lands
     * the bytes. Read them back to prove the data arrived rather than trusting
     * an OK status -- an upload that silently no-ops looks identical. */
    {
        uint8_t bb[sizeof(struct rm_wmt_info) + 32] = {0};
        struct rm_wmt_info *w = (void *)bb;
        w->owner = dev.handle; w->info_len = 32; w->extra_count = 0;
        uint64_t *blen = (uint64_t *)(bb + sizeof *w);
        *blen = 4096;                                  /* WMTBufferInfo.length */
        struct rm_ret_handle_u64 br = {0};
        st = wmtr_call(RM_OP_NEW_BUFFER_INFO, bb, sizeof bb, &br, sizeof br, 0);
        CHECK(st == RM_OK && br.handle, "newBuffer(4096) -> 0x%llx", (unsigned long long)br.handle);
        CHECK(br.value != 0, "gpu_address reported -> 0x%llx", (unsigned long long)br.value);

        uint8_t pat[256];
        for (int k = 0; k < 256; k++) pat[k] = (uint8_t)(k ^ 0x5a);
        uint8_t up[sizeof(struct rm_buffer_range) + 256];
        struct rm_buffer_range *rr2 = (void *)up;
        rr2->handle = br.handle; rr2->offset = 512; rr2->length = 256;
        memcpy(up + sizeof *rr2, pat, 256);
        st = wmtr_call(RM_OP_BUFFER_UPLOAD, up, sizeof up, 0, 0, 0);
        CHECK(st == RM_OK, "buffer upload at offset 512 -> status %u", st);

        struct rm_buffer_range rd2 = { br.handle, 512, 256 };
        uint8_t back[256] = {0}; uint32_t got2 = 0;
        st = wmtr_call(RM_OP_BUFFER_READ, &rd2, sizeof rd2, back, sizeof back, &got2);
        CHECK(st == RM_OK && got2 == 256 && memcmp(back, pat, 256) == 0,
              "read back the exact bytes written (%u of 256)", got2);

        /* An out-of-range upload must be refused, not silently clamped -- a
         * clamp would corrupt whatever sits at the end of the buffer. */
        rr2->offset = 4000; rr2->length = 256;
        st = wmtr_call(RM_OP_BUFFER_UPLOAD, up, sizeof up, 0, 0, 0);
        CHECK(st != RM_OK, "out-of-range upload refused (status %u)", st);

        struct rm_arg_handle ea = { dev.handle };
        struct rm_ret_handle ev = {0};
        st = wmtr_call(RM_OP_NEW_SHARED_EVENT, &ea, sizeof ea, &ev, sizeof ev, 0);
        CHECK(st == RM_OK && ev.handle, "newSharedEvent -> 0x%llx", (unsigned long long)ev.handle);
    }

    /* Caller-supplied buffer memory must remain THE buffer's storage.
     *
     * No existing check covered this, which is exactly why it survived: DXMT's
     * ring allocator hands in its own pointer, keeps writing argument data
     * through it, and a backend that substitutes its own allocation uploads
     * zeros. Draws then execute and draw nothing. Mutate through the caller's
     * pointer, flush, and read back from the host. */
    {
        uint64_t len = 4096;
        uint8_t *caller_mem = calloc(1, len);
        uint8_t bb2[sizeof(struct rm_wmt_info) + 32] = {0};
        struct rm_wmt_info *w2 = (void *)bb2;
        w2->owner = dev.handle; w2->info_len = 32; w2->extra_count = 0;
        struct wmt_buffer_info_shim { uint64_t length; uint32_t options; uint32_t pad;
                                      void *memory; uint64_t gpu_address; } bi;
        memset(&bi, 0, sizeof bi);
        bi.length = len; bi.memory = caller_mem;
        memcpy(bb2 + sizeof *w2, &bi, 32);
        struct rm_ret_handle_u64 br2 = {0};
        st = wmtr_call(RM_OP_NEW_BUFFER_INFO, bb2, sizeof bb2, &br2, sizeof br2, 0);
        CHECK(st == RM_OK && br2.handle, "buffer with caller memory -> 0x%llx",
              (unsigned long long)br2.handle);

        /* Write through the CALLER's pointer, as DXMT does. */
        for (uint64_t k = 0; k < len; k++) caller_mem[k] = (uint8_t)(k * 7 + 3);
        CHECK(wmtr_buf_upload(br2.handle, caller_mem, 0, len) == 0,
              "flushed the caller's memory to the host");

        uint8_t *back2 = malloc(len); uint32_t got3 = 0, mism = 0;
        struct rm_buffer_range rd3 = { br2.handle, 0, len };
        st = wmtr_call(RM_OP_BUFFER_READ, &rd3, sizeof rd3, back2, (uint32_t)len, &got3);
        for (uint64_t k = 0; k < len && k < got3; k++)
            if (back2[k] != (uint8_t)(k * 7 + 3)) mism++;
        CHECK(st == RM_OK && got3 == len && mism == 0,
              "host holds the caller's bytes (%u read, %u mismatched)", got3, mism);
        /* A zero readback is the exact signature of the substituted-allocation
         * bug: status OK, right length, all zeros. */
        uint32_t nonzero = 0;
        for (uint32_t k = 0; k < got3; k++) if (back2[k]) nonzero++;
        CHECK(nonzero > 0, "readback is not all zeros (%u non-zero bytes)", nonzero);
        free(back2); free(caller_mem);
    }

    /* Changed-page upload must still deliver every byte. A checksum that
     * misses a change shows up as a stale frame, not an error, so mutate one
     * byte deep inside a large buffer and prove the host sees it. */
    {
        uint64_t blen = 512 * 1024;
        uint8_t *mem = calloc(1, blen);
        uint8_t bb3[sizeof(struct rm_wmt_info) + 32] = {0};
        struct rm_wmt_info *w3 = (void *)bb3;
        w3->owner = dev.handle; w3->info_len = 32; w3->extra_count = 0;
        struct { uint64_t length; uint32_t options; uint32_t pad; void *memory; uint64_t gpu; } bi3;
        memset(&bi3, 0, sizeof bi3); bi3.length = blen; bi3.memory = mem;
        memcpy(bb3 + sizeof *w3, &bi3, 32);
        struct rm_ret_handle_u64 h3 = {0};
        st = wmtr_call(RM_OP_NEW_BUFFER_INFO, bb3, sizeof bb3, &h3, sizeof h3, 0);
        CHECK(st == RM_OK && h3.handle, "512K buffer for page-diff test");
        /* The registry is normally populated by the winemetal handler; this
         * test creates the buffer with a raw RPC, so register it here or the
         * flush has nothing to walk. */
        wmtr_buf_add(h3.handle, mem, blen, 0, 1, 0);

        for (uint64_t k = 0; k < blen; k++) mem[k] = (uint8_t)(k >> 8);
        wmtr_flush_buffers_for_test(h3.handle);

        /* One byte, in the middle of one page. */
        mem[300000] = 0xAB;
        wmtr_flush_buffers_for_test(h3.handle);

        uint8_t chk[4] = {0}; uint32_t g4 = 0;
        struct rm_buffer_range rr4 = { h3.handle, 300000, 4 };
        st = wmtr_call(RM_OP_BUFFER_READ, &rr4, sizeof rr4, chk, sizeof chk, &g4);
        CHECK(st == RM_OK && chk[0] == 0xAB,
              "a single changed byte deep in a large buffer reaches the host (got 0x%02x)", chk[0]);
        free(mem);
    }

    struct rm_arg_handle ra = { dev.handle };
    struct rm_ret_handle rr = {0};
    st = wmtr_call(RM_OP_RETAIN, &ra, sizeof ra, &rr, sizeof rr, 0);
    CHECK(st == RM_OK, "NSObject_retain -> status %u", st);
    /* Identity must survive retain. Minting a new handle left the guest holding
     * the old one while the reference lived on the new one. */
    CHECK(rr.handle == dev.handle, "retain returns the SAME handle (0x%llx)",
          (unsigned long long)rr.handle);

    /* Interning the same object twice must yield one identity, or the guest
     * gets two handles for one device and equality between them is false. */
    struct rm_ret_handle dev2 = {0};
    st = wmtr_call(RM_OP_ARRAY_OBJECT, &ao, sizeof ao, &dev2, sizeof dev2, 0);
    CHECK(st == RM_OK && dev2.handle == dev.handle,
          "re-fetching device 0 gives the same handle (0x%llx)",
          (unsigned long long)dev2.handle);

    /* refcount: two extra refs taken above, so two releases must NOT free it. */
    wmtr_call(RM_OP_RELEASE, &ra, sizeof ra, 0, 0, 0);
    wmtr_call(RM_OP_RELEASE, &ra, sizeof ra, 0, 0, 0);
    struct rm_ret_u64 alive = {0};
    st = wmtr_call(RM_OP_ARRAY_COUNT, &a, sizeof a, &alive, sizeof alive, 0);
    CHECK(st == RM_OK, "device array still valid after balanced releases");

    /* maxCommandBufferCount is part of the call: it bounds how many command
     * buffers may be in flight, so dropping it changes when the guest blocks. */
    struct rm_arg_handle_u64 qa_in = { dev.handle, 64 };
    struct rm_ret_handle q = {0};
    st = wmtr_call(RM_OP_NEW_COMMAND_QUEUE, &qa_in, sizeof qa_in, &q, sizeof q, 0);
    CHECK(st == RM_OK && q.handle != 0, "newCommandQueue -> 0x%llx",
          (unsigned long long)q.handle);
    CHECK(q.handle != dev.handle, "queue handle is distinct from the device");

    struct rm_arg_handle qa = { q.handle };
    st = wmtr_call(RM_OP_RELEASE, &qa, sizeof qa, 0, 0, 0);
    CHECK(st == RM_OK, "NSObject_release(queue) -> status %u", st);
    st = wmtr_call(RM_OP_RELEASE, &ra, sizeof ra, 0, 0, 0);
    CHECK(st == RM_OK, "NSObject_release(device) -> status %u", st);

    /* A stale handle must be REFUSED, not serviced. The generation tag exists
     * so a use-after-release is an error and not a hit on a recycled slot. */
    st = wmtr_call(RM_OP_ARRAY_COUNT, &qa, sizeof qa, &cnt, sizeof cnt, 0);
    CHECK(st != RM_OK, "released handle is refused (status %u)", st);

    printf(fails ? "\n%d CHECK(S) FAILED\n" : "\nall checks passed\n", fails);
    return fails ? 1 : 0;
}
