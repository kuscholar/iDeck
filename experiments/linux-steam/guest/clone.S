/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
.text
.global probe_clone
.type probe_clone,%function
probe_clone:
    sub x1, x1, #16
    str x2, [x1]
    mov x2, xzr
    mov x3, xzr
    mov x4, xzr
    mov x8, #220
    svc #0
    cbz x0, 1f
    ret
1:  ldr x9, [sp], #16
    blr x9
    mov x0, #99
    mov x8, #93
    svc #0
    brk #0
