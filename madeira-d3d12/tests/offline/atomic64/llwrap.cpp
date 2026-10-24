// llwrap in.ll template.dxbc out.dxbc : assemble LLVM 15 IR text (typed pointers)
// and put the bitcode into the DXIL part of a copy of the template container.
#include "llvm/AsmParser/Parser.h"
#include "llvm/Bitcode/BitcodeWriter.h"
#include "llvm/IR/LLVMContext.h"
#include "llvm/IR/Module.h"
#include "llvm/IR/Verifier.h"
#include "llvm/Support/SourceMgr.h"
#include "llvm/Support/raw_ostream.h"
#include <cstring>
#include <vector>
#include <cstdio>
using namespace llvm;
static uint32_t rd(const std::vector<uint8_t>&d,size_t o){uint32_t v;memcpy(&v,&d[o],4);return v;}
static void wr(std::vector<uint8_t>&d,size_t o,uint32_t v){memcpy(&d[o],&v,4);}
int main(int argc,char**argv){
    LLVMContext ctx; ctx.setOpaquePointers(false); SMDiagnostic err;
    auto m=parseAssemblyFile(argv[1],err,ctx); if(!m){err.print("llwrap",errs());return 1;}
    SmallVector<char,0> bc; {raw_svector_ostream os(bc); WriteBitcodeToFile(*m,os);} while(bc.size()&3) bc.push_back(0);
    FILE*f=fopen(argv[2],"rb"); std::vector<uint8_t> d; int c; while((c=fgetc(f))!=EOF) d.push_back((uint8_t)c); fclose(f);
    uint32_t n=rd(d,28); std::vector<std::pair<uint32_t,std::vector<uint8_t>>> parts;
    for(uint32_t i=0;i<n;i++){uint32_t o=rd(d,32+4*i),sz=rd(d,o+4),cc=rd(d,o); std::vector<uint8_t> p(d.begin()+o+8,d.begin()+o+8+sz);
        if(!memcmp(&cc,"DXIL",4)){std::vector<uint8_t> q(24+bc.size()); memcpy(q.data(),p.data(),16); wr(q,4,q.size()/4); wr(q,16,16); wr(q,20,bc.size()); memcpy(q.data()+24,bc.data(),bc.size()); p.swap(q);}
        parts.push_back({cc,p});}
    std::vector<uint8_t> o(32+4*parts.size()); memcpy(o.data(),d.data(),24); wr(o,28,parts.size());
    for(size_t i=0;i<parts.size();i++){wr(o,32+4*i,o.size()); uint8_t h[8]; memcpy(h,&parts[i].first,4); uint32_t s=parts[i].second.size(); memcpy(h+4,&s,4); o.insert(o.end(),h,h+8); o.insert(o.end(),parts[i].second.begin(),parts[i].second.end());}
    wr(o,24,o.size()); f=fopen(argv[3],"wb"); fwrite(o.data(),1,o.size(),f); fclose(f); return 0; }
