// Nanite shades materials in COMPUTE, where the hardware cannot pick a mip by
// itself, so every material texture fetch arrives as SampleGrad (analytic
// derivatives) or as an implicit Sample relying on SM6.6 compute derivatives.
// Mip k of the bound texture holds R = k/8, so R*8 is the mip actually read.
Texture2D<float4> Tex : register(t0);
SamplerState Smp : register(s0);
RWStructuredBuffer<float4> Out : register(u0);

[numthreads(64, 1, 1)]
void CSMain(uint gi : SV_GroupIndex)
{
    float2 base = float2(0.3, 0.3);
    float4 r = 0;
    // Lanes 0-6: SampleGrad with an isotropic gradient of 2^k texels -> mip k.
    // Lane 7: anisotropic 4:1 gradient (major axis 4 texels).
    if (gi < 7) {
        float g = exp2((float)gi) / 64.0;
        r = Tex.SampleGrad(Smp, base, float2(g, 0), float2(0, g));
    } else if (gi == 7) {
        r = Tex.SampleGrad(Smp, base, float2(4.0 / 64.0, 0), float2(0, 1.0 / 64.0));
    } else if (gi < 15) {
        r = Tex.SampleLevel(Smp, base, (float)(gi - 8));   // lanes 8-14: explicit mip 0-6
    }
    // Every lane: implicit Sample through SM6.6 compute quad derivatives. Quad
    // q = gi/4 steps its UV by 2^(q%6) texels in x (lane bit 0) and y (bit 1).
    uint q = gi >> 2;
    float g2 = exp2((float)(q % 6)) / 64.0;
    float2 uv = base + float2(gi & 1, (gi >> 1) & 1) * g2;
    float4 imp = Tex.Sample(Smp, uv);
    float2 dx = ddx(uv), dy = ddy(uv);
    if (gi >= 16) r = float4(imp.x, dx.x * 64.0, dy.y * 64.0, (float)(q % 6));
    Out[gi] = r;
}
