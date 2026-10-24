// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright 2026 125hz
// Madeira Converter Exception: see LICENSE-EXCEPTION.md

#include "chunk_zip.h"
#include <string.h>
#include <zlib.h>

// Steam serves chunks in three encodings: VZstd ("VSZa"), VZip ("VZ", LZMA)
// and, for older content, a plain PKZip archive holding one entry. Without
// the zip form every such chunk failed to decode and the whole install
// stopped. Integrity is still enforced by the caller's Adler-32 and size
// checks.

static unsigned rd16(const uint8_t *p) { return (unsigned)p[0] | (unsigned)p[1] << 8; }
static unsigned long rd32(const uint8_t *p)
{
    return (unsigned long)p[0] | (unsigned long)p[1] << 8 | (unsigned long)p[2] << 16 | (unsigned long)p[3] << 24;
}

int chunk_zip_decode(const uint8_t *in, size_t in_size,
                     uint8_t *out, size_t out_cap, size_t *produced)
{
    if (!in || !out || in_size < 30 || memcmp(in, "PK\3\4", 4) != 0) return -1;
    unsigned flags = rd16(in + 6), method = rd16(in + 8);
    unsigned long csize = rd32(in + 18), usize = rd32(in + 22);
    size_t start = 30 + (size_t)rd16(in + 26) + (size_t)rd16(in + 28);
    if (start > in_size) return -1;
    size_t avail = in_size - start;
    /* Bit 3: sizes follow the data in a descriptor and are zero here. */
    int sized = !(flags & 8) && csize != 0;
    if (sized) {
        if (csize > avail) return -1;
        avail = (size_t)csize;
        if (usize > out_cap) return -4;
    }
    if (method == 0) {
        size_t n = sized ? (size_t)csize : out_cap;
        if (n > avail) return -3;
        if (n > out_cap) return -4;
        memcpy(out, in + start, n);
        if (produced) *produced = n;
        return 0;
    }
    if (method != 8) return -2;
    z_stream s;
    memset(&s, 0, sizeof s);
    if (inflateInit2(&s, -15) != Z_OK) return -3;
    s.next_in = (Bytef *)(in + start);
    s.avail_in = (uInt)avail;
    s.next_out = out;
    s.avail_out = (uInt)out_cap;
    int r = inflate(&s, Z_FINISH);
    size_t total = (size_t)s.total_out;
    inflateEnd(&s);
    if (r == Z_BUF_ERROR && s.avail_out == 0) return -4;
    if (r != Z_STREAM_END) return -3;
    if (produced) *produced = total;
    return 0;
}
