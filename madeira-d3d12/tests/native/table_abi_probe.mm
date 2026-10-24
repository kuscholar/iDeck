/* Measures what a descriptor-table root parameter must contain.
 *
 * The converter's headers document the descriptor ENTRY layout and the bind
 * points, but not what the top-level argument buffer holds for a TABLE. A root
 * descriptor is a 64-bit GPU address; a table could plausibly be the same
 * address, a byte offset into the heap, or a descriptor index. Those are
 * indistinguishable by reading, and picking wrong renders black.
 *
 * So this renders the same textured triangle once per candidate on a real Metal
 * device and reports which one produces the expected pixel. It runs on the host
 * in seconds, which is the whole point: the answer is needed before the device
 * build, not after a blank window comes back from a phone. */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <dlfcn.h>
#import <Metal/Metal.h>

#include <metal_irconverter/metal_irconverter.h>
#include <metal_irconverter_runtime/metal_irconverter_runtime.h>

#define IR_FUNC_LIST(X) \
    X(IRObjectCreateFromDXIL) X(IRObjectDestroy) X(IRObjectGetMetalIRShaderStage) \
    X(IRObjectGetMetalLibBinary) X(IRObjectGetReflection) X(IRCompilerCreate) \
    X(IRCompilerDestroy) X(IRCompilerSetGlobalRootSignature) X(IRCompilerSetEntryPointName) \
    X(IRCompilerSetMinimumDeploymentTarget) X(IRCompilerSetMinimumGPUFamily) \
    X(IRCompilerAllocCompileAndLink) X(IRRootSignatureCreateFromDescriptor) \
    X(IRRootSignatureDestroy) X(IRMetalLibBinaryCreate) X(IRMetalLibBinaryDestroy) \
    X(IRMetalLibGetBytecodeSize) X(IRMetalLibGetBytecode) X(IRShaderReflectionCreate) \
    X(IRShaderReflectionDestroy) X(IRShaderReflectionGetEntryPointFunctionName) \
    X(IRErrorGetCode) X(IRErrorDestroy)

struct { void *h;
#define D(n) decltype(&::n) n;
    IR_FUNC_LIST(D)
#undef D
} ir;

static const unsigned char *slurp(const char *p, size_t *n) {
    FILE *f = fopen(p, "rb"); if (!f) return NULL;
    fseek(f, 0, SEEK_END); *n = ftell(f); fseek(f, 0, SEEK_SET);
    unsigned char *b = (unsigned char *)malloc(*n);
    if (fread(b, 1, *n, f) != *n) { free(b); fclose(f); return NULL; }
    fclose(f); return b;
}

/* The same three-parameter layout the shader declares. */
static IRRootSignature *make_rs(void) {
    IRDescriptorRange1 srv, smp;
    memset(&srv, 0, sizeof srv); memset(&smp, 0, sizeof smp);
    srv.RangeType = IRDescriptorRangeTypeSRV; srv.NumDescriptors = 1;
    srv.BaseShaderRegister = 0; srv.RegisterSpace = 0; srv.Flags = IRDescriptorRangeFlagNone;
    smp.RangeType = IRDescriptorRangeTypeSampler; smp.NumDescriptors = 1;
    smp.BaseShaderRegister = 0; smp.RegisterSpace = 0; smp.Flags = IRDescriptorRangeFlagNone;

    static IRRootParameter1 p[3];
    memset(p, 0, sizeof p);
    p[0].ParameterType = IRRootParameterTypeCBV;
    p[0].Descriptor.ShaderRegister = 0; p[0].ShaderVisibility = IRShaderVisibilityAll;
    p[1].ParameterType = IRRootParameterTypeDescriptorTable;
    p[1].DescriptorTable.NumDescriptorRanges = 1;
    p[1].DescriptorTable.pDescriptorRanges = &srv;
    p[1].ShaderVisibility = IRShaderVisibilityAll;
    p[2].ParameterType = IRRootParameterTypeDescriptorTable;
    p[2].DescriptorTable.NumDescriptorRanges = 1;
    p[2].DescriptorTable.pDescriptorRanges = &smp;
    p[2].ShaderVisibility = IRShaderVisibilityAll;

    IRVersionedRootSignatureDescriptor d;
    memset(&d, 0, sizeof d);
    d.version = IRRootSignatureVersion_1_1;
    d.desc_1_1.NumParameters = 3;
    d.desc_1_1.pParameters = p;
    d.desc_1_1.Flags = IRRootSignatureFlagNone;
    IRError *e = NULL;
    IRRootSignature *rs = ir.IRRootSignatureCreateFromDescriptor(&d, &e);
    if (!rs) { printf("root signature failed, code %u\n", e ? ir.IRErrorGetCode(e) : 0); }
    if (e) ir.IRErrorDestroy(e);
    return rs;
}

static id<MTLLibrary> build(id<MTLDevice> dev, const char *path, const char *entry,
                            IRRootSignature *rs, char *name_out) {
    size_t n = 0; const unsigned char *b = slurp(path, &n);
    if (!b) { printf("cannot read %s\n", path); return nil; }
    IRError *e = NULL;
    IRObject *in = ir.IRObjectCreateFromDXIL(b, n, IRBytecodeOwnershipNone);
    IRCompiler *c = ir.IRCompilerCreate();
    ir.IRCompilerSetGlobalRootSignature(c, rs);
    ir.IRCompilerSetEntryPointName(c, entry);
    ir.IRCompilerSetMinimumDeploymentTarget(c, IROperatingSystem_macOS, "15.0");
    ir.IRCompilerSetMinimumGPUFamily(c, IRGPUFamilyMetal3);
    IRObject *out = ir.IRCompilerAllocCompileAndLink(c, entry, in, &e);
    if (!out) { printf("compile failed for %s, code %u\n", entry, e ? ir.IRErrorGetCode(e) : 0); return nil; }
    IRShaderStage st = ir.IRObjectGetMetalIRShaderStage(out);
    IRMetalLibBinary *mb = ir.IRMetalLibBinaryCreate();
    ir.IRObjectGetMetalLibBinary(out, st, mb);
    size_t sz = ir.IRMetalLibGetBytecodeSize(mb);
    uint8_t *bytes = (uint8_t *)malloc(sz);
    ir.IRMetalLibGetBytecode(mb, bytes);
    IRShaderReflection *r = ir.IRShaderReflectionCreate();
    if (r && ir.IRObjectGetReflection(out, st, r)) {
        const char *nm = ir.IRShaderReflectionGetEntryPointFunctionName(r);
        if (nm) snprintf(name_out, 128, "%s", nm);
    }
    dispatch_data_t dd = dispatch_data_create(bytes, sz, NULL, DISPATCH_DATA_DESTRUCTOR_DEFAULT);
    NSError *err = nil;
    id<MTLLibrary> lib = [dev newLibraryWithData:dd error:&err];
    if (!lib) printf("newLibraryWithData failed: %s\n", err.localizedDescription.UTF8String);
    return lib;
}

int main(void) {
    ir.h = dlopen(getenv("MADEIRA_MSC_DYLIB"), RTLD_NOW);
    if (!ir.h) { printf("no converter: %s\n", dlerror()); return 1; }
#define B(n) ir.n = (decltype(&::n))dlsym(ir.h, #n); if (!ir.n) { printf("missing %s\n", #n); return 1; }
    IR_FUNC_LIST(B)
#undef B

    id<MTLDevice> dev = MTLCreateSystemDefaultDevice();
    printf("device: %s\n", dev.name.UTF8String);

    IRRootSignature *rs = make_rs();
    if (!rs) return 1;
    char vsn[128] = {0}, psn[128] = {0};
    id<MTLLibrary> vlib = build(dev, "madeira-d3d12/shaders/tex_vs.dxil", "MainVS", rs, vsn);
    id<MTLLibrary> plib = build(dev, "madeira-d3d12/shaders/tex_ps.dxil", "MainPS", rs, psn);
    if (!vlib || !plib) return 1;
    printf("entry points: '%s' / '%s'\n", vsn, psn);

    MTLRenderPipelineDescriptor *pd = [MTLRenderPipelineDescriptor new];
    pd.vertexFunction = [vlib newFunctionWithName:[NSString stringWithUTF8String:vsn]];
    pd.fragmentFunction = [plib newFunctionWithName:[NSString stringWithUTF8String:psn]];
    pd.colorAttachments[0].pixelFormat = MTLPixelFormatRGBA8Unorm;
    pd.maxTessellationFactor = 16;
    NSError *err = nil;
    id<MTLRenderPipelineState> pso = [dev newRenderPipelineStateWithDescriptor:pd error:&err];
    if (!pso) { printf("pipeline failed: %s\n", err.localizedDescription.UTF8String); return 1; }

    /* A texture whose every texel is the same known colour, so the check does
     * not depend on filtering or on which texel a UV lands in. */
    MTLTextureDescriptor *td = [MTLTextureDescriptor texture2DDescriptorWithPixelFormat:MTLPixelFormatRGBA8Unorm
                                                                                 width:2 height:2 mipmapped:NO];
    td.usage = MTLTextureUsageShaderRead;
    td.storageMode = MTLStorageModeShared;
    id<MTLTexture> tex = [dev newTextureWithDescriptor:td];
    uint8_t texels[2 * 2 * 4];
    for (int i = 0; i < 4; i++) { texels[i*4+0] = 0; texels[i*4+1] = 200; texels[i*4+2] = 100; texels[i*4+3] = 255; }
    [tex replaceRegion:MTLRegionMake2D(0, 0, 2, 2) mipmapLevel:0 withBytes:texels bytesPerRow:8];

    MTLSamplerDescriptor *sd = [MTLSamplerDescriptor new];
    sd.minFilter = MTLSamplerMinMagFilterNearest;
    sd.magFilter = MTLSamplerMinMagFilterNearest;
    sd.supportArgumentBuffers = YES;     /* required to encode into a table */
    id<MTLSamplerState> smp = [dev newSamplerStateWithDescriptor:sd];

    /* tint = 1.0 so the output is the texel colour unchanged. */
    float tint[4] = { 1.0f, 1.0f, 1.0f, 1.0f };
    id<MTLBuffer> cbv = [dev newBufferWithBytes:tint length:sizeof tint options:MTLResourceStorageModeShared];

    /* Heaps, with the descriptor placed at a NON-ZERO index so an encoding that
     * ignores the offset cannot pass by accident. */
    const uint64_t SRV_SLOT = 3, SMP_SLOT = 2;
    id<MTLBuffer> heap = [dev newBufferWithLength:sizeof(IRDescriptorTableEntry) * 8
                                          options:MTLResourceStorageModeShared];
    id<MTLBuffer> sheap = [dev newBufferWithLength:sizeof(IRDescriptorTableEntry) * 8
                                           options:MTLResourceStorageModeShared];
    IRDescriptorTableEntry *he = (IRDescriptorTableEntry *)heap.contents;
    IRDescriptorTableEntry *se = (IRDescriptorTableEntry *)sheap.contents;
    memset(he, 0, sizeof(IRDescriptorTableEntry) * 8);
    memset(se, 0, sizeof(IRDescriptorTableEntry) * 8);
    IRDescriptorTableSetTexture(&he[SRV_SLOT], tex, 0.0f, 0);
    IRDescriptorTableSetSampler(&se[SMP_SLOT], smp, 0.0f);

    MTLTextureDescriptor *rtd = [MTLTextureDescriptor texture2DDescriptorWithPixelFormat:MTLPixelFormatRGBA8Unorm
                                                                                   width:8 height:8 mipmapped:NO];
    rtd.usage = MTLTextureUsageRenderTarget;
    rtd.storageMode = MTLStorageModeShared;
    id<MTLTexture> rt = [dev newTextureWithDescriptor:rtd];
    id<MTLCommandQueue> q = [dev newCommandQueue];
    id<MTLBuffer> argbuf = [dev newBufferWithLength:64 options:MTLResourceStorageModeShared];

    struct { const char *name; uint64_t srv, smp; } cand[] = {
        { "absolute GPU address of the entry",
          heap.gpuAddress + SRV_SLOT * sizeof(IRDescriptorTableEntry),
          sheap.gpuAddress + SMP_SLOT * sizeof(IRDescriptorTableEntry) },
        { "byte offset into the heap",
          SRV_SLOT * sizeof(IRDescriptorTableEntry), SMP_SLOT * sizeof(IRDescriptorTableEntry) },
        { "descriptor index into the heap", SRV_SLOT, SMP_SLOT },
    };

    printf("\nexpecting (0,200,100,255) when the table is addressed correctly\n");
    int winner = -1;
    for (unsigned c = 0; c < 3; c++) {
        uint64_t *ab = (uint64_t *)argbuf.contents;
        ab[0] = cbv.gpuAddress;
        ab[1] = cand[c].srv;
        ab[2] = cand[c].smp;

        MTLRenderPassDescriptor *rp = [MTLRenderPassDescriptor renderPassDescriptor];
        rp.colorAttachments[0].texture = rt;
        rp.colorAttachments[0].loadAction = MTLLoadActionClear;
        rp.colorAttachments[0].storeAction = MTLStoreActionStore;
        rp.colorAttachments[0].clearColor = MTLClearColorMake(1, 0, 0, 1);
        id<MTLCommandBuffer> cb = [q commandBuffer];
        id<MTLRenderCommandEncoder> e = [cb renderCommandEncoderWithDescriptor:rp];
        [e setRenderPipelineState:pso];
        for (int stage = 0; stage < 2; stage++) {
            if (stage == 0) {
                [e setVertexBuffer:heap offset:0 atIndex:kIRDescriptorHeapBindPoint];
                [e setVertexBuffer:sheap offset:0 atIndex:kIRSamplerHeapBindPoint];
                [e setVertexBuffer:argbuf offset:0 atIndex:kIRArgumentBufferBindPoint];
            } else {
                [e setFragmentBuffer:heap offset:0 atIndex:kIRDescriptorHeapBindPoint];
                [e setFragmentBuffer:sheap offset:0 atIndex:kIRSamplerHeapBindPoint];
                [e setFragmentBuffer:argbuf offset:0 atIndex:kIRArgumentBufferBindPoint];
            }
        }
        /* Resources reached THROUGH an argument buffer are invisible to Metal's
         * dependency tracking unless named explicitly. */
        [e useResource:tex usage:MTLResourceUsageRead stages:MTLRenderStageFragment];
        [e useResource:cbv usage:MTLResourceUsageRead stages:MTLRenderStageVertex | MTLRenderStageFragment];
        [e drawPrimitives:MTLPrimitiveTypeTriangle vertexStart:0 vertexCount:3];
        [e endEncoding];
        [cb commit];
        [cb waitUntilCompleted];

        uint8_t px[4] = {0};
        [rt getBytes:px bytesPerRow:8 * 4 fromRegion:MTLRegionMake2D(4, 4, 1, 1) mipmapLevel:0];
        int ok = (px[0] == 0 && px[1] == 200 && px[2] == 100);
        printf("  %-34s -> (%3u,%3u,%3u,%3u) %s\n", cand[c].name, px[0], px[1], px[2], px[3],
               ok ? "MATCH" : "");
        if (ok && winner < 0) winner = (int)c;
    }
    printf("\n%s\n", winner >= 0 ? "table encoding identified" : "NONE matched -- do not guess, investigate");
    if (winner >= 0) printf("ANSWER: %s\n", cand[winner].name);
    return winner < 0;
}
