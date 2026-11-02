#!/usr/bin/env python3
"""Compile production Swift pair selection with actual failed-launch geometry."""
from pathlib import Path
import subprocess
import tempfile

source = (Path(__file__).resolve().parents[2] / 'app/Madeira/StikJITHelper.swift').read_text()


def function(name):
    start = source.index('    private static func ' + name)
    end = source.index('\n    }', start) + len('\n    }')
    return source[start:end].replace('private static func', 'static func')


start = source.index('            let ceiling: vm_address_t = 0x180000000')
end = source.index('                    if let pa = pairA {', start)
selection = source[start:end]
assert 'var best = keepLowForC ? 0 : singleFit' in selection
assert '(singleFit < vm_address_t(poolSize) || keepLowForC)' in selection
assert 'aFit >= 256 << 20' in selection and 'bFit >= 64 << 20' in selection
assert 'min(run.size, ceiling - run.base)' in selection

program = r'''
import Foundation
typealias vm_address_t = UInt
enum Test {
''' + function('poolRunSize(') + '\n' + function('cef64KeepsLowPoolFree(') + r'''
static func plan(_ holes: [(base: UInt, size: UInt)], _ wanted: Int,
                 _ env: [String: String], _ splitValue: String = "1",
                 _ windowHeld: Bool = true, _ pairOff: Bool = false)
    -> (a: (base: UInt, size: UInt), b: (base: UInt, size: UInt))? {
    let poolSize = wanted, pageFit = false
    let exeWinBase: UInt = 0x140000000, exeWinSize: UInt = 128 << 20
    let earlyPoolBase: UInt = 0x148000000
    let largest = holes.map { $0.size }.max() ?? 0
    var pairA: (base: UInt, size: UInt)?
    var selectedB: (base: UInt, size: UInt) = (0,0)
    for key in ["MADEIRA_CEF64_KEEP_LOW_POOL", "MADEIRA_STEAM_UI_SESSION", "MADEIRA_CEF64_SOURCE_LAYOUT"] {
        if let value = env[key] { setenv(key,value,1) } else { unsetenv(key) }
    }
''' + selection + r'''
                    selectedB = bestB
                }
            }
    guard let a = pairA else { return nil }
    return (a,selectedB)
}
}
let M: UInt = 1 << 20
let keys = ["MADEIRA_CEF64_KEEP_LOW_POOL", "MADEIRA_STEAM_UI_SESSION", "MADEIRA_CEF64_SOURCE_LAYOUT"]
var enabled = Dictionary(uniqueKeysWithValues: keys.map { ($0,"1") })
assert(Test.cef64KeepsLowPoolFree(enabled))
for key in keys {
    var e = enabled
    for bad in ["", "0", "true", "11"] { e[key]=bad; assert(!Test.cef64KeepsLowPoolFree(e)) }
    e.removeValue(forKey:key);assert(!Test.cef64KeepsLowPoolFree(e))
}
// Actual117 launch: a larger lower run wins in the ordinary algorithm and
// eliminates C. The opt-in permits existing A/B/mid allocation above it.
let holes: [(base:UInt,size:UInt)] = [(0x119ccc000,611*M),(0x148000000,285*M),
                                    (0x15bc00000,276*M),(0x16d67c000,297*M)]
assert(Test.plan(holes,704*Int(M),[:]) == nil)
assert(Test.plan(holes,544*Int(M),[:]) == nil)
for wanted in [544,704] {
    let p = Test.plan(holes,wanted*Int(M),enabled)!
    assert(p.a.base == 0x148000000 && p.a.size == 272*M)
    assert(p.b.base == 0x16d67c000 && p.b.size >= 64*M)
    assert(p.a.base+p.a.size <= p.b.base)
    assert(p.b.base+p.b.size <= 0x180000000)
    assert(p.a.size+p.b.size <= UInt(wanted)*M)
}
assert(Test.plan(holes,704*Int(M),enabled,"0") == nil)
assert(Test.plan(holes,704*Int(M),enabled,"1",false) == nil)
assert(Test.plan(holes,704*Int(M),enabled,"1",true,true) == nil)
assert(Test.plan([(0x119000000,611*M),(0x148000000,240*M)],704*Int(M),enabled) == nil)
// Existing single-above fit retains its ordinary steering, not a forced pair.
assert(Test.plan([(0x119000000,611*M),(0x148000000,592*M)],592*Int(M),enabled) == nil)
print("PASS actual Swift full64 gates and pair selection: failed-launch holes, budget/bounds, minima, default/disabled/single-fit paths; no device proof")
'''
with tempfile.TemporaryDirectory() as directory:
    directory = Path(directory)
    p = directory / 'plan.swift'
    p.write_text(program)
    subprocess.run(['swiftc', '-module-cache-path', str(directory / 'modules'),
                    str(p), '-o', str(directory / 'test')], check=True)
    subprocess.run([str(directory / 'test')], check=True)
