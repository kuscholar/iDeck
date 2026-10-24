//  Rotating indexed cube for the visible D3D12 frame.
//
//  24 vertices, four per face, so every face carries a flat distinct colour and
//  the shape reads as a cube rather than a smear of interpolated corners. Drawn
//  with a REAL index buffer through DrawIndexed; positions and colours come from
//  the constant buffer selected by SV_VertexID, which for an indexed draw is the
//  value fetched from the index buffer. That keeps the root signature to a single
//  root CBV and defers the separate vertex-attribute fetch ABI.
//
//  The rotation arrives as two cosine/sine pairs rather than a matrix. A
//  float4x4 in a constant buffer invites row- versus column-major confusion,
//  which costs device runs to diagnose while looking like a rendering fault. Two
//  pairs of scalars cannot be transposed. Yaw and pitch run at different rates,
//  so the cube tumbles and every face comes into view instead of two of them
//  staying permanently edge-on.

struct CubeParams
{
    float4 rot;           // x,y = cos,sin of yaw   z,w = cos,sin of pitch
    float4 positions[24];
    float4 colours[24];
};

ConstantBuffer<CubeParams> params : register(b0, space0);

#define CubeRootSig "RootFlags(0)," \
                    "CBV(b0, space=0)"

struct VertexOut
{
    float4 position : SV_Position;
    float4 colour   : COLOR0;
    float3 normal   : NORMAL0;
};

[RootSignature(CubeRootSig)]
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

    // Face normal, derived from which face this vertex belongs to rather than
    // supplied. Four consecutive vertices form one face, in the same order the
    // shared geometry header lists them.
    uint face = vertexID / 4;
    float3 n = float3(0, 0, 0);
    if (face == 0)      n = float3( 0,  0,  1);
    else if (face == 1) n = float3( 0,  0, -1);
    else if (face == 2) n = float3( 0,  1,  0);
    else if (face == 3) n = float3( 0, -1,  0);
    else if (face == 4) n = float3( 1,  0,  0);
    else                n = float3(-1,  0,  0);

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
    output.normal   = nb;
    return output;
}

[RootSignature(CubeRootSig)]
float4 MainPS(VertexOut input) : SV_Target
{
    // Real per-pixel work, not a pass-through. Faces turning away from the
    // fixed light darken as the cube tumbles, which is visible on screen and
    // impossible to produce from any previously converted shader: this maths
    // exists only in bytecode that has to be compiled at run time.
    float3 n = normalize(input.normal);
    float3 l = normalize(float3(0.4f, 0.7f, 1.0f));
    float lambert = saturate(dot(n, l));
    float shade = 0.35f + 0.65f * lambert;
    return float4(input.colour.rgb * shade, 1.0f);
}
