/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * HOST control: use the actual C ABI to invoke the Swift export. */
#include "LabDockRequestBridge.h"
int32_t ideck_test_call_dock_receiver(const void *bytes,size_t count,uint64_t sequence) {
    return ideck_lab_receive_dock_request(bytes,count,sequence);
}
