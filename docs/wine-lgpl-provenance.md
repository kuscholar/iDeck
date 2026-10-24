# Wine fork: LGPL branch provenance (DRAFT 2026-09-16, for review)

**Problem.** The fork on `wine` HEAD (branch used by the superproject)
applied LGPL-2.1 section 3 to convert the whole copy to GPL-3.0-or-later
(commit 0224441925d). That conversion is irreversible for that copy and
makes upstream Wine authors' code GPL-only there, so no exception for
Apple's proprietary converter can attach to it.

**Solution prepared.** Branch `madeira-lgpl` in the `wine` repository,
built as: upstream tag `wine-11.4` + the 51 Madeira commits below
cherry-picked in order with `-x` (skipping only the conversion commit) +
one commit adding LGPL `LICENSE-MADEIRA.md` and `CONTRIBUTING.md`.
All 51 applied without conflict. ADOPTED 2026-09-16: the wine submodule now points at `madeira-lgpl`
(a1e4a040484). A diff against the retired GPL branch differs only in
licence-notice lines (22629 lines swapped, equal counts, no code change).

**Authorship.** Every one of the 51 commits carries the author
`Will Faust <willtechnoduck@gmail.com>`. Git authorship is evidence of
origin, not proof of ownership. OWNERSHIP CONFIRMATION: pending an explicit
statement by the author that no patch below was adapted from third-party
code except as noted (requested 2026-09-16):
- `dlls/wineios.drv/coreaudio.c`, `coremidi.c`, `coreaudio.h`, `unixlib.h`
  derive from upstream Wine's `winecoreaudio.drv` (Copyright CodeWeavers,
  Huw Davies) and keep those notices. Their licence is upstream's LGPL.
- Notice-line touches outside the conversion commit: 8 lines across the
  series (headers copied when files were derived); none change a licence.

**Baseline:** wine-11.4 (upstream). **Commits (oldest first):**

- e544ca5eda5 2026-04-28 .gitignore: exclude in-tree build dirs (build-macos, build-arm64ec)
- 119bbbec067 2026-04-28 arm64ec_process_init: re-run update_hybrid_metadata after globals are set
- e81b8060e75 2026-04-28 ntdll/loader: apply arm64ec_redirect_ptr to imports at load time
- 3d1a183912d 2026-04-29 EC5c: arm64ec_process_init early-stash + iOS skip start.exe fallback
- 97a93087440 2026-04-29 loader: process_attach xtajit64 dependency tree before arm64ec_process_init
- b06e11567d5 2026-04-29 loader: redirect ARM64EC EntryPoint via arm64ec_redirect_ptr
- 49bcfb48173 2026-04-29 arm64ec: split process_init into dispatchers + ProcessInit; redirect ffwd thunks
- 07d3e009ded 2026-04-29 loader: trace load_arm64ec_module + arm64ec_process_init progression
- c6fc2f3915a 2026-04-29 env: skip start.exe fallback for AMD64 main on ARM64EC iOS
- 1da757ad07f 2026-04-30 arm64ec: re-patch all ARM64EC modules' hybrid metadata after dispatcher globals are set
- 89992f5f76f 2026-05-07 ARM64EC import binding: 3 iOS-port fixes
- f7412bdecfe 2026-05-08 ARM64EC iOS: translate redirect_ptr results to JIT-pool alias
- 5ec17759cdf 2026-05-08 ntdll: bounds-check RtlIsEcCode against non-canonical pointers
- e7048eee391 2026-05-08 ntdll: log thread-TLS allocation once for iOS bringup diagnostics
- 06e9dcc7822 2026-05-09 ntdll: pre-allocate main EXE TLS slot before load_arm64ec_module
- 519b098579e 2026-05-11 ntdll: add unix_ios_push_jit_aliases bridge for iOS FEX alias awareness
- d19b1d24a4a 2026-07-08 iOS build: catch-up commit — 2 months of accumulated fork work (S0 TLS → rpcss → task-21)
- 0c8f1426105 2026-07-08 iOS: WIP CoreAudio/CoreMIDI wineios.drv (experimental, not yet wired into build)
- 6c7286a6134 2026-07-09 Mythic: 🎮 FEX-2607 — EC-ntdll fixes: xtajit64 ctor-init + NLS casemap + is_ec_code per-thread peb
- d3e7c616517 2026-07-10 Mythic: ntdll ARM64EC — NULL-guard the KiUserExceptionDispatcher fast path
- c58cf755c11 2026-07-10 Mythic iOS: Steam S3 — kernelbase no-Win8-lie + arm64ec redirect Destination-RVA validation
- a2de48bbac5 2026-07-10 Mythic iOS: task #32 — stop_thread via Mach context capture (POSIX signal suspend is dead on iOS)
- 5004daea1fe 2026-07-11 iOS: EC exception dispatch across three stacks + [rtcs] guest-Rip conversion trace
- 71b042a5b63 2026-07-28 iOS: guard bulk non-exec protect notifications on all three paths
- 46a77d60990 2026-07-28 iOS: rpcrt4 diagnostics for the ccontext == 0x10 crash
- 82bee454550 2026-07-29 iOS: delay-load ARM64EC redirect; document why arm64x_check_call keeps the x18 read
- 7b20a40df07 2026-07-30 iOS: end-of-stack is not an invalid stack — make guest faults survivable
- ecb295e87c6 2026-07-31 ios: delay-load POOL-STALE closed — dual pool-side slot write + gated eager delay-import resolution
- 78aab076315 2026-07-31 ios: SEH unwind livelock breaker
- c154286bf61 2026-07-31 iOS-Mythic: wininet urlcache loop kills, [dll-missing] probe, user32 GetPointerDevice
- 1bebdf8aa96 2026-08-02 iOS: Crashpad-VEH context guard + EC exception hardening (ml418-ml432)
- 73fc9ef2e26 2026-08-04 iOS-Mythic: #79 TCP state numbering, NSI bypass, minidump gate, alert-probe TEB guard
- 712d8e6f191 2026-08-04 iOS-Mythic ml487/ml488 (#78): checksum the bytes NtReadFile hands back for steamui *.js
- 70d2028f1d7 2026-08-04 iOS-Mythic ml493 (#61, #79): glyph-rasterisation and connect-outcome probes
- e07db484d3a 2026-08-05 iOS-Mythic ml506-ml508: blit censuses — where Chromium's pixels do NOT come from
- f2fa8d3b883 2026-08-08 Mythic: free_async_queue UAF fix + wineserver fd-ownership/kill tracing
- 58b9db22108 2026-08-11 wine: ARM64EC SEH unwind fixes + JIT alias three-view probe
- a8ac939b45f 2026-08-12 wine: hand FEX the Mono backpatcher bridge
- 78497aaf273 2026-08-14 ntdll: critical-section and failed-open diagnostics for iOS
- a0ccfbe4651 2026-08-16 server: add ios_thread_wait_links() for wait-chain inspection
- 25b00c4700e 2026-08-16 ntdll/arm64ec: fix x64 setjmp/longjmp by unwinding a PE pc, not a JIT-pool pc
- 7f458f5b2e7 2026-08-16 loader: [tls-life] probe for TLS slot assignment and callback invocation
- ae1335b3d09 2026-08-17 ntdll: export ios_teb_tsd_offset so ARM64EC modules stop hardcoding a TSD slot
- 9dac3664912 2026-08-21 ntdll: register images at the loader boundary so child processes can execute x86-64
- 4cda511efe1 2026-08-21 Report thread context from the syscall frame, and stop capped probes hiding dependencies
- 022e61874dc 2026-08-22 Suspend threads for real instead of only snapshotting their registers
- daeb4ee6bb6 2026-08-25 Add opt-in native-call tracing for a video decoder and its stream
- fa8655ead45 2026-08-25 Extend native-call tracing to the audio backend and report what the hook sees
- ca6f153cf9e 2026-08-25 Rename the project from Mythic to Madeira
- 7817e220384 2026-08-28 Print the arena band selector's deferred log from dispatcher init
- abf22e09603 2026-09-16 ntdll ARM64EC: root-frame unwinding, TLS window, arena hand-over and loader traces

## After adoption

Later changes are committed on `madeira-lgpl` directly. Third-party
contributions keep their authors' copyright under LGPL-2.1-or-later and are
signed off under the DCO (the fork's `CONTRIBUTING.md`):

- feb96ad2be4 2026-09-25 xinput: read Madeira host controller snapshots
  through win32u. Author: 125hz. willfaust/wine pull request #1, merged as
  815cf1f92e2.
- 2026-09-29 the iOS WoW64 series, author 125hz, willfaust/wine pull
  requests #6-#12, merged as cea4dfc9a14: 970dac54a4e, 2ebe9374b26,
  db62a711998, e9289051644, 1a73c698b8c, f9074408fd9, 059cb1923c0.
- 2026-09-29 dinput: opt-in joystick backed by the Madeira host gamepad slot
  (56f69bc7528, pull request #3) and server iOS: queue a process-wide system
  APC on a live thread (3ba35adcbdd, pull request #13). Author: 125hz.
- 2026-09-30 round 3, author 125hz: nsi reads through the in-process
  fallback without `\\.\Nsi` (4e85de8c795, 8d4c3d9ab5b, 5c4d1f7a6f2, pull
  request #14, merged as 368f16891ea); server iOS: hand an undeliverable
  async I/O APC to a waiting thread (c3119789ade, pull request #15, merged as
  18322fc5617; narrowed by our 074e0e368b6 so it is dropped, never parked,
  when no thread is waiting); opt-in fastsync for events and semaphores
  (e200a5e19a9, f6848ad4e98, pull request #16, merged as e33e56e4db8); ntdll
  ARM64EC: opt-in guard against a self-deadlock in the loader's image-map
  notification (d770df01ae7, pull request #17, merged as f7df74abb76).
- 2026-10-04 author spitefulowl: ntdll ARM64EC: leave the syscall callback on
  the execute-request early return (38aa753f98b, pull request #22, merged as
  bcb9938b136); kernelbase iOS: GetTickCount and QueryInterruptTime from the
  performance counter (f2f3e4b42e4, pull request #23, merged as 84b25d3847c);
  ntdll ARM64EC: unwind data for x64 code running at a fixed base below 4 GB
  (f4bbccf9499, pull request #24, merged as 0bfd4a09b47).
- 2026-10-05 author meshoklv: ntdll: load the builtin XInput even when the
  game ships its own copy (30efeaa807b, pull request #19, merged as
  4dbaf6bd7d6). Pull request #18 (b7996f867cb) is the same fix as pull
  request #22 and was submitted first; recorded as merged (cdd29c7dee3) with
  no change of its own, since #22's identical line was already in.
- 2026-10-06 author bahacan16: xinput1_3 iOS: send XInputSetState motors to the
  host pad (67b8c8bed51, pull request #20, squashed; recorded as merged by
  4d30258eb82).
- 2026-10-06 author spitefulowl: mscoree iOS: cooperative thread suspend and
  keep-delegates for Wine Mono (000cac48452, pull request #26, merged as
  2790f7c2a5d); Madeira's follow-up bfa3a472397 builds it for i386 only and
  puts the variables back once Mono has read them.
