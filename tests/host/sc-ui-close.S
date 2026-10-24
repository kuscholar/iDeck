/* Observe the constructor of message 0x20005 without changing its payload or
 * delivery. The guarded constructor takes only RCX=this, RDX=payload; it sets
 * R8/R9 itself before its first call and reads no incoming vector arguments.
 * Replay its RBX home store, retain both inputs across the logger, then resume
 * its original body. For the guarded 0x32070 delegate call only, its known
 * frame gives the parent caller and its owning window field gives the HWND.
 * Other constructor callers carry no such frame/object assumption.
 * At most 16 scalar records per image; no URLs or tickets.
 */
.intel_syntax noprefix
.text
.global sc_ui_close
sc_ui_close:
    mov qword ptr [rsp+0x10], rbx
    push rcx
    push rdx
    sub rsp, 0x38                 /* aligned Win64 call, shadow + one vararg */
    cmp dword ptr [rip+close_count], 16
    jae done
    mov eax, 1
    lock xadd dword ptr [rip+close_count], eax
    cmp eax, 16
    jae done
    mov r8d, dword ptr [rdx]       /* the original four-byte payload */
    mov r9, rdx                   /* which object's field supplied it */
    mov rax, qword ptr [rsp+0x48]  /* original constructor caller */
    mov qword ptr [rsp+0x20], rax
    xor r10d, r10d
    mov qword ptr [rsp+0x28], r10  /* unknown delegate: no parent/HWND read */
    mov qword ptr [rsp+0x30], r10
    lea r10, [rip+delegate_caller]
    cmp rax, r10
    jne log
    mov rax, qword ptr [rsp+0x78]  /* 0x32070 pushes RBX and allocates 0x20 */
    mov qword ptr [rsp+0x28], rax
    mov rax, qword ptr [r9+0x188]  /* source=owner+0x10; HWND=owner+0x198 */
    mov qword ptr [rsp+0x30], rax
log:
    lea rdx, [rip+message]
    xor ecx, ecx
    call helper_log
done:
    add rsp, 0x38
    pop rdx
    pop rcx
    jmp ctor_continue
message:
    .asciz "[sc-ui] msg20005 value=%u source=%p caller=%p origin=%p hwnd=%p"
