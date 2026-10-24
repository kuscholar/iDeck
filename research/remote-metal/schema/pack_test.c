/* Tests that drive the REAL packer and the REAL validator.
 *
 * The earlier suite passed 63 checks while never calling wmtw_pack_render(),
 * and used a private walker instead of the production decoder -- so it proved
 * that the test worked, not that the implementation did. A two-node acyclic
 * list was reported as a cycle and the suite was green throughout.
 */
#include "../../dxmt/src/winemetal/unix/wmt_remote_pack.h"
#include "../host/wmt_decode.h"
#include <stdio.h>
#include <string.h>

static int fails, checks;
#define CHECK(c, msg) do { checks++; if (!(c)) { fails++; \
    printf("  FAIL %-52s (line %d)\n", msg, __LINE__); } } while (0)

static uint8_t recbuf[WMTW_MAX_BATCH_BYTES], sidebuf[WMTW_MAX_SIDECAR_BYTES];

static enum wmtw_pack_status run(const struct wmtcmd_base *head,
                                 struct wmtw_pack_result *r) {
    struct wmtw_packer p = { recbuf, sizeof recbuf, 0, sidebuf, sizeof sidebuf, 0, 0 };
    memset(r, 0, sizeof *r);
    return wmtw_pack_render(head, &p, r);
}

/* A minimal Nop node; `next` is the only field the walk follows. */
struct node { struct wmtcmd_render_nop n; };
static void link(struct node *a, struct node *b) { a->n.next.ptr = b; }

int main(void) {
    struct wmtw_pack_result r;
    printf("real packer, list shapes\n");

    /* empty */
    CHECK(run(NULL, &r) == WMTW_PACK_OK, "empty list packs");
    CHECK(r.record_count == 0, "empty list yields no records");

    /* one node */
    static struct node one; memset(&one, 0, sizeof one);
    one.n.type = WMTRenderCommandNop;
    CHECK(run((struct wmtcmd_base *)&one, &r) == WMTW_PACK_OK, "single node packs");
    CHECK(r.record_count == 1, "single node yields one record");

    /* two acyclic -- the case that was broken */
    static struct node a, b;
    memset(&a, 0, sizeof a); memset(&b, 0, sizeof b);
    a.n.type = b.n.type = WMTRenderCommandNop;
    link(&a, &b);
    enum wmtw_pack_status st = run((struct wmtcmd_base *)&a, &r);
    CHECK(st == WMTW_PACK_OK, "TWO acyclic nodes are not a cycle");
    CHECK(r.record_count == 2, "two nodes yield two records");
    if (st != WMTW_PACK_OK) printf("       (got %s at index %u)\n",
                                   wmtw_pack_strerror(st), r.record_index);

    /* long acyclic */
    enum { LONGN = 500 };
    static struct node chain[LONGN];
    memset(chain, 0, sizeof chain);
    for (int i = 0; i < LONGN; i++) {
        chain[i].n.type = WMTRenderCommandNop;
        chain[i].n.next.ptr = (i + 1 < LONGN) ? &chain[i+1] : NULL;
    }
    CHECK(run((struct wmtcmd_base *)&chain[0], &r) == WMTW_PACK_OK, "500-node acyclic list packs");
    CHECK(r.record_count == LONGN, "500 nodes yield 500 records");

    /* self cycle */
    static struct node selfc; memset(&selfc, 0, sizeof selfc);
    selfc.n.type = WMTRenderCommandNop; link(&selfc, &selfc);
    CHECK(run((struct wmtcmd_base *)&selfc, &r) == WMTW_PACK_CYCLE, "self-cycle detected");

    /* two-node cycle */
    static struct node c1, c2;
    memset(&c1, 0, sizeof c1); memset(&c2, 0, sizeof c2);
    c1.n.type = c2.n.type = WMTRenderCommandNop;
    link(&c1, &c2); link(&c2, &c1);
    CHECK(run((struct wmtcmd_base *)&c1, &r) == WMTW_PACK_CYCLE, "two-node cycle detected");

    /* record cap boundary: a cycle long enough to exceed the cap must still
     * terminate, by cap or by cycle -- never by running forever */
    enum { RING = 300 };
    static struct node ring[RING];
    memset(ring, 0, sizeof ring);
    for (int i = 0; i < RING; i++) {
        ring[i].n.type = WMTRenderCommandNop;
        ring[i].n.next.ptr = &ring[(i + 1) % RING];
    }
    st = run((struct wmtcmd_base *)&ring[0], &r);
    CHECK(st == WMTW_PACK_CYCLE || st == WMTW_PACK_TOO_MANY_RECORDS,
          "large ring terminates (cycle or cap)");

    /* unsupported opcode is NAMED */
    /* A value the packer CANNOT know, rather than a real opcode that merely is
     * not implemented yet. Naming a real one made this test fail the moment
     * that opcode was implemented, which says nothing about the behaviour under
     * test: that an UNKNOWN opcode is refused and named. */
    enum { WMT_OPCODE_THAT_CANNOT_EXIST = 0xBEEF };
    static struct node uns; memset(&uns, 0, sizeof uns);
    uns.n.type = (enum WMTRenderCommandType)WMT_OPCODE_THAT_CANNOT_EXIST;
    st = run((struct wmtcmd_base *)&uns, &r);
    CHECK(st == WMTW_PACK_UNSUPPORTED_OP, "unsupported opcode rejected");
    CHECK(r.opcode == WMT_OPCODE_THAT_CANNOT_EXIST, "failure names the opcode");
    CHECK(r.record_index == 0, "failure names the record index");

    /* --- packed output must satisfy the PRODUCTION validator --- */
    printf("real validator\n");
    struct wmtw_packer p = { recbuf, sizeof recbuf, 0, sidebuf, sizeof sidebuf, 0, 0 };
    memset(&r, 0, sizeof r);
    CHECK(wmtw_pack_render((struct wmtcmd_base *)&chain[0], &p, &r) == WMTW_PACK_OK,
          "pack a real list for validation");
    static uint8_t payload[WMTW_MAX_BATCH_BYTES + WMTW_MAX_SIDECAR_BYTES + 64];
    struct wmtw_batch *bp = (void *)payload;
    bp->magic = WMTW_BATCH_MAGIC; bp->version = WMTW_VERSION; bp->encoder_kind = 0;
    bp->record_bytes = p.rec_len; bp->record_count = p.count;
    bp->sidecar_bytes = p.side_len; bp->reserved = 0;
    memcpy(payload + sizeof *bp, recbuf, p.rec_len);
    memcpy(payload + sizeof *bp + p.rec_len, sidebuf, p.side_len);
    uint32_t plen = (uint32_t)(sizeof *bp + p.rec_len + p.side_len);
    struct wmtw_dec_result d; struct wmtw_view v;
    CHECK(wmtw_validate_batch(payload, plen, &v, &d) == WMTW_DEC_OK,
          "packer output passes the production validator");
    CHECK(v.rec_bytes == p.rec_len && v.side_bytes == p.side_len, "view spans match");
    CHECK(d.record_index == LONGN, "validator counts the same records the packer wrote");
    /* a header claiming more than arrived must be rejected, not believed */
    CHECK(wmtw_validate_batch(payload, plen - 1, &v, &d) == WMTW_DEC_NOT_EXACT,
          "header longer than the received payload rejected");
    bp->encoder_kind = 1;
    CHECK(wmtw_validate_batch(payload, plen, &v, &d) == WMTW_DEC_UNIMPLEMENTED_OP,
          "unknown encoder kind rejected");
    bp->encoder_kind = 0;

    /* validator must reject a corrupted prologue */
    uint32_t save_rc = bp->record_count, save_rb = bp->record_bytes;
    bp->magic = 0;
    CHECK(wmtw_validate_batch(payload, plen, &v, &d) != WMTW_DEC_OK, "bad magic rejected");
    bp->magic = WMTW_BATCH_MAGIC; bp->version = 99;
    CHECK(wmtw_validate_batch(payload, plen, &v, &d) != WMTW_DEC_OK, "bad version rejected");
    bp->version = WMTW_VERSION; bp->record_count = save_rc + 1;
    CHECK(wmtw_validate_batch(payload, plen, &v, &d) == WMTW_DEC_NOT_EXACT,
          "record-count mismatch rejected");
    bp->record_count = save_rc; bp->record_bytes = WMTW_MAX_BATCH_BYTES + 1;
    CHECK(wmtw_validate_batch(payload, plen, &v, &d) == WMTW_DEC_TRUNCATED,
          "oversized record region rejected");
    bp->record_bytes = save_rb; bp->record_count = WMTW_MAX_RECORDS + 1;
    CHECK(wmtw_validate_batch(payload, plen, &v, &d) == WMTW_DEC_TOO_MANY,
          "record cap enforced by the validator");
    bp->record_count = save_rc;

    printf("\n%d checks, %d failures\n", checks, fails);
    return fails != 0;
}
