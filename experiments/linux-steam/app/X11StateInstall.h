/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#ifndef IDECK_X11_STATE_INSTALL_H
#define IDECK_X11_STATE_INSTALL_H
#include <stddef.h>
#define IDECK_X11_STATE_BASE "/ideck-diagnostics"
#define IDECK_X11_STATE_FILE IDECK_X11_STATE_BASE "/x11-window-state-v1"
#define IDECK_X11_STATE_STAGE IDECK_X11_STATE_BASE "/.x11-window-state-v1.installing"
/* Copy immutable signed-bundle bytes once BEFORE guest entry, never guest IPC.
 * Install requires native init/PID1 and preserves conflicting/stale paths. */
int ideck_x11_state_configure(const void *bytes,size_t size);
int ideck_x11_state_install_prepared(void);
#endif
