/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * HOST ONLY: measure ownership after real interpreter cleanup. Never starts
 * Wine, restores runtime signals, resets globals or touches a device session. */
#include "LinuxLabRuntime.h"
#include "kernel/task.h"
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#if IDECK_TEST_NATIVE_SIGNAL_LEASE
#include "NativeSignalLease.h"
#include <errno.h>
#endif

static int failures;
static void check(const char *name, int ok) {
    printf("%s=%s\n", name, ok ? "PASS" : "FAIL");
    if (!ok) failures++;
}
static void previous_owner(int sig) { (void)sig; }
static int live_guests(void) {
    int count=0;
    lock(&pids_lock);
    for (unsigned i=2;i<MAX_PID;i++) if (pid_get_task(i)) count++;
    unlock(&pids_lock);
    return count;
}
static int same_action(const struct sigaction *a, const struct sigaction *b) {
    if (a->sa_flags!=b->sa_flags || a->sa_handler!=b->sa_handler) return 0;
    for (int sig=1;sig<NSIG;sig++)
        if (sigismember(&a->sa_mask,sig)!=sigismember(&b->sa_mask,sig)) return 0;
    return 1;
}
int main(int argc, char **argv) {
    if (argc!=3 || (strcmp(argv[2],"normal") && strcmp(argv[2],"failure"))) return 2;
    struct sigaction owner={0},before_usr1,before_pipe,after_usr1,after_pipe;
    owner.sa_handler=previous_owner;
    owner.sa_flags=SA_RESTART;
    sigemptyset(&owner.sa_mask);
    sigaddset(&owner.sa_mask,SIGUSR2);
    if (sigaction(SIGUSR1,&owner,NULL) || sigaction(SIGPIPE,&owner,NULL) ||
        sigaction(SIGUSR1,NULL,&before_usr1) || sigaction(SIGPIPE,NULL,&before_pipe)) return 3;
#if IDECK_TEST_NATIVE_SIGNAL_LEASE
    extern void sigusr1_handler(int);
    struct ideck_signal_lease *lease=ideck_signal_lease_capture(sigusr1_handler);
    if (!lease) return 5;
#endif
    dup2(2,666);
    int result=ideck_linux_lab_run(argv[1]);
    /* The standard probe exits1 when its clone cannot start. The older orphan
     * probe exits2 for the same injected condition; do not reuse its status. */
    check("expected-real-guest-status",result==(!strcmp(argv[2],"failure")?256:0));
    struct timespec tick={0,10000000};
    for (unsigned i=0;i<300;i++) {
        if (!live_guests() && ideck_linux_lab_live_guest_threads()==0) break;
        nanosleep(&tick,NULL);
    }
    check("no-live-guest-table-entries",live_guests()==0);
    check("all-native-guest-reservations-retired",ideck_linux_lab_live_guest_threads()==0);
    if (sigaction(SIGUSR1,NULL,&after_usr1) || sigaction(SIGPIPE,NULL,&after_pipe)) return 4;
    extern void sigusr1_handler(int);
    check("usr1-still-owned-by-linuxrunner",after_usr1.sa_handler==sigusr1_handler);
    check("pipe-still-ignored-by-linuxrunner",after_pipe.sa_handler==SIG_IGN);
    check("usr1-prior-owner-not-restored",!same_action(&before_usr1,&after_usr1));
    check("pipe-prior-owner-not-restored",!same_action(&before_pipe,&after_pipe));
#if IDECK_TEST_NATIVE_SIGNAL_LEASE
    check("real-linux-signal-ownership-recorded",ideck_signal_lease_claim(lease)==0);
    /* Deliberately UNKNOWN: the entry counter excludes timer/profile/TTY/
     * forwarding workers. Do not invent a full-quiescence assertion here. */
    struct ideck_signal_quiescence proof={1,1,live_guests(),ideck_linux_lab_live_guest_threads(),-1};
    check("unknown-other-workers-refuse-release",ideck_signal_lease_release(lease,&proof)==-EAGAIN);
    struct sigaction refused_usr1,refused_pipe;
    if (sigaction(SIGUSR1,NULL,&refused_usr1) || sigaction(SIGPIPE,NULL,&refused_pipe)) return 6;
    check("refusal-preserves-real-linux-handlers",same_action(&after_usr1,&refused_usr1)&&same_action(&after_pipe,&refused_pipe));
    check("owned-lease-cannot-be-discarded",ideck_signal_lease_destroy(lease)==-EBUSY);
    /* This one host test process now exits normally, reclaiming its deliberately
     * still-owned lease. No runtime restart or signal restoration was allowed. */
#endif
    check("native-runtime-reentry-remains-refused",ideck_linux_lab_run(argv[1])==-16);
    puts("scope=host signal ownership only; no Wine/iPad shutdown or handoff success");
    return failures?1:0;
}
