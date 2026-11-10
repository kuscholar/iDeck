/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * Minimal Linux AArch64 glibc entry for our own dynamic diagnostic programs.
 * x0 on ELF entry is the loader finalizer. Keep the original stack alignment.
 */
.text
.global _start
.type _start,%function
_start:
    mov x5, x0
    mov x6, sp
    ldr x1, [sp]
    add x2, sp, #8
    adrp x0, main
    add x0, x0, :lo12:main
    mov x3, #0
    mov x4, #0
    bl __libc_start_main
    brk #0
