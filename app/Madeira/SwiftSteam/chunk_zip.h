// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright 2026 125hz
// Madeira Converter Exception: see LICENSE-EXCEPTION.md

#ifndef chunk_zip_h
#define chunk_zip_h

#include <stddef.h>
#include <stdint.h>

/// Decodes a Steam content chunk stored as a single-entry PKZip
/// archive (the format older depots use besides VZip and VZstd).
/// Handles deflate and stored entries, with or without a trailing data
/// descriptor (sizes then come from the caller's expected output size).
/// Returns 0 on success and writes the decoded length to *produced;
/// negative values: -1 malformed header, -2 unsupported method,
/// -3 inflate error or truncated stream, -4 output larger than out_cap.
int chunk_zip_decode(const uint8_t *in, size_t in_size,
                     uint8_t *out, size_t out_cap, size_t *produced);

#endif
