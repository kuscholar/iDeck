/* A deliberately asymmetric test texture.
 *
 * A plain checkerboard is symmetric under rotation and mirroring, so it hides
 * exactly the faults worth seeing. This one carries three independent cues:
 *
 *   - an 8-pixel RED band along the TOP edge only
 *   - an 8-pixel GREEN band along the LEFT edge only
 *   - a single BLUE square inset from the top-left corner
 *
 * A rotation swaps which edge is red, a mirror swaps which edge is green, and
 * the inset square breaks the remaining diagonal symmetry. Stretching shows as
 * unequal checker cells, and a wrong sampler or address mode shows as blurred
 * or wrapped bands.
 */
#ifndef MADEIRA_D3D12_CHECKER_TEX_H
#define MADEIRA_D3D12_CHECKER_TEX_H

#define CHECKER_DIM  64
#define CHECKER_CELL 8

static void checker_fill(BYTE *px, UINT dim, UINT row_pitch) {
    for (UINT y = 0; y < dim; y++) {
        BYTE *row = px + (SIZE_T)y * row_pitch;
        for (UINT x = 0; x < dim; x++) {
            BYTE r, g, b;
            int cell = (int)((x / CHECKER_CELL + y / CHECKER_CELL) & 1);
            r = g = b = cell ? 235 : 70;

            if (y < CHECKER_CELL)                    { r = 230; g = 40;  b = 40;  }  /* top    */
            else if (x < CHECKER_CELL)               { r = 40;  g = 220; b = 60;  }  /* left   */
            else if (x >= CHECKER_CELL && x < CHECKER_CELL * 2 &&
                     y >= CHECKER_CELL && y < CHECKER_CELL * 2)
                                                     { r = 50;  g = 90;  b = 240; }  /* inset  */
            row[x * 4 + 0] = r;
            row[x * 4 + 1] = g;
            row[x * 4 + 2] = b;
            row[x * 4 + 3] = 255;
        }
    }
}

#endif
