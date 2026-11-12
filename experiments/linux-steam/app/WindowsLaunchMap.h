/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#ifndef IDECK_WINDOWS_LAUNCH_MAP_H
#define IDECK_WINDOWS_LAUNCH_MAP_H
#include "LaunchProtocol.h"
#define IDECK_DOCK_LIBRARY "SteamLibrary/steamapps"
struct ideck_windows_launch_map {
    uint32_t appid,verb,argc,argument_bytes;
    char install[1024],executable[1024],working[1024],arguments[4096];
};
/* Metadata conversion ONLY for the explicitly shared library under the Lab's
 * physical drive_c/SteamLibrary. Other arguments keep their boundaries; this is
 * NOT a shell/MADEIRA_ARGS string, file/owner check or runtime/writer permission.
 * Default /Steam needs a separate storage contract and returns ENOTSUP.
 */
int ideck_windows_launch_map(const struct ideck_launch_request *,struct ideck_windows_launch_map *);
#endif
