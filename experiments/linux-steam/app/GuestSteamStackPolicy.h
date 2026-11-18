/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#ifndef IDECK_GUEST_STEAM_STACK_POLICY_H
#define IDECK_GUEST_STEAM_STACK_POLICY_H
#ifndef IDECK_LAB_PTHREAD_STACK_SOFT_LIMIT
#define IDECK_LAB_PTHREAD_STACK_SOFT_LIMIT 0
#endif
#if IDECK_LAB_PTHREAD_STACK_SOFT_LIMIT != 0 && IDECK_LAB_PTHREAD_STACK_SOFT_LIMIT != 1
#error Select only the explicit default-off guest stack policy
#endif
/* Fixed Linux guest shell policy immediately before Steam; already-started X11
 * services keep their limits. No Darwin RLIMIT, hard limit or explicit pthread
 * attributes are changed. set -e in the caller rejects failure. Inherited soft
 * limit guides glibc defaults; it does not bound explicitly sized CEF stacks.
 * Read back numeric limits locally, never account/environment values.
 */
#if IDECK_LAB_PTHREAD_STACK_SOFT_LIMIT
#define IDECK_GUEST_STEAM_STACK_POLICY \
    "ideck_stack_hard_before=$(ulimit -H -s); ulimit -S -s 4096; " \
    "test \"$(ulimit -S -s)\" = 4096; " \
    "test \"$(ulimit -H -s)\" = \"$ideck_stack_hard_before\"; " \
    "printf 'soft_kib=%s\\nhard_kib=%s\\n' \"$(ulimit -S -s)\" \"$(ulimit -H -s)\" > /tmp/ideck-steam-stack-policy.txt; " \
    "unset ideck_stack_hard_before; "
#else
#define IDECK_GUEST_STEAM_STACK_POLICY ""
#endif
#endif
