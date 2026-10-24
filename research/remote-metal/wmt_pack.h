/* Guest-side packer: winemetal's pointer-linked wmtcmd_* list -> a contiguous,
 * self-describing batch.
 *
 * The source list is linked through guest pointers and carries further
 * pointers for inline bytes, viewports and scissors -- none of which mean
 * anything on another machine. This converts every one into an offset into a
 * sidecar region carried alongside the records.
 *
 * ⚠️ The input is a linked list built by another subsystem. It is walked with a
 * hard record cap and a slow/fast cycle check, because a corrupt `next` chain
 * would otherwise spin here forever -- which is exactly how the FEX IR list
 * corruption presented, and it cost days to find.
 */
#ifndef WMT_PACK_H
#define WMT_PACK_H
#include "wmt_wire.h"

enum wmtw_pack_status {
    WMTW_PACK_OK = 0,
    WMTW_PACK_UNSUPPORTED_OP,   /* names encoder kind, opcode and index */
    WMTW_PACK_TOO_MANY_RECORDS,
    WMTW_PACK_CYCLE,
    WMTW_PACK_SIDECAR_OVERFLOW,
    WMTW_PACK_BUFFER_OVERFLOW,
    WMTW_PACK_BAD_ARRAY_COUNT,
};

struct wmtw_pack_result {
    enum wmtw_pack_status status;
    uint32_t record_index;      /* where it went wrong */
    uint32_t opcode;
    uint32_t encoder_kind;
    uint32_t record_bytes;
    uint32_t record_count;
    uint32_t sidecar_bytes;
};

static inline const char *wmtw_pack_strerror(enum wmtw_pack_status s) {
    switch (s) {
    case WMTW_PACK_OK: return "ok";
    case WMTW_PACK_UNSUPPORTED_OP: return "unsupported opcode";
    case WMTW_PACK_TOO_MANY_RECORDS: return "record cap exceeded";
    case WMTW_PACK_CYCLE: return "cycle in the command list";
    case WMTW_PACK_SIDECAR_OVERFLOW: return "sidecar region overflow";
    case WMTW_PACK_BUFFER_OVERFLOW: return "batch buffer overflow";
    case WMTW_PACK_BAD_ARRAY_COUNT: return "array count out of range";
    }
    return "?";
}

/* Cursor over the output batch: records grow forward from `rec`, sidecar data
 * grows forward from `side`. They are separate regions so a decoder can skip a
 * record it does not implement without losing the sidecar alignment. */
struct wmtw_packer {
    uint8_t *rec;   uint32_t rec_cap,  rec_len;
    uint8_t *side;  uint32_t side_cap, side_len;
    uint32_t count;
};

static inline void *wmtw_rec_alloc(struct wmtw_packer *p, uint32_t size, uint16_t op) {
    if (p->rec_len + size > p->rec_cap || p->count >= WMTW_MAX_RECORDS) return 0;
    struct wmtw_hdr *h = (struct wmtw_hdr *)(p->rec + p->rec_len);
    h->op = op; h->version = WMTW_VERSION; h->size = size;
    p->rec_len += size; p->count++;
    return h;
}

/* Returns the sidecar OFFSET, or UINT32_MAX on overflow. Never a pointer:
 * the whole point is that the receiver is in another address space. */
static inline uint32_t wmtw_side_put(struct wmtw_packer *p, const void *data, uint32_t bytes) {
    /* 8-byte align. Viewports and scissors are cast straight to Metal structs
     * on replay, and a misaligned load of a double is undefined. Aligning here
     * costs at most 7 bytes per entry and removes a whole class of
     * platform-dependent failure.
     *
     * ZERO the padding. The buffer is reused across batches, so skipped bytes
     * would otherwise still hold data from an earlier batch and be transmitted
     * as part of the sidecar region -- stale guest data on the wire, and a
     * payload that differs run to run for identical input. */
    uint32_t aligned = (p->side_len + 7u) & ~7u;
    if (aligned > p->side_cap) return 0xffffffffu;      /* check before writing */
    if (aligned > p->side_len) memset(p->side + p->side_len, 0, aligned - p->side_len);
    p->side_len = aligned;
    if (bytes > WMTW_MAX_SIDECAR_BYTES || bytes > p->side_cap - p->side_len) return 0xffffffffu;
    uint32_t off = p->side_len;
    memcpy(p->side + off, data, bytes);
    p->side_len += bytes;
    return off;
}

#endif
