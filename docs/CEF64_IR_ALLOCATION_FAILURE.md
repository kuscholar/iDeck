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
The user subsequently authorized a private local FEX experiment only; see
the dated continuation below. Keep the original FEX submodule and all Valve
files unchanged. A controlled failure path would prevent the
invalid write, but would not by itself provide enough address space for Steam
and a game. A longer-term design needs demonstrated lower buffer/table demand
or genuine additional non-overlapping address capacity.

No stable full64 game/return, Bluetooth, account-switch regression, or
long-term GO result is claimed here.


## 2026-10-31 private authorized continuation: Build 123

The user explicitly permitted an isolated local FEX IR-size/failure-handling
experiment with no upstream submission. The private detached copy has no
remotes. This repository does not contain its modified FEX source or binary,
and the original pinned FEX submodule is unchanged.

The hypothesis was that 4 MiB paired IR buffers, with MAXINST reduced to 256
and release-mode bounds/NULL rejection, would fit substantially more threads
in the existing 9.5 GiB arena. This is a private diagnostic experiment, not
an upstream contribution or a production release. A rejected allocation aborts
explicitly before node access; it does not recover or guarantee game continuity.
Host tests exercised the actual private policy/classes under ASan/UBSan.

Build 123 is a private ARM64EC PE overlay on native Build 122, not a new full
Xcode build. Physical Kusch installation and the actual mode were verified:

- Own AMD64 probe: 16 threads, all outputs match an independent Python integer
  oracle, all thread exits and the enclosing batch exit zero.
- Actual native marker: MAXINST=256 and OpDispatcher allocation size=0x400000.
- Genuine full64 Steam saved login succeeds at 00:24:49 EDT.
- Hot Roads starts at 00:25:46; fresh Unity logs D3D11 level11.1 / A17 Pro GPU,
  Mono reload 0.915 seconds, input/touch initialized. An own helper accepted
  one balanced Enter to its verified game window.
- Steam records normal game exit0 at 00:27:19. The post-exit native snapshot
  contains 89 logged 4 MiB OpDispatcher allocations and no original IR NULL
  write, IR reject, FEX allocation fatal or repeated-exception termination.
  A log count is not a live-allocation census or evidence against every leak.
- Steam's existing Big Picture window responds to bounded WM_NULL after exit,
  but foreground activation fails with error5. Native startup identifies the
  foreground PID32 as Wine explorer. This separates this run's focus problem
  from a dead CEF message queue. A successful focus handoff is still required.

No physical screenshot was available because the Mac was locked. Do not
upgrade engine initialization to a visual gameplay claim. Source-layout V8
table capacity is unchanged. Actual signed regions were A544+B160=704 MiB
and C304 MiB; the reported723 MiB pool span contains an excluded19 MiB gap.
These ASLR-dependent budgets differ from Build122 (A624/noB/C352), so this
single run cannot isolate the IR change as the sole cause. No long-term
memory/performance or broad compatibility conclusion follows from one
successful engine/exit cycle.
Private artifact paths/hashes are recorded in the appended evidence object.
The next separate experiment limits a foreground handoff to the registered
Wine shell/desktop owned by the system explorer; unrelated windows remain
excluded.


The separate return-focus follow-up remains experimental. Build124's
registered-shell-handle check failed on device, despite a second normal
game exit. Build125's desktop-class32769 hypothesis was also falsified: the
actual foreground PID32 window has dynamic class atom49188, while Steam
WM_NULL remains responsive. These negative results are retained; neither
check should be called a device-validated fix. The next bounded discriminator
uses actual canonical system-explorer ownership for an explicit return, logs
queue-attach attempt/error numerically, and never launches another Steam
client when an existing Big Picture window is present.


Build126's first actual return succeeds: the responsive Steam window becomes
the real foreground after one system-explorer-owned queue join, immediately
detached (attached1/detached1/focused1, attach_error0). Steam records normal
game exit0 at00:46:41 EDT. A subsequent direction-key request is accepted and
the bounded no-spawn focus/WM_NULL check still passes. This addresses the
measured activation failure while keeping the independent private IR mode
unchanged. It is not a claim of physical visual gameplay or all browser
threads being healthy. Same-process second-cycle validation is still pending.


The same-process second cycle did NOT pass: PID1024 starts at00:48:17, but
the close times out and no second normal exit is recorded. A later snapshot
shows16MiB aligned allocations failing with max aligned gap0xd90000,475
reserved16MiB RW views, and new Steam/game thread-init errors c0000017.
The original IR NULL write is absent, but checking only its fatal text missed
this propagated allocation failure. Therefore the4MiBIR experiment is not a
long-term capacity solution. The repeated-cycle test remains NO-GO.

Build127 prepares a separate PRIVATE build-time8MiB rpmalloc span/large-page
experiment. Maximum pooled block is reduced to4MiB and large size classes to
16 so each class fits its page including metadata; larger requests retain the
existing huge path. Host tests of the actual allocator pass all pooled classes,
reallocation/huge boundaries,alignment and thread-retirement/remote frees
under ASan/UBSan. POSIX tests adapt only Win32 log sinks and the disabled
allocation-watch hook; they do not exercise Wine's mapping APIs. The DLL is
linked with actual8MiB getter/markers and signed in a disposable app.
Call-return/SEH geometry and native ownership/protection guards are unchanged.

Kusch's current wireless tunnel then disconnects (pairing retained), and the
idle guard refuses installation. Build127 is NOT installed or device-tested.
The independent probe also refuses its missing installation receipt before
mutating anything. The prior126 task is ended and original temporary
configs/attributes are restored. Next must be the independent device probe
with both actual mode markers and oracle/exit checks, before full Steam.
No private FEX source or binary has been published, and no long-term GO is
claimed from host checks or the first successful return.
