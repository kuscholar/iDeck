#!/usr/bin/env python3
"""Read-only diagnostic of pinned FEX IR pointer arithmetic after allocation failure.

This is an iDeck diagnostic, not a FEX contribution or a runtime patch. Extract
unchanged upstream classes into a temporary harness, inject only allocation
results, and never dereference the invalid result. A reproduced bug is not a fix.
"""
from pathlib import Path
import hashlib
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
header = root / 'FEX/FEXCore/Source/Interface/IR/IntrusiveIRList.h'
source = header.read_text()
base = source[source.index('class DualIntrusiveAllocator {'):
              source.index('class DualIntrusiveAllocatorMalloc final')]
pooled = source[source.index('class DualIntrusiveAllocatorThreadPool final'):
                source.index('class IRListView final')]
assert 'List = Data + MemorySize;' in pooled

harness = r'''
#include <cassert>
#include <cstdint>
#include <cstddef>
#include <cstdio>
#include <cstring>
#include <type_traits>
#define LOGMAN_THROW_A_FMT(condition,...) assert(condition)
namespace FEXCore::Utils {
struct IntrusivePooledAllocator {};
static uintptr_t reply;
static size_t requested;
template<typename Type,unsigned Period,unsigned Frequency>
struct PoolBufferWithTimedRetirement {
    PoolBufferWithTimedRetirement(IntrusivePooledAllocator&,size_t size){requested=size;}
    Type ReownOrClaimBuffer(){return static_cast<Type>(reply);}
    void DelayedDisownBuffer(){}
};
}
namespace FEXCore::IR {
''' + base + pooled + r'''
}
int main() {
    constexpr size_t half=8*1024*1024;
    FEXCore::Utils::IntrusivePooledAllocator allocator;
    alignas(16) static unsigned char real[half*2];
    FEXCore::Utils::reply=reinterpret_cast<uintptr_t>(real);
    FEXCore::IR::DualIntrusiveAllocatorThreadPool valid(allocator,half);
    assert(FEXCore::Utils::requested==half*2);
    valid.ReownOrClaimBuffer();valid.Reset();
    assert(valid.DataBegin()==reinterpret_cast<uintptr_t>(real));
    assert(valid.ListBegin()==reinterpret_cast<uintptr_t>(real)+half);
    auto node=valid.ListAllocate(24);
    memset(node,0,24);

    FEXCore::Utils::reply=0; // Native constrained VM allocation returned NULL.
    FEXCore::IR::DualIntrusiveAllocatorThreadPool failed(allocator,half);
    failed.ReownOrClaimBuffer();failed.Reset();
    assert(failed.DataBegin()==0&&failed.ListBegin()==0x800000);
    auto invalid=failed.ListAllocate(24);
    assert(reinterpret_cast<uintptr_t>(invalid)==0x800000);
    // Do not execute IREmitter's subsequent memset on this invalid pointer.
    puts("REPRODUCED pinned FEX: NULL 16MiB backing -> ListBegin/ListAllocate=0x800000; subsequent node+0x10 write matches device0x800010. No invalid dereference, runtime fix or FEX source change.");
}
'''
with tempfile.TemporaryDirectory() as directory:
    directory = Path(directory)
    cpp = directory / 'reproduce.cpp'
    cpp.write_text(harness)
    subprocess.run(['clang++', '-std=c++20', '-Wall', '-Wextra', '-Werror',
                    '-fsanitize=address,undefined', str(cpp), '-o', str(directory / 'test')], check=True)
    subprocess.run([str(directory / 'test')], check=True)
print('Upstream header SHA256:', hashlib.sha256(header.read_bytes()).hexdigest())
