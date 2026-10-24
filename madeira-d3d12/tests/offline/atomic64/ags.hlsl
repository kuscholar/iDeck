// T3: the same contest as v.hlsl, written the pre-SM6.6 way through AMD's AGS
// intrinsics (ags_shader_intrinsics_dx12.hlsl from AMD's AGS_SDK, not in git).
// Compiled at cs_6_0 it produces the magic-UAV sequence; madeira_ags.cpp must
// turn it into a real 64-bit max for the result to match.
#include "ags_shader_intrinsics_dx12.hlsl"
RWTexture2D<uint2> T : register(u0);
[numthreads(16, 16, 1)]
void CSMain(uint3 id : SV_DispatchThreadID)
{
    uint hi = (id.x * 37u + id.y * 11u) & 255u;
    uint lo = id.y * 16u + id.x;
    AmdExtD3DShaderIntrinsics_AtomicMaxU64(T, uint2(id.x & 3u, id.y & 3u), uint2(lo, hi));
}
