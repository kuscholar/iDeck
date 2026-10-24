//  Textured quad: the first shader here that needs a descriptor table.
//
//  The root signature deliberately mixes all three binding kinds -- a root CBV,
//  an SRV table and a sampler table -- because the whole question this shader
//  exists to answer is what the runtime must write into the top-level argument
//  buffer for a TABLE, which is not the same as for a root descriptor.

struct Params
{
    float4 tint;
};

ConstantBuffer<Params> params : register(b0, space0);
Texture2D<float4>      tex    : register(t0, space0);
SamplerState           smp    : register(s0, space0);

#define TexRootSig "RootFlags(0)," \
                   "CBV(b0, space=0)," \
                   "DescriptorTable(SRV(t0, space=0))," \
                   "DescriptorTable(Sampler(s0, space=0))"

struct VertexOut
{
    float4 position : SV_Position;
    float2 uv       : TEXCOORD0;
};

// A full-target triangle from the vertex id alone, so no vertex buffer and no
// attribute-fetch ABI is involved in answering the binding question.
[RootSignature(TexRootSig)]
VertexOut MainVS(uint vertexID : SV_VertexID)
{
    float2 p = float2((vertexID << 1) & 2, vertexID & 2);
    VertexOut output;
    output.uv = p;
    output.position = float4(p * 2.0f - 1.0f, 0.0f, 1.0f);
    return output;
}

[RootSignature(TexRootSig)]
float4 MainPS(VertexOut input) : SV_Target
{
    return tex.Sample(smp, input.uv) * params.tint;
}
