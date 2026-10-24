/* 24 vertices, four per face, so each face is a flat distinct colour.
 * GENERATED-style constant block kept in one place so the offscreen test and
 * the visible one cannot drift apart. */
#ifndef MADEIRA_D3D12_CUBE_GEOM_H
#define MADEIRA_D3D12_CUBE_GEOM_H

static const float cube_pos[24][4] = {
    /* +Z front  */ {-0.4f,-0.4f, 0.4f,1},{ 0.4f,-0.4f, 0.4f,1},{ 0.4f, 0.4f, 0.4f,1},{-0.4f, 0.4f, 0.4f,1},
    /* -Z back   */ { 0.4f,-0.4f,-0.4f,1},{-0.4f,-0.4f,-0.4f,1},{-0.4f, 0.4f,-0.4f,1},{ 0.4f, 0.4f,-0.4f,1},
    /* +X right  */ { 0.4f,-0.4f, 0.4f,1},{ 0.4f,-0.4f,-0.4f,1},{ 0.4f, 0.4f,-0.4f,1},{ 0.4f, 0.4f, 0.4f,1},
    /* -X left   */ {-0.4f,-0.4f,-0.4f,1},{-0.4f,-0.4f, 0.4f,1},{-0.4f, 0.4f, 0.4f,1},{-0.4f, 0.4f,-0.4f,1},
    /* +Y top    */ {-0.4f, 0.4f, 0.4f,1},{ 0.4f, 0.4f, 0.4f,1},{ 0.4f, 0.4f,-0.4f,1},{-0.4f, 0.4f,-0.4f,1},
    /* -Y bottom */ {-0.4f,-0.4f,-0.4f,1},{ 0.4f,-0.4f,-0.4f,1},{ 0.4f,-0.4f, 0.4f,1},{-0.4f,-0.4f, 0.4f,1},
};
static const float cube_col[24][4] = {
    {0.10f,0.45f,1.00f,1},{0.10f,0.45f,1.00f,1},{0.10f,0.45f,1.00f,1},{0.10f,0.45f,1.00f,1},
    {1.00f,0.35f,0.10f,1},{1.00f,0.35f,0.10f,1},{1.00f,0.35f,0.10f,1},{1.00f,0.35f,0.10f,1},
    {0.20f,0.85f,0.40f,1},{0.20f,0.85f,0.40f,1},{0.20f,0.85f,0.40f,1},{0.20f,0.85f,0.40f,1},
    {0.95f,0.80f,0.15f,1},{0.95f,0.80f,0.15f,1},{0.95f,0.80f,0.15f,1},{0.95f,0.80f,0.15f,1},
    {0.75f,0.30f,0.95f,1},{0.75f,0.30f,0.95f,1},{0.75f,0.30f,0.95f,1},{0.75f,0.30f,0.95f,1},
    {0.95f,0.25f,0.55f,1},{0.95f,0.25f,0.55f,1},{0.95f,0.25f,0.55f,1},{0.95f,0.25f,0.55f,1},
};
/* Front face first and back face second: at rest both cover the centre, so the
 * centre pixel reports whether depth testing kept the nearer one. */
static const unsigned short cube_idx[] = {
     0, 1, 2,  0, 2, 3,      4, 5, 6,  4, 6, 7,
     8, 9,10,  8,10,11,     12,13,14, 12,14,15,
    16,17,18, 16,18,19,     20,21,22, 20,22,23,
};
#endif
