// Does Metal's blend give src, NaN or 0 when dst = +inf and the dst factor is exactly 0?
// R16Float target cleared to +inf; quad writes (10, 0, 0, a) with SrcAlpha / OneMinusSrcAlpha.
#import <Metal/Metal.h>
#import <Foundation/Foundation.h>
#include <math.h>
static const char *src =
"#include <metal_stdlib>\nusing namespace metal;\n"
"struct V { float4 p [[position]]; };\n"
"vertex V vs(uint id [[vertex_id]]) { float2 q[4] = { {-1,-1},{1,-1},{-1,1},{1,1} }; V o; o.p = float4(q[id],0,1); return o; }\n"
"struct F { float4 c0 [[color(0)]]; float4 c1 [[color(1)]]; };\n"
"fragment F fs(float4 p [[position]], constant float &a [[buffer(0)]]) { F o; o.c0 = float4(1,2,3,a); o.c1 = float4(10.0, 0, 0, a); return o; }\n";
int main(int argc, char **argv) {
  id<MTLDevice> dev = MTLCreateSystemDefaultDevice();
  NSError *err = nil;
  id<MTLLibrary> lib = [dev newLibraryWithSource:[NSString stringWithUTF8String:src] options:nil error:&err];
  if (!lib) { NSLog(@"%@", err); return 1; }
  MTLRenderPipelineDescriptor *pd = [MTLRenderPipelineDescriptor new];
  pd.vertexFunction = [lib newFunctionWithName:@"vs"]; pd.fragmentFunction = [lib newFunctionWithName:@"fs"];
  pd.colorAttachments[0].pixelFormat = MTLPixelFormatRGBA16Float;
  pd.colorAttachments[1].pixelFormat = MTLPixelFormatR16Float;
  for (int i = 0; i < 2; i++) {
    pd.colorAttachments[i].blendingEnabled = YES;
    pd.colorAttachments[i].sourceRGBBlendFactor = MTLBlendFactorSourceAlpha;
    pd.colorAttachments[i].destinationRGBBlendFactor = MTLBlendFactorOneMinusSourceAlpha;
    pd.colorAttachments[i].sourceAlphaBlendFactor = MTLBlendFactorOne;
    pd.colorAttachments[i].destinationAlphaBlendFactor = MTLBlendFactorZero;
  }
  id<MTLRenderPipelineState> pso = [dev newRenderPipelineStateWithDescriptor:pd error:&err];
  if (!pso) { NSLog(@"%@", err); return 1; }
  MTLTextureDescriptor *td = [MTLTextureDescriptor texture2DDescriptorWithPixelFormat:MTLPixelFormatRGBA16Float width:4 height:4 mipmapped:NO];
  td.usage = MTLTextureUsageRenderTarget; td.storageMode = MTLStorageModeShared;
  id<MTLTexture> t0 = [dev newTextureWithDescriptor:td];
  td.pixelFormat = MTLPixelFormatR16Float;
  id<MTLTexture> t1 = [dev newTextureWithDescriptor:td];
  id<MTLCommandQueue> q = [dev newCommandQueue];
  float alphas[] = { 1.0f, 0.5f, 0.0f, 0.999f, 1.0f, 0.5f, 0.0f, 1.0f, 0.5f };
  for (int k = 0; k < 9; k++) {
    uint16_t fill = (k >= 4 && k < 7) ? 0x5640 : 0x7c00;   /* 100.0 half for the control cases */
    id<MTLRenderPipelineState> use = pso;
    if (k >= 7) { pd.colorAttachments[0].blendingEnabled = NO; pd.colorAttachments[1].blendingEnabled = NO; use = [dev newRenderPipelineStateWithDescriptor:pd error:&err]; }
    // clear to +inf through a load action (clearColor inf) and through explicit texel writes
    uint16_t inf16[16]; for (int i = 0; i < 16; i++) inf16[i] = fill;
    [t1 replaceRegion:MTLRegionMake2D(0,0,4,4) mipmapLevel:0 withBytes:inf16 bytesPerRow:8];
    MTLRenderPassDescriptor *rp = [MTLRenderPassDescriptor renderPassDescriptor];
    rp.colorAttachments[0].texture = t0; rp.colorAttachments[0].loadAction = MTLLoadActionClear; rp.colorAttachments[0].storeAction = MTLStoreActionStore;
    rp.colorAttachments[1].texture = t1; rp.colorAttachments[1].loadAction = (k == 3) ? MTLLoadActionClear : MTLLoadActionLoad; rp.colorAttachments[1].storeAction = MTLStoreActionStore;
    rp.colorAttachments[1].clearColor = MTLClearColorMake(INFINITY, 0, 0, 0);
    id<MTLCommandBuffer> cb = [q commandBuffer];
    id<MTLRenderCommandEncoder> enc = [cb renderCommandEncoderWithDescriptor:rp];
    [enc setRenderPipelineState:use];
    float a = alphas[k]; [enc setFragmentBytes:&a length:4 atIndex:0];
    [enc drawPrimitives:MTLPrimitiveTypeTriangleStrip vertexStart:0 vertexCount:4];
    [enc endEncoding]; [cb commit]; [cb waitUntilCompleted];
    uint16_t out[16]; [t1 getBytes:out bytesPerRow:8 fromRegion:MTLRegionMake2D(0,0,4,4) mipmapLevel:0];
    __fp16 h; memcpy(&h, &out[5], 2);
    printf("case %d alpha=%g dst=%s blend=%s -> R16F texel5 = 0x%04x = %g   texel0=0x%04x texel15=0x%04x\n", k, a, k == 3 ? "clear-inf" : (fill == 0x5640 ? "100" : "inf"), k >= 7 ? "off" : "on", out[5], (double)h, out[0], out[15]);
  }
  return 0;
}
