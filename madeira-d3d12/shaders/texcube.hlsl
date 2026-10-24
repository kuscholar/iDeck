//  The visible cube, textured.
//
//  Same tumble, same depth behaviour and same constant-buffer geometry as the
//  untextured cube; the additions are a UV per vertex and a sampled texture
//  reached through descriptor tables. Kept as its own file rather than an edit
//  to cube.hlsl so the offscreen cube check, which binds no texture, keeps
//  testing exactly what it tested before.
//
//  UVs are DERIVED from the vertex id rather than shipped in the constant
//  buffer. The shared geometry lists each face's four corners in the same order
//  -- bottom-left, bottom-right, top-right, top-left in that face's own frame --
//  so the mapping is a property of the geometry, and deriving it means the two
//  cannot disagree.

struct CubeParams
{
    float4 rot;           // x,y = cos,sin of yaw   z,w = cos,sin of pitch
    float4 positions[24];
    float4 colours[24];
};

ConstantBuffer<CubeParams> params : register(b0, space0);
Texture2D<float4>          tex    : register(t0, space0);
SamplerState               smp    : register(s0, space0);

#define TexCubeRootSig "RootFlags(0)," \
                       "CBV(b0, space=0)," \
                       "DescriptorTable(SRV(t0, space=0))," \
                       "DescriptorTable(Sampler(s0, space=0))"

struct VertexOut
{
    float4 position : SV_Position;
    float4 colour   : COLOR0;
    float2 uv       : TEXCOORD0;
    float3 normal   : NORMAL0;
};

[RootSignature(TexCubeRootSig)]
VertexOut MainVS(uint vertexID : SV_VertexID)
{
    float3 p = params.positions[vertexID].xyz;

    // Yaw about Y.
    float3 a;
    a.x = p.x * params.rot.x - p.z * params.rot.y;
    a.z = p.x * params.rot.y + p.z * params.rot.x;
    a.y = p.y;

    // Pitch about X.
    float3 b;
    b.x = a.x;
    b.y = a.y * params.rot.z - a.z * params.rot.w;
    b.z = a.y * params.rot.w + a.z * params.rot.z;

    uint face = vertexID / 4;
    uint corner = vertexID & 3;

    // V runs downward, as texture coordinates do, so the texture sits upright
    // on every face rather than mirrored on half of them.
    float2 uv;
    uv.x = (corner == 1 || corner == 2) ? 1.0f : 0.0f;
    uv.y = (corner == 0 || corner == 1) ? 1.0f : 0.0f;

    float3 n = float3(0, 0, 0);
    if (face == 0)      n = float3( 0,  0,  1);
    else if (face == 1) n = float3( 0,  0, -1);
    else if (face == 2) n = float3( 1,  0,  0);
    else if (face == 3) n = float3(-1,  0,  0);
    else if (face == 4) n = float3( 0,  1,  0);
    else                n = float3( 0, -1,  0);

    float3 na;
    na.x = n.x * params.rot.x - n.z * params.rot.y;
    na.z = n.x * params.rot.y + n.z * params.rot.x;
    na.y = n.y;
    float3 nb;
    nb.x = na.x;
    nb.y = na.y * params.rot.z - na.z * params.rot.w;
    nb.z = na.y * params.rot.w + na.z * params.rot.z;

    VertexOut output;
    // Near plane at 0, far at 1; +Z maps to smaller depth, so the face towards
    // the viewer wins the depth test.
    output.position = float4(b.x, b.y, 0.5f - b.z * 0.5f, 1.0f);
    output.colour   = params.colours[vertexID];
    output.uv       = uv;
    output.normal   = nb;
    return output;
}

[RootSignature(TexCubeRootSig)]
float4 MainPS(VertexOut input) : SV_Target
{
    float4 texel = tex.Sample(smp, input.uv);

    // The per-face tint stays, so which face is which is still readable while
    // the texture shows how it is oriented and whether it is stretched.
    float3 n = normalize(input.normal);
    float3 l = normalize(float3(0.4f, 0.7f, 1.0f));
    float shade = 0.35f + 0.65f * saturate(dot(n, l));

    // Blended toward the face tint rather than multiplied by it. Multiplying
    // killed the red marker band on the blue and green faces, because red does
    // not survive those tints -- the band was still in the right place but had
    // lost the colour that made it a cue. Blending keeps every marker readable
    // on all six faces while the tint still says which face is which.
    float3 tinted = lerp(texel.rgb, input.colour.rgb, 0.45f);
    return float4(tinted * shade, 1.0f);
}
