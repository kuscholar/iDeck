/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#ifndef IDECK_VA_HEADROOM_PROBE_H
#define IDECK_VA_HEADROOM_PROBE_H
#include <stddef.h>
#include <sys/types.h>
#define IDECK_VA_HEADROOM_BYTES (16u*1024u*1024u)
/* Prepare before Linux; one owned PROT_NONE reservation, no contents accessed.
 * The single-use probe releases it, then asks the OS for a fresh file mapping
 * without a fixed/hinted address. Never retries/replaces the guest request. */
int ideck_va_headroom_prepare(void);
void ideck_va_headroom_probe(int fd,size_t bytes,off_t offset,int prot,int flags,int error);
#endif
