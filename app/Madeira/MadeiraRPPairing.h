// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
//
// On-device remote pairing (iOS 27 and later): build/rppairing-ios, linked as
// libmadeira_rppairing.a. Keep in step with build/rppairing-ios/src/lib.rs.

#ifndef MADEIRA_RPPAIRING_H
#define MADEIRA_RPPAIRING_H

#include <stddef.h>
#include <stdint.h>

typedef struct MadeiraRPPairing MadeiraRPPairing;
typedef void (*MadeiraRPPairingPinCallback)(const char *pin, void *context);

/// New host identity and a listener on all IPv4 interfaces. NULL on failure,
/// with *error set (free with madeira_rppairing_string_free).
MadeiraRPPairing *madeira_rppairing_new(const char *name, char **error);
uint16_t madeira_rppairing_port(const MadeiraRPPairing *session);
/// The Bonjour instance name to publish; owned by the session.
const char *madeira_rppairing_service_name(const MadeiraRPPairing *session);
size_t madeira_rppairing_txt_count(const MadeiraRPPairing *session);
const char *madeira_rppairing_txt_key(const MadeiraRPPairing *session, size_t index);
const char *madeira_rppairing_txt_value(const MadeiraRPPairing *session, size_t index);
/// Blocks until paired (0), failed (1, *error set) or cancelled (2). On success
/// *out_plist/*out_len hold the RPPairing plist (madeira_rppairing_bytes_free)
/// and *out_device_name the device's name (madeira_rppairing_string_free).
int32_t madeira_rppairing_accept(const MadeiraRPPairing *session,
                                 MadeiraRPPairingPinCallback pin_callback, void *pin_context,
                                 uint8_t **out_plist, size_t *out_len,
                                 char **out_device_name, char **error);
/// Ends a running or future accept with 2. Any thread.
void madeira_rppairing_cancel(const MadeiraRPPairing *session);
/// Only after accept has returned (or was never called).
void madeira_rppairing_free(MadeiraRPPairing *session);
void madeira_rppairing_bytes_free(uint8_t *bytes, size_t len);
void madeira_rppairing_string_free(char *string);

#endif
