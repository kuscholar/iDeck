// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
// Actual Chromium126 allocator; no Steam, CEF, malloc interposition or JIT.
#import <UIKit/UIKit.h>
#include <atomic>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <thread>
#include "partition_alloc/partition_alloc.h"
#include "partition_alloc/partition_address_space.h"

namespace pa = partition_alloc;
namespace pi = partition_alloc::internal;
static std::atomic<unsigned> failures{0}, allocations{0}, frees{0};
static void Check(bool okay) { if (!okay) ++failures; }
[[noreturn]] static void OutOfMemory(size_t size) {
  fprintf(stderr,"[ideck-pa126] oom-bytes=%zu\n",size); abort();
}
static void Batch(pa::PartitionRoot* root, bool brp, unsigned seed) {
  constexpr size_t sizes[] = {1,16,128,4096,65536,2*1024*1024};
  void* objects[sizeof(sizes)/sizeof(sizes[0])] = {};
  for (unsigned i=0;i<std::size(sizes);++i) {
    objects[i]=root->Alloc(sizes[i]); ++allocations;
    uintptr_t addr=reinterpret_cast<uintptr_t>(objects[i]);
    Check(objects[i] && (brp ? pi::PartitionAddressSpace::IsInBRPPool(addr)
                            : pi::PartitionAddressSpace::IsInRegularPool(addr)));
    for (unsigned j=0;j<i;++j) {
      uintptr_t earlier=reinterpret_cast<uintptr_t>(objects[j]);
      Check(addr+sizes[i]<=earlier || earlier+sizes[j]<=addr);
    }
    memset(objects[i],static_cast<int>((seed+i)&255),sizes[i]);
  }
  for (unsigned i=0;i<std::size(sizes);++i) {
    const auto* bytes=static_cast<unsigned char*>(objects[i]);
    for(size_t j=0;j<sizes[i];++j) if(bytes[j]!=((seed+i)&255)) {++failures;break;}
  }
  // Non-LIFO frees exercise the actual slot/direct-map retirement paths.
  for (unsigned i : {2u,5u,0u,4u,1u,3u}) {root->Free(objects[i]);++frees;}
}
static unsigned Run() {
  fprintf(stderr,"[ideck-pa126] begin=1 chromium=126.0.6478.183 dcheck=1 brp=1 source-unmodified=1\n");
  pa::PartitionAllocGlobalInit(OutOfMemory);
  {
    pa::PartitionOptions normal, protected_opts;
    protected_opts.backup_ref_ptr=pa::PartitionOptions::kEnabled;
    pa::PartitionAllocator regular(normal), protected_pool(protected_opts);
    auto* regular_root=regular.root();auto* brp_root=protected_pool.root();
    void* normal_sample=regular_root->Alloc(16);++allocations;
    void* brp_sample=brp_root->Alloc(16);++allocations;
    auto normal_info=pi::PartitionAddressSpace::GetPoolInfo(reinterpret_cast<uintptr_t>(normal_sample));
    auto protected_info=pi::PartitionAddressSpace::GetPoolInfo(reinterpret_cast<uintptr_t>(brp_sample));
    const size_t pool_bytes=~normal_info.base_mask+1;
    Check(pool_bytes==(256u<<20));
    Check(~protected_info.base_mask+1==pool_bytes);
    const uintptr_t regular_base=normal_info.base;
    const uintptr_t brp_base=protected_info.base;
    regular_root->Free(normal_sample);brp_root->Free(brp_sample);frees+=2;
    Check(regular_base+pool_bytes<=brp_base || brp_base+pool_bytes<=regular_base);
    fprintf(stderr,"[ideck-pa126] pool-bytes=%zu pools-disjoint=%d\n",pool_bytes,
      regular_base+pool_bytes<=brp_base || brp_base+pool_bytes<=regular_base);
    Batch(regular_root,false,13);Batch(brp_root,true,29);
    std::thread workers[4];
    for(unsigned i=0;i<4;++i) workers[i]=std::thread([=]{
      for(unsigned pass=0;pass<8;++pass) {
        Batch(regular_root,false,pass+i*31);Batch(brp_root,true,pass+i*17);
      }
    });
    for(auto& worker:workers)worker.join();
  }
  Check(allocations==frees);
  // Only after every worker and root is destroyed may the test release pools.
  pi::PartitionAddressSpace::UninitForTesting();
  Check(!pi::PartitionAddressSpace::IsInitialized());
  pa::PartitionAllocGlobalUninitForTesting();
  fprintf(stderr,"[ideck-pa126] complete=1 allocations=%u frees=%u workers=4 failures=%u pools-uninitialized=%d cef-integrated=0\n",
    allocations.load(),frees.load(),failures.load(),!pi::PartitionAddressSpace::IsInitialized());
  return failures.load();
}
@interface IDeckPAScene : UIResponder <UIWindowSceneDelegate>
@property(strong,nonatomic) UIWindow* window;
@end
static UILabel* activeStatusLabel;
static NSString* completedStatus;
@implementation IDeckPAScene
- (void)scene:(UIScene*)scene willConnectToSession:(UISceneSession*)session options:(UISceneConnectionOptions*)options {
  (void)session;(void)options;
  if (![scene isKindOfClass:UIWindowScene.class]) return;
  fprintf(stderr,"[ideck-pa126] scene-connected=1\n");
  self.window=[[UIWindow alloc]initWithWindowScene:(UIWindowScene*)scene];
  UIViewController* controller=[UIViewController new];
  controller.view.backgroundColor=UIColor.systemBackgroundColor;
  UILabel* label=[[UILabel alloc]initWithFrame:controller.view.bounds];
  label.autoresizingMask=UIViewAutoresizingFlexibleWidth|UIViewAutoresizingFlexibleHeight;
  label.textAlignment=NSTextAlignmentCenter;label.numberOfLines=0;
  activeStatusLabel=label;
  label.text=completedStatus ?: @"Chromium 126 allocator\nTesting two 256 MiB pools…";
  [controller.view addSubview:label];self.window.rootViewController=controller;
  [self.window makeKeyAndVisible];
  // A scene reconnect must not run the global allocator teardown test twice.
  static dispatch_once_t once;
  dispatch_once(&once,^{
    dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INITIATED,0),^{
      unsigned count=Run();
      dispatch_async(dispatch_get_main_queue(),^{
        completedStatus=count ? @"Allocator test FAILED\nSee private device log" : @"Allocator test PASS\n256 MiB regular + BRP pools\n398 allocations / 398 frees\nCEF and Steam NOT tested";
        activeStatusLabel.text=completedStatus;
      });
    });
  });
}
@end
@interface IDeckPAApp : UIResponder <UIApplicationDelegate>
@end
@implementation IDeckPAApp
- (UISceneConfiguration*)application:(UIApplication*)app configurationForConnectingSceneSession:(UISceneSession*)session options:(UISceneConnectionOptions*)options {
  (void)app;(void)options;
  UISceneConfiguration* config=[[UISceneConfiguration alloc]initWithName:@"Allocator Probe" sessionRole:session.role];
  config.delegateClass=IDeckPAScene.class;
  return config;
}
@end
int main(int argc,char** argv) {
  @autoreleasepool {return UIApplicationMain(argc,argv,nil,NSStringFromClass(IDeckPAApp.class));}
}
