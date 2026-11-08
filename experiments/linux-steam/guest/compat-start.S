/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
.text
.global _start
.type _start,%function
_start:
    mov x0, sp
    bl compatibility_main
    mov x8, #94
    svc #0
    brk #0
