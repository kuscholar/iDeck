#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Observe the original Wine initial pthread in the private Lab copy only."""
CREATE='int ret = pthread_create(&g_wine_thread, &attr, wine_process_thread, NULL);'
REPLACEMENT='int ret = ideck_lab_wine_initial_create(&g_wine_thread, &attr, wine_process_thread, NULL);'
DETACH='    pthread_detach(g_wine_thread);'
EARLY='    if (g_prefix_path) free(g_prefix_path);'
NORMAL='            dprintf(STDERR_FILENO, "[WineProc] __wine_main returned normally\\n");'
LONGJMP='            dprintf(STDERR_FILENO, "[WineProc] Wine exited with code %d (caught by longjmp)\\n", wine_ios_exit_code);'
def patched(source):
    start=source.index('int wine_process_start(const char *prefix_path) {')
    assert source.count(CREATE)==1 and source.count(DETACH)==1,'Pinned Wine initial thread contract changed'
    assert source.count(NORMAL)==1 and source.count(LONGJMP)==1,'Pinned Wine body result contract changed'
    source=source.replace(NORMAL,NORMAL+'\n            (void)ideck_lab_wine_initial_report_result(IDECK_WINE_BODY_NORMAL_RETURN, 0);')
    source=source.replace(LONGJMP,LONGJMP+'\n            (void)ideck_lab_wine_initial_report_result(IDECK_WINE_BODY_LONGJMP, (uint32_t)wine_ios_exit_code);')
    start=source.index('int wine_process_start(const char *prefix_path) {')
    before=source[:start];body=source[start:]
    assert body.count(EARLY)==1
    body=body.replace(EARLY,'    if (ideck_lab_wine_initial_ready()) {\n        LOG("Lab initial Wine pthread is not reaped; preserve the current session");\n        return -1;\n    }\n\n'+EARLY)
    return '#include "WineInitialJoin.h"\n'+before+body.replace(CREATE,REPLACEMENT).replace(DETACH,'    /* Lab observer owns the initial pthread join; other Wine threads unchanged. */')
