//  Argument-buffer LAYOUT fixture.
//
//  canary.hlsl proves one root CBV at offset 0, which is the trivial case and
//  says nothing about how the converter packs a real root signature. This one
//  deliberately puts root constants ahead of a root CBV so that the layout rule
//  in the user manual is exercised rather than assumed:
//
//    "calculate the offsets of each resource in the top-level Argument Buffer by
//     taking the size of the root constants in bytes (if present), and adding
//     the resource index multiplied by sizeof(uint64_t)"
//
//  So: four 32-bit root constants occupy bytes 0..15, and the root CBV's 64-bit
//  GPU address lands at byte 16. Both contributions appear in the output colour,
//  so reading either at the wrong offset changes the pixel.

struct LayoutConstants
{
    uint4 channels;     // four 32-bit root constants
};

struct LayoutParams
{
    float4 colour;      // separate buffer behind a root CBV
};

ConstantBuffer<LayoutConstants> rootConstants : register(b0, space0);
ConstantBuffer<LayoutParams>    cbv           : register(b1, space0);

#define LayoutRootSig "RootFlags(0)," \
                      "RootConstants(num32BitConstants=4, b0, space=0)," \
                      "CBV(b1, space=0)"

struct VertexOut
{
    float4 position : SV_Position;
};

[RootSignature(LayoutRootSig)]
VertexOut MainVS(uint vertexID : SV_VertexID)
{
    float2 uv = float2((vertexID << 1) & 2, vertexID & 2);
    VertexOut output;
    output.position = float4(uv * float2(2.0f, -2.0f) + float2(-1.0f, 1.0f), 0.0f, 1.0f);
    return output;
}

[RootSignature(LayoutRootSig)]
float4 MainPS(VertexOut input) : SV_Target
{
    // Red and green come from the root constants, blue from the root CBV.
    // A layout mistake on either side is visible and unambiguous.
    return float4(rootConstants.channels.x / 255.0f,
                  rootConstants.channels.y / 255.0f,
                  cbv.colour.z,
                  1.0f);
}
