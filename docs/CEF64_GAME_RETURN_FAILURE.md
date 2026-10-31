# CEF64 game return: separate failures, measured experiments

Experimental source: `experiment/steam64-cef64`. Runtime base be8151a plus local
changes; evidence-only source HEAD8c4794d at the start of this run. Do not merge
this research into the working app. Detailed numeric records and private artifact
hashes: [CEF64_V8_TABLE_CAPACITY_EVIDENCE.json](CEF64_V8_TABLE_CAPACITY_EVIDENCE.json).
All times below are 2026-10-31 America/New_York unless explicitly UTC.

## What is actually observed

- Build127/eight tables: Hot Roads08:54:57..08:55:25 exit0; V8 table OOM08:55:32.
- Build128/nine tables: game09:11:43..09:12:09 exit0; V8 table OOM09:12:15.
- Build129/twelve tables: first game09:24:51..09:25:13 exit0. The user confirms
  continued Steam/Library browsing. Second launch09:31:35 exhausts the smaller
  FEX arena and faults in the native decoder; exact task termination is verified.
- Private130 decoder allocation experiment: effective256 entries request32KiB
  instead of a fixed65536-entry/8MiB buffer. First game exits0; second game
  exits0xd0594a27. CallRet8MiB+guards and general FEX allocation still fail.
  Native continues logging afterward; its later absence does not establish
  its termination cause. This is not long-term success.
- Private131 allocator geometry4MiB experiment: actual Steam/game first exit0;
  second game exitsc0000135, UnityPlayer.dll load reportsc000007b. Native sample
  has no matched FEX malloc/thread-init failure. CEF then requests a thirteenth
  table after all twelve are claimed, and fails. Stable browsing remains unproven.

A runtime notice for a failed x86launcher guest-window reservation is separate:
the guarded4GiB WoW64 window cannot be obtained, but the64bit game can still run.
Do not lower that guard or present this notice alone as proof the game failed.

## Bounded findings

V8 reports `ExternalEntityTable::InitializeTable (subspace allocation)` when
its table address subspace cannot be obtained; see the pinned
[V8 12.6.228 implementation](https://github.com/v8/v8/blob/12.6.228/src/sandbox/external-entity-table-inl.h).
Our actual native logs independently show exact512MiB table claims and the next
request being refused. Observed placeholder frees leave Wine views alive; they
are not proof that a lease can be reused. Merely adding a finite table postpones
this limit and also removes capacity from FEX. It is not a scalable lifetime fix.

FEX has a separate contiguous-address demand. The actual129 fault resolves to
the exact private DLL decoder atRVA21558, writing through NULL after an8MiB
buffer allocation fails. Reducing its default request preserves the original
instruction ceiling and explicit larger requests through the existing resize
API. Private130 device logs confirm the new32KiB request. General allocator8MiB
spans and unchanged guarded8MiB CallRet reservations can still exhaust/fragment
the7GiB arena. A large free total does not imply a sufficiently large aligned hole.

Do not infer every large view belongs to one allocator, a leak, a caller, or
committed physical memory from size alone. No matched diagnostic is not PASS.
Likewise, WM_NULL responsiveness and foreground focus are insufficient to claim
interactive Steam navigation; keep the user result or visual artifact separate.

## Current isolated validation

The user explicitly authorized local FEX allocation experiments. Private modified
FEX source/DLLs remain outside Git with no remotes. Original FEX/Wine submodules,
mainline app, accounts, games and saves remain intact. No assertion suppression,
Valve binary patch, overlapping grant or protection retry is used.

Local129 native geometry/ownership/fixed-hint aliases/all-slot create rollback,
concurrency and all20 game-image exclusions pass ASan/UBSan; all37 native units
and full Xcode link pass. Actual device20holds/40backing edges/20cleanup and
12-table own Windows contract pass. The private decoder pre-write checks and
actual POSIX allocator4MiB tests pass ASan/UBSan. These are scoped tests: they do
not establish Windows allocator semantics, complete decoder correctness, UI or
repeated gameplay. The own16worker AMD64 arithmetic program on130/131 exits0
and matches an independent Python64 oracle; actual policy markers are recorded.

Build132 adds a double-gated, bounded numeric-only section create/query trace to
discriminate the second-loadc000007b without guessing file corruption. It calls
the existing operation once and preserves its result, with no extra request or
file read. An own AMD64 lifetime PE maps the installed UnityPlayer and CEF DLLs
with `DONT_RESOLVE_DLL_REFERENCES` in three sequential children; it does not run
DllMain/imports/game/Steam authentication. Compilation is not its device result.

## Next discriminators and assessment

1. Capture actual create/query status and reported architecture for the failed
   second DLL load, and run the isolated lifetime PE. Patch only a demonstrated
   contract violation, preserving ordinary paths.
2. Address retained CEF subspace ownership/peak demand separately from FEX
   allocator capacity. Never recycle a live or preserved placeholder.
3. Re-run at least two game/return/navigation cycles in the same native lifetime,
   then account persistence, normal app-open behavior and controller regressions.

**NO-GO for claiming a stable full64 release.** Genuine64bit Steam/CEF and real
game execution are observed, including one user-confirmed interactive return;
repeated game/return remains incomplete. This is an evidence limit, not a claim
that the objective is technically impossible.
