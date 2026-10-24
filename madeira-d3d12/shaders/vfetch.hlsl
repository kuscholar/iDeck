//  Vertex-path differential test shaders (ml906).
//
//  One root signature for every case, laid out so that a wrong binding shows
//  as a wrong VALUE rather than a plausible one:
//    param 0  32-bit constant (b1)     -- deliberately NOT the CBV, so the CBV
//                                         is root parameter 1
//    param 1  root CBV b0              -- transform + colour + mode
//    param 2  SRV table t0..t1         -- typed Buffer<float> / Buffer<uint>
//    param 3  UAV table u0             -- compute probe output
//
//    param 4  root UAV u1              -- ml907: compute probe output, no table
//
//  Every vertex shader emits a flat colour the pixel shader returns unchanged,
//  so the readback reports exactly what the vertex stage consumed:
//    mode 0: the CBV colour
//    mode 1: the ID the vertex stage read (low byte in R, next byte in G)

struct Params
{
    float4x4 xform;
    float4   colour;
    uint4    misc;      // .x = mode
};

ConstantBuffer<Params> P     : register(b0);
Buffer<float>          PosBuf : register(t0);
Buffer<uint>           IdBuf  : register(t1);
RWStructuredBuffer<float4> Probe : register(u0);
RWStructuredBuffer<float4> Probe2 : register(u1);   // ml907: root UAV (param 4)

#define RS "RootFlags(ALLOW_INPUT_ASSEMBLER_INPUT_LAYOUT)," \
           "RootConstants(num32BitConstants=1, b1)," \
           "CBV(b0)," \
           "DescriptorTable(SRV(t0, numDescriptors=2))," \
           "DescriptorTable(UAV(u0, numDescriptors=1))," \
           "UAV(u1)"

struct VSOut
{
    float4 pos : SV_Position;
    nointerpolation float4 col : COLOR0;
};

static float4 colour_for(uint id)
{
    if (P.misc.x == 1)
        return float4((id & 255) / 255.0, ((id >> 8) & 255) / 255.0, 0.0, 1.0);
    return P.colour;
}

// A: positions from a vertex stream, ID from a constant-step (stride 0) stream
[RootSignature(RS)]
VSOut VSStream(float3 p : POSITION, uint id : INSTID)
{
    VSOut o;
    o.pos = mul(P.xform, float4(p, 1.0));
    o.col = colour_for(id);
    return o;
}

// B: positions and ID fetched by SV_VertexID through typed buffer SRVs
[RootSignature(RS)]
VSOut VSFetch(uint vid : SV_VertexID)
{
    float3 p = float3(PosBuf[vid * 3 + 0], PosBuf[vid * 3 + 1], PosBuf[vid * 3 + 2]);
    uint id = IdBuf[vid];
    VSOut o;
    o.pos = mul(P.xform, float4(p, 1.0));
    o.col = colour_for(id);
    return o;
}

[RootSignature(RS)]
float4 PSMain(VSOut i) : SV_Target
{
    return i.col;
}

// Probe: what a shader sees through the same bindings, written out verbatim.
[RootSignature(RS)]
[numthreads(1, 1, 1)]
void CSProbe(uint3 tid : SV_DispatchThreadID)
{
    Probe[0] = P.colour;
    Probe[1] = P.xform[0];
    Probe[2] = float4(PosBuf[0], PosBuf[1], PosBuf[2], PosBuf[3]);
    Probe[3] = float4(asfloat(IdBuf[0]), asfloat(IdBuf[1]), asfloat(IdBuf[2]), asfloat(IdBuf[3]));
}

// ml907: write-only probe through the TABLE UAV (no reads at all). If this
// fails the UAV write or the readback path is broken, not the bindings read.
[RootSignature(RS)]
[numthreads(1, 1, 1)]
void CSWrite(uint3 tid : SV_DispatchThreadID)
{
    Probe[0] = float4(1.0, 2.0, 3.0, 4.0);
    Probe[1] = float4(5.0, 6.0, 7.0, 8.0);
}

// ml907: the same reads written through the ROOT UAV (param 4) instead of the
// table; row 2 is a constant so a dead write and a dead read look different.
[RootSignature(RS)]
[numthreads(1, 1, 1)]
void CSRoot(uint3 tid : SV_DispatchThreadID)
{
    Probe2[0] = P.colour;
    Probe2[1] = float4(PosBuf[0], PosBuf[1], PosBuf[2], PosBuf[3]);
    Probe2[2] = float4(1.0, 2.0, 3.0, 4.0);
    Probe2[3] = P.xform[0];
}

// ml914: the instance id the vertex stage sees (D3D: SV_InstanceID excludes
// StartInstanceLocation). Colour = (id, 0, 0).
[RootSignature(RS)]
VSOut VSInst(float3 p : POSITION, uint iid : SV_InstanceID)
{
    VSOut o;
    o.pos = mul(P.xform, float4(p, 1.0));
    o.col = float4(iid / 255.0, 0.0, 0.0, 1.0);
    return o;
}
