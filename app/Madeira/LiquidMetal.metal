// LiquidMetal.metal — a flowing liquid-chrome fill for SwiftUI views.
//
// A SwiftUI [[stitchable]] color shader (View.colorEffect): SwiftUI runs it inside its own
// render pass for just the pixels the view covers, so a small control costs no extra
// drawable, texture or composite. Everything is procedural:
//
//   shape    a rounded box (a capsule when the radius is half the height) as a signed
//            distance field, its edge rippling slowly like a liquid's rim; anti-aliased to
//            one pixel;
//   surface  domed like a drop of mercury, with a flowing height field from domain-warped
//            sines on top whose slope tilts the normal; near the edge a bevel tilts it
//            steeply outward, which draws the raised rim;
//   chrome   the normal looks up a procedural studio (two crossing light bands, soft with a
//            crisp edge: white highlights, silver falloff, navy shadows) at six wavelengths,
//            each shifted a little, so every highlight's edges split into rainbows (orange
//            and yellow on one side, cyan, blue and violet on the other), as in chromatic
//            dispersion; averaging the wavelengths washes colour out, so the chroma is pushed
//            back up where they disagree;
//   rim      a bright specular line right at the edge with the bevel's dark band inside it.
//
// All lengths are in points; `size` is the view's size, `time` seconds, `scale` the display
// scale (for the anti-aliasing width), `light` 1 in light mode, where the bright band takes
// the middle instead of the dark one. Output is premultiplied.

#include <metal_stdlib>
#include <SwiftUI/SwiftUI_Metal.h>
using namespace metal;

namespace liquidmetal {

// Signed distance to a rounded box of half-size b and corner radius r.
static float roundBox(float2 p, float2 b, float r) {
    float2 q = abs(p) - b + r;
    return length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - r;
}

// The shape's edge: the rounded box with a slow ripple running along it.
static float shape(float2 p, float2 halfSize, float radius, float t, float ripple) {
    float w = 0.55 * sin(p.x * 0.40 + t * 1.10)
            + 0.30 * sin(p.x * 0.72 - t * 0.80 + p.y * 0.25)
            + 0.15 * sin(p.y * 0.60 + t * 0.60 + p.x * 0.15);
    return roundBox(p, halfSize, radius) - ripple * w;
}

// Height of the liquid surface at q (in units of the shape's height): three rounds of
// domain warping over sines give slow, folding flow.
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

// Brightness of the studio the chrome reflects, for a surface normal (x, y): broad soft
// light bands, pushed to chrome contrast (white highlights, deep shadows). The shifts move
// the bands, which is how each wavelength sees them a little apart.
static float studio(float2 n, float shiftA, float shiftB) {
    float a = dot(n, float2(0.80, 0.60)) * 3.4 + shiftA;
    float b = dot(n, float2(-0.55, 0.83)) * 2.3 + 1.2 - shiftB * 0.5;
    float v = 0.50 + 0.42 * sin(a) + 0.22 * sin(b);
    // Chrome: a soft gradient with a crisp edge through it.
    return mix(smoothstep(-0.05, 1.0, v), smoothstep(0.48, 0.60, v), 0.5);
}

// Six wavelengths, red to violet; their sum per channel normalises white to white.
constant float3 spectrum[6] = {
    float3(0.95, 0.10, 0.25),
    float3(1.00, 0.45, 0.00),
    float3(0.85, 0.85, 0.00),
    float3(0.10, 0.90, 0.35),
    float3(0.05, 0.40, 1.00),
    float3(0.45, 0.05, 0.95),
};
constant float3 spectrumSum = float3(3.40, 2.75, 2.55);

} // namespace liquidmetal

[[ stitchable ]] half4 liquidMetal(float2 position, half4 color, float2 size, float time, float scale, float light) {
    using namespace liquidmetal;
    const float ripple = 0.32;
    const float2 halfSize = size * 0.5 - ripple - 0.5;
    const float radius = min(halfSize.x, halfSize.y);
    const float px = 1.0 / max(scale, 1.0);
    const float2 p = position - size * 0.5;

    // Coverage of the shape, one pixel of anti-aliasing.
    float d = shape(p, halfSize, radius, time, ripple);
    float alpha = clamp(0.5 - d / px, 0.0, 1.0);
    if (alpha <= 0.0) { return half4(0.0); }

    // Surface slope from the height field (central differences).
    const float unit = size.y;
    float2 q = p / unit * 1.4;
    const float e = 0.012;
    float hx = height(q + float2(e, 0.0), time) - height(q - float2(e, 0.0), time);
    float hy = height(q + float2(0.0, e), time) - height(q - float2(0.0, e), time);
    float2 n = -float2(hx, hy) / (2.0 * e) * 0.5;

    // Where the dark band falls depends on the surface's slope, which the folds keep
    // changing. Aim it at the middle line, under the label: read the main band's phase
    // there, at the centre and in this pixel's column, and shift the band so its darkest
    // part lies on the line, mostly following the column (so a fold under one end of the
    // label cannot lift the band off it) and partly the centre (so the folds still bend
    // it). A slow sway moves it about. The second band keeps its own drift.
    const float aimCentre = bandPhase(float2(0.0), time, e);
    const float aimColumn = bandPhase(float2(p.x, 0.0) / unit * 1.4, time, e);
    const float sway = 0.32 * sin(time * 0.19) + 0.18 * sin(time * 0.31 + 2.0);
    const float target = light > 0.5 ? 1.570796 : 4.712389;
    const float aim = target - mix(aimCentre, aimColumn, 0.6) + sway;

    // The shape is domed like a drop of mercury: the surface curves across it, so the
    // studio's bands sweep over it. The dome is flat in the middle and curves toward the
    // edge, like a capsule: the edges tilt as steeply as ever (bright, coloured rims) while
    // the face stays on the dark band.
    const float2 across = p / halfSize;
    n += float2(across.x * abs(across.x) * 0.35, across.y * abs(across.y) * 0.85);

    // The bevel: the surface falls away over the last few points to the edge, tilting the
    // normal outward, steepest at the very edge.
    const float h = 0.25;
    float2 outward = float2(roundBox(p + float2(h, 0.0), halfSize, radius) - roundBox(p - float2(h, 0.0), halfSize, radius),
                            roundBox(p + float2(0.0, h), halfSize, radius) - roundBox(p - float2(0.0, h), halfSize, radius));
    outward = normalize(outward + 1e-5);
    float inside = -d;
    float bevel = clamp(size.y * 0.12, 2.0, 6.0);
    float k = clamp(1.0 - inside / bevel, 0.0, 1.0);
    n += outward * (k * k * 1.7);

    // Chrome with dispersion: the studio at six wavelengths, each shifted a little further.
    float drift = time * 0.15;
    float dispersion = 0.26 + 0.25 * k;
    float3 rgb = 0.0;
    for (int i = 0; i < 6; i++) {
        float spreadI = dispersion * (float(i) - 2.5) / 2.5;
        rgb += spectrum[i] * studio(n, aim + spreadI, drift + spreadI);
    }
    rgb /= spectrumSum;
    // Averaging the wavelengths washes their colours out; push the chroma back up where
    // they disagree (the bands), leaving white and dark alone.
    float lum = dot(rgb, float3(0.299, 0.587, 0.114));
    rgb = lum + (rgb - lum) * 2.7;

    // Shadows go deep navy, the mid-tones slate blue.
    float3 navy = float3(0.03, 0.04, 0.085);
    rgb = navy + (1.0 - navy) * clamp(rgb, 0.0, 1.0);
    rgb += float3(-0.03, 0.0, 0.07) * (lum * (1.0 - lum) * 4.0);

    // The rim: a bright specular line right at the edge.
    float line = clamp(1.0 - inside / (2.2 * px + 0.5), 0.0, 1.0);
    rgb = mix(rgb, float3(1.0), line * 0.75);

    rgb = clamp(rgb, 0.0, 1.0);
    // In dark mode the highlights roll off to 0.8 (the darks are left alone); in light
    // mode they stay full white, like the page around them.
    if (light < 0.5) { rgb -= 0.2 * rgb * rgb; }
    return half4(half3(rgb * alpha), half(alpha));
}
