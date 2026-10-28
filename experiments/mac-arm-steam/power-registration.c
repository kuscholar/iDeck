// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
// No macOS root-domain power-notification service is supplied by this shim.
// Return the documented failure sentinel; never expose a fake IONotificationPort
// to real IOKit dispatch/run-loop functions. No callback or privilege requested.
#include <mach/mach.h>
#include <stdint.h>
#include <stdio.h>
typedef struct IONotificationPort *IONotificationPortRef;
typedef void (*IOServiceInterestCallback)(void *,mach_port_t,uint32_t,void *);
mach_port_t IORegisterForSystemPower(void *refcon,IONotificationPortRef *port,
                                   IOServiceInterestCallback callback,mach_port_t *notifier) {
    (void)refcon;(void)callback;
    if(port)*port=NULL;
    if(notifier)*notifier=MACH_PORT_NULL;
    fputs("[ideck-mac-power] registration=unsupported session=0 port=null notifier=0\n",stderr);
    return MACH_PORT_NULL;
}
