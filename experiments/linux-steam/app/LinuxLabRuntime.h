/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#ifndef IDECK_LINUX_LAB_RUNTIME_H
#define IDECK_LINUX_LAB_RUNTIME_H
/* Consumes one runtime lifetime. Returns Linux errno or guest wait status.
 * Run on a worker thread. This does not establish all-task quiescence. */
int ideck_linux_lab_run(const char *root_path);
/* Loader-only experiment in an independent root with no account data. */
int ideck_linux_lab_steam_probe(const char *root_path);
int ideck_linux_lab_compat_probe(const char *root_path);
/* Fixed, non-authenticating Debian/glibc control in a prepared private fakefs.
 * root_path contains data/ and meta.db; never a production prefix. */
int ideck_linux_lab_distro_probe(const char *root_path);
/* Explicit frontend build only; one lifetime, no reusable shutdown guarantee. */
int ideck_linux_lab_steam_frontend(const char *root_path);
/* Explicit fixed, signed-Debian dependency repair in this Lab root only. */
int ideck_linux_lab_dependencies(const char *root_path);
/* Optional copied-archive count includes queued guest starts until outer cleanup.
 * Negative means unsupported/invalid. Zero is not a Wine/restart permission. */
int ideck_linux_lab_live_guest_threads(void);
/* Optional accounting for four LinuxRunner native-worker providers only;
 * excludes UIKit/RFB/TLS destructors and never authorizes Wine/restart. */
int ideck_linux_lab_native_worker_entries(void);
struct ideck_tool_payload;
struct ideck_x11_trace_payload;
/* Explicit diagnostic build only. Bundle-owned Linux ELF bytes, preboot VFS
 * installation and fixed child environment; no live-session injection. */
int ideck_linux_lab_steam_frontend_with_trace(const char *root_path,
    const struct ideck_tool_payload *tool,const struct ideck_x11_trace_payload *trace);
/* Opt-in preboot installer; the payload belongs to the signed native app. */
int ideck_linux_lab_steam_frontend_with_tool(const char *root_path,const struct ideck_tool_payload *tool);
/* Diagnostic125 only, with synthetic metadata; no Steam ownership/game claim. */
int ideck_linux_lab_compatibility_tool_probe(const char *root_path,const struct ideck_tool_payload *tool);
const char *ideck_linux_lab_stage(void);
/* Private numeric diagnostic only. Nonblocking bounded task-table observation;
 * last syscall may have returned. Never a stopped frame or handoff permission. */
void ideck_linux_lab_log_tasks(void);
#endif
