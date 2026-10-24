/* Observe the helper's shared IPC manager before changing its channel.
 * Replay the displaced instruction, preserve the complete volatile state,
 * and use the helper's own text logger. At most eight records per image.
 * This records ownership; it does not change the connection or its result. */
.intel_syntax noprefix
.text
.global sc_ipc_rebind
sc_ipc_rebind:
    mov qword ptr [rsp+0x18], rbx
    pushfq
    push rax
    push rcx
    push rdx
    push r8
    push r9
    push r10
    push r11
    sub rsp, 0x60
    movdqu xmmword ptr [rsp], xmm0
    movdqu xmmword ptr [rsp+0x10], xmm1
    movdqu xmmword ptr [rsp+0x20], xmm2
    movdqu xmmword ptr [rsp+0x30], xmm3
    movdqu xmmword ptr [rsp+0x40], xmm4
    movdqu xmmword ptr [rsp+0x50], xmm5
    cmp dword ptr [rip+rebind_counter], 8
    jae done
    mov eax, 1
    lock xadd dword ptr [rip+rebind_counter], eax
    cmp eax, 8
    jae done
    mov r8, rcx
    lea r9, [rcx+0x50]              /* previous std::wstring inline data */
    cmp qword ptr [rcx+0x68], 7
    jbe inline_name
    mov r9, qword ptr [rcx+0x50]    /* previous heap-backed channel name */
inline_name:
    sub rsp, 0x48                  /* Win64 alignment, shadow and variadics */
    mov qword ptr [rsp+0x20], rdx   /* requested channel name */
    mov rax, qword ptr [rsp+0xe8]   /* original caller's return address */
    mov qword ptr [rsp+0x28], rax
    lea rdx, [rip+message]
    xor ecx, ecx                   /* same log level as "Connecting to IPC" */
    call helper_log
    add rsp, 0x48
done:
    movdqu xmm0, xmmword ptr [rsp]
    movdqu xmm1, xmmword ptr [rsp+0x10]
    movdqu xmm2, xmmword ptr [rsp+0x20]
    movdqu xmm3, xmmword ptr [rsp+0x30]
    movdqu xmm4, xmmword ptr [rsp+0x40]
    movdqu xmm5, xmmword ptr [rsp+0x50]
    add rsp, 0x60
    pop r11
    pop r10
    pop r9
    pop r8
    pop rdx
    pop rcx
    pop rax
    popfq
    jmp connect_return
message:
    .asciz "[sc-ipc] rebind manager=%p old=%.80ls new=%.80ls caller=%p"
