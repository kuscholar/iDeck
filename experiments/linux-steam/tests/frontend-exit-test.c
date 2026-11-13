/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#include "RetainedFrontend.h"
#include <assert.h>
#include <errno.h>
#include <stdio.h>

int main(void) {
    assert(!ideck_frontend_restart_ready(NULL));
    unsigned admitted = 0;
    for (int status = 0; status <= 65535; status++) {
        struct ideck_frontend_result result = {
            .wave = 1, .reaped = 1, .guest_status = status,
            .phase = IDECK_FRONTEND_DORMANT
        };
        int expected = status == 0 || status == 10752;
        assert(ideck_frontend_restart_ready(&result) == expected);
        admitted += ideck_frontend_restart_ready(&result);
        // Any actual cleanup error blocks both clean and updater exits.
        result.error = -EBUSY;
        assert(!ideck_frontend_restart_ready(&result));
        result.error = 0;
        for (int phase = IDECK_FRONTEND_UNUSED; phase <= IDECK_FRONTEND_POISONED; phase++) {
            result.phase = phase;
            if (phase != IDECK_FRONTEND_DORMANT)
                assert(!ideck_frontend_restart_ready(&result));
        }
    }
    assert(admitted == 2);
    assert(!ideck_frontend_update_exit(42)); // signal bits, not exit42
    assert(!ideck_frontend_update_exit(-1));
    assert(!ideck_frontend_update_exit(0x2a7f)); // stopped status
    struct ideck_frontend_result negative = {
        .guest_status = -1, .phase = IDECK_FRONTEND_DORMANT
    };
    assert(!ideck_frontend_restart_ready(&negative));
    puts("HOST frontend exit classification PASS: all65536 wait statuses; native error/phase gates; Linux reentry only, not game/device proof");
    return 0;
}
