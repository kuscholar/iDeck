/* ml821: framing tests for the coalesced upload and release messages.
 *
 * These exercise rm_multi_ok / rm_release_multi_ok -- the SAME validators the
 * daemon calls -- with well-formed and malformed payloads. A wire format that
 * only gets tested by the code that produces it proves nothing about what a
 * corrupt or hostile message does, and this pair is walked before any handle is
 * resolved, so it is the first thing standing between the daemon and bad input. */
#include "../protocol.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

static int fails, checks;
#define CHECK(c, msg) do { checks++; if (!(c)) { fails++; \
    printf("FAIL %s:%d %s\n", __FILE__, __LINE__, msg); } } while (0)

/* Build a valid message with `n` ranges of `len` bytes each. */
static uint32_t build(uint8_t *p, uint32_t n, uint32_t len) {
    struct rm_buffer_multi *m = (void *)p;
    m->count = n; m->data_bytes = n * len;
    memset(p + sizeof *m, 0xAB, n * len);
    struct rm_buffer_range *r = (void *)(p + sizeof *m + n * len);
    for (uint32_t i = 0; i < n; i++) {
        r[i].handle = 0x8000000100000000ull | i;
        r[i].offset = i * 4096; r[i].length = len;
    }
    return (uint32_t)(sizeof *m + n * len + n * sizeof *r);
}

int main(void) {
    static uint8_t buf[1 << 20];
    const struct rm_buffer_range *r; const uint8_t *d;

    uint32_t total = build(buf, 4, 1000);
    CHECK(rm_multi_ok(buf, total, &r, &d), "4x1000 valid");
    CHECK(d == buf + sizeof(struct rm_buffer_multi), "data starts after header");
    CHECK(r == (const struct rm_buffer_range *)(d + 4000), "descriptors trail the data");
    CHECK(r[3].length == 1000, "last descriptor readable");

    total = build(buf, 1, 1);
    CHECK(rm_multi_ok(buf, total, &r, &d), "single 1-byte range valid");
    total = build(buf, RM_MULTI_MAX_RANGES, 16);
    CHECK(rm_multi_ok(buf, total, &r, &d), "max ranges valid");

    /* ---- malformed ---- */
    total = build(buf, 4, 1000);
    CHECK(!rm_multi_ok(buf, total - 1, &r, &d), "truncated by one byte rejected");
    CHECK(!rm_multi_ok(buf, total + 1, &r, &d), "one byte too long rejected");
    CHECK(!rm_multi_ok(buf, 4, &r, &d), "shorter than the header rejected");

    total = build(buf, 4, 1000);
    ((struct rm_buffer_multi *)buf)->count = 0;
    CHECK(!rm_multi_ok(buf, total, &r, &d), "zero ranges rejected");
    total = build(buf, 4, 1000);
    ((struct rm_buffer_multi *)buf)->count = RM_MULTI_MAX_RANGES + 1;
    CHECK(!rm_multi_ok(buf, total, &r, &d), "count over the cap rejected");

    /* lengths that do not sum to data_bytes */
    total = build(buf, 4, 1000);
    ((struct rm_buffer_range *)(buf + sizeof(struct rm_buffer_multi) + 4000))[2].length = 999;
    CHECK(!rm_multi_ok(buf, total, &r, &d), "lengths under data_bytes rejected");
    total = build(buf, 4, 1000);
    ((struct rm_buffer_range *)(buf + sizeof(struct rm_buffer_multi) + 4000))[2].length = 1001;
    CHECK(!rm_multi_ok(buf, total, &r, &d), "lengths over data_bytes rejected");
    total = build(buf, 4, 1000);
    ((struct rm_buffer_range *)(buf + sizeof(struct rm_buffer_multi) + 4000))[1].length = 0;
    CHECK(!rm_multi_ok(buf, total, &r, &d), "zero-length range rejected");

    /* a length chosen to wrap a 32-bit sum must not pass */
    total = build(buf, 2, 8);
    { struct rm_buffer_range *rr = (void *)(buf + sizeof(struct rm_buffer_multi) + 16);
      rr[0].length = 0xFFFFFFF8ull; rr[1].length = 0x10ull;
      CHECK(!rm_multi_ok(buf, total, &r, &d), "32-bit wrapping lengths rejected"); }

    /* a range larger than the per-message ceiling must not pass */
    total = build(buf, 1, 16);
    { struct rm_buffer_range *rr = (void *)(buf + sizeof(struct rm_buffer_multi) + 16);
      rr[0].length = (uint64_t)RM_CHUNK_BYTES + 1;
      CHECK(!rm_multi_ok(buf, total, &r, &d), "range over the chunk cap rejected"); }

    /* ---- releases ---- */
    const uint64_t *hs;
    struct rm_release_multi *rm = (void *)buf;
    rm->count = 3; rm->reserved = 0;
    uint64_t *h = (uint64_t *)(buf + sizeof *rm);
    h[0] = 1; h[1] = 2; h[2] = 3;
    uint32_t rtot = (uint32_t)(sizeof *rm + 3 * sizeof(uint64_t));
    CHECK(rm_release_multi_ok(buf, rtot, &hs), "3 handles valid");
    CHECK(hs[2] == 3, "handles readable");
    CHECK(!rm_release_multi_ok(buf, rtot - 1, &hs), "truncated release rejected");
    CHECK(!rm_release_multi_ok(buf, rtot + 8, &hs), "over-long release rejected");
    rm->count = 0;
    CHECK(!rm_release_multi_ok(buf, rtot, &hs), "zero handles rejected");
    rm->count = RM_MULTI_MAX_HANDLES + 1;
    CHECK(!rm_release_multi_ok(buf, rtot, &hs), "handle count over the cap rejected");

    printf("\n%d checks, %d failures\n", checks, fails);
    return fails != 0;
}
