/* iOS-Madeira 2026-08-03 rev=ml470 (#79 transport): in-process NSI TCP
 * connection tables.
 *
 * nsiproxy.sys is not shipped on iOS (no winedevice/driver stack), so PE
 * nsi.dll's CreateFileW(\\.\Nsi) fails and every NSI table read errors —
 * including GetExtendedTcpTable, which Steam's SteamUI uses to
 * authenticate loopback peers (it looks the connecting peer's remote
 * port up in TCP_TABLE_OWNER_PID_CONNECTIONS and compares dwOwningPid
 * against its own / tracked child pid). With the table unavailable the
 * helper fails before any pid compare and every CEF loopback connection
 * is "Rejecting connection attempt from unknown source" -> the #79
 * accept/reject loop and the VGUI "Unexpected Transport Error" dialog.
 *
 * wineserver already tracks the honest owner pid for every TCP socket
 * (server/sock.c get_tcp_connections, in-process for this port), so we
 * service the three TCP connection tables directly from the server.
 * PE nsi.dll falls back to this unixlib (WINE_UNIX_CALL code 0, same
 * struct nsi_enumerate_all_ex the nsiproxy ioctl path uses) when the
 * device is absent; registration is by module name in virtual_ios.c
 * load_builtin_unixlib. Other modules (network interfaces, IPv4/IPv6
 * addresses, routes and neighbours) go to Wine's BSD providers through
 * nsi_network_ios.c, which also serves the row and field reads (codes 1
 * and 2); a table nobody serves still answers STATUS_NOT_SUPPORTED, which
 * nsi.dll turns back into the old device-open error.
 *
 * The enumerator is wine/dlls/nsiproxy.sys/tcp.c tcp_conns_enumerate_all
 * copied faithfully, except IPv6 scope ids come straight from the server
 * reply instead of a getifaddrs scope table (iOS: fewer BSD headers; the
 * Steam path is AF_INET only). */

#include "config.h"
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <unistd.h>
#include <netinet/in.h>

#include "ntstatus.h"
#include "windef.h"
#include "winbase.h"
#include "winternl.h"
#define USE_WS_PREFIX
#include "winsock2.h"
#include "ifdef.h"
#include "netiodef.h"
#include "ws2ipdef.h"
#include "tcpmib.h"
#include "wine/nsi.h"
#include "wine/server.h"
#include "wine/unixlib.h"   /* ios_wow_host_ptr() for the wow64 table below */

/* nsi_network_ios.c: the interface, address and route tables. */
NTSTATUS nsi_enumerate_all_ex( struct nsi_enumerate_all_ex *params );
NTSTATUS nsi_get_all_parameters_ex( struct nsi_get_all_parameters_ex *params );
NTSTATUS nsi_get_parameter_ex( struct nsi_get_parameter_ex *params );

/* NPI_MS_TCP_MODULEID (netiodef.h declares it extern; the defining
 * translation unit lives in nsiproxy.sys which we don't build) */
static const NPI_MODULEID ios_tcp_moduleid =
    { sizeof(NPI_MODULEID), MIT_GUID,
      { { 0xeb004a03, 0x9b1a, 0x11d4, { 0x91, 0x23, 0x00, 0x50, 0x04, 0x77, 0x59, 0xbc } } } };

static NTSTATUS ios_tcp_conns_enumerate_all( UINT filter, struct nsi_tcp_conn_key *key_data, UINT key_size,
                                             void *rw, UINT rw_size,
                                             struct nsi_tcp_conn_dynamic *dynamic_data, UINT dynamic_size,
                                             struct nsi_tcp_conn_static *static_data, UINT static_size,
                                             UINT_PTR *count )
{
    static int rows_logged;
    BOOL want_data = key_size || rw_size || dynamic_size || static_size;
    struct nsi_tcp_conn_key key;
    struct nsi_tcp_conn_dynamic dyn;
    struct nsi_tcp_conn_static stat;
    NTSTATUS ret = STATUS_SUCCESS;
    union tcp_connection *connections = NULL;

    if (want_data)
    {
        connections = malloc( sizeof(*connections) * (*count) );
        if (!connections) return STATUS_NO_MEMORY;
    }

    SERVER_START_REQ( get_tcp_connections )
    {
        req->state_filter = filter;
        wine_server_set_reply( req, connections, want_data ? (sizeof(*connections) * (*count)) : 0 );
        if (!(ret = wine_server_call( req )))
            *count = reply->count;
        else if (ret == STATUS_BUFFER_TOO_SMALL)
        {
            if (!want_data)
            {
                *count = reply->count;
                return STATUS_SUCCESS;
            }

            free( connections );
            return STATUS_BUFFER_OVERFLOW;
        }
    }
    SERVER_END_REQ;

    for (unsigned int i = 0; i < *count; i++)
    {
        union tcp_connection *conn = &connections[i];

        if (key_data)
        {
            memset( &key, 0, sizeof(key) );
            if (conn->common.family == WS_AF_INET)
            {
                key.local.Ipv4.sin_family = key.remote.Ipv4.sin_family = WS_AF_INET;
                key.local.Ipv4.sin_addr.WS_s_addr = conn->ipv4.local_addr;
                key.local.Ipv4.sin_port = conn->ipv4.local_port;
                key.remote.Ipv4.sin_addr.WS_s_addr = conn->ipv4.remote_addr;
                key.remote.Ipv4.sin_port = conn->ipv4.remote_port;
            }
            else
            {
                key.local.Ipv6.sin6_family = key.remote.Ipv6.sin6_family = WS_AF_INET6;
                memcpy( &key.local.Ipv6.sin6_addr, &conn->ipv6.local_addr, 16 );
                key.local.Ipv6.sin6_port = conn->ipv6.local_port;
                key.local.Ipv6.sin6_scope_id = conn->ipv6.local_scope_id;
                memcpy( &key.remote.Ipv6.sin6_addr, &conn->ipv6.remote_addr, 16 );
                key.remote.Ipv6.sin6_port = conn->ipv6.remote_port;
                key.remote.Ipv6.sin6_scope_id = conn->ipv6.remote_scope_id;
            }
            *key_data++ = key;
        }

        if (dynamic_data)
        {
            memset( &dyn, 0, sizeof(dyn) );
            dyn.state = conn->common.state;
            *dynamic_data++ = dyn;
        }

        if (static_data)
        {
            memset( &stat, 0, sizeof(stat) );
            stat.pid = conn->common.owner;
            stat.create_time = 0;
            stat.mod_info = 0;
            *static_data++ = stat;
        }

        /* ml473 (#79): Steam matches row.localport against the connecting
         * peer's remote port, requires state ESTAB and compares dwOwningPid
         * with its tracked child pid — dump what we actually hand it. */
        if (rows_logged < 60)
        {
            rows_logged++;
            if (conn->common.family == WS_AF_INET)
                dprintf( 2, "[nsi-row] v4 local=%u.%u.%u.%u:%u remote=%u.%u.%u.%u:%u state=%u pid=%u rev=ml474\n",
                         (UINT)(conn->ipv4.local_addr & 0xff), (UINT)((conn->ipv4.local_addr >> 8) & 0xff),
                         (UINT)((conn->ipv4.local_addr >> 16) & 0xff), (UINT)((conn->ipv4.local_addr >> 24) & 0xff),
                         (UINT)ntohs( conn->ipv4.local_port ),
                         (UINT)(conn->ipv4.remote_addr & 0xff), (UINT)((conn->ipv4.remote_addr >> 8) & 0xff),
                         (UINT)((conn->ipv4.remote_addr >> 16) & 0xff), (UINT)((conn->ipv4.remote_addr >> 24) & 0xff),
                         (UINT)ntohs( conn->ipv4.remote_port ),
                         (UINT)conn->common.state, (UINT)conn->common.owner );
            else
                dprintf( 2, "[nsi-row] v6 localport=%u remoteport=%u state=%u pid=%u rev=ml474\n",
                         (UINT)ntohs( conn->ipv6.local_port ), (UINT)ntohs( conn->ipv6.remote_port ),
                         (UINT)conn->common.state, (UINT)conn->common.owner );
        }
    }

    free( connections );
    return ret;
}

/* code 0: struct nsi_enumerate_all_ex *, same validation as nsiproxy's
 * unix-side nsi_enumerate_all_ex dispatcher (sizes must be 0 or exact) */
static NTSTATUS ios_nsi_enumerate_all_ex( void *args )
{
    struct nsi_enumerate_all_ex *params = args;
    static int logged;
    NTSTATUS status;
    UINT filter;

    if (!params || !params->module) return STATUS_INVALID_PARAMETER;
    if (!NmrIsEqualNpiModuleId( params->module, &ios_tcp_moduleid ))
    {
        /* iOS-Madeira: interfaces, addresses and routes (nsi_network_ios.c) */
        status = nsi_enumerate_all_ex( params );
        /* ml472 (#80 attribution): a hot caller retrying an unserviced table
         * would otherwise be invisible here. */
        static int non_tcp_logged;
        if (status == STATUS_NOT_SUPPORTED && non_tcp_logged < 16)
        {
            non_tcp_logged++;
            dprintf( 2, "[nsi-ios] non-tcp module %08x table=%u -> NOT_SUPPORTED rev=ml472\n",
                     (UINT)params->module->Guid.Data1, (UINT)params->table );
        }
        return status;
    }

    switch ((UINT)params->table)
    {
    case NSI_TCP_ALL_TABLE:    filter = 0; break;
    case NSI_TCP_ESTAB_TABLE:  filter = MIB_TCP_STATE_ESTAB; break;
    case NSI_TCP_LISTEN_TABLE: filter = MIB_TCP_STATE_LISTEN; break;
    default: return STATUS_NOT_SUPPORTED;
    }

    if (params->key_size && params->key_size != sizeof(struct nsi_tcp_conn_key))
        return STATUS_INVALID_PARAMETER;
    if (params->rw_size) return STATUS_INVALID_PARAMETER;
    if (params->dynamic_size && params->dynamic_size != sizeof(struct nsi_tcp_conn_dynamic))
        return STATUS_INVALID_PARAMETER;
    if (params->static_size && params->static_size != sizeof(struct nsi_tcp_conn_static))
        return STATUS_INVALID_PARAMETER;

    status = ios_tcp_conns_enumerate_all( filter,
                                          params->key_size ? params->key_data : NULL, params->key_size,
                                          NULL, 0,
                                          params->dynamic_size ? params->dynamic_data : NULL, params->dynamic_size,
                                          params->static_size ? params->static_data : NULL, params->static_size,
                                          &params->count );
    if (logged < 16)
    {
        logged++;
        dprintf( 2, "[nsi-ios] tcp table=%u filter=%u -> status=0x%x count=%u rev=ml472\n",
                 (UINT)params->table, filter, (UINT)status, (UINT)params->count );
    }
    return status;
}

const void *nsi_unix_call_funcs[] =
{
    (const void *)ios_nsi_enumerate_all_ex,
    (const void *)nsi_get_all_parameters_ex,   /* 1: NsiGetAllParametersEx */
    (const void *)nsi_get_parameter_ex,        /* 2: NsiGetParameterEx */
};

/* The 32-bit counterpart.  A 32-bit nsi.dll passes a struct
 * nsi_enumerate_all_ex whose pointer members are 4 bytes wide.  `args` itself
 * is already a HOST pointer (the WoW64 module converts that one outer
 * pointer); every pointer EMBEDDED in the block is a GUEST address and needs
 * + B (ios_wow_host_ptr, NULL-preserving).  The row buffers are the caller's
 * own, allocated inside its guest window.  count is in/out. */
typedef ULONG PTR32;

struct nsi_enumerate_all_ex32
{
    PTR32 unknown[2];
    PTR32 module;
    ULONG table;
    UINT  first_arg;
    UINT  second_arg;
    PTR32 key_data;
    UINT  key_size;
    PTR32 rw_data;
    UINT  rw_size;
    PTR32 dynamic_data;
    UINT  dynamic_size;
    PTR32 static_data;
    UINT  static_size;
    ULONG count;
};

static NTSTATUS ios_wow64_nsi_enumerate_all_ex( void *args )
{
    struct nsi_enumerate_all_ex32 *params32 = args;
    struct nsi_enumerate_all_ex params;
    NTSTATUS status;

    if (!params32) return STATUS_INVALID_PARAMETER;

    params.unknown[0]   = ios_wow_host_ptr( params32->unknown[0] );
    params.unknown[1]   = ios_wow_host_ptr( params32->unknown[1] );
    params.module       = ios_wow_host_ptr( params32->module );
    params.table        = params32->table;
    params.first_arg    = params32->first_arg;
    params.second_arg   = params32->second_arg;
    params.key_data     = ios_wow_host_ptr( params32->key_data );
    params.key_size     = params32->key_size;
    params.rw_data      = ios_wow_host_ptr( params32->rw_data );
    params.rw_size      = params32->rw_size;
    params.dynamic_data = ios_wow_host_ptr( params32->dynamic_data );
    params.dynamic_size = params32->dynamic_size;
    params.static_data  = ios_wow_host_ptr( params32->static_data );
    params.static_size  = params32->static_size;
    params.count        = params32->count;

    status = ios_nsi_enumerate_all_ex( &params );

    params32->count = (ULONG)params.count;
    return status;
}

/* The row and field reads, converted the same way: every embedded pointer is
 * a guest address (the key and the caller's output buffers included), the
 * sizes, table and param_type are plain numbers. Nothing is written back
 * into the argument block; the data goes to the converted buffers. */
struct nsi_get_all_parameters_ex32
{
    PTR32 unknown[2];
    PTR32 module;
    ULONG table;
    UINT  first_arg;
    UINT  unknown2;
    PTR32 key;
    UINT  key_size;
    PTR32 rw_data;
    UINT  rw_size;
    PTR32 dynamic_data;
    UINT  dynamic_size;
    PTR32 static_data;
    UINT  static_size;
};

struct nsi_get_parameter_ex32
{
    PTR32 unknown[2];
    PTR32 module;
    ULONG table;
    UINT  first_arg;
    UINT  unknown2;
    PTR32 key;
    UINT  key_size;
    ULONG param_type;
    PTR32 data;
    UINT  data_size;
    UINT  data_offset;
};

static NTSTATUS ios_wow64_nsi_get_all_parameters_ex( void *args )
{
    struct nsi_get_all_parameters_ex32 *params32 = args;
    struct nsi_get_all_parameters_ex params;

    if (!params32) return STATUS_INVALID_PARAMETER;

    params.unknown[0]   = ios_wow_host_ptr( params32->unknown[0] );
    params.unknown[1]   = ios_wow_host_ptr( params32->unknown[1] );
    params.module       = ios_wow_host_ptr( params32->module );
    params.table        = params32->table;
    params.first_arg    = params32->first_arg;
    params.unknown2     = params32->unknown2;
    params.key          = ios_wow_host_ptr( params32->key );
    params.key_size     = params32->key_size;
    params.rw_data      = ios_wow_host_ptr( params32->rw_data );
    params.rw_size      = params32->rw_size;
    params.dynamic_data = ios_wow_host_ptr( params32->dynamic_data );
    params.dynamic_size = params32->dynamic_size;
    params.static_data  = ios_wow_host_ptr( params32->static_data );
    params.static_size  = params32->static_size;

    return nsi_get_all_parameters_ex( &params );
}

static NTSTATUS ios_wow64_nsi_get_parameter_ex( void *args )
{
    struct nsi_get_parameter_ex32 *params32 = args;
    struct nsi_get_parameter_ex params;

    if (!params32) return STATUS_INVALID_PARAMETER;

    params.unknown[0]  = ios_wow_host_ptr( params32->unknown[0] );
    params.unknown[1]  = ios_wow_host_ptr( params32->unknown[1] );
    params.module      = ios_wow_host_ptr( params32->module );
    params.table       = params32->table;
    params.first_arg   = params32->first_arg;
    params.unknown2    = params32->unknown2;
    params.key         = ios_wow_host_ptr( params32->key );
    params.key_size    = params32->key_size;
    params.param_type  = params32->param_type;
    params.data        = ios_wow_host_ptr( params32->data );
    params.data_size   = params32->data_size;
    params.data_offset = params32->data_offset;

    return nsi_get_parameter_ex( &params );
}

const void *nsi_unix_call_wow64_funcs[] =
{
    (const void *)ios_wow64_nsi_enumerate_all_ex,
    (const void *)ios_wow64_nsi_get_all_parameters_ex,
    (const void *)ios_wow64_nsi_get_parameter_ex,
};
