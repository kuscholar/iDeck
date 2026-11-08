/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#include "../app/LinuxLabRuntime.h"
#include <stdio.h>
#include <string.h>
int main(int argc, char **argv) {
    if (argc != 2 && argc != 3) return 2;
    int steam = argc == 3 && !strcmp(argv[2], "--steam-loader-probe");
    int compat = argc == 3 && !strcmp(argv[2], "--compatibility-probe");
    if (argc == 3 && !steam && !compat) return 2;
    int status = steam ? ideck_linux_lab_steam_probe(argv[1]) : compat ? ideck_linux_lab_compat_probe(argv[1]) : ideck_linux_lab_run(argv[1]);
    printf("embedded-wait-status=%d\n", status);
    printf("embedded-stage=%s\n", ideck_linux_lab_stage());
    int repeat = ideck_linux_lab_run(argv[1]);
    printf("repeat-start=%d\n", repeat);
    return status != (compat ? 125 << 8 : 0) || repeat != -16;
}
