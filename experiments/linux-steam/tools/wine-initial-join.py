#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Observe the original Wine initial pthread in the private Lab copy only."""
CREATE='int ret = pthread_create(&g_wine_thread, &attr, wine_process_thread, NULL);'
REPLACEMENT='int ret = ideck_lab_wine_initial_create(&g_wine_thread, &attr, wine_process_thread, NULL);'
DETACH='    pthread_detach(g_wine_thread);'
EARLY='    if (g_prefix_path) free(g_prefix_path);'
def patched(source):
    start=source.index('int wine_process_start(const char *prefix_path) {')
    assert source.count(CREATE)==1 and source.count(DETACH)==1,'Pinned Wine initial thread contract changed'
    before=source[:start];body=source[start:]
    assert body.count(EARLY)==1
    body=body.replace(EARLY,'    if (ideck_lab_wine_initial_ready()) {\n        LOG("Lab initial Wine pthread is not reaped; preserve the current session");\n        return -1;\n    }\n\n'+EARLY)
    return '#include "WineInitialJoin.h"\n'+before+body.replace(CREATE,REPLACEMENT).replace(DETACH,'    /* Lab observer owns the initial pthread join; other Wine threads unchanged. */')
