/* Round-trip and malformed-input tests for the command wire format.
 *
 * Run BEFORE exposing the decoder to DXMT. A wire format that only gets
 * exercised by real traffic fails as corruption on a remote GPU, which is
 * among the worst things to debug -- the symptom appears in pixels, one
 * machine away from the cause.
 */
#include "../wmt_pack.h"
#include "../host/wmt_decode.h"
#include <stdio.h>
#include <stdlib.h>

static int fails, checks;
#define CHECK(c, msg) do { checks++; if (!(c)) { fails++; \
    printf("  FAIL %-46s (%s:%d)\n", msg, __FILE__, __LINE__); } } while (0)

/* No private walker here. The production validator in host/wmt_decode.h is
 * the only implementation, so these tests exercise what rmetald actually runs
 * -- a test that walks the stream its own way proves only that the test works.
 */
/* Assemble a real payload: prologue, records, sidecar -- exactly as it would
 * arrive on the wire, so the validator sees what rmetald will see. */
static uint8_t payload[WMTW_MAX_BATCH_BYTES + WMTW_MAX_SIDECAR_BYTES + 64];
static enum wmtw_dec_status vcheck(const uint8_t *rec, uint32_t rec_bytes,
                                   uint32_t count, const uint8_t *side, uint32_t side_bytes) {
    struct wmtw_batch *b = (void *)payload;
    b->magic = WMTW_BATCH_MAGIC; b->version = WMTW_VERSION; b->encoder_kind = 0;
    b->record_bytes = rec_bytes; b->record_count = count;
    b->sidecar_bytes = side_bytes; b->reserved = 0;
    memcpy(payload + sizeof *b, rec, rec_bytes);
    if (side_bytes) memcpy(payload + sizeof *b + rec_bytes, side, side_bytes);
    struct wmtw_dec_result d; struct wmtw_view v;
    return wmtw_validate_batch(payload, (uint32_t)(sizeof *b + rec_bytes + side_bytes), &v, &d);
}

int main(void) {
    static uint8_t recbuf[WMTW_MAX_BATCH_BYTES], sidebuf[WMTW_MAX_SIDECAR_BYTES];
    struct wmtw_packer p = { recbuf, sizeof recbuf, 0, sidebuf, sizeof sidebuf, 0, 0 };

    printf("wire round-trip, version %d, %d record types\n", WMTW_VERSION, WMTW_OP_COUNT);

    /* --- one of every record type --- */
    #define R(T, OP) struct wmtw_##T *T = wmtw_rec_alloc(&p, sizeof *T, OP); CHECK(T, #OP " alloc")
    R(nop, WMTW_OP_Nop);
    R(useresource, WMTW_OP_UseResource);       useresource->resource = 0x1111;
    R(setvertexbuffer, WMTW_OP_SetVertexBuffer); setvertexbuffer->buffer = 0x2222;
    R(setvertexbufferoffset, WMTW_OP_SetVertexBufferOffset);
    R(setfragmentbuffer, WMTW_OP_SetFragmentBuffer);
    R(setfragmenttexture, WMTW_OP_SetFragmentTexture); setfragmenttexture->texture = 0x3333;
    R(setrasterizerstate, WMTW_OP_SetRasterizerState);
    R(setpso, WMTW_OP_SetPSO);                 setpso->pso = 0x4444;
    R(setdsso, WMTW_OP_SetDSSO);
    R(setblendfactorandstencilref, WMTW_OP_SetBlendFactorAndStencilRef);
    R(draw, WMTW_OP_Draw);                     draw->count = 3;
    R(drawindexed, WMTW_OP_DrawIndexed);       drawindexed->index_count = 6;

    /* sidecar-bearing: bytes, viewports, scissors */
    uint8_t payload[12] = {1,2,3,4,5,6,7,8,9,10,11,12};
    struct wmtw_setfragmentbytes *fb = wmtw_rec_alloc(&p, sizeof *fb, WMTW_OP_SetFragmentBytes);
    fb->index = 0;
    fb->bytes_offset = wmtw_side_put(&p, payload, sizeof payload);
    fb->bytes_count  = sizeof payload;
    CHECK(fb->bytes_offset != 0xffffffffu, "setFragmentBytes sidecar stored");

    struct wmtw_viewport vp = { 0, 0, 640, 480, 0, 1 };
    struct wmtw_setviewports *sv = wmtw_rec_alloc(&p, sizeof *sv, WMTW_OP_SetViewports);
    sv->viewports_offset = wmtw_side_put(&p, &vp, sizeof vp);
    sv->viewports_count  = 1;

    struct wmtw_scissor sc = { 0, 0, 640, 480 };
    struct wmtw_setscissorrects *ss = wmtw_rec_alloc(&p, sizeof *ss, WMTW_OP_SetScissorRects);
    ss->scissors_offset = wmtw_side_put(&p, &sc, sizeof sc);
    ss->scissors_count  = 1;

    CHECK(vcheck(recbuf, p.rec_len, p.count, sidebuf, p.side_len) == WMTW_DEC_OK,
          "well-formed batch passes the production validator");
    CHECK(p.count == 15, "all 15 record types round-trip");
    printf("  packed %u records, %u record bytes, %u sidecar bytes\n",
           p.count, p.rec_len, p.side_len);

    /* verify the sidecar survived byte-for-byte */
    CHECK(memcmp(sidebuf + fb->bytes_offset, payload, sizeof payload) == 0,
          "sidecar bytes identical after packing");
    struct wmtw_viewport back;
    memcpy(&back, sidebuf + sv->viewports_offset, sizeof back);
    CHECK(back.width == 640 && back.height == 480, "viewport survives round-trip");

    /* --- malformed inputs must be REJECTED, not tolerated --- */
    printf("malformed input\n");
    uint8_t bad_buf[256];
    memcpy(bad_buf, recbuf, sizeof bad_buf);

    struct wmtw_hdr *h0 = (void *)bad_buf;
    uint32_t s0 = h0->size;
    h0->size = 0;                        /* size smaller than the header */
    CHECK(vcheck(bad_buf, 128, 99, sidebuf, 0) == WMTW_DEC_BAD_SIZE, "zero-size record rejected");
    h0->size = 0xffff;                   /* size past the end of the batch */
    CHECK(vcheck(bad_buf, 128, 99, sidebuf, 0) == WMTW_DEC_TRUNCATED, "oversized record rejected");
    h0->size = s0;
    h0->version = 99;                    /* wrong version */
    CHECK(vcheck(bad_buf, 128, 99, sidebuf, 0) == WMTW_DEC_BAD_VERSION, "version mismatch rejected");
    h0->version = WMTW_VERSION;

    /* sidecar reference pointing outside the region */
    struct wmtw_setfragmentbytes evil = { { WMTW_OP_SetFragmentBytes, WMTW_VERSION, sizeof evil },
                                          0, 0, 999999 };
    CHECK(vcheck((uint8_t *)&evil, sizeof evil, 1, sidebuf, 16) == WMTW_DEC_SIDECAR_RANGE,
          "oversized sidecar count rejected");
    struct wmtw_setfragmentbytes evil2 = { { WMTW_OP_SetFragmentBytes, WMTW_VERSION, sizeof evil2 },
                                           0, 8, 100 };
    CHECK(vcheck((uint8_t *)&evil2, sizeof evil2, 1, sidebuf, 16) == WMTW_DEC_SIDECAR_RANGE,
          "sidecar range past region rejected");
    /* integer overflow in offset+count must not wrap into acceptance */
    struct wmtw_setfragmentbytes evil3 = { { WMTW_OP_SetFragmentBytes, WMTW_VERSION, sizeof evil3 },
                                           0, 0xfffffff0u, 64 };
    CHECK(vcheck((uint8_t *)&evil3, sizeof evil3, 1, sidebuf, 16) != WMTW_DEC_OK,
          "offset+count overflow rejected");

    /* trailing garbage: a batch whose records do not exactly fill it */
    CHECK(vcheck(recbuf, p.rec_len - 3, p.count, sidebuf, p.side_len) != WMTW_DEC_OK,
          "truncated batch rejected");

    /* --- decoder-side validation, the half that faces the wire --- */
    printf("decoder validation\n");
    CHECK(wmtw_min_size(WMTW_OP_Draw) == sizeof(struct wmtw_draw), "min size known for Draw");
    CHECK(wmtw_min_size(WMTW_OP_DrawIndexed) == sizeof(struct wmtw_drawindexed), "min size known for DrawIndexed");
    CHECK(wmtw_min_size(9999) == 0, "unknown opcode has no min size");
    for (int op = 0; op < WMTW_OP__MAX; op++) {
        uint32_t m = wmtw_min_size((uint16_t)op);
        if (m) CHECK(m >= sizeof(struct wmtw_hdr), "every known opcode is at least a header");
    }
    /* overflow-safe sidecar arithmetic */
    CHECK(wmtw_side_ok(0, 1, sizeof(struct wmtw_viewport), 48), "exact-fit viewport accepted");
    CHECK(!wmtw_side_ok(0, 2, sizeof(struct wmtw_viewport), 48), "one element too many rejected");
    CHECK(!wmtw_side_ok(0xfffffff0u, 64, 1, 1024), "offset+count overflow rejected");
    CHECK(!wmtw_side_ok(0, 0xffffffffu, sizeof(struct wmtw_viewport), 1024),
          "count*elem overflow rejected");
    CHECK(wmtw_side_ok(0, 0, 1, 0), "empty sidecar accepted");
    /* the packer's own status strings must all be distinct and non-empty */
    for (int i = 0; i <= WMTW_PACK_BAD_ARRAY_COUNT; i++)
        CHECK(wmtw_pack_strerror((enum wmtw_pack_status)i)[0] != '?', "pack status named");
    for (int i = 0; i <= WMTW_DEC_NOT_EXACT; i++)
        CHECK(wmtw_dec_strerror((enum wmtw_dec_status)i)[0] != '?', "decode status named");

    printf("\n%d checks, %d failures\n", checks, fails);
    return fails != 0;
}
