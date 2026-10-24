/* X3 mixed-mode pseudo-processes: per-process ntdll entry points.
 *
 * A cross-arch child (AMD64 exe under an aarch64 session) runs its own
 * ARM64EC ntdll image — the session's aarch64 ntdll has no EC syscall
 * thunks, KiUserEmulationDispatcher or load_arm64ec_module. The unix side
 * must then dispatch that child's user-mode entries (LdrInitializeThunk,
 * exception/APC/callback dispatchers) into the CHILD's image, not the
 * session globals. loader_ios.c owns the registry; signal_arm64_ios.c
 * consumes it via ios_cur_ntdll_funcs() (NULL → use the p* globals).
 */
#ifndef __MADEIRA_IOS_MIXED_H
#define __MADEIRA_IOS_MIXED_H

struct ios_ntdll_funcs
{
    void *LdrInitializeThunk;
    void *RtlUserThreadStart;
    void *KiUserExceptionDispatcher;
    void *KiUserApcDispatcher;
    void *KiUserCallbackDispatcher;
    void *KiUserEmulationDispatcher;
    void *KiRaiseUserExceptionDispatcher;
    void *DbgUiRemoteBreakin;
};

/* Current thread's pseudo-process ntdll funcs; NULL = session ntdll. */
extern const struct ios_ntdll_funcs *ios_cur_ntdll_funcs(void);

#endif /* __MADEIRA_IOS_MIXED_H */
