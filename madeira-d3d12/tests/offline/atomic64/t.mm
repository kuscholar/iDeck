/* T1: SM6.6 InterlockedMax on RWTexture2D<uint64_t>, converted the way the
 * runtime converts (Apple9 family, ForceTextureArray, descriptor table), run on
 * an RG32Uint 2D-array texture with ShaderAtomic usage. Prints PASS/FAIL per cell.
 * usage: t <file.dxil> [expect-mode]   (mode 0 = v.hlsl pattern) */
#import <Metal/Metal.h>
#import <Foundation/Foundation.h>
#include <metal_irconverter/metal_irconverter.h>
#define IR_PRIVATE_IMPLEMENTATION
#include <metal_irconverter_runtime/metal_irconverter_runtime.h>
static uint8_t *load(const char*p,size_t*n){FILE*f=fopen(p,"rb");if(!f){fprintf(stderr,"missing %s\n",p);exit(1);}fseek(f,0,SEEK_END);*n=ftell(f);rewind(f);uint8_t*b=(uint8_t*)malloc(*n);fread(b,1,*n,f);fclose(f);return b;}
int main(int argc,char**argv){@autoreleasepool{
    setbuf(stdout,NULL);
    const char *path = argc > 1 ? argv[1] : "CSMain.dxil";
    id<MTLDevice> dev=MTLCreateSystemDefaultDevice(); id<MTLCommandQueue> q=[dev newCommandQueue];
    fprintf(stderr,"device: %s apple9=%d\n", dev.name.UTF8String, (int)[dev supportsFamily:MTLGPUFamilyApple9]);
    IRError *err=NULL;
    IRDescriptorRange1 rg; memset(&rg,0,sizeof rg); rg.RangeType=IRDescriptorRangeTypeUAV; rg.NumDescriptors=1;
    IRRootParameter1 p; memset(&p,0,sizeof p); p.ParameterType=IRRootParameterTypeDescriptorTable;
    p.DescriptorTable.NumDescriptorRanges=1; p.DescriptorTable.pDescriptorRanges=&rg; p.ShaderVisibility=IRShaderVisibilityAll;
    IRVersionedRootSignatureDescriptor rsd; memset(&rsd,0,sizeof rsd);
    rsd.version=IRRootSignatureVersion_1_1; rsd.desc_1_1.NumParameters=1; rsd.desc_1_1.pParameters=&p;
    IRRootSignature *rs=IRRootSignatureCreateFromDescriptor(&rsd,&err);
    if(!rs){fprintf(stderr,"root signature failed\n");return 1;}
    IRCompiler *c=IRCompilerCreate();
    IRCompilerSetGlobalRootSignature(c,rs);
    IRCompilerSetMinimumDeploymentTarget(c,IROperatingSystem_macOS,"15.0");
    IRCompilerSetMinimumGPUFamily(c,IRGPUFamilyApple9);
    IRCompilerSetCompatibilityFlags(c,IRCompatibilityFlagForceTextureArray);
    size_t n; uint8_t *d=load(path,&n);
    IRObject *in=IRObjectCreateFromDXIL(d,n,IRBytecodeOwnershipNone);
    IRObject *o=IRCompilerAllocCompileAndLink(c,NULL,in,&err);
    if(!o){fprintf(stderr,"CONVERSION FAILED %u\n", err?IRErrorGetCode(err):0); return 1;}
    IRMetalLibBinary *mlb=IRMetalLibBinaryCreate(); IRObjectGetMetalLibBinary(o,IRShaderStageCompute,mlb);
    size_t ln=IRMetalLibGetBytecodeSize(mlb); uint8_t *lb=(uint8_t*)malloc(ln); IRMetalLibGetBytecode(mlb,lb);
    { FILE *f=fopen("out.metallib","wb"); if(f){fwrite(lb,1,ln,f);fclose(f);} }
    IRShaderReflection *r=IRShaderReflectionCreate(); IRObjectGetReflection(o,IRShaderStageCompute,r);
    NSError *e=nil;
    id<MTLLibrary> L=[dev newLibraryWithData:dispatch_data_create(lb,ln,NULL,DISPATCH_DATA_DESTRUCTOR_DEFAULT) error:&e];
    if(!L){fprintf(stderr,"metallib rejected: %s\n", e.localizedDescription.UTF8String); return 1;}
    id<MTLFunction> fn=[L newFunctionWithName:[NSString stringWithUTF8String:IRShaderReflectionGetEntryPointFunctionName(r)]];
    id<MTLComputePipelineState> pso=[dev newComputePipelineStateWithFunction:fn error:&e];
    if(!pso){fprintf(stderr,"pso rejected: %s\n", e.localizedDescription.UTF8String); return 1;}
    MTLTextureDescriptor *td=[MTLTextureDescriptor new];
    td.textureType=MTLTextureType2DArray; td.arrayLength=1; td.pixelFormat=MTLPixelFormatRG32Uint;
    td.width=4; td.height=4; td.usage=MTLTextureUsageShaderRead|MTLTextureUsageShaderWrite|(getenv("NO_ATOMIC_USAGE")?0:MTLTextureUsageShaderAtomic); td.storageMode=MTLStorageModeShared;
    id<MTLTexture> t=[dev newTextureWithDescriptor:td];
    if(!t){fprintf(stderr,"texture refused\n");return 1;}
    uint32_t zero[32]={0}; [t replaceRegion:MTLRegionMake2D(0,0,4,4) mipmapLevel:0 slice:0 withBytes:zero bytesPerRow:32 bytesPerImage:128];
    id<MTLBuffer> tabs=[dev newBufferWithLength:sizeof(IRDescriptorTableEntry) options:MTLResourceStorageModeShared];
    IRDescriptorTableSetTexture((IRDescriptorTableEntry*)tabs.contents,t,0.0f,0);
    uint64_t top1=tabs.gpuAddress;
    id<MTLBuffer> top=[dev newBufferWithBytes:&top1 length:8 options:MTLResourceStorageModeShared];
    id<MTLCommandBuffer> cb=[q commandBuffer]; id<MTLComputeCommandEncoder> enc=[cb computeCommandEncoder];
    [enc setComputePipelineState:pso];
    [enc setBuffer:top offset:0 atIndex:kIRArgumentBufferBindPoint];
    [enc useResource:t usage:MTLResourceUsageRead|MTLResourceUsageWrite]; [enc useResource:tabs usage:MTLResourceUsageRead];
    [enc dispatchThreadgroups:MTLSizeMake(1,1,1) threadsPerThreadgroup:MTLSizeMake(16,16,1)];
    [enc endEncoding]; [cb commit]; [cb waitUntilCompleted];
    fprintf(stderr,"status=%ld\n",(long)cb.status);
    uint32_t px[32]; [t getBytes:px bytesPerRow:32 bytesPerImage:128 fromRegion:MTLRegionMake2D(0,0,4,4) mipmapLevel:0 slice:0];
    int bad=0;
    for(int cy=0;cy<4;cy++) for(int cx=0;cx<4;cx++){
        uint64_t best=0;
        for(int y=0;y<16;y++) for(int x=0;x<16;x++) if((x&3)==cx&&(y&3)==cy){
            uint64_t v=((uint64_t)((x*37u+y*11u)&255u)<<32)|(uint64_t)(y*16u+x); if(v>best)best=v; }
        uint64_t got=((uint64_t)px[(cy*4+cx)*2+1]<<32)|px[(cy*4+cx)*2];
        if(got!=best){bad++; fprintf(stderr,"  cell %d,%d got %016llx want %016llx\n",cx,cy,(unsigned long long)got,(unsigned long long)best);}
    }
    fprintf(stderr,"%s (%d/16 cells wrong)\n", bad?"FAIL":"PASS", bad);
    return bad?1:0; } }
