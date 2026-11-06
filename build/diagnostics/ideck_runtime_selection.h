/* SPDX-License-Identifier: GPL-3.0-or-later
 * Madeira Converter Exception: see LICENSE-EXCEPTION.md.
 * Explicit persisted launch selection, shared with the Swift launch policy. */
#ifndef IDECK_RUNTIME_SELECTION_H
#define IDECK_RUNTIME_SELECTION_H
#include <stdlib.h>
#include <string.h>
#include <stddef.h>

static int ideck_steam64_selected(const char *configured, int argc, char **argv)
{
    for (int i=1;i<argc;i++)
        if (argv[i] && (!strcmp(argv[i],"madeira-steam64-experiment") ||
                        !strcmp(argv[i],"madeira-steam64-big-picture-experiment") ||
                        !strcmp(argv[i],"madeira-cef64-component-diagnostics"))) return 1;
    /* An explicit legacy/other diagnostic must not inherit product mode. */
    for (int i=1;i<argc;i++)
        if (argv[i] && !strncmp(argv[i],"madeira-",8)) return 0;
    return configured && !strcmp(configured,"steam64");
}

/* Only a locally opted-in full64 profile needs these before native holds/JIT.
 * Read the existing config with its normal parser, without Foundation/SwiftUI
 * allocations. Explicit launch environment values continue to win. */
static int ideck_steam64_early_environment(const char *configured, int argc,
    char **argv, int (*read_config)(const char *, char *, size_t))
{
    char value[128], key[160];
    static const char *const names[]={
        "MADEIRA_STEAM_UI_SESSION", "MADEIRA_CEF64_SOURCE_LAYOUT",
        "MADEIRA_CEF64_SPLIT_LAYOUT", "MADEIRA_CEF64_NEAR_CODE",
        "MADEIRA_CEF64_CRASH_POOLS", "MADEIRA_CEF64_MULTI_TABLES",
        "MADEIRA_CEF64_FOUR_TABLES", "MADEIRA_CEF64_SIX_TABLES",
        "MADEIRA_CEF64_SEVENTH_TABLE", "MADEIRA_CEF64_EIGHTH_TABLE",
        "MADEIRA_CEF64_NINTH_TAIL_TABLE", "MADEIRA_CEF64_TWELVE_TABLES",
        "MADEIRA_CEF64_TABLES_FROM_ARENA", "MADEIRA_CEF64_STANDALONE_LAYOUT",
        "MADEIRA_CEF64_EXTERNAL_CRASHPAD", "MADEIRA_CEF64_COMPACT_SOURCE_POOLS",
        "MADEIRA_CEF64_WIDE_ARENA", "MADEIRA_CEF64_EXACT_POOL_B",
        "MADEIRA_CEF64_KEEP_LOW_POOL", "MADEIRA_CEF64_FEX_PACK",
        "MADEIRA_CEF64_IMAGE_SPILL", "MADEIRA_CEF64_LIBCEF_DATA_ONLY",
        "MADEIRA_CEF64_ROOT_STORE", "MADEIRA_FEX_IR_HALF_MIB",
        "MADEIRA_FEX_DECODER_COMPACT", "MADEIRA_X64_IMAGE_NOCOPY",
        "MADEIRA_POOL_LOW_IMAGES", "MADEIRA_THREAD_STACK_SPILL",
        "MADEIRA_CPU_COUNT", "MADEIRA_STEAM64_DIRECT_CEF32", "MADEIRA_JIT_DUMP",
        "MADEIRA_STEAM_UI_STRICT_RESERVATIONS", "MADEIRA_SMALL_STACK_EXES"
        ,"MADEIRA_CEF64_DELAYLOAD_TRACE", "MADEIRA_CEF64_LEASE_FILE",
        "MADEIRA_CEF64_LEASE_TRACE", "MADEIRA_CEF64_SECTION_TRACE",
        "MADEIRA_STEAM64_GAME_LAUNCH_DIAGNOSTICS", "MADEIRA_STEAM64_INPUT_DIAGNOSTICS",
        "MADEIRA_STEAM_UI_MODULE_ERRORS", "MADEIRA_JITLESS", "MADEIRA_LEAN_DIAG", "MADEIRA_STEAM_UI_SAMPLING", "MADEIRA_CEF64_UNITY_DATA_ONLY",
        "MADEIRA_CEF64_IMAGE_DATA_PROBE"
    };
    if (!configured || strcmp(configured,"steam64") ||
        !ideck_steam64_selected(configured,argc,argv)) return 0;
    const char *restore=getenv("MADEIRA_CEF64_CONFIG_RESTORE");
    if (restore && !strcmp(restore,"1")) return 0;
    if (!read_config("steam64.env.MADEIRA_CEF64_SOURCE_LAYOUT",value,sizeof(value)) || strcmp(value,"1") ||
        !read_config("steam64.env.MADEIRA_STEAM_UI_SESSION",value,sizeof(value)) || strcmp(value,"1")) return -1;
    for (size_t i=0;i<sizeof(names)/sizeof(names[0]);i++)
    {
        size_t n=strlen(names[i]);
        /* Do not leak a selected full64 profile into explicit legacy probes
         * through the ordinary env.* exporter later in the launch. */
        memcpy(key,"steam64.env.",12);memcpy(key+12,names[i],n+1);
        if (!getenv(names[i]) && read_config(key,value,sizeof(value)) && value[0] &&
            setenv(names[i],value,0)) return -1;
    }
    return 1;
}
#endif
