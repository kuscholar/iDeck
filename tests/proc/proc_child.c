/* proc_child.c — the child side of the S1 CreateProcess smoke test (v2).
 *
 * argv[1] = depth. At depth > 0 the child spawns ITSELF at depth-1 (the
 * grandchild) and requires its exit code to be 42 — so a 3-process tree
 * runs with two pseudo-processes alive at once (two ntdll copies, two
 * owner_peb entries, the global-peb flip happening twice). Every level
 * also verifies MADEIRA_TEST_VAR inherited from the top-level parent.
 *
 * Exit codes: 42 = all good; 51 = env var missing/wrong; 52 = grandchild
 * spawn failed; 53 = grandchild wait/exit-code wrong; 7/8 = memory checks.
 */
#include <windows.h>

#ifndef CHILD_EXE_NAME
#define CHILD_EXE_NAME "child-test.exe"
#endif
#include <stdio.h>
#include <stdlib.h>

static void out(const char *fmt, ...)
{
    char buf[1024];
    va_list ap;
    DWORD written;
    int len;
    va_start(ap, fmt);
    len = vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);
    WriteFile(GetStdHandle(STD_OUTPUT_HANDLE), buf, len, &written, NULL);
}

int main(int argc, char **argv)
{
    void *mem;
    char envbuf[64];
    DWORD envlen;
    int depth = (argc > 1) ? atoi(argv[1]) : 0;

    out("[child-test] alive! pid=%lu depth=%d\n",
        (unsigned long)GetCurrentProcessId(), depth);

    /* Env inheritance check (set by the top-level parent) */
    envlen = GetEnvironmentVariableA("MADEIRA_TEST_VAR", envbuf, sizeof(envbuf));
    if (!envlen || strcmp(envbuf, "steam-s1") != 0)
    {
        out("[child-test] depth=%d env MADEIRA_TEST_VAR=%s (len=%lu) — WRONG\n",
            depth, envlen ? envbuf : "(unset)", (unsigned long)envlen);
        return 51;
    }
    out("[child-test] depth=%d env MADEIRA_TEST_VAR=%s OK\n", depth, envbuf);

    /* Exercise virtual memory + heap in this process's own context */
    mem = VirtualAlloc(NULL, 0x10000, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
    if (!mem)
    {
        out("[child-test] VirtualAlloc FAILED err=%lu\n", GetLastError());
        return 7;
    }
    memset(mem, 0xAB, 0x10000);
    if (((unsigned char *)mem)[0x8000] != 0xAB)
    {
        out("[child-test] memory readback MISMATCH\n");
        return 8;
    }
    VirtualFree(mem, 0, MEM_RELEASE);

    if (depth > 0)
    {
        STARTUPINFOA si;
        PROCESS_INFORMATION pi;
        char cmdline[128];
        DWORD wait_rc, exit_code = 0xdeadbeef;

        memset(&si, 0, sizeof(si));
        si.cb = sizeof(si);
        snprintf(cmdline, sizeof(cmdline),
                 "C:\\windows\\system32\\" CHILD_EXE_NAME " %d", depth - 1);
        out("[child-test] depth=%d spawning grandchild: %s\n", depth, cmdline);

        if (!CreateProcessA(NULL, cmdline, NULL, NULL, TRUE, 0, NULL, NULL, &si, &pi))
        {
            out("[child-test] depth=%d CreateProcessA FAILED err=%lu\n",
                depth, GetLastError());
            return 52;
        }
        wait_rc = WaitForSingleObject(pi.hProcess, 60000);
        GetExitCodeProcess(pi.hProcess, &exit_code);
        CloseHandle(pi.hThread);
        CloseHandle(pi.hProcess);
        out("[child-test] depth=%d grandchild wait=%lu exit=%lu\n",
            depth, wait_rc, exit_code);
        if (wait_rc != WAIT_OBJECT_0 || exit_code != 42) return 53;
    }

    Sleep(200);
    out("[child-test] depth=%d done, exiting 42\n", depth);
    return 42;
}
