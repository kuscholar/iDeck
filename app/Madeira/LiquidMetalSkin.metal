// LiquidMetalSkin.metal — liquid metal drawn under the system's Liquid Glass shapes.
//
// A plain Metal render pipeline (a full-screen triangle and a fragment shader) for a
// CAMetalLayer that GlassSkin places inside a glass pill's layer tree, where the render
// server clips it to the pill's live signed-distance shape. So this shader only paints
// the metal; the shape, its morphs, merges and press stretch come from the system.
//
// The surface is the Desktop button's (LiquidMetal.metal, which stays separate): domed
// like a drop of mercury with slowly flowing folds, reflecting a studio of two crossing
// light bands at six wavelengths, so each highlight's edges split into rainbows. The
// dome follows the bounding box of the pill's current elements; the flowing folds are
// fixed to the screen, so the pill slides over them. The dark band is aimed at the middle
// of the pill (the system's white icons and labels) and sways around it.
//
// With `rim` set (the tab bar's lens, which keeps its glass) the metal covers only the
// shape's edge and dissolves toward the middle along a flowing boundary, showing the
// glass inside.
//
// Coordinates are points in the layer's space: layer pixel / scale + origin.

#include <metal_stdlib>
using namespace metal;

namespace liquidmetalskin {

struct Uniforms {
    float2 origin;     // the layer's top-left, in points
    float  scale;      // pixels per point
    float  time;       // seconds
    float4 pills[4];   // current pill rects (x, y, width, height), points
    int    pillCount;
    float  rim;        // 1: metal on the edge only, dissolving into the glass inside
    float  lift;       // the lens's lift progress, 0 to 1 (rim only)
    float  light;      // 1 in light mode: the bright band in the middle instead of the dark
};

struct VertexOut { float4 position [[position]]; };

static float roundBox(float2 p, float2 b, float r) {
    float2 q = abs(p) - b + r;
    return length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - r;
}

static float height(float2 q, float t) {
    float2 w = q;
    w += 0.38 * float2(sin(w.y * 1.3 + t * 0.35), cos(w.x * 1.1 - t * 0.28));
    w += 0.22 * float2(sin(w.y * 2.1 - t * 0.23 + 1.3), cos(w.x * 1.7 + t * 0.31 + 0.7));
    return 0.65 * sin(w.x * 1.2 + w.y * 0.7) + 0.35 * sin(w.y * 1.6 - w.x * 0.5 + 1.0);
}

// The main light band's phase from the folds' slope at q, as studio() sees it.
static float bandPhase(float2 q, float t, float e) {
    float h0 = height(q, t);
    float2 n = -float2(height(q + float2(e, 0.0), t) - h0, height(q + float2(0.0, e), t) - h0) / e * 0.5;
    return dot(n, float2(0.80, 0.60)) * 3.4;
}

static float studio(float2 n, float shiftA, float shiftB) {
    float a = dot(n, float2(0.80, 0.60)) * 3.4 + shiftA;
    float b = dot(n, float2(-0.55, 0.83)) * 2.3 + 1.2 - shiftB * 0.5;
    float v = 0.38 + 0.42 * sin(a) + 0.22 * sin(b);
    return mix(smoothstep(-0.05, 1.0, v), smoothstep(0.48, 0.60, v), 0.5);
}

constant float3 spectrum[6] = {
    float3(0.95, 0.10, 0.25),
    float3(1.00, 0.45, 0.00),
    float3(0.85, 0.85, 0.00),
    float3(0.10, 0.90, 0.35),
    float3(0.05, 0.40, 1.00),
    float3(0.45, 0.05, 0.95),
};
constant float3 spectrumSum = float3(3.40, 2.75, 2.55);

} // namespace liquidmetalskin

vertex liquidmetalskin::VertexOut liquidMetalSkinVertex(uint vid [[vertex_id]]) {
    // One triangle that covers the whole target.
    float2 uv = float2((vid << 1) & 2, vid & 2);
    liquidmetalskin::VertexOut out;
    out.position = float4(uv * float2(2.0, -2.0) + float2(-1.0, 1.0), 0.0, 1.0);
    return out;
}

fragment half4 liquidMetalSkinFragment(liquidmetalskin::VertexOut in [[stage_in]],
                                       constant liquidmetalskin::Uniforms &u [[buffer(0)]]) {
    using namespace liquidmetalskin;
    const float2 point = u.origin + in.position.xy / max(u.scale, 1.0);

    // The distance to the nearest element sets the bevel; the bounding box of all of them
    // sets the dome, so the lighting cannot jump between elements as the system reshapes
    // the pill (a press or a drag stretches it).
    float best = 1e9;
    float2 nearestCentre = 0.0, nearestHalf = float2(1.0);
    float2 lo = float2(1e9), hi = float2(-1e9);
    for (int i = 0; i < u.pillCount && i < 4; i++) {
        float4 r = u.pills[i];
        float2 half2 = r.zw * 0.5;
        float d = roundBox(point - (r.xy + half2), half2, min(half2.x, half2.y));
        if (d < best) { best = d; nearestCentre = r.xy + half2; nearestHalf = half2; }
        lo = min(lo, r.xy); hi = max(hi, r.xy + r.zw);
    }
    // Well outside every pill (with room for a press stretch): nothing here is shown.
    if (u.pillCount == 0 || best > 60.0) { return half4(0.0); }

    const float2 halfSize = max((hi - lo) * 0.5, float2(1.0));
    const float2 p = point - (lo + halfSize);
    const float time = u.time;

    // The flowing folds are fixed to the screen at a fixed scale (44 pt, a pill's height):
    // the pill slides over them as it moves and stretches, instead of rescaling them.
    float2 q = point / 44.0 * 1.4;
    const float e = 0.012;
    float hx = height(q + float2(e, 0.0), time) - height(q - float2(e, 0.0), time);
    float hy = height(q + float2(0.0, e), time) - height(q - float2(0.0, e), time);
    float2 n = -float2(hx, hy) / (2.0 * e) * 0.5;

    // Where the dark band falls depends on the surface's slope, which the folds keep
    // changing. Aim it at the pill's middle line: read the main band's phase there, at the
    // pill's centre and in this pixel's column, and shift the band so its darkest part lies
    // on the line, mostly following the column (so a fold under one icon cannot lift the
    // band off it) and partly the centre (so the folds still bend it). A slow sway moves it
    // about. The second band keeps its own drift.
    const float2 middle = lo + halfSize;
    const float aimCentre = bandPhase(middle / 44.0 * 1.4, time, e);
    const float aimColumn = bandPhase(float2(point.x, middle.y) / 44.0 * 1.4, time, e);
    const float sway = 0.32 * sin(time * 0.19) + 0.18 * sin(time * 0.31 + 2.0);
    // In light mode the bright band takes the middle (the system's glyphs are dark).
    const float target = u.light > 0.5 ? 1.570796 : 4.712389;
    const float aim = target - mix(aimCentre, aimColumn, 0.6) + sway;
    // The dome is flat in the middle and curves toward the edge, like a capsule: the edges
    // tilt as steeply as ever (bright, coloured rims) while the face stays on the dark band.
    const float2 across = clamp(p / halfSize, -1.15, 1.15);
    n += float2(across.x * abs(across.x) * 0.35, across.y * abs(across.y) * 0.85);

    // A gentle bevel toward the pill's edge (the system's rim highlight sits on top).
    float bevelWidth = clamp(nearestHalf.y * 0.24, 2.0, 6.0);
    float k = clamp(1.0 + best / bevelWidth, 0.0, 1.0);
    const float2 np = point - nearestCentre;
    const float nr = min(nearestHalf.x, nearestHalf.y);
    float2 outward = normalize(float2(roundBox(np + float2(0.25, 0.0), nearestHalf, nr) - roundBox(np - float2(0.25, 0.0), nearestHalf, nr),
                                      roundBox(np + float2(0.0, 0.25), nearestHalf, nr) - roundBox(np - float2(0.0, 0.25), nearestHalf, nr)) + 1e-5);
    n += outward * (k * k * 1.2);

    // Each wavelength sees the bands a little apart (the dispersion).
    float drift = time * 0.15;
    float dispersion = 0.26 + 0.25 * k;
    float3 rgb = 0.0;
    for (int i = 0; i < 6; i++) {
        float spreadI = dispersion * (float(i) - 2.5) / 2.5;
        rgb += spectrum[i] * studio(n, aim + spreadI, drift + spreadI);
    }
    rgb /= spectrumSum;
    float lum = dot(rgb, float3(0.299, 0.587, 0.114));
    rgb = lum + (rgb - lum) * 2.7;

    float3 navy = float3(0.03, 0.04, 0.085);
    rgb = navy + (1.0 - navy) * clamp(rgb, 0.0, 1.0);
    rgb += float3(-0.03, 0.0, 0.07) * (lum * (1.0 - lum) * 4.0);
    rgb = clamp(rgb, 0.0, 1.0);
    // In dark mode the highlights roll off to 0.8 (the darks are left alone); in light
    // mode they stay full white, like the page around them.
    if (u.light < 0.5) { rgb -= 0.2 * rgb * rgb; }

    // The lens: full metal at the edge, gone a rim's width in. The boundary flows with
    // its own finer, faster folds, so the metal seems to melt into the glass. It grows in
    // and fades out with the lift.
    if (u.rim > 0.5) {
        float lift = smoothstep(0.0, 1.0, u.lift);
        float inside = -best;
        float width = clamp(min(nearestHalf.x, nearestHalf.y) * 0.6, 6.0, 20.0) * mix(0.4, 1.0, lift);
        float wobble = height(point / 16.0 + float2(3.1, 1.7), time * 1.4) * width * 0.3;
        float alpha = (1.0 - smoothstep(width * 0.2, width, inside + wobble)) * lift;
        return half4(half3(rgb * alpha), half(alpha));
    }
    return half4(half3(rgb), 1.0h);
}
