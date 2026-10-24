/*
 * Unix interface for Win32 syscalls, iOS override
 *
 * Copyright (C) 2021 Alexandre Julliard
 * Copyright 2026 125hz
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2.1 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301, USA
 */

/* Wraps wine/dlls/win32u/syscall.c and adds win32u_zero_bits().
 *
 * Upstream win32u keeps one process global, `zero_bits`, set at unix-library
 * init when the process has a WoW64 TEB, and passes it to every allocation
 * whose address 32-bit code will see (the DC_ATTR buckets, DIB sections,
 * message return buffers, Vulkan mappings).  On iOS every Windows process is a
 * pseudo-process inside one Mach task sharing one win32u, so that global is
 * really task-wide and wrong for every process except the one that wrote it:
 * a 32-bit process leaves a sub-4 GB ceiling behind for later 64-bit ones, and
 * a cleared global hands 32-bit code host pointers it truncates.
 *
 * win32u_zero_bits() therefore answers for the CALLING pseudo-process:
 *
 *     WoW64 thread (WowTebOffset != 0) -> HighestUserAddress | 0x7fffffff, a
 *         GUEST ceiling that the ntdll unix side translates into the process's
 *         guest window;
 *     otherwise                          -> 0, the upstream value for a 64-bit
 *         process.
 *
 * Wine's win32u calls it through caller_zero_bits() (win32u_private.h).  The
 * answer is cached per (pid, PEB), plus a per-thread fast path, and the task
 * global is kept at 0 so any remaining reader behaves as a 64-bit process.
 */

#include <stdio.h>
#include <unistd.h>
#include <pthread.h>

/* Compile upstream syscall.c with its init entry point renamed, then wrap it.
 * build.sh already maps __wine_unix_lib_init -> win32u_unix_lib_init. */
#define win32u_unix_lib_init win32u_unix_lib_init_upstream
#include "../../wine/dlls/win32u/syscall.c"
#undef win32u_unix_lib_init

struct ios_zero_bits_entry
{
    DWORD     pid;
    void     *peb;
    ULONG_PTR zero_bits;
};

#define IOS_MAX_ZERO_BITS_PROCS 64
static struct ios_zero_bits_entry ios_zero_bits_reg[IOS_MAX_ZERO_BITS_PROCS];
static int ios_zero_bits_count;
static pthread_mutex_t ios_zero_bits_lock = PTHREAD_MUTEX_INITIALIZER;

/* a thread never changes pseudo-process, so this needs no invalidation */
static __thread void      *ios_zero_bits_cached_peb;
static __thread ULONG_PTR  ios_zero_bits_cached;

static ULONG_PTR ios_compute_zero_bits(void)
{
    SYSTEM_BASIC_INFORMATION info;
    ULONG_PTR high = 0;

    if (!NtCurrentTeb()->WowTebOffset) return 0;
    if (!NtQuerySystemInformation( SystemEmulationBasicInformation, &info, sizeof(info), NULL ))
        high = (ULONG_PTR)info.HighestUserAddress;
    /* A sane answer is a GUEST address below 4 GB.  Anything else must not
     * escape as a ceiling: >= 4 GB would be taken for a host address and skip
     * the window translation, so fall back to the 2 GB guest ceiling. */
    return (high && high < ((ULONG_PTR)1 << 32)) ? (high | 0x7fffffff) : 0x7fffffff;
}

ULONG_PTR win32u_zero_bits(void)
{
    void *peb = NtCurrentTeb()->Peb;
    ULONG_PTR ret;
    DWORD pid;
    int i;

    if (ios_zero_bits_cached_peb == peb) return ios_zero_bits_cached;
    /* a 64-bit thread needs no registry: its answer is always 0 */
    if (!NtCurrentTeb()->WowTebOffset) return 0;

    pid = HandleToULong( NtCurrentTeb()->ClientId.UniqueProcess );

    pthread_mutex_lock( &ios_zero_bits_lock );
    for (i = 0; i < ios_zero_bits_count; i++)
        if (ios_zero_bits_reg[i].peb == peb && ios_zero_bits_reg[i].pid == pid) break;

    if (i < ios_zero_bits_count) ret = ios_zero_bits_reg[i].zero_bits;
    else
    {
        ret = ios_compute_zero_bits();
        if (ios_zero_bits_count < IOS_MAX_ZERO_BITS_PROCS)
        {
            ios_zero_bits_reg[i].pid       = pid;
            ios_zero_bits_reg[i].peb       = peb;
            ios_zero_bits_reg[i].zero_bits = ret;
            ios_zero_bits_count = i + 1;
        }
    }
    pthread_mutex_unlock( &ios_zero_bits_lock );

    /* only cache what the registry vouches for */
    if (i < IOS_MAX_ZERO_BITS_PROCS)
    {
        ios_zero_bits_cached     = ret;
        ios_zero_bits_cached_peb = peb;
    }
    return ret;
}

NTSTATUS win32u_unix_lib_init(void)
{
    NTSTATUS status = win32u_unix_lib_init_upstream();

    /* the task global is dead here: every consumer asks win32u_zero_bits() */
    zero_bits = 0;
    return status;
}
