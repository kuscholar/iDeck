//  M1 canary fixture for the native D3D12 -> Metal track.
//
//  Deliberately the smallest shader that still proves the whole binding path:
//
//    * No vertex input. SV_VertexID generates a full-screen triangle, which the
//      design permits for the first native proof so that vertex fetch is not
//      being tested at the same time as the converter. The indexed cube at M4
//      proves the real vertex-buffer path.
//    * One root CBV at b0. Metal shader converter places a root argument as a
//      64-bit GPU address in the top-level argument buffer, so a correct run
//      requires the argument buffer to be laid out, bound and read correctly.
//      Getting any of that wrong yields a wrong colour rather than a plausible
//      one, which is the property the canary needs.
//
//  The pixel shader returns the constant buffer contents unmodified so the
//  readback comparison is exact and independent of rasterisation rules.

struct CanaryParams
{
    float4 colour;
};

ConstantBuffer<CanaryParams> params : register(b0, space0);

#define CanaryRootSig "RootFlags(0)," \
                      "CBV(b0, space=0)"

struct VertexOut
{
    float4 position : SV_Position;
};

[RootSignature(CanaryRootSig)]
VertexOut MainVS(uint vertexID : SV_VertexID)
{
    // Oversized triangle covering the viewport: (0,0) (2,0) (0,2) in UV, mapped
    // to clip space. Three vertices, no buffers, no input layout.
    float2 uv = float2((vertexID << 1) & 2, vertexID & 2);
    VertexOut output;
    output.position = float4(uv * float2(2.0f, -2.0f) + float2(-1.0f, 1.0f), 0.0f, 1.0f);
    return output;
}

[RootSignature(CanaryRootSig)]
float4 MainPS(VertexOut input) : SV_Target
{
    return params.colour;
}
