// T1: does a converted SM6.6 64-bit InterlockedMax on a typed 2D UAV work?
// 16 x 16 threads fight over a 4 x 4 texture; each cell must end at the max
// of the 16 values aimed at it (high word decides, low word identifies).
RWTexture2D<uint64_t> T : register(u0);
[numthreads(16, 16, 1)]
void CSMain(uint3 id : SV_DispatchThreadID)
{
    uint hi = (id.x * 37u + id.y * 11u) & 255u;
    uint lo = id.y * 16u + id.x;
    InterlockedMax(T[uint2(id.x & 3u, id.y & 3u)], ((uint64_t)hi << 32) | lo);
}
