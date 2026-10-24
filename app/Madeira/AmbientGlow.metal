// AmbientGlow.metal — the library's ambient card light (AmbientGlow in Library.swift).
//
// A SwiftUI [[stitchable]] color shader on the glow layer: a soft knee on its brightest
// parts, so a very bright artwork (a neon green cover) throws light as strong as the rest
// instead of glaring, while dark and mid tones pass almost unchanged. `knee` is how much
// the brightest value comes down (0: off).

#include <metal_stdlib>
#include <SwiftUI/SwiftUI_Metal.h>
using namespace metal;

[[ stitchable ]] half4 ambientKnee(float2 position, half4 color, float knee) {
    if (color.a <= 0.0h || knee <= 0.0) { return color; }
    float3 rgb = float3(color.rgb) / float(color.a);
    rgb -= knee * rgb * rgb;
    return half4(half3(rgb * float(color.a)), color.a);
}
