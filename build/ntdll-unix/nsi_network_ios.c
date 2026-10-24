/*
 * nsiproxy.sys
 *
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

/* iOS-Madeira: the in-process NSI network tables.
 *
 * iOS ships no nsiproxy.sys, so PE nsi.dll falls back to the unixlib in
 * nsi_unixlib_ios.c, which used to serve only TCP connections: every other
 * table (network interfaces, IP addresses, routes, neighbours) failed, so
 * GetAdaptersAddresses, GetIfTable2, GetIpForwardTable and friends reported
 * no network at all to every program.
 *
 * This is the table dispatcher of wine/dlls/nsiproxy.sys/nsi.c (the unix
 * half of nsiproxy.sys) over Wine's own BSD providers: NDIS interfaces
 * (ndis.c, compiled by nsi_ndis_ios.c) and IPv4/IPv6 (ip.c, compiled by
 * nsi_ip_ios.c). nsi_unixlib_ios.c hands it every non-TCP enumerate (unix
 * call 0) and every row/field read (calls 1 and 2). Differences from
 * nsiproxy.sys's version:
 *   - only those three modules; the TCP table stays server-backed and there
 *     is no UDP provider, so a table that is not served answers
 *     STATUS_NOT_SUPPORTED, which nsi.dll turns back into the device-open
 *     error callers got before (nsiproxy.sys answers INVALID_PARAMETER);
 *   - a caller's non-zero size with a NULL buffer, and a field read whose
 *     offset and size overflow, are refused instead of trusted;
 *   - MADEIRA_NSI_NETWORK_TABLES=0 serves nothing (every table answers
 *     STATUS_NOT_SUPPORTED again, as before this file existed);
 *   - an identical enumerate within MADEIRA_NSI_CACHE_MS reuses the last
 *     result (see ios_nsi_cached_enumerate);
 *   - [nsi-network] logs the first 16 enumerates per process: module,
 *     table, status and row count only. */
#include "config.h"
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include "ntstatus.h"
#include "windef.h"
#include "winbase.h"
#include "winternl.h"
#include "ifdef.h"
#define __WINE_INIT_NPI_MODULEID
#define USE_WS_PREFIX
#include "netiodef.h"
#include "wine/nsi.h"
#include "wine/debug.h"
#include "../../wine/dlls/nsiproxy.sys/unix_private.h"

WINE_DEFAULT_DEBUG_CHANNEL(nsi);

static const struct module *modules[] =
{
    &ndis_module,
    &ipv4_module,
    &ipv6_module,
};

/* Read once per process. */
static BOOL ios_nsi_network_enabled( void )
{
    static int enabled = -1;

    if (enabled < 0)
    {
        /* On by default: programs see this device's network interfaces, IP
         * addresses and routes. 0 serves none of them, as before. */
        const char *value = getenv( "MADEIRA_NSI_NETWORK_TABLES" );
        __atomic_store_n( &enabled, !(value && !strcmp( value, "0" )), __ATOMIC_RELAXED );
    }
    return enabled;
}

static const struct module_table *get_module_table( const NPI_MODULEID *id, UINT table )
{
    const struct module_table *entry;
    int i;

    if (!id || !ios_nsi_network_enabled()) return NULL;
    for (i = 0; i < ARRAY_SIZE(modules); i++)
        if (NmrIsEqualNpiModuleId( modules[i]->module, id ))
            for (entry = modules[i]->tables; entry->table != ~0u; entry++)
                if (entry->table == table) return entry;

    return NULL;
}

/* A short-lived copy of the interface, address and route tables.
 *
 * Each enumerate rebuilds a whole table from the host (if_nameindex, the
 * interface ioctls, getifaddrs, the routing sysctls), for data that changes a
 * few times a minute at most, and some programs poll: in a device log one
 * program's network-watch thread read these tables about 1,700 times a
 * second. An identical request (module, table, both arguments, the four row
 * sizes, rows or only the count) within MADEIRA_NSI_CACHE_MS of the last
 * successful one is answered from that result with the provider's own
 * semantics: every row and the count, or STATUS_BUFFER_OVERFLOW with the
 * count untouched when the caller's buffer is too small. Eight tables of at
 * most 1 MB each; a failed read is never kept. Row and field reads (unix
 * calls 1 and 2) always go to the provider. */
#define IOS_NSI_CACHE_SLOTS 8
#define IOS_NSI_CACHE_MAX_BYTES (1u << 20)

struct ios_nsi_cache_slot
{
    NPI_MODULEID module;
    UINT table, first_arg, second_arg, sizes[4];
    UINT_PTR count;
    BOOL want_data, used;
    unsigned char *rows[4];
    unsigned long long when_ms;
};

static pthread_mutex_t ios_nsi_cache_lock = PTHREAD_MUTEX_INITIALIZER;
static struct ios_nsi_cache_slot ios_nsi_cache[IOS_NSI_CACHE_SLOTS];

static unsigned long long ios_nsi_now_ms( void )
{
    struct timespec ts;
    clock_gettime( CLOCK_MONOTONIC, &ts );
    return (unsigned long long)ts.tv_sec * 1000ull + ts.tv_nsec / 1000000;
}

static unsigned int ios_nsi_cache_ms( void )
{
    static int value = -1;

    if (value < 0)
    {
        /* On by default (500 ms): an identical interface, address or route
         * table read within this many milliseconds reuses the last result.
         * 0 reads the host every time; at most 5000. */
        const char *e = getenv( "MADEIRA_NSI_CACHE_MS" );
        int ms = e && *e ? atoi( e ) : 500;
        if (ms < 0) ms = 0;
        if (ms > 5000) ms = 5000;
        __atomic_store_n( &value, ms, __ATOMIC_RELAXED );
    }
    return value;
}

/* ios_nsi_cache_lock held. */
static BOOL ios_nsi_cache_match( const struct ios_nsi_cache_slot *slot, const struct nsi_enumerate_all_ex *params,
                                 const UINT sizes[4], BOOL want_data )
{
    return slot->used && slot->want_data == want_data && slot->table == (UINT)params->table
        && slot->first_arg == params->first_arg && slot->second_arg == params->second_arg
        && !memcmp( slot->sizes, sizes, sizeof(slot->sizes) )
        && NmrIsEqualNpiModuleId( &slot->module, params->module );
}

static NTSTATUS ios_nsi_cached_enumerate( struct nsi_enumerate_all_ex *params, const struct module_table *entry,
                                          void *data[4], const UINT sizes[4] )
{
    unsigned int ttl = ios_nsi_cache_ms(), i, j;
    BOOL want_data = data[0] || data[1] || data[2] || data[3];
    struct ios_nsi_cache_slot *slot, *victim = NULL;
    UINT_PTR capacity = params->count;
    unsigned long long now;
    size_t bytes = 0;
    NTSTATUS status;

    if (!ttl)
        return entry->enumerate_all( data[0], sizes[0], data[1], sizes[1], data[2], sizes[2], data[3], sizes[3],
                                     &params->count );

    now = ios_nsi_now_ms();
    pthread_mutex_lock( &ios_nsi_cache_lock );
    for (i = 0; i < IOS_NSI_CACHE_SLOTS; i++)
    {
        slot = &ios_nsi_cache[i];
        if (!ios_nsi_cache_match( slot, params, sizes, want_data )) continue;
        if (now - slot->when_ms > ttl) break;   /* too old (or newer than `now`): read again */
        if (want_data && slot->count > capacity)
            status = STATUS_BUFFER_OVERFLOW;
        else
        {
            for (j = 0; j < 4; j++)
                if (data[j] && slot->count) memcpy( data[j], slot->rows[j], (size_t)slot->count * sizes[j] );
            params->count = slot->count;
            status = STATUS_SUCCESS;
        }
        pthread_mutex_unlock( &ios_nsi_cache_lock );
        return status;
    }
    pthread_mutex_unlock( &ios_nsi_cache_lock );

    status = entry->enumerate_all( data[0], sizes[0], data[1], sizes[1], data[2], sizes[2], data[3], sizes[3],
                                   &params->count );
    if (status != STATUS_SUCCESS) return status;
    for (i = 0; i < 4; i++) bytes += (size_t)params->count * sizes[i];
    if (bytes > IOS_NSI_CACHE_MAX_BYTES) return status;

    pthread_mutex_lock( &ios_nsi_cache_lock );
    /* The same request's slot, else an unused one, else the oldest. */
    for (i = 0; i < IOS_NSI_CACHE_SLOTS && !victim; i++)
        if (ios_nsi_cache_match( &ios_nsi_cache[i], params, sizes, want_data )) victim = &ios_nsi_cache[i];
    for (i = 0; i < IOS_NSI_CACHE_SLOTS && !victim; i++)
        if (!ios_nsi_cache[i].used) victim = &ios_nsi_cache[i];
    if (!victim)
    {
        victim = &ios_nsi_cache[0];
        for (i = 1; i < IOS_NSI_CACHE_SLOTS; i++)
            if (ios_nsi_cache[i].when_ms < victim->when_ms) victim = &ios_nsi_cache[i];
    }
    victim->used = TRUE;
    for (i = 0; i < 4; i++)
    {
        free( victim->rows[i] );
        victim->rows[i] = NULL;
        if (!data[i] || !params->count) continue;
        if (!(victim->rows[i] = malloc( (size_t)params->count * sizes[i] ))) victim->used = FALSE;
        else memcpy( victim->rows[i], data[i], (size_t)params->count * sizes[i] );
    }
    victim->module = *params->module;
    victim->table = params->table;
    victim->first_arg = params->first_arg;
    victim->second_arg = params->second_arg;
    memcpy( victim->sizes, sizes, sizeof(victim->sizes) );
    victim->count = params->count;
    victim->want_data = want_data;
    victim->when_ms = ios_nsi_now_ms();
    pthread_mutex_unlock( &ios_nsi_cache_lock );
    return status;
}

NTSTATUS nsi_enumerate_all_ex( struct nsi_enumerate_all_ex *params )
{
    const struct module_table *entry = get_module_table( params->module, params->table );
    UINT sizes[4] = { params->key_size, params->rw_size, params->dynamic_size, params->static_size };
    void *data[4] = { params->key_data, params->rw_data, params->dynamic_data, params->static_data };
    static unsigned int reports;
    NTSTATUS status;
    int i;

    if (!entry || !entry->enumerate_all)
    {
        WARN( "table not found\n" );
        return STATUS_NOT_SUPPORTED;
    }

    for (i = 0; i < ARRAY_SIZE(sizes); i++)
    {
        if (!sizes[i]) data[i] = NULL;
        else if (!data[i] || sizes[i] != entry->sizes[i]) return STATUS_INVALID_PARAMETER;
    }

    status = ios_nsi_cached_enumerate( params, entry, data, sizes );
    if (__atomic_fetch_add( &reports, 1, __ATOMIC_RELAXED ) < 16)
        dprintf( 2, "[nsi-network] module=%08x table=%u status=%08x count=%u\n",
                 (UINT)params->module->Guid.Data1, (UINT)params->table, (UINT)status, (UINT)params->count );
    return status;
}

NTSTATUS nsi_get_all_parameters_ex( struct nsi_get_all_parameters_ex *params )
{
    const struct module_table *entry = get_module_table( params->module, params->table );
    void *rw = params->rw_data;
    void *dyn = params->dynamic_data;
    void *stat = params->static_data;

    if (!entry || !entry->get_all_parameters)
    {
        WARN( "table not found\n" );
        return STATUS_NOT_SUPPORTED;
    }

    if ((params->key_size && !params->key) || params->key_size != entry->sizes[0]) return STATUS_INVALID_PARAMETER;
    if (!params->rw_size) rw = NULL;
    else if (!rw || params->rw_size != entry->sizes[1]) return STATUS_INVALID_PARAMETER;
    if (!params->dynamic_size) dyn = NULL;
    else if (!dyn || params->dynamic_size != entry->sizes[2]) return STATUS_INVALID_PARAMETER;
    if (!params->static_size) stat = NULL;
    else if (!stat || params->static_size != entry->sizes[3]) return STATUS_INVALID_PARAMETER;

    return entry->get_all_parameters( params->key, params->key_size, rw, params->rw_size,
                                      dyn, params->dynamic_size, stat, params->static_size );
}

NTSTATUS nsi_get_parameter_ex( struct nsi_get_parameter_ex *params )
{
    const struct module_table *entry = get_module_table( params->module, params->table );

    if (!entry || !entry->get_parameter)
    {
        WARN( "table not found\n" );
        return STATUS_NOT_SUPPORTED;
    }

    if (params->param_type > 2) return STATUS_INVALID_PARAMETER;
    if ((params->key_size && !params->key) || params->key_size != entry->sizes[0]) return STATUS_INVALID_PARAMETER;
    if ((params->data_size && !params->data) ||
        params->data_offset > entry->sizes[params->param_type + 1] ||
        params->data_size > entry->sizes[params->param_type + 1] - params->data_offset)
        return STATUS_INVALID_PARAMETER;
    return entry->get_parameter( params->key, params->key_size, params->param_type,
                                 params->data, params->data_size, params->data_offset );
}
