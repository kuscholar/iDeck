#!/usr/bin/env python3
"""Generate a Windows PE conformance harness from FEX's own ASM test suite.

WHY
---
FEX ships 2,239 hand-written x86-64 instruction tests, each carrying the exact
expected register state in a CONFIG header. That is a golden-value suite written
by people who know where x86 semantics are subtle -- vastly better coverage than
anything we would hand-roll, and it costs us nothing to reuse.

But FEX's own runner (Source/Tools/TestHarnessRunner) is a LINUX tool: it wants
ELF loading, Linux syscalls, and mmap at fixed low addresses. None of that exists
on our target. So we re-host the test BODIES in a Windows PE that runs under our
actual shipping configuration -- our FEX fork, the ARM64EC/xtajit64 path, jitless
mode, our HostFeatures. Upstream CI never exercises that combination, which is
precisely where a divergence would hide.

CONTRACT (measured, not assumed)
--------------------------------
  - Tests terminate with `hlt`. FEX's runner treats that as "test complete and
    capture state". Here it becomes a jump to a capture epilogue.
  - 867 of the 1,306 ungated tests use a scratch region at 0xe0000000. That is a
    valid Win64 user VA, so the driver reserves it at a fixed base. If that
    reservation fails the driver must SAY SO rather than silently report passes.
  - Local labels (.data, .loop) bind to the preceding global label, so wrapping
    each test in its own global symbol keeps them collision-free.
  - Tests with a "HostFeatures" gate (e.g. AVX) are skipped: they assert
    behaviour for a CPU configuration we are not running.

DISCIPLINE
----------
Emits an explicit expected-count so a truncated run cannot masquerade as a clean
one, and every test is announced to the log BEFORE it runs, so a test that kills
the process names itself instead of leaving a silent gap.
"""

import json, os, re, sys, pathlib

FEX_ASM = pathlib.Path(__file__).resolve().parents[2] / "FEX" / "unittests" / "ASM"
OUT_DIR = pathlib.Path(__file__).resolve().parent / "asmconf_gen"
OUT_HDR = pathlib.Path(__file__).resolve().parent / "asmconf_tests.h"

# 64-bit GPR names as they appear in RegData, in our capture-buffer order.
GPRS = ["RAX","RBX","RCX","RDX","RSI","RDI","RBP","RSP",
        "R8","R9","R10","R11","R12","R13","R14","R15"]
NXMM = 16


def parse(path):
    """Return (config_dict, body_text) or None if the test is unusable/gated."""
    text = path.read_text(errors="replace")
    m = re.search(r"%ifdef\s+CONFIG\s*(\{.*?\})\s*%endif", text, re.S)
    if not m:
        return None
    try:
        cfg = json.loads(m.group(1))
    except json.JSONDecodeError:
        return None
    if "HostFeatures" in cfg:
        return None                      # asserts a CPU config we are not running
    if not cfg.get("RegData"):
        return None                      # nothing to check
    body = text[:m.start()] + text[m.end():]
    return cfg, body


# NASM keywords/mnemonics we must never mistake for a label reference.
_RESERVED = {
    "byte","word","dword","qword","oword","yword","zword","ptr","rel","abs",
    "times","db","dw","dd","dq","dt","resb","resw","resd","resq","equ","align",
    "section","global","extern","short","near","far","strict",
}

def rename_globals(body, sym):
    """Prefix every bare (non-dot) label defined in this body, and its uses."""
    names = set()
    for m in re.finditer(r"^\s*([A-Za-z_][A-Za-z0-9_$#@~?]*)\s*:", body, re.M):
        n = m.group(1)
        if n.lower() not in _RESERVED:
            names.add(n)
    for n in sorted(names, key=len, reverse=True):
        body = re.sub(rf"(?<![A-Za-z0-9_.$#@~?]){re.escape(n)}(?![A-Za-z0-9_$#@~?])",
                      f"{sym}__{n}", body)
    return body


def emit(tests, limit=None):
    """One .asm file per test.

    NASM macros and non-local labels are GLOBAL to a translation unit, and these
    tests freely define macros with the same names (`copy`, `cfmerge`,
    `check_flags` ...) with different bodies. Concatenating them lets test 900's
    macro silently redefine the meaning of test 200 -- which would produce
    failures that are artifacts of the harness, not of FEX. Per-test objects make
    that impossible by construction, and also remove the need to rename labels.
    """
    if limit:
        tests = tests[:limit]
    OUT_DIR.mkdir(exist_ok=True)
    for old in OUT_DIR.glob("t*.asm"):
        old.unlink()

    for idx, (name, cfg, body) in enumerate(tests):
        sym = f"asmconf_t{idx}"
        a = []
        a.append(f"; GENERATED from {name} -- do not edit by hand")
        a.append("BITS 64")
        a.append("DEFAULT REL")
        a.append("section .tcode exec write align=32")
        a.append(f"global {sym}")
        a.append("extern asmconf_regs")
        a.append("extern asmconf_save")
        a.append(f"{sym}:")
        # Rename bare (non-dot) labels per test. Even with one object per test,
        # NASM exports non-local labels into the COFF symbol table, so tests that
        # both define `_start` or `temp_data` collide at LINK time.
        body = rename_globals(body, sym)
        # Preserve the host's world. The test body owns every register, so save
        # to a static area (single-threaded by construction) rather than the
        # stack, which the body may also reposition.
        a.append("    mov [rel asmconf_save + 0*8], rsp")
        a.append("    mov [rel asmconf_save + 1*8], rbx")
        a.append("    mov [rel asmconf_save + 2*8], rbp")
        a.append("    mov [rel asmconf_save + 3*8], rsi")
        a.append("    mov [rel asmconf_save + 4*8], rdi")
        a.append("    mov [rel asmconf_save + 5*8], r12")
        a.append("    mov [rel asmconf_save + 6*8], r13")
        a.append("    mov [rel asmconf_save + 7*8], r14")
        a.append("    mov [rel asmconf_save + 8*8], r15")
        # Test body, with every `hlt` rewritten to jump to the capture epilogue.
        for line in body.splitlines():
            stripped = line.strip()
            if re.fullmatch(r"hlt\s*(;.*)?", stripped, re.I):
                a.append(f"    jmp {sym}_done")
            else:
                a.append(line)
        a.append(f"{sym}_done:")
        # Capture GPRs. rsp is captured as the test left it, before restore.
        for i, g in enumerate(GPRS):
            a.append(f"    mov [rel asmconf_regs + {i}*8], {g.lower()}")
        for i in range(NXMM):
            a.append(f"    movups [rel asmconf_regs + 128 + {i}*16], xmm{i}")
        a.append("    mov rsp, [rel asmconf_save + 0*8]")
        a.append("    mov rbx, [rel asmconf_save + 1*8]")
        a.append("    mov rbp, [rel asmconf_save + 2*8]")
        a.append("    mov rsi, [rel asmconf_save + 3*8]")
        a.append("    mov rdi, [rel asmconf_save + 4*8]")
        a.append("    mov r12, [rel asmconf_save + 5*8]")
        a.append("    mov r13, [rel asmconf_save + 6*8]")
        a.append("    mov r14, [rel asmconf_save + 7*8]")
        a.append("    mov r15, [rel asmconf_save + 8*8]")
        a.append("    ret")
        (OUT_DIR / f"t{idx}.asm").write_text("\n".join(a) + "\n")

    # Shared capture buffers live in their own object so every test can extern them.
    (OUT_DIR / "buffers.asm").write_text(
        "BITS 64\nDEFAULT REL\nsection .tdata data align=32\n"
        "global asmconf_regs\nglobal asmconf_save\n"
        "asmconf_regs: times (128 + 16*16) db 0\n"
        "asmconf_save: times (16*8) db 0\n")

    # Expected-value table for the C driver.
    h = ["/* GENERATED by gen_asmconf.py -- do not edit by hand */",
         "#ifndef ASMCONF_TESTS_H", "#define ASMCONF_TESTS_H", "",
         "typedef struct { const char *name; int reg; int lane; unsigned long long val; } asmconf_exp;",
         "/* reg: 0-15 = GPR index, 16+ = XMM index; lane = qword within the reg */", ""]
    for idx, (name, cfg, _) in enumerate(tests):
        h.append(f"extern void asmconf_t{idx}(void);")
    h.append("")
    h.append("static const struct { const char *name; void (*fn)(void); int first_exp, n_exp; } asmconf_tests[] = {")
    exps = []
    for idx, (name, cfg, _) in enumerate(tests):
        first = len(exps)
        for k, v in cfg["RegData"].items():
            ku = k.upper()
            if ku in GPRS:
                reg = GPRS.index(ku)
            elif ku.startswith("XMM"):
                reg = 16 + int(ku[3:])
            else:
                continue                            # MM/flags: not captured in v1
            vals = v if isinstance(v, list) else [v]
            for lane, item in enumerate(vals):
                if reg >= 16 and lane >= 2:
                    continue                        # 128-bit capture: skip AVX upper lanes
                exps.append((name, reg, lane, int(str(item), 16)))
        h.append(f'    {{ "{name}", asmconf_t{idx}, {first}, {len(exps)-first} }},')
    h.append("};")
    h.append(f"#define ASMCONF_NTESTS {len(tests)}")
    h.append(f"#define ASMCONF_NEXPECT {len(exps)}")
    h.append("")
    h.append("static const asmconf_exp asmconf_expected[] = {")
    for name, reg, lane, val in exps:
        h.append(f'    {{ "{name}", {reg}, {lane}, 0x{val:016X}ULL }},')
    h.append("};")
    h.append("#endif")
    OUT_HDR.write_text("\n".join(h) + "\n")
    return len(tests), len(exps)


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    tests, skipped = [], 0
    for p in sorted(FEX_ASM.rglob("*.asm")):
        r = parse(p)
        if r is None:
            skipped += 1
            continue
        cfg, body = r
        tests.append((str(p.relative_to(FEX_ASM)), cfg, body))
    n, e = emit(tests, limit)
    print(f"usable tests found : {len(tests)}   (skipped {skipped}: gated/no-RegData/unparsable)")
    print(f"emitted            : {n} tests, {e} expected register values")
    print(f"  {OUT_DIR}/ (one .asm per test + buffers.asm)")
    print(f"  {OUT_HDR}")


if __name__ == "__main__":
    main()
