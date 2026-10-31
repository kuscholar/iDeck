# CEF64 / FEX IR allocation failure: Build 122

This is an observed failure and a read-only source diagnosis, not a runtime fix
or a successful game-return result. Runtime code is based on
`be8151a7bf5773b1013f275161b7db6149284bcc` plus local experimental changes.
Raw device artifacts remain outside Git; hashes are recorded in
`CEF64_IR_ALLOCATION_FAILURE_EVIDENCE.json`.

## Device observation

The genuine AMD64 Steam session logged in with its saved account. Steam records
Hot Roads (`hr.exe`, guest PID 752) starting at 2026-10-30 23:53:55 EDT.
Fresh Unity output identifies Direct3D 11 level 11.1 / Apple A17 Pro GPU, Mono
assembly reload in 0.912 seconds, and input/touch initialization.
This is engine progress, not a new visual gameplay confirmation.

Later, native Wine cannot satisfy a 16 MiB allocation in the owned
`[0x7500000000,0x7760000000)` FEX arena. Its census reports:

| Measurement | Actual value |
| --- | --- |
| Live Wine views | 1153 |
| Total free virtual bytes | `0x41e1000` |
| Largest aligned free interval | `0xdc0000` |
| Requested interval | `0x1000000` |
| Overlapping Wine views | `0` |
| 16 MiB reserved RW views | 440 |

Total free bytes exceed the request, but no contiguous interval fits it.
These are virtual address measurements, not free physical RAM or disk space.
The count alone does not establish a leak or identify the owner of every view.

The next captured native failure writes to `0x800010` with x8=`0x800000`.
The trace resolves its PC to `libarm64ecfex.dll+0xfe770`, then terminates the
native session after 2000 identical exception redeliveries. Do not suppress
that guard or return a fabricated memory allocation.

## Exact code and local discriminator

The prepared/signed bundle's `arm64ec-windows/xtajit64.dll` is the
`libarm64ecfex.dll` image, SHA256:

`a32e1b21bf19b91d189b0675e215917c6e59f16f66ea126cf719226d5889c72c`

Its COFF symbols identify RVA `0xfe750` as
`FEXCore::IR::IREmitter::ResetWorkingList()`. RVA `0xfe770` is
`str wzr, [x8, #0x10]`, matching the device instruction and registers.
The module/function attribution uses the actual trace and matching instruction
sequence. A direct prefix-file hash readback was refused for the bundle-linked
path; do not describe this as an independent device-file SHA verification.

Read-only inspection of pinned FEX shows:

1. `IREmitter` constructs its dual allocator with two 8 MiB halves.
2. `DualIntrusiveAllocatorThreadPool::ReownOrClaimBuffer` sets `Data` to the
   returned allocation and computes `List = Data + MemorySize`.
3. If the allocation returns NULL, `List` becomes `0x800000`.
4. `ResetWorkingList` allocates an invalid node and zeroes it without rejecting
   that NULL backing. The observed node field write is at `0x800010`.

Run this diagnostic from the iDeck checkout:

```sh
python3 tests/host/reproduce-fex-ir-null-buffer.py
```

It compiles the unchanged pinned dual-allocator classes into a temporary
ASan/UBSan harness with synthetic success/NULL allocation results. The success
case writes only into its own real buffer. The failure case reproduces the
`0x800000` result without dereferencing it. No FEX source or binary is modified.
This reproduces pointer arithmetic after an allocation failure; it does not
explain all arena growth or prove an allocator-lifetime leak.

## Separate failures and current boundaries

- The earlier Unity graphics error was a DLL placement failure. Build 119's
  actual guarded `d3d11.dll` spill and module load passed that point.
- The user's confirmed game entry and normal exit in Build 119 are separate
  evidence from this later failed session.
- CEF also needs more live 512 MiB ExternalEntityTable reservations than some
  layouts provide. Do not recycle a live/preserved placeholder to hide it.
- Build 120 stopped unnecessarily launching another Steam client when an
  existing Big Picture window is found. Its measured return still reported
  focus pending; responsive return is not established.
- Build 121 adds bounded window-response / actual-focus diagnostics. No
  successful post-game focus handoff has been collected yet.
- Build 122's opt-in exact second-JIT-pool attempt failed full RX validation,
  released its own new range and did not retry. It is not an accepted solution.

## Next work

The next allocation study should attribute 16 MiB arena reservations and their
complete release/retirement lifetime under an isolated thread/IR workload.
Keep FEX and Valve files unchanged unless the explicit local-experiment
restriction is reconsidered. A controlled failure path would prevent the
invalid write, but would not by itself provide enough address space for Steam
and a game. A longer-term design needs demonstrated lower buffer/table demand
or genuine additional non-overlapping address capacity.

No stable full64 game/return, Bluetooth, account-switch regression, or
long-term GO result is claimed here.
