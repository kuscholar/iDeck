/* Which mip does a converted COMPUTE shader read for SampleGrad, SampleLevel
 * and an implicit (SM6.6 compute-derivative) Sample?  Converted the way the
 * runtime converts: IRCompatibilityFlagForceTextureArray, descriptor tables,
 * every 2D texture allocated as a one-slice 2D array.  Mip k holds R = k*32. */
#import <Metal/Metal.h>
#import <Foundation/Foundation.h>
#include <metal_irconverter/metal_irconverter.h>
#define IR_PRIVATE_IMPLEMENTATION
#include <metal_irconverter_runtime/metal_irconverter_runtime.h>
static uint8_t *load(const char*p,size_t*n){FILE*f=fopen(p,"rb");if(!f){fprintf(stderr,"missing %s\n",p);exit(1);}fseek(f,0,SEEK_END);*n=ftell(f);rewind(f);uint8_t*b=(uint8_t*)malloc(*n);fread(b,1,*n,f);fclose(f);return b;}
int main(int argc,char**argv){@autoreleasepool{
    setbuf(stdout,NULL);
    int mip_linear = argc > 1 && atoi(argv[1]);
    id<MTLDevice> dev=MTLCreateSystemDefaultDevice(); id<MTLCommandQueue> q=[dev newCommandQueue];
    fprintf(stderr,"device: %s, mip filter %s\n", dev.name.UTF8String, mip_linear ? "linear" : "nearest");
    IRError *err=NULL;
    IRDescriptorRange1 rg[3]; memset(rg,0,sizeof rg);
    rg[0].RangeType=IRDescriptorRangeTypeSRV; rg[0].NumDescriptors=1;
    rg[1].RangeType=IRDescriptorRangeTypeSampler; rg[1].NumDescriptors=1;
    rg[2].RangeType=IRDescriptorRangeTypeUAV; rg[2].NumDescriptors=1;
    IRRootParameter1 p[3]; memset(p,0,sizeof p);
    for(int i=0;i<3;i++){ p[i].ParameterType=IRRootParameterTypeDescriptorTable; p[i].DescriptorTable.NumDescriptorRanges=1; p[i].DescriptorTable.pDescriptorRanges=&rg[i]; p[i].ShaderVisibility=IRShaderVisibilityAll; }
    IRVersionedRootSignatureDescriptor rsd; memset(&rsd,0,sizeof rsd);
    rsd.version=IRRootSignatureVersion_1_1; rsd.desc_1_1.NumParameters=3; rsd.desc_1_1.pParameters=p;
    IRRootSignature *rs=IRRootSignatureCreateFromDescriptor(&rsd,&err);
    if(!rs){fprintf(stderr,"root signature failed\n");return 1;}
    IRCompiler *c=IRCompilerCreate();
    IRCompilerSetGlobalRootSignature(c,rs);
    IRCompilerSetMinimumDeploymentTarget(c,IROperatingSystem_macOS,"15.0");
    IRCompilerSetMinimumGPUFamily(c,IRGPUFamilyMetal3);
    IRCompilerSetCompatibilityFlags(c,IRCompatibilityFlagForceTextureArray);
    size_t n; uint8_t *d=load("CSMain.dxil",&n);
    IRObject *in=IRObjectCreateFromDXIL(d,n,IRBytecodeOwnershipNone);
    IRObject *o=IRCompilerAllocCompileAndLink(c,NULL,in,&err);
    if(!o){fprintf(stderr,"CONVERSION FAILED %u\n", err?IRErrorGetCode(err):0); return 1;}
    IRMetalLibBinary *mlb=IRMetalLibBinaryCreate(); IRObjectGetMetalLibBinary(o,IRShaderStageCompute,mlb);
    size_t ln=IRMetalLibGetBytecodeSize(mlb); uint8_t *lb=(uint8_t*)malloc(ln); IRMetalLibGetBytecode(mlb,lb);
    { FILE *f=fopen("CSMain.metallib","wb"); if(f){fwrite(lb,1,ln,f);fclose(f);} }
    IRShaderReflection *r=IRShaderReflectionCreate(); IRObjectGetReflection(o,IRShaderStageCompute,r);
    NSError *e=nil;
    id<MTLLibrary> L=[dev newLibraryWithData:dispatch_data_create(lb,ln,NULL,DISPATCH_DATA_DESTRUCTOR_DEFAULT) error:&e];
    if(!L){fprintf(stderr,"metallib rejected: %s\n", e.localizedDescription.UTF8String); return 1;}
    id<MTLFunction> fn=[L newFunctionWithName:[NSString stringWithUTF8String:IRShaderReflectionGetEntryPointFunctionName(r)]];
    id<MTLComputePipelineState> pso=[dev newComputePipelineStateWithFunction:fn error:&e];
    if(!pso){fprintf(stderr,"pso rejected: %s\n", e.localizedDescription.UTF8String); return 1;}

    MTLTextureDescriptor *td=[MTLTextureDescriptor new];
    td.textureType=MTLTextureType2DArray; td.arrayLength=1; td.pixelFormat=MTLPixelFormatRGBA8Unorm;
    td.width=64; td.height=64; td.mipmapLevelCount=7; td.usage=MTLTextureUsageShaderRead; td.storageMode=MTLStorageModeShared;
    id<MTLTexture> t=[dev newTextureWithDescriptor:td];
    for(int m=0;m<7;m++){ int w=64>>m; uint32_t *px=(uint32_t*)malloc(w*w*4); for(int i=0;i<w*w;i++) px[i]=0xff000000u|(uint32_t)(m*32);
        [t replaceRegion:MTLRegionMake2D(0,0,w,w) mipmapLevel:m slice:0 withBytes:px bytesPerRow:w*4 bytesPerImage:w*w*4]; free(px); }
    MTLSamplerDescriptor *sd=[MTLSamplerDescriptor new];
    sd.minFilter=MTLSamplerMinMagFilterLinear; sd.magFilter=MTLSamplerMinMagFilterLinear;
    sd.mipFilter=mip_linear?MTLSamplerMipFilterLinear:MTLSamplerMipFilterNearest;
    sd.supportArgumentBuffers=YES; sd.lodMinClamp=0; sd.lodMaxClamp=1000;
    id<MTLSamplerState> smp=[dev newSamplerStateWithDescriptor:sd];
    id<MTLBuffer> out=[dev newBufferWithLength:64*16 options:MTLResourceStorageModeShared]; memset(out.contents,0xcc,64*16);
    id<MTLBuffer> tabs=[dev newBufferWithLength:3*sizeof(IRDescriptorTableEntry) options:MTLResourceStorageModeShared];
    IRDescriptorTableEntry *te=(IRDescriptorTableEntry*)tabs.contents;
    IRDescriptorTableSetTexture(&te[0],t,0.0f,0);
    IRDescriptorTableSetSampler(&te[1],smp,0.0f);
    IRBufferView bv; memset(&bv,0,sizeof bv); bv.buffer=out; bv.bufferSize=64*16;
    IRDescriptorTableSetBufferView(&te[2],&bv);
    uint64_t top3[3]={tabs.gpuAddress, tabs.gpuAddress+sizeof(IRDescriptorTableEntry), tabs.gpuAddress+2*sizeof(IRDescriptorTableEntry)};
    id<MTLBuffer> top=[dev newBufferWithBytes:top3 length:sizeof top3 options:MTLResourceStorageModeShared];
    id<MTLCommandBuffer> cb=[q commandBuffer]; id<MTLComputeCommandEncoder> enc=[cb computeCommandEncoder];
    [enc setComputePipelineState:pso];
    [enc setBuffer:top offset:0 atIndex:kIRArgumentBufferBindPoint];
    [enc useResource:t usage:MTLResourceUsageRead]; [enc useResource:out usage:MTLResourceUsageWrite]; [enc useResource:tabs usage:MTLResourceUsageRead];
    [enc dispatchThreadgroups:MTLSizeMake(1,1,1) threadsPerThreadgroup:MTLSizeMake(64,1,1)];
    [enc endEncoding]; [cb commit]; [cb waitUntilCompleted];
    fprintf(stderr,"status=%ld\n",(long)cb.status);
    float *v=(float*)out.contents;
    fprintf(stderr,"SampleGrad, isotropic 2^k texels (expect mip k):\n");
    for(int k=0;k<7;k++) fprintf(stderr,"  k=%d -> mip %.2f\n",k,v[k*4]*255.0/32.0);
    fprintf(stderr,"SampleGrad, 4:1 anisotropic (expect ~0 with aniso, 2 without): mip %.2f\n", v[7*4]*255.0/32.0);
    fprintf(stderr,"SampleLevel k (expect k):\n ");
    for(int k=0;k<7;k++) fprintf(stderr," %.2f",v[(8+k)*4]*255.0/32.0);
    fprintf(stderr,"\nimplicit Sample in compute (quad steps 2^s texels; expect mip s; ddx/ddy in texels expect 2^s):\n");
    for(int l=16;l<64;l+=4) fprintf(stderr,"  quad %2d s=%.0f -> mip %.2f  ddx %.2f ddy %.2f\n",l/4,v[l*4+3],v[l*4]*255.0/32.0,v[l*4+1],v[l*4+2]);
    return 0; } }
