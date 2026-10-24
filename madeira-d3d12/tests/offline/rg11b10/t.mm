/* Lumen's card DirectLighting / FinalLighting atlases are RG11B10Float and come
 * back 100% empty, while the RGBA8 albedo/normal atlases beside them are fine.
 * LumenCardBatchDirectLighting writes them through a UAV, so: can a Metal
 * compute shader write RG11B10Float at all on this GPU, and does a texture
 * even accept MTLTextureUsageShaderWrite in that format? */
#import <Metal/Metal.h>
#import <Foundation/Foundation.h>

static const char *fmtname(MTLPixelFormat f) {
    switch (f) {
    case MTLPixelFormatRG11B10Float: return "RG11B10Float";
    case MTLPixelFormatRGB9E5Float:  return "RGB9E5Float";
    case MTLPixelFormatRGBA16Float:  return "RGBA16Float";
    case MTLPixelFormatRGBA8Unorm:   return "RGBA8Unorm";
    case MTLPixelFormatR32Uint:      return "R32Uint";
    default: return "?";
    }
}

int main(void) { @autoreleasepool {
    setbuf(stdout, NULL);
    id<MTLDevice> dev = MTLCreateSystemDefaultDevice();
    id<MTLCommandQueue> q = [dev newCommandQueue];
    printf("device: %s\n\n", dev.name.UTF8String);
    NSError *e = nil;
    id<MTLLibrary> lib = [dev newLibraryWithSource:
        @"#include <metal_stdlib>\nusing namespace metal;\n"
         "kernel void w(texture2d<float, access::write> dst [[texture(0)]], uint2 g [[thread_position_in_grid]]) {\n"
         "  dst.write(float4(0.25, 0.5, 0.75, 1.0), g);\n}\n" options:nil error:&e];
    if (!lib) { printf("MSL: %s\n", e.localizedDescription.UTF8String); return 1; }
    id<MTLComputePipelineState> pso = [dev newComputePipelineStateWithFunction:[lib newFunctionWithName:@"w"] error:&e];
    if (!pso) { printf("pso: %s\n", e.localizedDescription.UTF8String); return 1; }

    MTLPixelFormat fmts[] = { MTLPixelFormatRGBA8Unorm, MTLPixelFormatRGBA16Float,
                              MTLPixelFormatRG11B10Float, MTLPixelFormatRGB9E5Float };
    for (unsigned i = 0; i < sizeof fmts / sizeof *fmts; i++) {
        MTLPixelFormat f = fmts[i];
        MTLTextureDescriptor *td = [MTLTextureDescriptor texture2DDescriptorWithPixelFormat:f width:8 height:8 mipmapped:NO];
        td.usage = MTLTextureUsageShaderWrite | MTLTextureUsageShaderRead;
        td.storageMode = MTLStorageModeShared;
        id<MTLTexture> t = [dev newTextureWithDescriptor:td];
        if (!t) { printf("%-14s texture with ShaderWrite: REFUSED\n", fmtname(f)); continue; }
        id<MTLCommandBuffer> cb = [q commandBuffer];
        id<MTLComputeCommandEncoder> enc = [cb computeCommandEncoder];
        [enc setComputePipelineState:pso]; [enc setTexture:t atIndex:0];
        [enc dispatchThreads:MTLSizeMake(8,8,1) threadsPerThreadgroup:MTLSizeMake(8,8,1)];
        [enc endEncoding]; [cb commit]; [cb waitUntilCompleted];
        uint32_t px[64] = {0};
        unsigned bpp = (f == MTLPixelFormatRGBA16Float) ? 8 : 4;
        [t getBytes:px bytesPerRow:8*bpp fromRegion:MTLRegionMake2D(0,0,8,8) mipmapLevel:0];
        printf("%-14s ShaderWrite OK, status=%ld, first word=0x%08x  %s\n",
               fmtname(f), (long)cb.status, px[0], px[0] ? "WROTE" : "*** NOTHING WRITTEN ***");
    }
    return 0; } }
