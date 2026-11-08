/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#ifndef IDECK_GUEST_LIFETIME_H
#define IDECK_GUEST_LIFETIME_H
/* Internal copied-archive hooks. Reserve BEFORE pthread_create; retire only
 * on create failure or the outer guest-entry pthread cleanup callback. */
void ideck_guest_lifetime_reserve(void);
void ideck_guest_lifetime_retire(void *unused);
unsigned ideck_guest_lifetime_live(void);
const char *ideck_guest_lifetime_marker(void);
#endif
