/* conv <in.dxbc> [out.metallib]: convert a real shader through MSC the way the
 * runtime does (Apple9, ForceTextureArray) against a permissive root signature:
 * one table with CBV b0-b7, SRV t0-t31, UAV u0-u15, samplers s0-s15 separate. */
#import <Metal/Metal.h>
#import <Foundation/Foundation.h>
#include <metal_irconverter/metal_irconverter.h>
static uint8_t *load(const char*p,size_t*n){FILE*f=fopen(p,"rb");if(!f){fprintf(stderr,"missing %s\n",p);exit(1);}fseek(f,0,SEEK_END);*n=ftell(f);rewind(f);uint8_t*b=(uint8_t*)malloc(*n);fread(b,1,*n,f);fclose(f);return b;}
int main(int argc,char**argv){@autoreleasepool{
    IRError *err=NULL;
    IRDescriptorRange1 rg[4]; memset(rg,0,sizeof rg);
    rg[0].RangeType=IRDescriptorRangeTypeCBV; rg[0].NumDescriptors=8;
    rg[1].RangeType=IRDescriptorRangeTypeSRV; rg[1].NumDescriptors=32; rg[1].OffsetInDescriptorsFromTableStart=8;
    rg[2].RangeType=IRDescriptorRangeTypeUAV; rg[2].NumDescriptors=16; rg[2].OffsetInDescriptorsFromTableStart=40;
    rg[3].RangeType=IRDescriptorRangeTypeSampler; rg[3].NumDescriptors=16;
    IRRootParameter1 p[2]; memset(p,0,sizeof p);
    p[0].ParameterType=IRRootParameterTypeDescriptorTable; p[0].DescriptorTable.NumDescriptorRanges=3; p[0].DescriptorTable.pDescriptorRanges=rg; p[0].ShaderVisibility=IRShaderVisibilityAll;
    p[1].ParameterType=IRRootParameterTypeDescriptorTable; p[1].DescriptorTable.NumDescriptorRanges=1; p[1].DescriptorTable.pDescriptorRanges=rg+3; p[1].ShaderVisibility=IRShaderVisibilityAll;
    IRVersionedRootSignatureDescriptor rsd; memset(&rsd,0,sizeof rsd);
    rsd.version=IRRootSignatureVersion_1_1; rsd.desc_1_1.NumParameters=2; rsd.desc_1_1.pParameters=p;
    IRRootSignature *rs=IRRootSignatureCreateFromDescriptor(&rsd,&err);
    if(!rs){fprintf(stderr,"root signature failed %u\n", err?IRErrorGetCode(err):0);return 1;}
    IRCompiler *c=IRCompilerCreate();
    IRCompilerSetGlobalRootSignature(c,rs);
    IRCompilerSetMinimumDeploymentTarget(c,IROperatingSystem_iOS,"26.0");
    IRCompilerSetMinimumGPUFamily(c,IRGPUFamilyApple9);
    IRCompilerSetCompatibilityFlags(c,IRCompatibilityFlagForceTextureArray);
    size_t n; uint8_t *d=load(argv[1],&n);
    IRObject *in=IRObjectCreateFromDXIL(d,n,IRBytecodeOwnershipNone);
    if(!in){fprintf(stderr,"IRObjectCreateFromDXIL refused\n");return 1;}
    IRObject *o=IRCompilerAllocCompileAndLink(c,NULL,in,&err);
    if(!o){fprintf(stderr,"CONVERSION FAILED code %u\n", err?IRErrorGetCode(err):0); if(err){const char*m=(const char*)IRErrorGetPayload(err); if(m)fprintf(stderr,"  %s\n",m);} return 1;}
    IRShaderStage st=IRObjectGetMetalIRShaderStage(o);
    IRMetalLibBinary *mlb=IRMetalLibBinaryCreate(); IRObjectGetMetalLibBinary(o,st,mlb);
    size_t ln=IRMetalLibGetBytecodeSize(mlb); uint8_t *lb=(uint8_t*)malloc(ln); IRMetalLibGetBytecode(mlb,lb);
    if(argc>2){ FILE *f=fopen(argv[2],"wb"); if(f){fwrite(lb,1,ln,f);fclose(f);} }
    id<MTLDevice> dev=MTLCreateSystemDefaultDevice(); NSError *e=nil;
    id<MTLLibrary> L=[dev newLibraryWithData:dispatch_data_create(lb,ln,NULL,DISPATCH_DATA_DESTRUCTOR_DEFAULT) error:&e];
    fprintf(stderr,"converted: stage %d, %zu bytes of metallib, Metal %s\n",(int)st,ln, L?"accepts it":e.localizedDescription.UTF8String);
    return L?0:1; } }
