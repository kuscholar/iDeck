#ifndef FEX_BRIDGE_H
#define FEX_BRIDGE_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

// Initialize FEXCore engine. Must be called once before any other fex_* functions.
// Returns true on success.
bool fex_initialize(void);

// Shut down FEXCore and free resources.
void fex_shutdown(void);

// Test FEXCore by translating and executing a trivial x86-64 program.
// The test program does: mov eax, 42; ret
// Returns 42 on success, negative on failure.
int64_t fex_test_execute(void);

// Log callback type (same as JIT allocator)
typedef void (*fex_log_callback_t)(const char *message);

// Set a log callback for FEX operations
void fex_set_log_callback(fex_log_callback_t callback);

// Returns the runtime RX->RW distance of the dual-mapped JIT pool
// (g_jit_rw_base - g_jit_rx_base), or 0 if the pool is not yet initialized.
// Published to xtajit64.dll via the MADEIRA_JIT_WRITE_OFFSET env var so its
// own FEXCore copy uses the true offset (the RW alias is placed with
// VM_FLAGS_ANYWHERE and is NOT guaranteed to sit at RX+0x10000000).
int64_t fex_get_jit_write_offset(void);

#ifdef __cplusplus
}
#endif

#endif // FEX_BRIDGE_H
