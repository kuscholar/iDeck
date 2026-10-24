# Steam UI interval ownership audit

2026-10-23, Phase 1, parent 026dfde456f9b5015ba5d9ab38d3d4dbb14a194f.
This is an offline audit of the existing Build 18/19 artifacts, not a new device
run or a complete live Mach map. The automated device availability check failed
with CoreDevice 4016 (required trusted connectivity/power assertion unavailable).
It did not establish a lock state. No install or launch was attempted afterward.

## Observed intervals

`tools/analyze-steam-ui-pools.py` extracts only known numeric event fields from
private logs. `STEAM_UI_POOL_INVENTORY.json` records their hashes and line numbers.
Raw log payloads are excluded. Historical intersections do not track releases or
pseudo-process restarts; Build 19's direct rejection against a live Wine view is
stronger evidence of coexisting ownership than an intersection alone.

| Interval, half open | Size | Recorded purpose and evidence |
|---|---:|---|
| [0x7000000000, 0x8000000000) | 64 GiB | Current high-band policy/candidate arena, 448–512 GiB; not all free |
| [0x7c00000000, 0x8000000000) | 16 GiB | FEX-only native PROT_NONE reservation published at boot, Build 19 lines 324–325 |
| [0x7200000000, 0x73ffff0000) | 8 GiB minus 64 KiB | Native V8/cppgc holdback, line 225 |
| [0x7800000000, 0x7c00000000) | 16 GiB | First successful reported real fallback pool, line 11775 |
| [0x73ffff0000, 0x7800000000) | 16 GiB plus 64 KiB | Guard-prefixed reported real pool, line 11780 |
| [0x7400000000, 0x7800000000) | 16 GiB | Build 18 soft claim overlaps the preceding guard pool; Build 19 rejects it |
| [0x77ffff0000, 0x7c00000000) | 16 GiB plus 64 KiB | Build 18 soft claim overlaps the first pool and 64 KiB of the guard pool; Build 19 rejects it |

Names such as chrome_elf/libcef pool are hypotheses based on initialization
order, not module ownership carried by every grant record. The file_view query
in the strict experiment confirms actual overlap, but does not identify an
allocator instance or process owner. Both modules live inside one Mach task.

The two real payload pools occupy 32 GiB; four successful claims in Build 18
advertise 64 GiB plus 128 KiB while reusing those same two intervals. Combined
with the existing 16 GiB FEX arena and 8 GiB-minus-64 KiB holdback, disjoint full
claims would require at least **88 GiB plus 64 KiB**, before furniture, native
alias mappings, DLLs, stacks and other allocations. They cannot all be packed
inside the current 64 GiB high band. This is address reservation arithmetic;
it is not a physical RAM requirement or a global iPhone feasibility verdict.
Merely shrinking FEX cannot fit four full pools plus the unchanged cage here.

The current source furniture ceiling is 0x73ffff0000, even though earlier
comments describe a different ceiling; use the definition, not the comments.
Furniture/cage/JIT alias policies overlap this band and are not independently
free pools. Source's pressure valve can steer reserve-only allocations into pool
slots, and the separate 4 GiB soft-cage path deliberately nests inside the guard
pool. Build 19's guard covers neither all those paths nor future native mappings.
Do not claim the current allocator is globally collision-free.

## What remains unmeasured

Build 19 tried 16 GiB plain candidates 0x6800000000, 0x6c00000000,
0x7000000000, 0x7400000000, 0x7800000000 and 0x7c00000000; each eventually
returned STATUS_CONFLICTING_ADDRESSES. That result combines runtime allocation
policy and the current map; it is not proof that the lower candidates can never
be mapped by the kernel. Fixed 16 KiB native probes at 32–63 GiB returned Mach
kr=3, while 496 GiB was mappable. These sparse probes do not cover every hole
below 448 GiB. A 512 GiB TASK_VM_INFO ceiling is not 512 GiB of usable space.

`ios_bigres` reporting is also incomplete: the source's note hook at syscall
exit covers 256 MiB..1 GiB reserves and other hooks selectively count pools.
Its displayed zero committed MB cannot prove zero committed bytes. Commit
counts, owner, lifetime and kernel backing must be measured independently.

The existing Social Club layout 2 is NOT a ready-made Steam solution. It is
helper-name gated and describes 4 GiB backing for a 32 GiB advertised pool plus
8 GiB backing for 16 GiB metadata requests, alongside separate FEX/alias/cage
ranges. Reusing those reported tails without explicit ownership, boundary
checks and lifetime handling would reintroduce misleading grants. This audit
does not enable it or change the working game's layout.

## Next bounded experiment

The compiled x86-64 PE `tests/steam-ui/reservation-ownership.c` asks for at most
four reserve-only regions using the observed plain/guard sizes. It does not
load Steam, commit/access memory, free an alias, or retry indefinitely. It needs
`--isolated-reserve-only`, prints VirtualQuery metadata, and exits distinctly:
0 = reported grants disjoint; 40 = overlap; 41 = overflow; 64 = missing opt-in;
70 = capacity gate before all four grants. No status proves backing or CEF.
Use only in a fresh isolated Lab or an independent Windows control. End the
whole Lab process afterward: pseudo-process exit is not OS address-space exit.

The actual probe C logic passes disjoint/alias/capacity/overflow/refusal fixtures
under ASan/UBSan, and compiles to PE x86-64. Neither device nor Windows execution
is claimed. The host mock is not an operating-system control. The new explicit `madeira-reservation-diagnostics` Lab argument uses the
existing paired automatic JIT flow and fixed batch. It requires the isolated
bundle/feature flag and a fresh session, validates the selected x64 PE and
writes drive_c/madeira-reservation-results.txt. Build 20 is prepared locally;
no installation or execution is claimed.

After that contract test, obtain native Mach map/backing/capability evidence for
unprobed disjoint intervals using non-overwriting PROT_NONE requests, restoring
only mappings the test actually creates. A broker/layout patch requires evidence
of distinct ownership, reported-vs-backed boundaries, commit denial on foreign
ranges, release/process-lifetime semantics and full final Mach-O verification.
Keep strict rejection on; do not achieve startup by reintroducing soft aliases.


## Subsequent actual device validation (Builds 20/21)

The earlier 4016 gate is resolved. Build 20 directly confirms two MEM_RESERVE
intervals then a third-request failure (Win32 487, probe category/exit70).
Build 21's fresh pre-Wine/JIT-enabled native sweep confirms only the four high
16 GiB-aligned slots accept either 64 KiB or full 16 GiB mappings; all 27 lower
sampled boundaries fail kr3 and query existing native mappings. The native
probe's 8 successful requests and all queried object ports are released.
These are individually measured capacities, not simultaneous full CEF ownership.
Full results: STEAM_UI_NATIVE_VM_EVIDENCE.json / STEAM_UI_NATIVE_VM_SAMPLES.csv.
Do not identify the lower mappings' owner or reclaim them from these data.
Current full-pool/FEX/cage packing remains NO-GO; overall feasibility is open.
Next test must attribute request roles/contracts or a correct reduced-demand
model, not repeat the same address grid or silently alias independent owners.
