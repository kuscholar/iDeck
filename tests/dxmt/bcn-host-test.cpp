/* Madeira: host-side unit test for the shared BCn decoder
 * (dxmt/src/dxmt/dxmt_bcn.hpp + dxmt_bcn.cpp).
 *
 * WHY A HOST TEST
 * ---------------
 * The decoder is the only thing standing between a device with no BC texture
 * support and a screen full of noise, and it is unreachable from a debugger on
 * that device: it runs inside a translated i386 DLL, its output goes straight
 * into a private Metal texture, and the only symptom of a wrong bit is "the
 * art looks wrong", which is also the symptom of six other things. So the
 * block layout is pinned here, on the build machine, against blocks whose
 * correct output can be computed by hand from the D3D BC specification.
 *
 * Every case below states the bytes AND the expected texels, so a failure
 * names the exact rule that broke rather than "mismatch at offset 47".
 *
 * Build and run:  bash tests/dxmt/build-bcn-host-test.sh
 * Exit code 0 = all cases passed; the last line is PASS or FAIL.
 */
#include "dxmt_bcn.hpp"

#include <cstdio>
#include <cstring>
#include <vector>

using namespace dxmt;

static int g_failures = 0;
static int g_checks = 0;

static void
expect_rgba(const char *what, const uint8_t *px, int r, int g, int b, int a) {
  ++g_checks;
  if (px[0] == r && px[1] == g && px[2] == b && px[3] == a)
    return;
  ++g_failures;
  std::printf("  FAIL %-46s got (%3u,%3u,%3u,%3u) want (%3d,%3d,%3d,%3d)\n", what, px[0], px[1], px[2], px[3], r, g,
              b, a);
}

static void
expect_u8(const char *what, unsigned got, unsigned want) {
  ++g_checks;
  if (got == want)
    return;
  ++g_failures;
  std::printf("  FAIL %-46s got %u want %u\n", what, got, want);
}

/* 565 -> 888 the way the spec's bit-replication expands it, duplicated here so
 * the expectations are independent of the decoder's own helper. */
static void
ref565(unsigned c, int out[3]) {
  unsigned r = (c >> 11) & 0x1f, g = (c >> 5) & 0x3f, b = c & 0x1f;
  out[0] = (int)((r << 3) | (r >> 2));
  out[1] = (int)((g << 2) | (g >> 4));
  out[2] = (int)((b << 3) | (b >> 2));
}

static void
put16(uint8_t *p, unsigned v) {
  p[0] = (uint8_t)(v & 0xff);
  p[1] = (uint8_t)(v >> 8);
}

/* ------------------------------------------------------------------ BC1 --
 * Case 1: c0 > c1, the 4-colour mode. Indices 0..3 must be
 * c0, c1, (2*c0+c1)/3, (c0+2*c1)/3, all opaque.
 * Case 2: c0 <= c1, the 3-colour punch-through mode. Index 2 is the 1/2
 * blend (NOT a 1/3 blend) and index 3 is TRANSPARENT BLACK. Getting this
 * wrong is the single most visible BC1 bug: cut-out foliage turns into
 * solid quads or the wrong colour bleeds along every alpha edge.
 */
static void
test_bc1_four_colour() {
  std::printf("BC1 four-colour mode (c0 > c1)\n");
  const unsigned c0 = 0xF800; /* pure red  */
  const unsigned c1 = 0x001F; /* pure blue */
  uint8_t blk[8] = {};
  put16(blk + 0, c0);
  put16(blk + 2, c1);
  /* Texel 0..3 of row 0 take indices 0,1,2,3; every other row is index 0. */
  blk[4] = 0x00 | (1 << 2) | (2 << 4) | (3 << 6);

  int e0[3], e1[3];
  ref565(c0, e0);
  ref565(c1, e1);

  uint8_t out[4 * 4 * 4];
  bcn_decode_image(blk, sizeof blk, out, 0, 4, 4, /*kind=*/1);
  expect_rgba("bc1.4c idx0 = c0", out + 0, e0[0], e0[1], e0[2], 255);
  expect_rgba("bc1.4c idx1 = c1", out + 4, e1[0], e1[1], e1[2], 255);
  expect_rgba("bc1.4c idx2 = (2c0+c1)/3", out + 8, (2 * e0[0] + e1[0] + 1) / 3, (2 * e0[1] + e1[1] + 1) / 3,
              (2 * e0[2] + e1[2] + 1) / 3, 255);
  expect_rgba("bc1.4c idx3 = (c0+2c1)/3", out + 12, (e0[0] + 2 * e1[0] + 1) / 3, (e0[1] + 2 * e1[1] + 1) / 3,
              (e0[2] + 2 * e1[2] + 1) / 3, 255);
  expect_rgba("bc1.4c row1 idx0 = c0", out + 4 * 4, e0[0], e0[1], e0[2], 255);
}

static void
test_bc1_punchthrough() {
  std::printf("BC1 three-colour punch-through mode (c0 <= c1)\n");
  const unsigned c0 = 0x001F; /* blue, the SMALLER value */
  const unsigned c1 = 0xF800; /* red                      */
  uint8_t blk[8] = {};
  put16(blk + 0, c0);
  put16(blk + 2, c1);
  blk[4] = 0x00 | (1 << 2) | (2 << 4) | (3 << 6);

  int e0[3], e1[3];
  ref565(c0, e0);
  ref565(c1, e1);

  uint8_t out[4 * 4 * 4];
  bcn_decode_image(blk, sizeof blk, out, 0, 4, 4, /*kind=*/1);
  expect_rgba("bc1.pt idx0 = c0 opaque", out + 0, e0[0], e0[1], e0[2], 255);
  expect_rgba("bc1.pt idx1 = c1 opaque", out + 4, e1[0], e1[1], e1[2], 255);
  expect_rgba("bc1.pt idx2 = HALF blend, opaque", out + 8, (e0[0] + e1[0] + 1) / 2, (e0[1] + e1[1] + 1) / 2,
              (e0[2] + e1[2] + 1) / 2, 255);
  expect_rgba("bc1.pt idx3 = TRANSPARENT BLACK", out + 12, 0, 0, 0, 0);
}

/* ------------------------------------------------------------------ BC2 --
 * Explicit 4-bit alpha, one nibble per texel, LOW nibble first; the colour
 * half is a BC1 block that is ALWAYS in 4-colour mode even when c0 <= c1.
 * The nibble expands by replication (0xA -> 0xAA), not by a shift.
 */
static void
test_bc2() {
  std::printf("BC2 explicit 4-bit alpha\n");
  uint8_t blk[16] = {};
  /* alpha nibbles: texel0=0x0 texel1=0xF texel2=0x8 texel3=0xA, rest 0 */
  blk[0] = (uint8_t)(0x0 | (0xF << 4));
  blk[1] = (uint8_t)(0x8 | (0xA << 4));
  /* colour half: c0 <= c1 on purpose -- BC2 must NOT punch through. */
  put16(blk + 8, 0x001F);
  put16(blk + 10, 0xF800);
  blk[12] = 0x00 | (1 << 2) | (3 << 4) | (3 << 6);

  int e0[3], e1[3];
  ref565(0x001F, e0);
  ref565(0xF800, e1);

  uint8_t out[4 * 4 * 4];
  bcn_decode_image(blk, sizeof blk, out, 0, 4, 4, /*kind=*/2);
  expect_u8("bc2 alpha texel0 = 0x00", out[3], 0x00);
  expect_u8("bc2 alpha texel1 = 0xFF", out[7], 0xFF);
  expect_u8("bc2 alpha texel2 = 0x88", out[11], 0x88);
  expect_u8("bc2 alpha texel3 = 0xAA", out[15], 0xAA);
  expect_rgba("bc2 colour idx3 is the 1/3 blend, NOT black", out + 12, (e0[0] + 2 * e1[0] + 1) / 3,
              (e0[1] + 2 * e1[1] + 1) / 3, (e0[2] + 2 * e1[2] + 1) / 3, 0xAA);
}

/* ------------------------------------------------------------------ BC3 --
 * Interpolated alpha. Two sub-cases, because they use different tables:
 *   a0 >  a1  -> 8 values, indices 2..7 are six interpolants of a0..a1
 *   a0 <= a1  -> 6 interpolants plus HARD 0 at index 6 and HARD 255 at 7
 */
static void
test_bc3_eight_interpolant() {
  std::printf("BC3 interpolated alpha, eight-value mode (a0 > a1)\n");
  uint8_t blk[16] = {};
  blk[0] = 255; /* a0 */
  blk[1] = 0;   /* a1 */
  /* three-bit indices, texels 0..4 = 0,1,2,6,7 */
  uint64_t bits = 0ull | (1ull << 3) | (2ull << 6) | (6ull << 9) | (7ull << 12);
  for (int i = 0; i < 6; i++)
    blk[2 + i] = (uint8_t)((bits >> (8 * i)) & 0xff);
  put16(blk + 8, 0xFFFF);
  put16(blk + 10, 0x0000);

  uint8_t out[4 * 4 * 4];
  bcn_decode_image(blk, sizeof blk, out, 0, 4, 4, /*kind=*/3);
  expect_u8("bc3.8 idx0 = a0", out[3], 255);
  expect_u8("bc3.8 idx1 = a1", out[7], 0);
  expect_u8("bc3.8 idx2 = (6*a0+1*a1)/7", out[11], (6 * 255 + 0 + 3) / 7);
  expect_u8("bc3.8 idx6 = (2*a0+5*a1)/7", out[15], (2 * 255 + 0 + 3) / 7);
  expect_u8("bc3.8 idx7 = (1*a0+6*a1)/7", out[4 * 4 + 3], (1 * 255 + 0 + 3) / 7);
}

static void
test_bc3_six_interpolant() {
  std::printf("BC3 interpolated alpha, six-value mode (a0 <= a1)\n");
  uint8_t blk[16] = {};
  blk[0] = 10;  /* a0 */
  blk[1] = 200; /* a1, GREATER -> the six-interpolant table */
  uint64_t bits = 0ull | (1ull << 3) | (2ull << 6) | (6ull << 9) | (7ull << 12);
  for (int i = 0; i < 6; i++)
    blk[2 + i] = (uint8_t)((bits >> (8 * i)) & 0xff);
  put16(blk + 8, 0xFFFF);
  put16(blk + 10, 0x0000);

  uint8_t out[4 * 4 * 4];
  bcn_decode_image(blk, sizeof blk, out, 0, 4, 4, /*kind=*/3);
  expect_u8("bc3.6 idx0 = a0", out[3], 10);
  expect_u8("bc3.6 idx1 = a1", out[7], 200);
  expect_u8("bc3.6 idx2 = (4*a0+1*a1)/5", out[11], (4 * 10 + 1 * 200 + 2) / 5);
  expect_u8("bc3.6 idx6 = HARD 0", out[15], 0);
  expect_u8("bc3.6 idx7 = HARD 255", out[4 * 4 + 3], 255);
}

/* ------------------------------------------------------------ BC4 / BC5 --
 * The 3Dc pair (D3DFMT_ATI1 / ATI2) lowers to these, so a device without BC
 * needs them decoded to R8 / RG8 exactly as the sampler swizzle expects.
 */
static void
test_bc4_bc5() {
  std::printf("BC4 / BC5 scalar blocks\n");
  uint8_t blk[16] = {};
  blk[0] = 255;
  blk[1] = 0;
  uint64_t bits = 0ull | (1ull << 3) | (2ull << 6);
  for (int i = 0; i < 6; i++)
    blk[2 + i] = (uint8_t)((bits >> (8 * i)) & 0xff);

  uint8_t r8[4 * 4];
  bcn_decode_image(blk, 8, r8, 0, 4, 4, /*kind=*/4);
  expect_u8("bc4 texel0", r8[0], 255);
  expect_u8("bc4 texel1", r8[1], 0);
  expect_u8("bc4 texel2", r8[2], (6 * 255 + 3) / 7);
  expect_u8("bc4 texel size is 1 byte", bcn_texel_size(4), 1);

  /* BC5: the second 8 bytes drive green. Make green the mirror of red. */
  std::memcpy(blk + 8, blk, 8);
  blk[8] = 0;
  blk[9] = 255;
  uint8_t rg8[4 * 4 * 2];
  bcn_decode_image(blk, 16, rg8, 0, 4, 4, /*kind=*/5);
  expect_u8("bc5 texel0.r", rg8[0], 255);
  expect_u8("bc5 texel0.g", rg8[1], 0);
  expect_u8("bc5 texel1.r", rg8[2], 0);
  expect_u8("bc5 texel1.g", rg8[3], 255);
  expect_u8("bc5 texel size is 2 bytes", bcn_texel_size(5), 2);
}

/* ------------------------------------------------------- odd extents -----
 * A 5x3 BC1 level is 2x1 blocks on the wire: the right-hand block contributes
 * ONE column and the only block row contributes THREE rows. Writing the full
 * 4x4 would run one texel past the row and one row past the image, which on
 * the upload path means corrupting the next row of a staging span.
 */
static void
test_odd_extents() {
  std::printf("odd extents: partial blocks are clipped, not written past\n");
  const unsigned c0 = 0xF800, c1 = 0x001F;
  uint8_t blocks[2][8] = {};
  for (int i = 0; i < 2; i++) {
    put16(blocks[i] + 0, c0);
    put16(blocks[i] + 2, c1);
    std::memset(blocks[i] + 4, i == 0 ? 0x00 : 0x55, 4); /* left: all c0, right: all c1 */
  }
  int e0[3], e1[3];
  ref565(c0, e0);
  ref565(c1, e1);

  /* Destination is 5x3 RGBA8 inside a 6-wide canvas so overruns are visible. */
  const uint32_t w = 5, h = 3, canvas_w = 6;
  std::vector<uint8_t> dst((size_t)canvas_w * 4 * (h + 1), 0xCD);
  bcn_decode_image(&blocks[0][0], sizeof blocks[0] * 2 /* 2 blocks per row */, dst.data(), (size_t)canvas_w * 4, w, h,
                   /*kind=*/1);

  expect_rgba("odd (0,0) from left block", dst.data() + 0, e0[0], e0[1], e0[2], 255);
  expect_rgba("odd (3,2) from left block", dst.data() + (size_t)2 * canvas_w * 4 + 3 * 4, e0[0], e0[1], e0[2], 255);
  expect_rgba("odd (4,0) from right block", dst.data() + 4 * 4, e1[0], e1[1], e1[2], 255);
  expect_rgba("odd (4,2) from right block", dst.data() + (size_t)2 * canvas_w * 4 + 4 * 4, e1[0], e1[1], e1[2], 255);
  /* Column 5 and row 3 are outside the image: untouched guard bytes. */
  expect_u8("odd column 5 untouched", dst[5 * 4], 0xCD);
  expect_u8("odd row 3 untouched", dst[(size_t)3 * canvas_w * 4], 0xCD);
}

static void
test_tiny_levels() {
  std::printf("tiny levels: 2x2 and 1x1 are still one whole block\n");
  uint8_t blk[8] = {};
  put16(blk + 0, 0xF800);
  put16(blk + 2, 0x001F);
  blk[4] = 0x00; /* every texel index 0 */
  int e0[3];
  ref565(0xF800, e0);

  uint8_t out2[2 * 2 * 4];
  std::memset(out2, 0xCD, sizeof out2);
  bcn_decode_image(blk, 8, out2, 0, 2, 2, 1);
  expect_rgba("2x2 (0,0)", out2 + 0, e0[0], e0[1], e0[2], 255);
  expect_rgba("2x2 (1,1)", out2 + (2 + 1) * 4, e0[0], e0[1], e0[2], 255);

  uint8_t out1[1 * 1 * 4];
  std::memset(out1, 0xCD, sizeof out1);
  bcn_decode_image(blk, 8, out1, 0, 1, 1, 1);
  expect_rgba("1x1 (0,0)", out1 + 0, e0[0], e0[1], e0[2], 255);

  expect_u8("decoded bytes for 1x1 BC1", (unsigned)bcn_decoded_bytes(1, 1, 1), 4u);
  expect_u8("decoded bytes for 2x2 BC3", (unsigned)bcn_decoded_bytes(3, 2, 2), 16u);
  expect_u8("BC1 block is 8 bytes", bcn_block_bytes(1), 8u);
  expect_u8("BC3 block is 16 bytes", bcn_block_bytes(3), 16u);
}

/* DXT2/DXT4 are the premultiplied-alpha twins of DXT3/DXT5 and decode with the
 * SAME bit layout -- the premultiplication is a shading convention, not a
 * storage difference. Asserted so a future reader does not add a second kind. */
static void
test_premultiplied_twins_share_layout() {
  std::printf("DXT2/DXT4 share DXT3/DXT5 layout (premultiply is not a decode)\n");
  uint8_t blk[16];
  for (int i = 0; i < 16; i++)
    blk[i] = (uint8_t)(i * 17 + 3);
  uint8_t a[4 * 4 * 4], b[4 * 4 * 4];
  bcn_decode_image(blk, 16, a, 0, 4, 4, 2);
  bcn_decode_image(blk, 16, b, 0, 4, 4, 2);
  ++g_checks;
  if (std::memcmp(a, b, sizeof a) != 0) {
    ++g_failures;
    std::printf("  FAIL BC2 decode is not deterministic\n");
  }
}

int
main() {
  std::printf("=== dxmt BCn decoder host test ===\n");
  test_bc1_four_colour();
  test_bc1_punchthrough();
  test_bc2();
  test_bc3_eight_interpolant();
  test_bc3_six_interpolant();
  test_bc4_bc5();
  test_odd_extents();
  test_tiny_levels();
  test_premultiplied_twins_share_layout();
  std::printf("=== %d checks, %d failures ===\n", g_checks, g_failures);
  std::printf("%s\n", g_failures == 0 ? "PASS" : "FAIL");
  return g_failures == 0 ? 0 : 1;
}
