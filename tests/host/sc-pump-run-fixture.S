/* Win64 stand-in for the pump's Run at the guarded RunState write sites, written
 * for this test (nothing here is taken from the helper). Only what the production
 * hooks rely on is fixed: the two hook sites, byte for byte, at +0x41 and +0x4b;
 * the RunState the install site publishes (delegate, dispatcher, quit, depth at
 * +0x14); rbx holding the pump and rdi the outer state across the call; and the
 * caller's rbx in the home slot the restore site reloads ([rsp+0x50] there).
 * Link at 0x1740e0. */
.intel_syntax noprefix
.section .fixture,"ax"
.global fixture_run, fixture_install, fixture_restore
fixture_run:
    mov qword ptr [rsp+8], rbx
    push rdi
    sub rsp, 0x40
    mov rbx, rcx
    mov rdi, qword ptr [rbx+0x40]
    mov qword ptr [rsp+0x20], rdx
    xor eax, eax
    mov qword ptr [rsp+0x28], rax
    mov byte ptr [rsp+0x30], al
    inc eax
    test rdi, rdi
    jz 1f
    add eax, dword ptr [rdi+0x14]
1:
    mov dword ptr [rsp+0x34], eax
    lea rax, [rsp+0x20]
    .org fixture_run + 0x41, 0x90
fixture_install:
    mov qword ptr [rcx+0x40], rax
    mov rax, qword ptr [rcx]
    call qword ptr [rax+0x28]
fixture_restore:
    mov qword ptr [rbx+0x40], rdi
    mov rbx, qword ptr [rsp+0x50]
    add rsp, 0x40
    pop rdi
    ret
