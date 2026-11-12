/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#ifndef IDECK_GAME_FILES_H
#define IDECK_GAME_FILES_H
#include <stddef.h>
#include <stdint.h>
enum ideck_library_kind { IDECK_LIBRARY_DEFAULT, IDECK_LIBRARY_SHARED };
/* Trusted NATIVE capabilities, never paths/descriptors supplied by a guest.
 * The caller retains/serializes these handles throughout open(). -1 disables
 * a library. Each descriptor names that library's steamapps/common directory.
 */
struct ideck_library_caps { int default_common,shared_common; };
struct ideck_game_files;
/* Copies and validates the fixed IPC frame ONCE. Opens every component relative
 * to the selected capability, without following symlinks or changing cwd.
 * Initial experiment accepts singly linked regular .exe files with a supported
 * Windows PE identity; it is not a complete PE verifier or a licensing check.
 * Returns native negative errno. *out must be NULL, remains NULL on failure.
 */
int ideck_game_files_open(const struct ideck_library_caps *libraries,
    const void *frame,size_t size,struct ideck_game_files **out);
/* Native embedding convenience: data_directory is the trusted app-private
 * LinuxRootFS/data capability. Opens ONLY the selected fixed library subtree
 * on each request, so a later Steam download may create common/ legitimately.
 * No guest-selected native root, bind-mount/symlink following or file creation.
 */
int ideck_game_files_from_data(int data_directory,const void *frame,size_t size,
    struct ideck_game_files **out);
/* Separate realfs library's native root (containing steamapps), not fakefs data.
 * -1 keeps the legacy from_data route. Neither descriptor proves ownership. */
int ideck_game_files_from_roots(int data_directory,int shared_library_directory,
    const void *frame,size_t size,struct ideck_game_files **out);
void ideck_game_files_close(struct ideck_game_files *files);
/* Borrowed, read-only handles; caller must not close them. They pin observed
 * objects, not future path lookups by Wine. Never execute a host shell/command.
 */
int ideck_game_files_executable(const struct ideck_game_files *files);
int ideck_game_files_working(const struct ideck_game_files *files);
uint32_t ideck_game_files_appid(const struct ideck_game_files *files);
unsigned ideck_game_files_machine(const struct ideck_game_files *files);
enum ideck_library_kind ideck_game_files_library(const struct ideck_game_files *files);
/* Best-effort metadata/path revalidation, NOT an atomic freeze or execution
 * authorization. Future sequential handoff must first stop all guest writers,
 * acquire an exclusive storage lease, and preserve Valve's legitimate launch
 * and ownership checks through Madeira. This component launches NOTHING.
 */
int ideck_game_files_unchanged(const struct ideck_game_files *files);
#endif
