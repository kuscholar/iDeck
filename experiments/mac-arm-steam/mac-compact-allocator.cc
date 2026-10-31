// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
// Real macOS-compiled allocator component; no CEF/Steam or malloc replacement.
#include "mac-compact-allocator.h"
#include <atomic>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <thread>
#include "partition_alloc/partition_alloc.h"
#include "partition_alloc/partition_address_space.h"
namespace pa=partition_alloc;
namespace pi=partition_alloc::internal;
static_assert(BUILDFLAG(IS_MAC) && !BUILDFLAG(IS_IOS), "Must compile as macOS, not iOS");
static_assert(PA_CONFIG(DYNAMICALLY_SELECT_POOL_SIZE), "Every consumer needs dynamic masks");
static_assert(PA_BUILDFLAG(ENABLE_BACKUP_REF_PTR_SUPPORT), "Preserve BRP support");
static_assert(PA_BUILDFLAG(PA_DCHECK_IS_ON) && PA_BUILDFLAG(PA_EXPENSIVE_DCHECKS_ARE_ON), "Checks remain enabled");
static std::atomic<bool> used{false};
static std::atomic<unsigned> allocations{0},frees{0},failures{0};
static void Check(bool okay) {if (!okay) ++failures;}
[[noreturn]] static void OOM(size_t size) {
    fprintf(stderr,"[ideck-mac-pa126] oom-bytes=%zu\n",size);abort();
}
static void Batch(pa::PartitionRoot* root,bool brp,unsigned seed) {
    constexpr size_t sizes[]={1,16,128,4096,65536,2*1024*1024};
    void* objects[std::size(sizes)]={};
    for(unsigned i=0;i<std::size(sizes);++i) {
        objects[i]=root->Alloc(sizes[i]);++allocations;
        uintptr_t address=reinterpret_cast<uintptr_t>(objects[i]);
        Check(objects[i] && (brp ? pi::PartitionAddressSpace::IsInBRPPool(address)
                                  : pi::PartitionAddressSpace::IsInRegularPool(address)));
        for(unsigned j=0;j<i;++j) {
            uintptr_t earlier=reinterpret_cast<uintptr_t>(objects[j]);
            Check(address+sizes[i]<=earlier || earlier+sizes[j]<=address);
        }
        memset(objects[i],static_cast<int>((seed+i)&255),sizes[i]);
    }
    for(unsigned i=0;i<std::size(sizes);++i) {
        const auto* bytes=static_cast<const unsigned char*>(objects[i]);
        for(size_t j=0;j<sizes[i];++j)if(bytes[j]!=((seed+i)&255)){++failures;break;}
    }
    for(unsigned i:{2u,5u,0u,4u,1u,3u}){root->Free(objects[i]);++frees;}
}
extern "C" __attribute__((visibility("default")))
int IDeckRunMacAllocator(IDeckMacAllocatorResult* result,uint64_t capacity) {
    if(!result || capacity!=sizeof(*result))return 2;
    *result={};
    if(used.exchange(true))return 3;
    result->abi=2;result->compiled_mac=1;
    fputs("[ideck-mac-pa126] begin=1 compiled-mac=1 source-compact=1 dcheck=1 cef-integrated=0\n",stderr);
    pa::PartitionAllocGlobalInit(OOM);
    {
        pa::PartitionOptions options,protected_options;
        protected_options.backup_ref_ptr=pa::PartitionOptions::kEnabled;
        pa::PartitionAllocator normal(options),protected_pool(protected_options);
        auto* normal_root=normal.root();auto* brp_root=protected_pool.root();
        void* first=normal_root->Alloc(16);void* second=brp_root->Alloc(16);allocations+=2;
        auto regular=pi::PartitionAddressSpace::GetPoolInfo(reinterpret_cast<uintptr_t>(first));
        auto brp=pi::PartitionAddressSpace::GetPoolInfo(reinterpret_cast<uintptr_t>(second));
        result->pool_bytes=~regular.base_mask+1;
        result->disjoint=regular.base+result->pool_bytes<=brp.base || brp.base+result->pool_bytes<=regular.base;
        Check(result->pool_bytes==(256u<<20) && ~brp.base_mask+1==result->pool_bytes && result->disjoint);
#if PA_BUILDFLAG(GLUE_CORE_POOLS)
        result->glued=1;
        Check(brp.base==regular.base+result->pool_bytes);
        Check(pi::PartitionAddressSpace::CorePoolsSize()==2*result->pool_bytes);
        Check(pi::PartitionAddressSpace::IsInCorePools(reinterpret_cast<uintptr_t>(first)));
        Check(pi::PartitionAddressSpace::IsInCorePools(reinterpret_cast<uintptr_t>(second)));
        Check(!pi::PartitionAddressSpace::IsInCorePools(regular.base+2*result->pool_bytes));
#endif
        normal_root->Free(first);brp_root->Free(second);frees+=2;
        Batch(normal_root,false,13);Batch(brp_root,true,29);
        std::thread workers[4];
        for(unsigned i=0;i<4;++i)workers[i]=std::thread([=]{
            for(unsigned pass=0;pass<8;++pass){Batch(normal_root,false,pass+i*31);Batch(brp_root,true,pass+i*17);}
        });
        for(auto& worker:workers)worker.join();
    }
    Check(allocations==frees);
    pi::PartitionAddressSpace::UninitForTesting();
    Check(!pi::PartitionAddressSpace::IsInitialized());
    pa::PartitionAllocGlobalUninitForTesting();
    result->allocations=allocations.load();result->frees=frees.load();result->failures=failures.load();
    result->cleaned=!pi::PartitionAddressSpace::IsInitialized();
    fprintf(stderr,"[ideck-mac-pa126] complete=1 allocations=%llu frees=%llu workers=4 failures=%llu pool-bytes=%llu disjoint=%llu cleaned=%llu glued=%llu cef-integrated=0\n",
        (unsigned long long)result->allocations,(unsigned long long)result->frees,
        (unsigned long long)result->failures,(unsigned long long)result->pool_bytes,
        (unsigned long long)result->disjoint,(unsigned long long)result->cleaned,(unsigned long long)result->glued);
    return result->failures?1:0;
}
