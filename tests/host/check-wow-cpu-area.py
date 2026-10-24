#!/usr/bin/env python3
"""FEX WOW64 module: the CPU area is kept current and RESET_STATE is honoured; no Wine or JIT runs.

The wineserver applies a cross-thread SetThreadContext to a 32-bit thread by writing its WoW64
CPU area and setting WOW64_CPURESERVED_FLAG_RESET_STATE while the thread is held in a system
call (build/wineserver/mach_ios.c), and a cross-thread GetThreadContext reads that area. This
checks FEX/Source/Windows/WOW64/Module.cpp at the pinned commit:

Part A: both HandleSyscallImpl exits (unix call and system call) store the JIT state into the
CPU area before they leave emitted code, and LockJITContext consumes RESET_STATE.
Part B compiles the production ConsumeCpuAreaReset / FlushCpuAreaForExit / LockJITContext /
UnlockJITContext against a stub TEB and counts reloads and stores.
"""
from pathlib import Path
import re, subprocess, tempfile

root = Path(__file__).resolve().parents[2]
mod = (root / "FEX/Source/Windows/WOW64/Module.cpp").read_text()

def function(source, start):
    a = source.index(start); b = source.index("{", a); depth = 1; c = b + 1
    while depth:
        depth += (source[c] == "{") - (source[c] == "}"); c += 1
    return source[a:c]

# ---- Part A
impl = function(mod, "static uint64_t HandleSyscallImpl(")
for call in ["WineUnixCall(", "Wow64SystemServiceEx("]:
    before = impl[:impl.index(call)]
    flush = before.rindex("Context::FlushCpuAreaForExit(TLS);")
    unlock = before.rindex("Context::UnlockJITContext(TLS);")
    assert flush < unlock and before.rindex("const auto TLS = GetTLS();") < flush, f"flush before unlock for {call}"
lock = function(mod, "void LockJITContext(TLS TLS)")
assert lock.index("ConsumeCpuAreaReset(TLS.TEB)") < lock.index("if (Expected & ControlBits::WOW_CPU_AREA_DIRTY)")
print("PASS: both syscall exits flush the CPU area before unlocking; LockJITContext consumes RESET_STATE first")

# ---- Part B
start = mod.index("#ifdef FEX_IOS_HOST\n/* MADEIRA: the CPU area is the 32-bit register state")
end = mod.index("}", mod.index("void UnlockJITContext(TLS TLS)")) + 1
prod = mod[start:end]
bits = mod[mod.index("namespace ControlBits {"):mod.index("}; // namespace ControlBits") + len("}; // namespace ControlBits")]
code = r"""
#include <atomic>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstddef>
typedef unsigned short USHORT;
struct _TEB { void* TlsSlots[64]; };
struct WOW64_CONTEXT { uint32_t ContextFlags; uint32_t Eax; };
namespace FEXCore::Core { struct InternalThreadState { uint32_t Eax; }; }
""" + bits + r"""
static _TEB g_self, g_other;
static _TEB* CurrentTEB() { return &g_self; }
struct TLS {
  _TEB* TEB;
  std::atomic<uint32_t>& ControlWord() const { return reinterpret_cast<std::atomic<uint32_t>&>(TEB->TlsSlots[17]); }
  FEXCore::Core::InternalThreadState*& ThreadState() const {
    return reinterpret_cast<FEXCore::Core::InternalThreadState*&>(TEB->TlsSlots[14]);
  }
};
struct CpuArea { USHORT Flags; USHORT Machine; WOW64_CONTEXT Context; };
static CpuArea g_area_self, g_area_other;
extern "C" long RtlWow64GetCurrentCpuArea(USHORT*, void** Context, void**) {
  *Context = &static_cast<CpuArea*>(CurrentTEB()->TlsSlots[1])->Context; return 0;
}
static uint64_t GetWowTEB(void*) { return 0x7ffd0000; }
static int loads, stores;
static WOW64_CONTEXT* last;
namespace Context {
void LoadStateFromWowContext(FEXCore::Core::InternalThreadState* T, uint64_t, WOW64_CONTEXT* C) { loads++; last = C; T->Eax = C->Eax; }
void StoreWowContextFromState(FEXCore::Core::InternalThreadState* T, WOW64_CONTEXT* C) { stores++; last = C; C->Eax = T->Eax; }
""" + prod + r"""
} // namespace Context
int main() {
  FEXCore::Core::InternalThreadState self_state {0x1111}, other_state {0x2222};
  g_self.TlsSlots[1] = &g_area_self; g_other.TlsSlots[1] = &g_area_other;
  TLS self {&g_self}, other {&g_other};
  self.ThreadState() = &self_state; other.ThreadState() = &other_state;

  // exit to a syscall: the JIT state lands in the thread's own CPU area
  Context::FlushCpuAreaForExit(self);
  assert(stores == 1 && last == &g_area_self.Context && g_area_self.Context.Eax == 0x1111);
  Context::UnlockJITContext(self);
  // back with nothing set: no reload
  Context::LockJITContext(self);
  assert(loads == 0 && (self.ControlWord().load() & ControlBits::IN_JIT));
  Context::UnlockJITContext(self);
  // a context set from outside while held in the call: reload once, flag consumed
  g_area_self.Context.Eax = 0x3333; g_area_self.Flags |= 1;
  Context::LockJITContext(self);
  assert(loads == 1 && last == &g_area_self.Context && self_state.Eax == 0x3333 && !(g_area_self.Flags & 1));
  Context::UnlockJITContext(self);
  Context::LockJITContext(self);
  assert(loads == 1);                                   // consumed: not reloaded again
  Context::UnlockJITContext(self);
  // the module's own WOW_CPU_AREA_DIRTY still reloads, as before
  self.ControlWord().fetch_or(ControlBits::WOW_CPU_AREA_DIRTY);
  Context::LockJITContext(self);
  assert(loads == 2 && !(self.ControlWord().load() & ControlBits::WOW_CPU_AREA_DIRTY));
  Context::UnlockJITContext(self);
  // another thread's TLS (BTCpuGetContext on a handle): its flag and area are left alone
  g_area_other.Flags |= 1;
  Context::LockJITContext(other);
  assert(loads == 2 && (g_area_other.Flags & 1));
  Context::UnlockJITContext(other);
  Context::FlushCpuAreaForExit(other);
  assert(stores == 1);
  // no CPU area published yet: nothing is touched
  g_self.TlsSlots[1] = nullptr;
  Context::FlushCpuAreaForExit(self);
  Context::LockJITContext(self);
  assert(stores == 1 && loads == 2);
  std::puts("cpu-area ok");
  return 0;
}
"""
with tempfile.TemporaryDirectory() as tmp:
    c = Path(tmp) / "check.cpp"; exe = Path(tmp) / "check"; c.write_text(code)
    subprocess.run(["c++", "-std=c++20", "-DFEX_IOS_HOST", "-O1", "-g", "-fsanitize=address,undefined",
                    "-fno-omit-frame-pointer", str(c), "-o", str(exe)], check=True)
    out = subprocess.run([str(exe)], check=True, capture_output=True, text=True)
    assert "cpu-area ok" in out.stdout, out.stdout + out.stderr
print("PASS: RESET_STATE reloads once and is consumed; DIRTY still reloads; other threads and an unpublished area are untouched")
