/*
 * nsiproxy.sys tcp module
 *
 * Copyright 2003, 2006, 2011 Juan Lang
 * Copyright 2007 TransGaming Technologies Inc.
 * Copyright 2021 Huw Davies
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

/* iOS-Madeira: Wine's IPv4 and IPv6 providers for the in-process NSI.
 *
 * This translation unit compiles wine/dlls/nsiproxy.sys/ip.c unchanged (its
 * own copyright notice is in that file) for the iOS ntdll unix library; see
 * nsi_network_ios.c. The iPhoneOS SDK omits a few optional BSD headers that
 * the macOS config.h announces, so their HAVE_* macros are dropped here and
 * ip.c takes its portable paths (the statistics it cannot read stay
 * unimplemented, as on any platform without them). The routing sysctls it
 * reads are declared by shims/net/route.h.
 *
 * The two address-scope helpers after it are copied from tcp.c (whose
 * notice heads this file), which is not built here: the TCP connection
 * table stays the server-backed one in nsi_unixlib_ios.c. Two changes to
 * the copy: *size is set on every path, and an interface entry without an
 * address is skipped. */
#include "config.h"
/* madeira-bcd: CI configures Wine against the iPhoneOS SDK, which has no
 * <net/route.h>, so its config.h leaves HAVE_NET_ROUTE_H undefined and the
 * routing declarations below were never included (RTM_IFINFO, RTA_IFP,
 * RTF_LLINFO undeclared, build 254). shims/net/route.h provides them. */
#ifndef HAVE_NET_ROUTE_H
#define HAVE_NET_ROUTE_H 1
#endif
#undef HAVE_NET_IF_ARP_H
#undef HAVE_NETINET_IF_ETHER_H
#undef HAVE_NETINET_IP_VAR_H
#undef HAVE_NETINET_ICMP_VAR_H
#undef HAVE_STRUCT_IPSTAT_IPS_TOTAL
#undef HAVE_STRUCT_IP_STATS_IPS_TOTAL
#include <sys/socket.h>
#include <netinet/in.h>

/* The address that leads each NET_RT_FLAGS/RTF_LLINFO (neighbour) message,
 * normally from <netinet/if_ether.h>, which the iPhoneOS SDK omits. The
 * layout is Darwin's public routing-socket ABI (a 16-byte sockaddr: length,
 * family, port, the IPv4 address, then source address, TOS and flags);
 * ip.c reads sin_len and sin_addr. */
struct sockaddr_inarp
{
    unsigned char sin_len;
    unsigned char sin_family;
    unsigned short sin_port;
    struct in_addr sin_addr;
    struct in_addr sin_srcaddr;
    unsigned short sin_tos;
    unsigned short sin_other;
};
_Static_assert(sizeof(struct sockaddr_inarp) == 16, "Darwin sockaddr_inarp is 16 bytes");

#include "../../wine/dlls/nsiproxy.sys/ip.c"

struct ipv6_addr_scope *get_ipv6_addr_scope_table( unsigned int *size )
{
    struct ipv6_addr_scope *table = NULL, *new_table;
    unsigned int table_size = 0, num = 0;
    *size = 0;

#ifdef __linux__
    {
        char buf[512], *ptr;
        FILE *fp;

        if (!(fp = fopen( "/proc/net/if_inet6", "r" ))) goto failed;

        while ((ptr = fgets( buf, sizeof(buf), fp )))
        {
            WORD a[8];
            UINT scope;
            struct ipv6_addr_scope *entry;
            unsigned int i;

            if (sscanf( ptr, "%4hx%4hx%4hx%4hx%4hx%4hx%4hx%4hx %*s %*s %x",
                        a, a + 1, a + 2, a + 3, a + 4, a + 5, a + 6, a + 7, &scope ) != 9)
                continue;

            if (++num > table_size)
            {
                if (!table_size) table_size = 4;
                else table_size *= 2;
                if (!(new_table = realloc( table, table_size * sizeof(table[0]) )))
                {
                    fclose( fp );
                    goto failed;
                }
                table = new_table;
            }

            entry = table + num - 1;
            for (i = 0; i < 8; i++)
                entry->addr.u.Word[i] = htons( a[i] );
            entry->scope = htons( scope );
        }

        fclose( fp );
    }
#elif defined(HAVE_GETIFADDRS)
    {
        struct ifaddrs *addrs, *cur;

        if (getifaddrs( &addrs ) == -1)  goto failed;

        for (cur = addrs; cur; cur = cur->ifa_next)
        {
            struct sockaddr_in6 *sin6;
            struct ipv6_addr_scope *entry;

            if (!cur->ifa_addr || cur->ifa_addr->sa_family != AF_INET6) continue;

            if (++num > table_size)
            {
                if (!table_size) table_size = 4;
                else table_size *= 2;
                if (!(new_table = realloc( table, table_size * sizeof(table[0]) )))
                {
                    freeifaddrs( addrs );
                    goto failed;
                }
                table = new_table;
            }

            sin6 = (struct sockaddr_in6 *)cur->ifa_addr;
            entry = table + num - 1;
            memcpy( &entry->addr, &sin6->sin6_addr, sizeof(entry->addr) );
            entry->scope = sin6->sin6_scope_id;
        }

        freeifaddrs( addrs );
    }
#else
    FIXME( "not implemented\n" );
    goto failed;
#endif

    *size = num;
    return table;

failed:
    free( table );
    return NULL;
}

UINT find_ipv6_addr_scope( const IN6_ADDR *addr, const struct ipv6_addr_scope *table, unsigned int size )
{
    const BYTE multicast_scope_mask = 0x0F;
    const BYTE multicast_scope_shift = 0;
    unsigned int i;

    if (WS_IN6_IS_ADDR_UNSPECIFIED( addr )) return 0;

    if (WS_IN6_IS_ADDR_MULTICAST( addr ))
        return htons( (addr->u.Byte[1] & multicast_scope_mask) >> multicast_scope_shift );

    if (!table) return -1;

    for (i = 0; i < size; i++)
        if (!memcmp( &table[i].addr, addr, sizeof(table[i].addr) ))
            return table[i].scope;

    return -1;
}
