/* The single-process renderer must drain its own helper TLS MessageLoop.
 * The helper's original renderer call drains the browser's global I/O loop,
 * which may already be running on another thread. No lock or work discard. */
.intel_syntax noprefix
.text
.global sc_renderer_drain
sc_renderer_drain:
    sub rsp, 0x28
    call current_loop
    test rax, rax
    jz no_loop
    mov rcx, rax
    add rsp, 0x28
    jmp run_until_idle
no_loop:
    add rsp, 0x28
    ret
