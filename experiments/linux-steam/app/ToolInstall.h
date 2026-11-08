/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#ifndef IDECK_TOOL_INSTALL_H
#define IDECK_TOOL_INSTALL_H
#include <stddef.h>
#define IDECK_COMPAT_TOOL_DIR "/Steam/compatibilitytools.d/ideck-madeira-lab-v1"
#define IDECK_COMPAT_TOOL_EXE IDECK_COMPAT_TOOL_DIR "/ideck-madeira"
#define IDECK_COMPAT_TOOL_STAGE "/Steam/compatibilitytools.d/.ideck-madeira-lab-v1-installing"
struct ideck_tool_payload {
    const void *executable; size_t executable_size;
    const void *compatibility; size_t compatibility_size;
    const void *manifest; size_t manifest_size;
};
/* Before guest execution, in this Lab's mounted VFS and current native init
 * context. Assets originate in the signed app bundle, never guest requests.
 * Existing matching files are reused; conflicts/stale stages are preserved.
 * Returns Linux errno, sets created only after a newly complete publication. */
int ideck_tool_install(const struct ideck_tool_payload *payload,int *created);
#endif
