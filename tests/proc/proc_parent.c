/* proc_parent.c — Steam S1 smoke test for pseudo-process CreateProcess.
 *
 * Spawns child-test.exe, waits for it, and checks the exit code (42).
 * The child's own stdout may or may not surface in the log depending on
 * console handle plumbing — the PASS signal is exit-code-only, which
 * exercises the full path Steam needs: NtCreateUserProcess → wineserver
 * process object → child thread group boots its own ntdll copy → runs PE
 * code → NtTerminateProcess → parent's process-handle wait wakes.
 */
#include <windows.h>

#ifndef CHILD_EXE_NAME
#define CHILD_EXE_NAME "child-test.exe"
#endif
#include <stdio.h>

static void out(const char *fmt, ...)
{
    char buf[2048];
    va_list ap;
    DWORD written;
    int len;
    va_start(ap, fmt);
    len = vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);
    WriteFile(GetStdHandle(STD_OUTPUT_HANDLE), buf, len, &written, NULL);
}

int main(void)
{
    STARTUPINFOA si;
    PROCESS_INFORMATION pi;
    /* depth=1: the child spawns a grandchild (itself at depth 0). Exercises
     * a 3-process tree with two simultaneous pseudo-processes. */
    char cmdline[] = "C:\\windows\\system32\\" CHILD_EXE_NAME " 1";
    DWORD wait_rc, exit_code = 0xdeadbeef;
    int pass;

    memset(&si, 0, sizeof(si));
    si.cb = sizeof(si);

    out("[proc-test] === Madeira S1 CreateProcess smoke test v2 (env + 3-deep tree) ===\n");

    /* Env inheritance: every process in the tree must see this. */
    if (!SetEnvironmentVariableA("MADEIRA_TEST_VAR", "steam-s1"))
        out("[proc-test] SetEnvironmentVariable FAILED err=%lu\n", GetLastError());

    out("[proc-test] parent pid=%lu spawning: %s\n",
        (unsigned long)GetCurrentProcessId(), cmdline);

    if (!CreateProcessA(NULL, cmdline, NULL, NULL, TRUE, 0, NULL, NULL, &si, &pi))
    {
        out("[proc-test] CreateProcessA FAILED err=%lu\n", GetLastError());
        out("[proc-test] === RESULT: FAIL ===\n");
        return 1;
    }
    out("[proc-test] child created: pid=%lu tid=%lu\n",
        (unsigned long)pi.dwProcessId, (unsigned long)pi.dwThreadId);

    wait_rc = WaitForSingleObject(pi.hProcess, 60000);
    out("[proc-test] WaitForSingleObject -> %lu (%s)\n", wait_rc,
        wait_rc == WAIT_OBJECT_0 ? "child exited" :
        wait_rc == WAIT_TIMEOUT  ? "TIMEOUT" : "error");

    if (!GetExitCodeProcess(pi.hProcess, &exit_code))
        out("[proc-test] GetExitCodeProcess FAILED err=%lu\n", GetLastError());
    out("[proc-test] child exit code = %lu (want 42)\n", (unsigned long)exit_code);

    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);

    pass = (wait_rc == WAIT_OBJECT_0 && exit_code == 42);
    out("[proc-test] === RESULT: %s ===\n", pass ? "PASS" : "FAIL");
    return pass ? 0 : 1;
}
