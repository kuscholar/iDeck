// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright 2026 Jfishin, 125hz
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
//
// Derived from Jfishin's Madeira Steam client, used in Madeira with the
// author's permission (see docs/STEAM_SIGNIN.md, "Provenance").

#include "lzma_shim.h"
#include <stdlib.h>
#include <string.h>

// Minimal liblzma ABI declarations (SDK ships liblzma.tbd without headers).
// VZip's raw LZMA1 stream has no end-of-payload marker, so a raw decode can't
// detect stream end. The .lzma "alone" format carries the uncompressed size in
// its 13-byte header; lzma_alone_decoder uses it and returns STREAM_END.
typedef struct {
    const uint8_t *next_in;
    size_t avail_in;
    uint64_t total_in;
    uint8_t *next_out;
    size_t avail_out;
    uint64_t total_out;
    const void *allocator;
    void *internal;
    void *reserved_ptr1, *reserved_ptr2, *reserved_ptr3, *reserved_ptr4;
    uint64_t reserved_int1, reserved_int2;
    size_t reserved_int3, reserved_int4;
    int reserved_enum1, reserved_enum2;
} lzma_stream_shim;

extern int lzma_alone_decoder(lzma_stream_shim *strm, uint64_t memlimit);
extern int lzma_code(lzma_stream_shim *strm, int action); // LZMA_FINISH = 3
extern void lzma_end(lzma_stream_shim *strm);

int lzma_shim_decode(const uint8_t *props, size_t props_size,
                     const uint8_t *in, size_t in_size,
                     uint8_t *out, size_t out_size,
                     size_t *out_produced) {
    if (props_size != 5) return 9; // LZMA_OPTIONS_ERROR

    // Synthesize .lzma alone stream: props(5) + uncompressed size (8 LE) + data
    size_t buf_size = 13 + in_size;
    uint8_t *buf = malloc(buf_size);
    if (!buf) return 5; // LZMA_MEM_ERROR
    memcpy(buf, props, 5);
    uint64_t sz = out_size;
    for (int i = 0; i < 8; i++) buf[5 + i] = (uint8_t)(sz >> (8 * i));
    memcpy(buf + 13, in, in_size);

    lzma_stream_shim strm;
    memset(&strm, 0, sizeof(strm));
    int ret = lzma_alone_decoder(&strm, UINT64_MAX);
    if (ret == 0) {
        strm.next_in = buf;
        strm.avail_in = buf_size;
        strm.next_out = out;
        strm.avail_out = out_size;
        ret = lzma_code(&strm, 3); // LZMA_FINISH
        if (ret == 1) { // LZMA_STREAM_END
            if (out_produced) *out_produced = (size_t)strm.total_out;
            ret = 0;
        } else if (ret == 0) {
            // LZMA_OK here means the input ended before the stream
            // did (truncated or corrupt chunk). It is not a successful decode.
            ret = 10; // LZMA_BUF_ERROR
        }
        lzma_end(&strm);
    }
    free(buf);
    return ret;
}
