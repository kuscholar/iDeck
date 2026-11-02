#!/usr/bin/env python3
"""Compile actual Swift exact-B ownership, RX validation and rollback policy."""
from pathlib import Path
import subprocess
import tempfile

source = (Path(__file__).resolve().parents[2] / 'app/Madeira/StikJITHelper.swift').read_text()


def function(name):
    start = source.index('    private static func ' + name)
    end = source.index('\n    }', start) + len('\n    }')
    return source[start:end].replace('private static func', 'static func')


program = r'''
import Foundation
typealias vm_address_t = UInt
typealias vm_size_t = UInt
typealias mach_port_t = UInt32
typealias mach_msg_type_number_t = UInt32
let mach_task_self_: UInt32 = 17
let KERN_SUCCESS: Int32 = 0
let VM_REGION_BASIC_INFO_64: Int32 = 9
let VM_PROT_READ: Int32 = 1, VM_PROT_WRITE: Int32 = 2, VM_PROT_EXECUTE: Int32 = 4
struct vm_region_basic_info_data_64_t { var protection: Int32 = 0 }
enum Level { case info,error }
struct LogStore { static let shared=LogStore();func log(_ s:String,level:Level = .info) {} }
struct Region { var base:UInt;var size:UInt;var prot:Int32 }
var regions:[Region]=[],allocError:Int32=0,wrongAllocation=false,wrongReply=false
var allocationCalls=0,prepareCalls=0,protectCalls=0,queryCalls=0,portReleases=0,released:[(UInt,UInt)]=[]
var preparedProtection:Int32=5
var protectError:Int32=0
func vm_allocate(_ task:UInt32,_ address:UnsafeMutablePointer<UInt>,_ size:UInt,_ flags:Int32)->Int32 {
    assert(task==17&&flags==0);allocationCalls+=1
    if allocError != 0{return allocError}
    if wrongAllocation{address.pointee+=0x10000}
    regions=[Region(base:address.pointee,size:size,prot:3)];return 0
}
func vm_deallocate(_ task:UInt32,_ address:UInt,_ size:UInt) {
    assert(task==17);released.append((address,size));regions=[]
}
func mach_port_deallocate(_ task:UInt32,_ port:UInt32) {assert(task==17&&port==73);portReleases+=1}
func jit26_prepare_region(_ pointer:UnsafeMutableRawPointer?,_ size:Int)->UnsafeMutableRawPointer? {
    assert(pointer != nil&&size>0);prepareCalls+=1
    regions=[Region(base:UInt(bitPattern:pointer!),size:UInt(size),prot:3)]
    return wrongReply ? UnsafeMutableRawPointer(bitPattern:0x7770000000) : pointer
}
func vm_protect(_ task:UInt32,_ base:UInt,_ size:UInt,_ maximum:Int32,_ protection:Int32)->Int32 {
    assert(task==17&&maximum==0&&protection==5&&prepareCalls==1);protectCalls+=1
    if protectError != 0{return protectError}
    regions=[Region(base:base,size:size,prot:preparedProtection)];return 0
}
func vm_region_64(_ task:UInt32,_ address:UnsafeMutablePointer<UInt>,_ length:UnsafeMutablePointer<UInt>,
                  _ flavor:Int32,_ info:UnsafeMutablePointer<Int32>,_ count:UnsafeMutablePointer<UInt32>,
                  _ object:UnsafeMutablePointer<UInt32>)->Int32 {
    assert(task==17&&flavor==9&&count.pointee>0);queryCalls+=1
    guard let r=regions.first(where:{ $0.base>=address.pointee || (address.pointee >= $0.base && address.pointee-$0.base < $0.size)}) else {return 1}
    address.pointee=r.base;length.pointee=r.size;info.pointee=r.prot;object.pointee=73;return 0
}
func reset() {
    regions=[];allocError=0;wrongAllocation=false;wrongReply=false;preparedProtection=5
    allocationCalls=0;prepareCalls=0;protectCalls=0;protectError=0;queryCalls=0;portReleases=0;released=[]
}
enum Test {
''' + function('cef64ExactSecondPool(') + '\n' + function('poolRangeIsRX(') + '\n' + function('prepareExactSecondPool(') + r'''
}
let base:UInt=0x16b4ec000,size:UInt=160<<20
let keys=["MADEIRA_CEF64_EXACT_POOL_B","MADEIRA_STEAM_UI_SESSION","MADEIRA_CEF64_SOURCE_LAYOUT"]
let enabled=Dictionary(uniqueKeysWithValues:keys.map{($0,"1")})
assert(Test.cef64ExactSecondPool(enabled))
for key in keys {
    var e=enabled
    for value in ["","0","true","11"] {e[key]=value;assert(!Test.cef64ExactSecondPool(e))}
    e.removeValue(forKey:key);assert(!Test.cef64ExactSecondPool(e))
}
reset();assert(Test.prepareExactSecondPool(base,size)==UnsafeMutableRawPointer(bitPattern:base))
assert(allocationCalls==1&&prepareCalls==1&&released.isEmpty&&queryCalls==portReleases)
assert(protectCalls==1)
reset();allocError=3;assert(Test.prepareExactSecondPool(base,size)==nil)
assert(allocationCalls==1&&prepareCalls==0&&released.isEmpty)
reset();wrongAllocation=true;assert(Test.prepareExactSecondPool(base,size)==nil)
assert(prepareCalls==0&&released.count==1&&released[0].0==base+0x10000)
reset();wrongReply=true;assert(Test.prepareExactSecondPool(base,size)==nil)
assert(prepareCalls==1&&released.count==1&&released[0].0==base) // Never free foreign reply.
assert(protectCalls==0)
reset();protectError=2;assert(Test.prepareExactSecondPool(base,size)==nil)
assert(prepareCalls==1&&protectCalls==1&&queryCalls==0&&released.count==1)
for protection:Int32 in [0,1,3,7] {
    reset();preparedProtection=protection;assert(Test.prepareExactSecondPool(base,size)==nil)
    assert(prepareCalls==1&&released.count==1&&released[0].0==base&&queryCalls==portReleases)
}
for (b,s):(UInt,UInt) in [(0x140000000,size),(base,32<<20),(base+1,size),(base,size+1),(0x17f000000,size),(UInt.max,size)] {
    reset();assert(Test.prepareExactSecondPool(b,s)==nil&&allocationCalls==0&&prepareCalls==0)
}
reset();regions=[Region(base:base,size:0x4000,prot:5),Region(base:base+0x4000,size:0x4000,prot:5)]
assert(Test.poolRangeIsRX(base,0x8000)&&queryCalls==2&&portReleases==2)
reset();regions=[Region(base:base,size:0x4000,prot:5),Region(base:base+0x8000,size:0x4000,prot:5)]
assert(!Test.poolRangeIsRX(base,0xc000)&&queryCalls==portReleases)
reset();regions=[Region(base:base,size:0x4000,prot:5)]
assert(!Test.poolRangeIsRX(base,0x8000))
reset();assert(!Test.poolRangeIsRX(UInt.max-1,4)&&queryCalls==0)
print("PASS actual Swift exact-B: triple gate, no-overwrite claim, non-null debugger prepare, full RX coverage, owned-only rollback, no retry/foreign free; host simulation only")
'''
with tempfile.TemporaryDirectory() as directory:
    directory = Path(directory)
    swift = directory / 'exact.swift'
    # Bind platform calls to mocks explicitly; never dispatch a host Mach API.
    for name in ['vm_allocate', 'vm_deallocate', 'vm_protect', 'mach_port_deallocate', 'vm_region_64']:
        program = program.replace(name + '(', 'test_' + name + '(')
    swift.write_text(program)
    subprocess.run(['swiftc', '-module-cache-path', str(directory / 'modules'),
                    str(swift), '-o', str(directory / 'test')], check=True)
    subprocess.run([str(directory / 'test')], check=True)
