// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright 2026 Jfishin, 125hz
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
//
// Derived from Jfishin's Madeira Steam client, used in Madeira with the
// author's permission (see docs/STEAM_SIGNIN.md, "Provenance").

#ifndef lzma_shim_h
#define lzma_shim_h

#include <stddef.h>
#include <stdint.h>

/// Decode a raw LZMA1 stream using the 5-byte LZMA property block
/// (props byte + 4-byte dictionary size, as found in Steam's VZip chunks).
/// Returns 0 (LZMA_OK) on success; out_produced receives bytes written.
int lzma_shim_decode(const uint8_t *props, size_t props_size,
                     const uint8_t *in, size_t in_size,
                     uint8_t *out, size_t out_size,
                     size_t *out_produced);

#include "zstd_edu.h"
#include "chunk_zip.h"

#endif
