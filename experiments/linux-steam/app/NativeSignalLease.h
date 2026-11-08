/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#ifndef IDECK_NATIVE_SIGNAL_LEASE_H
#define IDECK_NATIVE_SIGNAL_LEASE_H

struct ideck_signal_lease;
/* Native-owner assertions, NOT guest-controlled IPC. Unknown counts must be
 * negative. The caller must actually measure all categories before release.
 * The current Lab cannot attest other_native_workers, so MUST use -1. */
struct ideck_signal_quiescence {
    int runtime_call_returned;
    int future_guest_starts_disabled;
    int guest_tasks;
    int native_guest_entries;
    int other_native_workers;
};
/* All calls belong to one dedicated native serial owner thread. Other signal
 * owners must also be serialized: POSIX sigaction has no compare-and-swap API.
 * This is a signal-resource component, NEVER permission to start Wine/restart.
 * Not integrated into the Lab until authoritative full worker cleanup exists. */
struct ideck_signal_lease *ideck_signal_lease_capture(void (*expected_usr1)(int));
int ideck_signal_lease_claim(struct ideck_signal_lease *lease);
int ideck_signal_lease_release(struct ideck_signal_lease *lease,
                              const struct ideck_signal_quiescence *proof);
/* Releases bookkeeping only. Captured/owned leases refuse destruction. A
 * poisoned lease may be destroyed but does NOT mean signals were restored. */
int ideck_signal_lease_destroy(struct ideck_signal_lease *lease);
#endif
