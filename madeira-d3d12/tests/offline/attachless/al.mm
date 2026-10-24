/* ml934 follow-up: an attachment-less render pass takes its rasterisation area
 * from renderTargetWidth/Height, which the D3D12 runtime now derives from the
 * viewport. Nanite's HW rasteriser and UE's cull passes write through UAVs at
 * the rasterised pixel coordinate. If that area is bigger than the resource
 * being written, does the GPU page-fault (the kIOGPUCommandBufferCallbackError-
 * PageFault we saw), or are the out-of-range writes discarded?
 *
 * Textures and buffers are asked separately: Metal discards out-of-bounds
 * TEXTURE writes, but a BUFFER index computed from the pixel is a raw address.
 */
#import <Metal/Metal.h>
#import <Foundation/Foundation.h>

static NSString *SRC = @"#include <metal_stdlib>\n"
"using namespace metal;\n"
"struct VOut { float4 pos [[position]]; };\n"
"vertex VOut vmain(uint vid [[vertex_id]]) {\n"
"  float2 p[3] = { float2(-1,-3), float2(-1,1), float2(3,1) };\n"   /* covers the whole area */
"  VOut o; o.pos = float4(p[vid], 0, 1); return o;\n"
"}\n"
"fragment void ftex(VOut in [[stage_in]], texture2d<uint, access::write> dst [[texture(0)]]) {\n"
"  dst.write(uint4(1), uint2(in.pos.xy));\n"
"}\n"
"fragment void fbuf(VOut in [[stage_in]], device uint *dst [[buffer(0)]], constant uint &w [[buffer(1)]]) {\n"
"  uint2 c = uint2(in.pos.xy); dst[c.y * w + c.x] = 1;\n"
"}\n";

static id<MTLLibrary> lib;
static id<MTLDevice> dev;
static id<MTLCommandQueue> q;

static id<MTLRenderPipelineState> pso_for(const char *frag) {
    MTLRenderPipelineDescriptor *pd = [MTLRenderPipelineDescriptor new];
    pd.vertexFunction = [lib newFunctionWithName:@"vmain"];
    pd.fragmentFunction = [lib newFunctionWithName:[NSString stringWithUTF8String:frag]];
    pd.rasterSampleCount = 1;
    /* no colour attachments at all -- the whole point */
    NSError *e = nil;
    id<MTLRenderPipelineState> p = [dev newRenderPipelineStateWithDescriptor:pd error:&e];
    if (!p) { printf("   pipeline (%s) REJECTED: %s\n", frag, e.localizedDescription.UTF8String); }
    return p;
}

static void run(const char *label, NSUInteger areaW, NSUInteger areaH,
                NSUInteger resW, NSUInteger resH, int use_buffer) {
    @autoreleasepool {
        id<MTLRenderPipelineState> pso = pso_for(use_buffer ? "fbuf" : "ftex");
        if (!pso) return;
        id<MTLTexture> tex = nil; id<MTLBuffer> buf = nil;
        if (use_buffer) {
            buf = [dev newBufferWithLength:resW * resH * 4 options:MTLResourceStorageModeShared];
            memset(buf.contents, 0, resW * resH * 4);
        } else {
            MTLTextureDescriptor *td = [MTLTextureDescriptor texture2DDescriptorWithPixelFormat:MTLPixelFormatR32Uint
                                                                                          width:resW height:resH mipmapped:NO];
            td.usage = MTLTextureUsageShaderWrite | MTLTextureUsageShaderRead;
            td.storageMode = MTLStorageModeShared;
            tex = [dev newTextureWithDescriptor:td];
        }
        MTLRenderPassDescriptor *rp = [MTLRenderPassDescriptor renderPassDescriptor];
        rp.renderTargetWidth = areaW; rp.renderTargetHeight = areaH;
        rp.defaultRasterSampleCount = 1;
        id<MTLCommandBuffer> cb = [q commandBuffer];
        id<MTLRenderCommandEncoder> enc = [cb renderCommandEncoderWithDescriptor:rp];
        if (!enc) { printf("%-52s ENCODER REFUSED\n", label); return; }
        [enc setRenderPipelineState:pso];
        [enc setViewport:(MTLViewport){0, 0, (double)areaW, (double)areaH, 0, 1}];
        if (use_buffer) {
            uint32_t w32 = (uint32_t)areaW;
            [enc setFragmentBuffer:buf offset:0 atIndex:0];
            [enc setFragmentBytes:&w32 length:4 atIndex:1];
        } else {
            [enc setFragmentTexture:tex atIndex:0];
        }
        [enc drawPrimitives:MTLPrimitiveTypeTriangle vertexStart:0 vertexCount:3];
        [enc endEncoding];
        [cb commit]; [cb waitUntilCompleted];
        const char *st = cb.status == MTLCommandBufferStatusCompleted ? "completed" : "NOT COMPLETED";
        printf("%-52s %s", label, st);
        if (cb.error) printf("  ERROR: %s", [[cb.error localizedDescription] UTF8String]);
        printf("\n");
    }
}

int main(void) { @autoreleasepool {
    dev = MTLCreateSystemDefaultDevice(); q = [dev newCommandQueue];
    NSError *e = nil;
    lib = [dev newLibraryWithSource:SRC options:nil error:&e];
    if (!lib) { printf("MSL failed: %s\n", e.localizedDescription.UTF8String); return 1; }
    printf("device: %s   maxTextureDim=16384\n\n", dev.name.UTF8String);
    printf("-- attachment-less render passes, fragment writes at the pixel coordinate --\n");
    run("A texture, area == texture (64x64)",            64, 64,    64, 64,   0);
    run("B texture, area 736x416 >> texture 64x64",      736, 416,  64, 64,   0);
    run("C buffer,  area == buffer (64x64)",             64, 64,    64, 64,   1);
    run("D buffer,  area 736x416 >> buffer for 64x64",   736, 416,  64, 64,   1);
    run("E buffer,  area 12288x2048, buffer sized to it",12288, 2048, 12288, 2048, 1);
    run("F buffer,  area 12288x2048 into a 64x64 buffer",12288, 2048, 64, 64,   1);
    return 0; } }
