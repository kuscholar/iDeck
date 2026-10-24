// UE's distance-field atlas is a 3D texture written by ScatterUploadDistanceFieldAtlasCS
// through a UAV. This is the plainest form of that: write a known pattern into
// every voxel of a full-resource RWTexture3D and see whether it lands.
RWTexture3D<float> Dst : register(u0);
[numthreads(4,4,4)]
void CSMain(uint3 id : SV_DispatchThreadID) { Dst[id] = (float)(id.z + 1) / 8.0; }
