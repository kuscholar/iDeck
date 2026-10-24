/* ml1141: decode one block-compressed capture file with the Mac's GPU.
 *
 *   bc-decode <in.raw> <width> <height> <metal pixel format> <out.f32>
 *
 * The input is what the runtime's capture writes for a BC texture: whole 4x4
 * blocks, rows of ceil(width/4) blocks. The output is width*height float4
 * (RGBA, 16 bytes per pixel), read back through a compute kernel, so every BC
 * format Metal supports decodes the same way the GPU samples it. sRGB formats
 * are uploaded as their linear twin: the values come out as stored.
 * capture-to-png.py builds and calls this; it is not meant to be run by hand. */
#import <Metal/Metal.h>
#import <Foundation/Foundation.h>

static unsigned block_bytes(MTLPixelFormat pf) {
    switch (pf) {
    case MTLPixelFormatBC1_RGBA: case MTLPixelFormatBC1_RGBA_sRGB:
    case MTLPixelFormatBC4_RUnorm: case MTLPixelFormatBC4_RSnorm: return 8;
    default: return 16;
    }
}
static MTLPixelFormat linear_twin(MTLPixelFormat pf) {
    switch (pf) {
    case MTLPixelFormatBC1_RGBA_sRGB: return MTLPixelFormatBC1_RGBA;
    case MTLPixelFormatBC2_RGBA_sRGB: return MTLPixelFormatBC2_RGBA;
    case MTLPixelFormatBC3_RGBA_sRGB: return MTLPixelFormatBC3_RGBA;
    case MTLPixelFormatBC7_RGBAUnorm_sRGB: return MTLPixelFormatBC7_RGBAUnorm;
    default: return pf;
    }
}

int main(int argc, char **argv) { @autoreleasepool {
    if (argc != 6) { fprintf(stderr, "usage: bc-decode in.raw w h pf out.f32\n"); return 2; }
    unsigned w = (unsigned)atoi(argv[2]), h = (unsigned)atoi(argv[3]);
    MTLPixelFormat pf = linear_twin((MTLPixelFormat)atoi(argv[4]));
    NSData *raw = [NSData dataWithContentsOfFile:[NSString stringWithUTF8String:argv[1]]];
    unsigned bw = (w + 3) / 4, bh = (h + 3) / 4, bpr = bw * block_bytes(pf);
    if (!raw || raw.length < (NSUInteger)bpr * bh) { fprintf(stderr, "input too short: %lu < %u\n", (unsigned long)raw.length, bpr * bh); return 1; }
    id<MTLDevice> dev = MTLCreateSystemDefaultDevice();
    MTLTextureDescriptor *td = [MTLTextureDescriptor texture2DDescriptorWithPixelFormat:pf width:w height:h mipmapped:NO];
    td.usage = MTLTextureUsageShaderRead; td.storageMode = MTLStorageModeShared;
    id<MTLTexture> t = [dev newTextureWithDescriptor:td];
    if (!t) { fprintf(stderr, "pixel format %u refused\n", (unsigned)pf); return 1; }
    [t replaceRegion:MTLRegionMake2D(0, 0, w, h) mipmapLevel:0 withBytes:raw.bytes bytesPerRow:bpr];
    NSString *src = @"#include <metal_stdlib>\nusing namespace metal;\n"
        "kernel void k(texture2d<float> t [[texture(0)]], device float4 *o [[buffer(0)]], constant uint2 &sz [[buffer(1)]],"
        " uint2 id [[thread_position_in_grid]]) { if (id.x < sz.x && id.y < sz.y) o[id.y * sz.x + id.x] = t.read(id); }";
    NSError *e = nil;
    id<MTLLibrary> L = [dev newLibraryWithSource:src options:nil error:&e];
    id<MTLComputePipelineState> p = L ? [dev newComputePipelineStateWithFunction:[L newFunctionWithName:@"k"] error:&e] : nil;
    if (!p) { fprintf(stderr, "kernel: %s\n", e.localizedDescription.UTF8String); return 1; }
    id<MTLBuffer> out = [dev newBufferWithLength:(NSUInteger)w * h * 16 options:MTLResourceStorageModeShared];
    uint32_t sz[2] = { w, h };
    id<MTLCommandQueue> q = [dev newCommandQueue];
    id<MTLCommandBuffer> cb = [q commandBuffer];
    id<MTLComputeCommandEncoder> enc = [cb computeCommandEncoder];
    [enc setComputePipelineState:p]; [enc setTexture:t atIndex:0]; [enc setBuffer:out offset:0 atIndex:0]; [enc setBytes:sz length:sizeof sz atIndex:1];
    [enc dispatchThreads:MTLSizeMake(w, h, 1) threadsPerThreadgroup:MTLSizeMake(8, 8, 1)];
    [enc endEncoding]; [cb commit]; [cb waitUntilCompleted];
    if (cb.status != MTLCommandBufferStatusCompleted) { fprintf(stderr, "GPU error\n"); return 1; }
    [[NSData dataWithBytesNoCopy:out.contents length:out.length freeWhenDone:NO] writeToFile:[NSString stringWithUTF8String:argv[5]] atomically:NO];
    return 0;
} }
