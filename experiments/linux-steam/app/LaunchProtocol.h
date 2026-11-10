/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#ifndef IDECK_LAUNCH_PROTOCOL_H
#define IDECK_LAUNCH_PROTOCOL_H
#include <stdint.h>
#include <stddef.h>
#define IDECK_LAUNCH_MAGIC 0x314b4449u
#define IDECK_LAUNCH_VERSION 1u
#define IDECK_LAUNCH_MAX_ARGS 32u
#define IDECK_LAUNCH_ROOT "/mnt/ideck/SteamLibrary/steamapps/common/"
#define IDECK_LAUNCH_DEFAULT_ROOT "/Steam/steamapps/common/"
/* Fixed little-endian frame; ARM64 guest and iOS host are both little-endian.
 * No host pointer, pid, credentials or unconstrained environment values. */
struct ideck_launch_request {
    uint32_t magic, version, appid, verb, argc, argument_bytes;
    char install[1024], executable[1024], working[1024], compatdata[1024];
    char arguments[4096];
};
struct ideck_launch_response { uint32_t magic, version, appid, result; };
_Static_assert(sizeof(struct ideck_launch_request) == 8216, "launch ABI");
_Static_assert(sizeof(struct ideck_launch_response) == 16, "response ABI");
/* Syntax-only validation. Never authorizes native file access or execution. */
int ideck_launch_validate(const void *frame, size_t size);
#endif
