/* SPDX-License-Identifier: GPL-3.0-or-later
 * Copyright 2026 125hz
 * Madeira Converter Exception: see LICENSE-EXCEPTION.md
 *
 * The routing-socket declarations that Wine's BSD network providers use
 * (wine/dlls/nsiproxy.sys/ndis.c and ip.c, compiled into the ntdll unix
 * library by nsi_ndis_ios.c and nsi_ip_ios.c). The iPhoneOS SDK does not
 * ship <net/route.h>, although the kernel answers the routing sysctls
 * (NET_RT_DUMP, NET_RT_FLAGS, NET_RT_IFLIST from <sys/socket.h>) exactly as
 * on macOS.
 *
 * Only what those two files read is declared here: the fixed header of a
 * routing message and its metrics block, and the message types, route flags
 * and address bits they test. The layout and the values are Darwin's public
 * routing-socket ABI (the format of the messages the kernel writes); they
 * are not a copy of Apple's header. The asserts at the end pin the layout,
 * because the providers find a message's addresses right after
 * `struct rt_msghdr` (rtm + 1).
 */
#ifndef MADEIRA_SHIM_NET_ROUTE_H
#define MADEIRA_SHIM_NET_ROUTE_H

#include <stddef.h>
#include <stdint.h>
#include <sys/types.h>

/* Per-route metrics as the kernel reports them: fourteen 32-bit words. */
struct rt_metrics
{
    uint32_t rmx_locks;
    uint32_t rmx_mtu;
    uint32_t rmx_hopcount;     /* read as the route's metric */
    int32_t  rmx_expire;       /* 0 for a permanent neighbour entry */
    uint32_t rmx_recvpipe;
    uint32_t rmx_sendpipe;
    uint32_t rmx_ssthresh;
    uint32_t rmx_rtt;
    uint32_t rmx_rttvar;
    uint32_t rmx_pksent;
    uint32_t rmx_filler[4];
};

/* The fixed part of every message from NET_RT_DUMP and NET_RT_FLAGS; the
 * socket addresses named by rtm_addrs follow it directly. */
struct rt_msghdr
{
    uint16_t rtm_msglen;       /* whole message, header and addresses */
    uint8_t  rtm_version;
    uint8_t  rtm_type;         /* RTM_* */
    uint16_t rtm_index;        /* interface index */
    int32_t  rtm_flags;        /* RTF_* */
    int32_t  rtm_addrs;        /* RTA_* bits of the addresses that follow */
    pid_t    rtm_pid;
    int32_t  rtm_seq;
    int32_t  rtm_errno;
    int32_t  rtm_use;
    uint32_t rtm_inits;
    struct rt_metrics rtm_rmx;
};

/* Message types (rtm_type; if_msghdr's ifm_type for interface messages). */
#define RTM_GET         0x4    /* one route of a NET_RT_DUMP/NET_RT_FLAGS reply */
#define RTM_IFINFO      0xe    /* an interface in a NET_RT_IFLIST reply */

/* Route flags (rtm_flags, and the NET_RT_FLAGS filter). */
#define RTF_GATEWAY     0x2
#define RTF_LLINFO      0x400
#define RTF_MULTICAST   0x800000

/* Bits of rtm_addrs/ifm_addrs, in the order the addresses follow. */
#define RTA_DST         0x1
#define RTA_GATEWAY     0x2
#define RTA_NETMASK     0x4
#define RTA_IFP         0x10

_Static_assert(sizeof(struct rt_metrics) == 56, "Darwin rt_metrics is 56 bytes");
_Static_assert(offsetof(struct rt_msghdr, rtm_flags) == 8, "rtm_flags at 8");
_Static_assert(offsetof(struct rt_msghdr, rtm_rmx) == 36, "rtm_rmx at 36");
_Static_assert(sizeof(struct rt_msghdr) == 92, "Darwin rt_msghdr is 92 bytes");

#endif /* MADEIRA_SHIM_NET_ROUTE_H */
