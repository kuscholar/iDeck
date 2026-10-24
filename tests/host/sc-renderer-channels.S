/* A single renderer hosts several pages. Keep their existing IPC connections;
 * the embedded client has 64 connection slots. At capacity, leave the current
 * connections intact and resume the original reply cleanup without opening
 * another transport. Explicit disconnects and shutdown are unchanged. */
.intel_syntax noprefix
.text
.global sc_renderer_channel_keep
sc_renderer_channel_keep:
    cmp dword ptr [rax+0x220], 64   /* Manager::client (+0x198), count (+0x88) */
    jae full
    xor r8d, r8d                  /* Connect(name, replace_old=false) */
    mov rcx, rax                  /* displaced instruction */
    jmp reply_continue            /* next TEST recomputes the flags */
full:
    jmp reply_cleanup             /* existing CefString/ref cleanup */
