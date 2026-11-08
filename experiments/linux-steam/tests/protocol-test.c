/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#include "../app/LaunchProtocol.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static struct ideck_launch_request valid(void) {
    struct ideck_launch_request r = {
        .magic=IDECK_LAUNCH_MAGIC, .version=IDECK_LAUNCH_VERSION, .appid=480,
        .verb=1, .argc=2, .install=IDECK_LAUNCH_ROOT "Control", .working=IDECK_LAUNCH_ROOT "Control",
        .executable=IDECK_LAUNCH_ROOT "Control/control.exe", .arguments=IDECK_LAUNCH_ROOT "Control/control.exe\0--demo"
    };
    r.argument_bytes = sizeof(IDECK_LAUNCH_ROOT "Control/control.exe\0--demo");
    return r;
}
int main(void) {
    struct ideck_launch_request r = valid();
    assert(ideck_launch_validate(&r, sizeof r) == 0);
    for (size_t n = 0; n < sizeof r; n++) assert(ideck_launch_validate(&r, n) < 0);
    r.appid = 0; assert(ideck_launch_validate(&r, sizeof r) < 0);
    r = valid(); r.version++; assert(ideck_launch_validate(&r, sizeof r) < 0);
    r = valid(); r.verb = 3; assert(ideck_launch_validate(&r, sizeof r) < 0);
    r = valid(); r.argc = 33; assert(ideck_launch_validate(&r, sizeof r) < 0);
    r = valid(); r.argument_bytes++; assert(ideck_launch_validate(&r, sizeof r) < 0);
    r = valid(); r.arguments[sizeof r.arguments - 1] = 'x'; assert(ideck_launch_validate(&r, sizeof r) < 0);
    r = valid(); r.compatdata[1] = 'x'; assert(ideck_launch_validate(&r, sizeof r) < 0);
    const char *bad[] = {"/tmp/game.exe", IDECK_LAUNCH_ROOT "Control/../escape.exe", IDECK_LAUNCH_ROOT "ControlSibling/file.exe", IDECK_LAUNCH_ROOT "Control//bad.exe", IDECK_LAUNCH_ROOT "Control/./bad.exe"};
    for (unsigned i = 0; i < sizeof bad / sizeof bad[0]; i++) {
        r = valid(); memset(r.executable, 0, sizeof r.executable); strcpy(r.executable, bad[i]);
        assert(ideck_launch_validate(&r, sizeof r) < 0);
    }
    r = valid(); memset(r.install, 'x', sizeof r.install); assert(ideck_launch_validate(&r, sizeof r) < 0);
    /* Mutate every byte deterministically under sanitizers, including lengths. */
    for (size_t i = 0; i < sizeof r; i++) { r = valid(); ((unsigned char *)&r)[i] ^= 0xff; (void)ideck_launch_validate(&r, sizeof r); }
    puts("protocol: valid frame, truncation, hostile sizes/paths, argument boundaries, mutation PASS");
}
