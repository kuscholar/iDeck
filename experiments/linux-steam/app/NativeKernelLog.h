/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#ifndef IDECK_NATIVE_KERNEL_LOG_H
#define IDECK_NATIVE_KERNEL_LOG_H
#include <stddef.h>
#define IDECK_NATIVE_LOG_LIMIT (4u*1024u*1024u)
/* Native app-owned private directory, never guest paths/IPC. One start per
 * process. No reader thread, signal hook or runtime restart is introduced. */
int ideck_native_log_start(const char *directory);
const char *ideck_native_log_name(void);
size_t ideck_native_log_bytes(void);
void ideck_native_log_line(const char *line);
/* Public self-task metrics only; available-memory is an instantaneous snapshot,
 * not a reserved budget or proof of why an external SIGKILL occurred. */
void ideck_native_log_resources(void);
/* Defined ONLY by the opted-in copied kernel/log.c object. */
const char *ideck_native_log_bridge_marker(void);
#endif
