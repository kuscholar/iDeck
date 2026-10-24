/* Does a UAV write into a 3D texture land, through the same path the runtime
 * uses: MSC conversion with IRCompatibilityFlagForceTextureArray, a descriptor
 * table, and the top-level argument buffer?  UE's distance-field atlas is a 3D
 * texture written exactly this way, and it comes back empty on the device. */
#import <Metal/Metal.h>
#import <Foundation/Foundation.h>
#include <metal_irconverter/metal_irconverter.h>
#define IR_PRIVATE_IMPLEMENTATION
#include <metal_irconverter_runtime/metal_irconverter_runtime.h>
static uint8_t *load(const char*p,size_t*n){FILE*f=fopen(p,"rb");if(!f){fprintf(stderr,"missing %s\n",p);exit(1);}fseek(f,0,SEEK_END);*n=ftell(f);rewind(f);uint8_t*b=(uint8_t*)malloc(*n);fread(b,1,*n,f);fclose(f);return b;}
int main(void){@autoreleasepool{
    setbuf(stdout,NULL);
    id<MTLDevice> dev=MTLCreateSystemDefaultDevice(); id<MTLCommandQueue> q=[dev newCommandQueue];
    fprintf(stderr,"device: %s\n", dev.name.UTF8String);
    IRError *err=NULL;
    IRDescriptorRange1 range; memset(&range,0,sizeof range);
    range.RangeType=IRDescriptorRangeTypeUAV; range.NumDescriptors=1; range.Flags=IRDescriptorRangeFlagNone;
    IRRootParameter1 param; memset(&param,0,sizeof param);
    param.ParameterType=IRRootParameterTypeDescriptorTable;
    param.DescriptorTable.NumDescriptorRanges=1; param.DescriptorTable.pDescriptorRanges=&range;
    param.ShaderVisibility=IRShaderVisibilityAll;
    IRVersionedRootSignatureDescriptor rsd; memset(&rsd,0,sizeof rsd);
    rsd.version=IRRootSignatureVersion_1_1; rsd.desc_1_1.NumParameters=1; rsd.desc_1_1.pParameters=&param;
    IRRootSignature *rs=IRRootSignatureCreateFromDescriptor(&rsd,&err);
    IRCompiler *c=IRCompilerCreate();
    IRCompilerSetGlobalRootSignature(c,rs);
    IRCompilerSetEntryPointName(c,"CSMain");
    IRCompilerSetMinimumDeploymentTarget(c,IROperatingSystem_macOS,"15.0");
    IRCompilerSetMinimumGPUFamily(c,IRGPUFamilyApple8);
    IRCompilerSetCompatibilityFlags(c,IRCompatibilityFlagForceTextureArray);   /* as the runtime does */
    size_t n; uint8_t *d=load("CSMain.dxil",&n);
    IRObject *in=IRObjectCreateFromDXIL(d,n,IRBytecodeOwnershipNone);
    IRObject *o=IRCompilerAllocCompileAndLink(c,"CSMain",in,&err);
    if(!o){fprintf(stderr,"CONVERSION FAILED %u\n", err?IRErrorGetCode(err):0); return 1;}
    IRMetalLibBinary *mlb=IRMetalLibBinaryCreate(); IRObjectGetMetalLibBinary(o,IRShaderStageCompute,mlb);
    size_t ln=IRMetalLibGetBytecodeSize(mlb); uint8_t *lb=(uint8_t*)malloc(ln); IRMetalLibGetBytecode(mlb,lb);
    IRShaderReflection *r=IRShaderReflectionCreate(); IRObjectGetReflection(o,IRShaderStageCompute,r);
    NSError *e=nil;
    id<MTLLibrary> L=[dev newLibraryWithData:dispatch_data_create(lb,ln,NULL,DISPATCH_DATA_DESTRUCTOR_DEFAULT) error:&e];
    if(!L){fprintf(stderr,"metallib rejected: %s\n", e.localizedDescription.UTF8String); return 1;}
    id<MTLFunction> fn=[L newFunctionWithName:[NSString stringWithUTF8String:IRShaderReflectionGetEntryPointFunctionName(r)]];
    id<MTLComputePipelineState> pso=[dev newComputePipelineStateWithFunction:fn error:&e];
    if(!pso){fprintf(stderr,"pso rejected: %s\n", e.localizedDescription.UTF8String); return 1;}
    fprintf(stderr,"converted and built a pipeline OK\n");

    MTLTextureDescriptor *td=[MTLTextureDescriptor new];
    td.textureType=MTLTextureType3D; td.pixelFormat=MTLPixelFormatR8Unorm;
    td.width=8; td.height=8; td.depth=8; td.mipmapLevelCount=1;
    td.usage=MTLTextureUsageShaderWrite|MTLTextureUsageShaderRead;
    td.storageMode=MTLStorageModeShared;
    id<MTLTexture> t=[dev newTextureWithDescriptor:td];
    if(!t){fprintf(stderr,"3D texture with ShaderWrite REFUSED\n"); return 1;}
    uint8_t zero[8*8*8]={0};
    [t replaceRegion:MTLRegionMake3D(0,0,0,8,8,8) mipmapLevel:0 slice:0 withBytes:zero bytesPerRow:8 bytesPerImage:64];

    id<MTLBuffer> table=[dev newBufferWithLength:sizeof(IRDescriptorTableEntry) options:MTLResourceStorageModeShared];
    IRDescriptorTableSetTexture((IRDescriptorTableEntry*)table.contents,t,0.0f,0);
    uint64_t ta=table.gpuAddress;
    id<MTLBuffer> top=[dev newBufferWithBytes:&ta length:8 options:MTLResourceStorageModeShared];
    id<MTLCommandBuffer> cb=[q commandBuffer];
    id<MTLComputeCommandEncoder> enc=[cb computeCommandEncoder];
    [enc setComputePipelineState:pso];
    [enc setBuffer:top offset:0 atIndex:kIRArgumentBufferBindPoint];
    [enc useResource:t usage:MTLResourceUsageRead|MTLResourceUsageWrite];
    [enc useResource:table usage:MTLResourceUsageRead];
    [enc dispatchThreadgroups:MTLSizeMake(2,2,2) threadsPerThreadgroup:MTLSizeMake(4,4,4)];
    [enc endEncoding]; [cb commit]; [cb waitUntilCompleted];

    uint8_t out[8*8*8]={0};
    [t getBytes:out bytesPerRow:8 bytesPerImage:64 fromRegion:MTLRegionMake3D(0,0,0,8,8,8) mipmapLevel:0 slice:0];
    fprintf(stderr,"status=%ld\nper-depth-slice first voxel (expect 32 64 96 128 159 191 223 255):\n  ",(long)cb.status);
    int bad=0;
    for(int z=0;z<8;z++){ int got=out[z*64]; int want=(int)((z+1)/8.0*255.0+0.5); fprintf(stderr,"%d ",got); if(abs(got-want)>2) bad=1; }
    fprintf(stderr,"\n%s\n", bad?"*** 3D UAV WRITE IS WRONG ***":"3D UAV write is correct");
    return bad; } }
