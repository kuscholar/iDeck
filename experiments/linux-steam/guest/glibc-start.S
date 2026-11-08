/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
.text
.global _start
.type _start,%function
_start:
    mov x29, xzr
    mov x30, xzr
    ldr x1, [sp]
    add x2, sp, #8
    mov x6, sp
    mov x3, xzr
    mov x4, xzr
    mov x5, xzr
    adrp x0, main
    add x0, x0, :lo12:main
    bl __libc_start_main
    brk #0
