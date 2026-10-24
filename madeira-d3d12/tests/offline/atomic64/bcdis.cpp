// bcdis in.bc : print LLVM 15 textual IR of a DXIL bitcode blob (typed pointers).
#include "llvm/Bitcode/BitcodeReader.h"
#include "llvm/IR/LLVMContext.h"
#include "llvm/IR/Module.h"
#include "llvm/Support/MemoryBuffer.h"
#include "llvm/Support/raw_ostream.h"
using namespace llvm;
int main(int argc, char **argv) {
    LLVMContext ctx; ctx.setOpaquePointers(false);
    auto mb = MemoryBuffer::getFile(argv[1]); if (!mb) return 2;
    auto m = parseBitcodeFile((*mb)->getMemBufferRef(), ctx);
    if (!m) { errs() << toString(m.takeError()) << "\n"; return 1; }
    (*m)->print(outs(), nullptr); return 0;
}
