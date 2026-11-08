/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#ifndef IDECK_LINUX_LAB_RUNTIME_H
#define IDECK_LINUX_LAB_RUNTIME_H
/* Consumes one runtime lifetime. Returns Linux errno or guest wait status.
 * Run on a worker thread. This does not establish all-task quiescence. */
int ideck_linux_lab_run(const char *root_path);
/* Loader-only experiment in an independent root with no account data. */
int ideck_linux_lab_steam_probe(const char *root_path);
int ideck_linux_lab_compat_probe(const char *root_path);
const char *ideck_linux_lab_stage(void);
#endif
