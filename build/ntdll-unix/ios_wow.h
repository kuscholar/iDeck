/*
 * WoW64 guest windows on iOS
 *
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

/* XNU's mandatory 4 GB __PAGEZERO makes the classic WoW64 identity (guest
 * address == host address) impossible: nothing can be mapped below 4 GB.
 * Instead every 32-bit pseudo-process owns one reserved host range [B, B+4G);
 * guest address `a` (always < 4 GB, what the x86 code sees) lives at host
 * address `B + a`.
 *
 * The unix side and the wineserver speak HOST addresses throughout.  The one
 * exception is a CEILING that a WoW process sends down (a zero_bits value or a
 * MEM_ADDRESS_REQUIREMENTS limit below 4 GB) or that is reported back up
 * (HighestUserAddress): those are GUEST-namespace numbers, and the unix side
 * translates a guest ceiling L into the host range [B, B+L] when it picks an
 * address.
 *
 * Windows are LAZY: a session reserves one only when a 32-bit process needs it
 * (see ios_wow_session_arm).  A 64-bit-only session reserves nothing, and every
 * function below is then a no-op that returns 0.
 *
 * virtual_ios.c owns the registry; this header is the interface the other
 * forked unix files use.
 */
#ifndef __MADEIRA_IOS_WOW_H
#define __MADEIRA_IOS_WOW_H

#define IOS_WOW_WINDOW_SIZE  ((ULONG_PTR)1 << 32)   /* 4 GB */

/* B for an explicit pseudo-process, 0 when that process has no window. */
extern ULONG_PTR ios_wow_base_for_peb( void *peb_id );

/* B for the calling thread's pseudo-process.  Also reports a window that was
 * reserved on this thread but is not bound to a PEB yet (the child boot path
 * reserves before its PEB exists).  0 when the caller is not in a WoW
 * process, which makes this the per-process "is this a WoW process" test. */
extern ULONG_PTR ios_wow_base(void);

/* Published by the app before __wine_main: nonzero when this session's MAIN
 * image is 32-bit.  virtual_init then arms the session and reserves the main
 * image's window before the system frameworks can take the slot.  0 for a
 * 64-bit main image. */
extern int ios_main_image_i386;

/* Nonzero once the session can have a 32-bit process: a 32-bit main image was
 * published, a 32-bit child is being created, or a window was reserved.  Until
 * then nothing reserves VA for 32-bit support and placement is unchanged. */
extern int ios_wow_session_armed(void);
extern void ios_wow_session_arm(void);

/* Reserve a window for the calling thread.  Idempotent per thread.  Returns
 * STATUS_NO_MEMORY when the address map cannot afford another window. */
extern NTSTATUS ios_wow_window_reserve(void);
/* Bind the window reserved on this thread to a pseudo-process. */
extern void ios_wow_window_bind( void *peb_id );
/* Release a pseudo-process's window (process EXIT).  The slot stops resolving
 * at once; the 4 GB range and Wine's bookkeeping inside it are torn down when
 * the next 32-bit pseudo-process wants a slot (release-on-next-adopt: nothing
 * joins a dead pseudo-process's threads on iOS, so the teardown cannot run on
 * the dying thread, which still stands on a TEB inside the window). */
extern void ios_wow_window_release( void *peb_id );
/* Same, for the calling thread's own pseudo-process. */
extern void ios_wow_window_release_current(void);
/* ABANDON the calling thread's window for good: for a pseudo-process that
 * stops being a WoW process while STAYING ALIVE inside the window.  The VA is
 * kept on purpose and the slot serves no further 32-bit process. */
extern void ios_wow_window_retire_current(void);

/* Translate a GUEST-namespace ceiling pair into the calling process's host
 * window.  A no-op when the caller has no window, or when limit_high is not a
 * guest ceiling (0 = unconstrained, or already >= 4 GB = a host address). */
extern void ios_wow_translate_limits( ULONG_PTR *limit_low, ULONG_PTR *limit_high );

/* TRUE when `addr` lies inside the calling process's window. */
extern int ios_wow_in_window( const void *addr );

/* Guest view of a host address for the calling process: host - B, or the
 * address truncated unchanged when the caller has no window.  NULL stays 0. */
extern ULONG ios_wow_guest_addr( const void *host );

/* Map a read-only second view of KUSER_SHARED_DATA at host B + 0x7ffe0000,
 * i.e. at guest 0x7ffe0000.  No-op outside a window. */
extern void ios_wow_map_user_shared_data(void);

/* Hold guest 0x7ffe0000 from before the first TEB block is reserved until the
 * real KUSER_SHARED_DATA view replaces it; otherwise the MEM_TOP_DOWN search
 * for the TEB block takes that address and every 32-bit tick read in the
 * process is frozen. */
extern void ios_wow_reserve_usd_slot( ULONG_PTR base );
extern void ios_wow_release_usd_slot(void);

/* Convert the PEB64 pointer fields that the 32-bit ntdll writes itself with
 * the classic WoW64 identity (`peb64->X = PtrToUlong( guest_ptr )`) into HOST
 * pointers for the native readers of those fields.  Exact test: nothing is
 * mapped below iOS's 4 GB __PAGEZERO, so a non-zero sub-4 GB value is a guest
 * address.  Idempotent; no-op without a window.  Implemented in env_ios.c. */
extern void ios_wow_fixup_peb64_ptrs(void);

/* A pointer EMBEDDED in a 32-bit unix-call argument block is a GUEST address:
 * the WoW64 module converts only the OUTER `args` pointer.  ios_wow_host_ptr()
 * is the +B conversion for those, NULL-preserving; ios_wow_guest_ptr32() writes
 * one back.  Wine's wine/unixlib.h may define the same helpers; the guard keeps
 * whichever header is included first as the definition. */
#ifndef __MADEIRA_IOS_WOW_HOST_PTR
#define __MADEIRA_IOS_WOW_HOST_PTR
static inline void *ios_wow_host_ptr( ULONG addr )
{
    return addr ? (void *)(ios_wow_base() + (ULONG_PTR)addr) : NULL;
}
static inline ULONG ios_wow_guest_ptr32( const void *host )
{
    return host ? (ULONG)((ULONG_PTR)host - ios_wow_base()) : 0;
}
#endif

#endif /* __MADEIRA_IOS_WOW_H */
