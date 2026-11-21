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

def patched_server(source):
    # Observe the server's actual pthread join and main return in the private Lab only.
    before, stop = source.split("void wineserver_stop(void) {", 1)
    thread = 'static void *wineserver_thread_func(void *arg) {'
    marker = '        g_wineserver_running = 0;\n    }\n    return NULL;'
    token = '''static char ideck_server_zero_token;
static char ideck_server_nonzero_token;
static void *ideck_server_main_exit_value(int result) {
    return result ? &ideck_server_nonzero_token : &ideck_server_zero_token;
}
'''
    assert before.count(thread)==1 and before.count(marker)==1
    before=before.replace(thread,token+thread).replace(marker,
        '        g_wineserver_running = 0;\n        return ideck_server_main_exit_value(ret);\n    }')
    join = '        pthread_join(t, NULL);'
    finished = '        wine_log_msg("Wineserver thread joined");\n    }'
    assert stop.count(join) == 1 and stop.count(finished) == 1, "Pinned wineserver stop contract changed"
    stop = stop.replace(join, '''        void *value = NULL;
        int error = pthread_join(t, &value);
        unsigned main_outcome = IDECK_WINE_SERVER_MAIN_UNKNOWN;
        if (!error && value == &ideck_server_zero_token)
            main_outcome = IDECK_WINE_SERVER_MAIN_RETURNED_ZERO;
        if (!error && value == &ideck_server_nonzero_token)
            main_outcome = IDECK_WINE_SERVER_MAIN_RETURNED_NONZERO;
        (void)ideck_lab_wine_initial_report_server_join(1, error, main_outcome);''')
    stop = stop.replace(finished, '''        if (!error) wine_log_msg("Wineserver thread joined");
        else wine_log_msg("Wineserver join failed: %d", error);
    } else {
        (void)ideck_lab_wine_initial_report_server_join(0, 0, IDECK_WINE_SERVER_MAIN_UNKNOWN);
    }''')
    return '#include "WineInitialJoin.h"\n' + before + "void wineserver_stop(void) {" + stop
