/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#ifndef IDECK_SHARED_STEAM_LIBRARY_H
#define IDECK_SHARED_STEAM_LIBRARY_H
#define IDECK_SHARED_STEAM_GUEST "/mnt/ideck/SteamLibrary"
/* Initial native Linux owner only, after root/init and before any guest child.
 * Default source is root_directory/SharedSteamLibrary. Explicit DOCK_STORAGE
 * uses MadeiraPrefix/drive_c/SteamLibrary and refuses an existing default source.
 * Mounts via LinuxRunner realfs. No migration
 * of the default /Steam library, account/config or existing games. Never remount
 * in an existing native lifetime, or use this as an exclusive-writer certificate.
 */
/* Native-only directory preparation; returns an owned directory descriptor.
 * May run before Linux initialization. Does not mount/start/claim a runtime. */
int ideck_shared_steam_prepare(const char *root_directory);
int ideck_shared_steam_mount(const char *root_directory);
#endif
