/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#ifndef IDECK_SHARED_LIBRARY_CONFIG_H
#define IDECK_SHARED_LIBRARY_CONFIG_H
#include <stddef.h>
#define IDECK_LIBRARY_CONFIG_MAX 262144
#define IDECK_LIBRARY_CONFIG_PATH "/Steam/steamapps/libraryfolders.vdf"
#define IDECK_LIBRARY_CONFIG_BACKUP "/Steam/steamapps/libraryfolders.vdf.ideck-before-shared-library"
#define IDECK_LIBRARY_CONFIG_STAGE "/Steam/steamapps/.libraryfolders.vdf.ideck-registering"
/* Pure metadata plan. Existing bytes/entries retained, new library appended.
 * changed=0 leaves output unused. Empty input creates primary + shared entries.
 * Linux errno result; no filesystem/runtime/writer or Steam-acceptance claim. */
int ideck_shared_library_plan(const char *,size_t,char *,size_t,size_t *,int *);
/* Native Linux PID1 owner only, before any guest starts. Caller must own this
 * private root exclusively. Keeps an exact old-file backup, no migration. */
int ideck_shared_library_register(int *changed);
#endif
