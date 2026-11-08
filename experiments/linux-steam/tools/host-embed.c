/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#include "../app/LinuxLabRuntime.h"
#include <stdio.h>
#include <string.h>
int main(int argc, char **argv) {
    if (argc != 2 && argc != 3) return 2;
    int steam = argc == 3 && !strcmp(argv[2], "--steam-loader-probe");
    int compat = argc == 3 && !strcmp(argv[2], "--compatibility-probe");
    int distro = argc == 3 && !strcmp(argv[2], "--distro-probe");
    if (argc == 3 && !steam && !compat && !distro) return 2;
    int status = distro ? ideck_linux_lab_distro_probe(argv[1]) : steam ? ideck_linux_lab_steam_probe(argv[1]) : compat ? ideck_linux_lab_compat_probe(argv[1]) : ideck_linux_lab_run(argv[1]);
    printf("embedded-wait-status=%d\n", status);
    printf("embedded-stage=%s\n", ideck_linux_lab_stage());
    int other = ideck_linux_lab_native_worker_entries();
    printf("linux-worker-entries=%d\n", other);
#if !IDECK_LAB_NATIVE_WORKERS
    if (other != -95) return 1; /* Disabled means unknown, not falsely clean. */
#endif
    int repeat = ideck_linux_lab_run(argv[1]);
    printf("repeat-start=%d\n", repeat);
    return status != (compat ? 125 << 8 : 0) || repeat != -16;
}
