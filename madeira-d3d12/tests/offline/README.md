# Offline Metal / converter tests

Questions about what Metal or the Metal Shader Converter will actually do,
answered on the M4 Max without spending a device run. Every one of these was
written to kill a specific hypothesis about the D3D12 runtime, and every one
of them did.

Build each one standalone. The converter SDK is not in git; extract it from
Apple's installer package first:

```sh
pkgutil --expand-full "research/GPTK/Metal Shader Converter 4.0 beta 2.pkg" /tmp/msc
INC=/tmp/msc/MetalShaderConverter.pkg/Payload/usr/local/include
LIB=/tmp/msc/MetalShaderConverter.pkg/Payload/usr/local/lib
```

`clang++`, not `clang` — these are .mm files and need the C++ runtime for the
ObjC exception personality.

| test | needs converter | question | answer |
| --- | --- | --- | --- |
| `rg11b10/` | no | can a compute shader write `RG11B10Float` (and `RGB9E5Float`) through a UAV? | yes, all four formats tested write correctly |
| `attachless/` | no | does a render pass with NO attachments whose area exceeds the bound resource page-fault? | no — a 100 MB overrun into a 16 KB buffer completes; out-of-bounds fragment writes do not fault |
| `tex3d/` | yes | does a UAV write into a 3D texture land, through MSC with `ForceTextureArray` + descriptor table? | yes, all 8 depth slices exact |
| `atomic64/` | yes | (T1) does a converted SM6.6 64-bit `InterlockedMax` on `RWTexture2D<uint64_t>` work on an RG32Uint texture? (T3) does `src/unix/madeira_ags.cpp` turn AMD AGS `AtomicMaxU64` (magic UAV, `cs_6_0`) into the same thing? | T1 yes, 16/16 contested cells exact; T3 yes after the rewrite (refused before it). The converter rejects any shader that READS a 64-bit texture atomic's result |

Build and run:

```sh
# no converter needed
clang++ -O1 -fobjc-arc -framework Metal -framework Foundation -o t rg11b10/t.mm && ./t
clang++ -O1 -fobjc-arc -framework Metal -framework Foundation -o al attachless/al.mm && ./al

# converter needed; compile the HLSL with the repo's dxc under wine first
cd tex3d
wine ../../../../toolchains/dxc-win/bin/x64/dxc.exe -T cs_6_0 -E CSMain -Fo CSMain.dxil v.hlsl
clang++ -O1 -fobjc-arc -I"$INC" -L"$LIB" -lmetalirconverter \
        -framework Metal -framework Foundation -o t t.mm
DYLD_LIBRARY_PATH="$LIB" ./t
```

⚠️ Print to stderr, or `setbuf(stdout, NULL)`. Several of these abort during
teardown *after* producing their result, and a block-buffered stdout throws the
answer away — which cost a confusing round trip.

## Lost to a /tmp wipe, worth recreating if the questions come back

- **`slices/`** — does a Metal texture view over ONE array slice redirect a
  converted shader's writes and reads to that slice? Built the view the way
  `mad_texture_view_id` does for `FirstArraySlice=3, ArraySize=1`. Result 3/3:
  `RWTexture2D` through a slice-3 view, `RWTexture2DArray` over the whole
  array, and `Texture2D` reading through a slice-3 view all addressed the
  right slice. This is load-bearing because ml932 made every 2D texture an
  array.
- **`atomic64/`** — are the 64-bit atomics Nanite gates on real? `cs_6_6`,
  `InterlockedMax` on `RWTexture2D<uint64_t>` and `InterlockedMax64` on a
  `RWByteAddressBuffer`. Both converted, built pipelines, and returned the
  correct maximum with 64 threads contending: `0x80000abcd`. **M4 Max
  (Apple9) only** — untested on the A15 and on the paravirtual device, which
  matters if rendering ever moves back on-device.

`atomic64/` also needs the host LLVM 15 build (`dxmt/toolchains/llvm-host-build`)
for the rewrite driver, and AMD's `ags_shader_intrinsics_dx12.hlsl` (GPUOpen AGS_SDK,
`ags_lib/hlsl/`, MIT) next to `ags.hlsl` for T3 — it is not kept in git:

```sh
cd atomic64
T=../../../../dxmt/toolchains; L=$($T/llvm-host-build/bin/llvm-config --libs bitreader bitwriter core)
clang++ -std=c++17 -O1 -fno-rtti -I$T/llvm-project/llvm/include -I$T/llvm-host-build/include \
        ../../../src/unix/madeira_ags.cpp rw_main.cpp -L$T/llvm-host-build/lib $L -o rw
clang++ -O1 -fobjc-arc -I"$INC" -L"$LIB" -lmetalirconverter -framework Metal -framework Foundation -o t t.mm
wine ../../../../toolchains/dxc-win/bin/x64/dxc.exe -T cs_6_6 -E CSMain -Fo CSMain.dxil v.hlsl
DYLD_LIBRARY_PATH="$LIB" ./t CSMain.dxil                      # T1
wine ../../../../toolchains/dxc-win/bin/x64/dxc.exe -T cs_6_0 -E CSMain -Fo ags.dxil ags.hlsl
./rw ags.dxil ags_rw.dxil && DYLD_LIBRARY_PATH="$LIB" ./t ags_rw.dxil   # T3
```

`conv.mm` converts any container against a permissive root signature (conversion only);
`llwrap.cpp` assembles edited LLVM 15 IR text back into a container, and `bcdis.cpp`
prints a container's bitcode as text -- the pair that found the result-read rule.
