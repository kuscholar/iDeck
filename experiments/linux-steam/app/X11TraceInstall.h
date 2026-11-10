/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#ifndef IDECK_X11_TRACE_INSTALL_H
#define IDECK_X11_TRACE_INSTALL_H
#include <stddef.h>
#define IDECK_X11_TRACE_BASE "/ideck-diagnostics"
#define IDECK_X11_TRACE_FILE IDECK_X11_TRACE_BASE "/x11-window-trace-v3.so"
#define IDECK_X11_TRACE_STAGE IDECK_X11_TRACE_BASE "/.x11-window-trace-v3.installing"
struct ideck_x11_trace_payload {const void *bytes;size_t size;};
/* Trusted immutable signed-bundle bytes, not guest IPC. Before any guest runs,
 * current must be native init/PID1. Stage+exact-byte validation, atomic no-
 * overwrite hardlink publication then removal of OWN stage. Never removes a
 * preexisting stage/target or edits Steam/account data. Return Linux errno.
 */
int ideck_x11_trace_install(const struct ideck_x11_trace_payload *payload,int *created);
#endif
