#!/usr/bin/env python3
"""A TEB access whose base register was computed from a zeroed x18 is repaired
in the Mach handler, also when the ADD wrote its own index register; no Wine.

iOS zeroes x18 on a context switch. build/ntdll-unix/signal_arm64_ios.c then
emulates a faulting load or store against the real TEB when its base register
is x18, or (ios_x18_derived_base) was computed from x18 by the instruction
right before it, directly or in the x18 patcher's "via x18" trampoline. That
check used to decline an ADD whose other operand is its own destination,
`add x8, x18, x8, lsl #3`: Horizon Zero Dawn died on build 500 (2026-10-11
19:17) at madeira_d3d12.dll+0x15ed4, `ldr x0, [x8, #0x1480]` reading 0x1508
(TEB 0 + TLS slot 17), pc-4 = `b` 0x141018d3 into that trampoline. The
emulation needs only the fault address, so the form is accepted now.

Compiles ios_x18_derived_base from the source with a fake instruction memory
and checks, with encodings from the AArch64 assembler:
  - the build-500 crash (its own words) and the same ADD right before the load
    are repaired, as are Wine's TlsGetValue `add x8, x18, w0, uxtw #3`,
    `add x8, x18, w8, uxtw #3`, `add x8, x18, x9`, `add x8, x8, x18`,
    `add x8, x9, x18`, `add x8, x18, #16` and `mov x8, x18`;
  - declined: x18 shifted, an ADD that wrote another register, no x18, SUB,
    a base of x18 itself or x29..x31, an unreadable pc-4, and a trampoline that
    is not the "via x18" one or does not branch back to the fault;
and textually that the handler emulates only with x18 == 0, a fault address
below 0x10000, and the access at thread_teb + fault_addr.
Needs python3 and a C compiler.
"""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
src = (root / 'build/ntdll-unix/signal_arm64_ios.c').read_text()


def function(signature):
    start = src.index(signature + '\n{')
    return src[start:src.index('\n}\n', start) + 3]


code = function('static int ios_x18_derived_base( uint64_t fault_pc, int rn )')

harness = r'''
#include <stdint.h>
#include <stdio.h>
struct word { uint64_t a; uint32_t w; };
static struct word mem[16];
static int nmem;
static void put(uint64_t a, uint32_t w) { mem[nmem].a = a; mem[nmem].w = w; nmem++; }
static int ios_fault_read_insn( uint64_t fault_pc, uint32_t *out )
{
    int i;
    for (i = 0; i < nmem; i++) if (mem[i].a == fault_pc) { *out = mem[i].w; return 1; }
    *out = 0;
    return 0;
}
''' + code + r'''
static int fails;
#define CHECK(c, ...) do { if (!(c)) { printf("FAIL: " __VA_ARGS__); printf("\n"); fails++; } } while (0)
#define PC 0x15368ded4ull                       /* build 500's fault pc */
#define LDR_X0_X8_1480 0xf94a4100u              /* ldr x0, [x8, #0x1480] */
#define MRS_X18 0xd53bd072u                     /* mrs x18, TPIDRRO_EL0 */
#define MRS_X8  0xd53bd068u                     /* mrs x8, TPIDRRO_EL0 */
#define AND_X18 0x927df252u                     /* and x18, x18, #~7 */
#define LDR_X18_SLOT 0xf9407252u                /* ldr x18, [x18, #0xe0] */
static uint32_t b_to(uint64_t from, uint64_t to) { return 0x14000000u | (uint32_t)(((int64_t)(to - from) >> 2) & 0x3ffffff); }

/* the instruction right before the load */
static int direct(uint32_t prev, int rn)
{
    nmem = 0;
    put(PC - 4, prev); put(PC, LDR_X0_X8_1480);
    return ios_x18_derived_base(PC, rn);
}
/* the patcher's "via x18" trampoline: b tramp at pc-4, the ADD at tramp+12 */
static int tramp(uint32_t first, uint32_t add, uint64_t back)
{
    uint64_t t = PC - 4 + 0x40634c;
    nmem = 0;
    put(PC - 4, b_to(PC - 4, t)); put(PC, LDR_X0_X8_1480);
    put(t, first); put(t + 4, AND_X18); put(t + 8, LDR_X18_SLOT); put(t + 12, add); put(t + 16, b_to(t + 16, back));
    return ios_x18_derived_base(PC, 8);
}

int main(void)
{
    /* 1: build 500, with the log's own pc-4 word */
    CHECK(b_to(PC - 4, PC - 4 + 0x40634c) == 0x141018d3u, "the trampoline branch does not encode as the log's 141018d3");
    CHECK(tramp(MRS_X18, 0x8b080e48u, PC), "HZD build 500: add x8, x18, x8, lsl #3 in the via-x18 trampoline declined");
    CHECK(direct(0x8b080e48u, 8), "add x8, x18, x8, lsl #3 right before the load declined");

    /* 2: the forms repaired before, and the other own-index forms */
    CHECK(direct(0x8b204e48u, 8), "add x8, x18, w0, uxtw #3 (Wine's TlsGetValue) declined");
    CHECK(direct(0x8b284e48u, 8), "add x8, x18, w8, uxtw #3 declined");
    CHECK(direct(0x8b090248u, 8), "add x8, x18, x9 declined");
    CHECK(direct(0x8b120108u, 8), "add x8, x8, x18 declined");
    CHECK(direct(0x8b120128u, 8), "add x8, x9, x18 declined");
    CHECK(direct(0x91004248u, 8), "add x8, x18, #16 declined");
    CHECK(direct(0xaa1203e8u, 8), "mov x8, x18 declined");
    CHECK(tramp(MRS_X18, 0x8b204e48u, PC), "add x8, x18, w0, uxtw #3 in the trampoline declined");

    /* 3: not a TEB offset in the base register */
    CHECK(!direct(0x8b120d28u, 8), "add x8, x9, x18, lsl #3 (x18 shifted) accepted");
    CHECK(!direct(0x8b080249u, 8), "add x9, x18, x8 accepted for base x8");
    CHECK(!direct(0x8b0a0128u, 8), "add x8, x9, x10 accepted");
    CHECK(!direct(0xcb080248u, 8), "sub x8, x18, x8 accepted");
    CHECK(!direct(0x8b080e48u, 18), "a base of x18 itself went through the derived check");
    CHECK(!direct(0x8b080e48u, 29) && !direct(0x8b080e48u, 31), "x29..x31 accepted");
    nmem = 0;
    CHECK(!ios_x18_derived_base(PC, 8), "an unreadable pc-4 accepted");

    /* 4: a trampoline of another shape, or one that does not come back here */
    CHECK(!tramp(MRS_X8, 0x8b080e48u, PC), "a via-destination trampoline (mrs x8) followed");
    CHECK(!tramp(MRS_X18, 0x8b080e48u, PC + 4), "a trampoline branching elsewhere followed");
    {
        uint64_t t = PC - 4 + 0x40634c;
        nmem = 0;
        put(PC - 4, b_to(PC - 4, t)); put(PC, LDR_X0_X8_1480);
        put(t, MRS_X18); put(t + 4, AND_X18); put(t + 8, LDR_X18_SLOT); put(t + 12, 0x8b080e48u); put(t + 16, 0xd65f03c0u);
        CHECK(!ios_x18_derived_base(PC, 8), "a trampoline ending in ret followed");
    }

    if (fails) return 1;
    printf("PASS: build 500's add x8, x18, x8, lsl #3 (direct and in the via-x18 trampoline) and every x18 ADD/MOV form are repaired; "
           "shifted x18, other registers, SUB and foreign trampolines are declined\n");
    return 0;
}
'''

with tempfile.TemporaryDirectory(prefix='madeira-x18-derived-') as directory:
    c = Path(directory) / 'x18.c'
    exe = Path(directory) / 'x18'
    c.write_text(harness)
    build = subprocess.run(['cc', '-std=gnu11', '-Wall', '-Werror', '-Wno-unused-function',
                            '-fsanitize=address,undefined', '-o', str(exe), str(c)],
                           capture_output=True, text=True)
    assert build.returncode == 0, build.stdout + build.stderr
    run = subprocess.run([str(exe)], capture_output=True, text=True)
    print(run.stdout, end='')
    assert run.returncode == 0, run.stdout + run.stderr

# --- the emulation the check feeds: x18 == 0, a TEB offset, thread_teb + fault_addr ---
emu = src[src.index('            if (!handled && state.__x[18] == 0 && thread_teb)\n'):]
emu = emu[:emu.index('                        switch (insn & 0xffc00000)')]
assert 'if (!is_exec_fault && fault_addr < 0x10000 &&' in emu, 'the x18 emulation must take only fault addresses below 0x10000'
assert 'int x18_derived = ios_x18_derived_base( fault_pc, rn );' in emu, 'the handler must ask ios_x18_derived_base'
assert emu.index('int x18_derived = ios_x18_derived_base( fault_pc, rn );') < emu.index('if (rn == 18 || x18_derived)') \
    < emu.index('uintptr_t ea = thread_teb + fault_addr;'), 'a derived base must be emulated at thread_teb + fault_addr'
print('PASS: the handler emulates a derived base only with x18 == 0 and a fault address below 0x10000, at thread_teb + fault_addr')
