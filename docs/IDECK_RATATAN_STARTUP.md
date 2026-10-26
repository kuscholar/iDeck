# Ratatan startup investigation

2026-10-26. Baseline source: `4ad061b`; installed failing baseline Build 59.
The user confirms Ratatan downloads and installs after the AMD64 capability
repair. That does not establish game startup or gameplay.

## Observed failure

Steam tracks app 2949320's `game.exe` at 08:15:48. Unity 6000.0.72f1 creates a
D3D11 device using the Apple A17 Pro GPU, then its Player.log stops. The
runtime creates Job.Worker 0..4 and Background Job.Worker 0..15. Later the
emulator's fixed address band cannot allocate a thread state:

- `[va-scan] FAILED window=0x7c00000000..0x8000000000 size=0x1000000`;
- `THREADSTATE ALLOC FAILED: 12288 bytes, 4096 alignment` for thread 03c8;
- `ThreadInit: thread state unavailable ... STATUS_NO_MEMORY`;
- a later call-return allocation also fails;
- game main thread 0318 waits indefinitely on an unsignaled event.

This is evidence of failed thread initialization, not proof that every wait or
all graphical initialization failures share that cause. Pool shrinkage and
`mprotect` messages alone do not establish the causal failure.

## One-hypothesis test, Build 61

Hypothesis: reducing Unity worker creation leaves enough emulator address space
for the remaining startup threads and removes this startup wait.

An explicit isolated-app argument `madeira-ratatan-thread-experiment` uses the
existing paired JIT flow and genuine Steam with:

```
-applaunch 2949320 -job-worker-count 2 -background-job-worker-count 2
```

No authentication or game binary is modified. Ordinary launches have no
`-applaunch` addition. Account-switch sessions and the x64-client path reject
this test. No FEX changes are made. The actual game's UnityPlayer.dll contains
both parameter names; Unity documents `-job-worker-count` at
<https://docs.unity3d.com/kr/current/ScriptReference/Unity.Jobs.LowLevel.Unsafe.JobsUtility.JobWorkerMaximumCount.html>.
The background parameter's actual effect still requires thread/log evidence.

Accept only new device evidence: exact child arguments, worker counts, no
corresponding allocation failure, Player.log advancing, and visible game UI.
Successful compilation or backend login does not establish success.

## Private evidence (not committed)

Paths relative to `FunProjects/.madeira-install/`:

| Artifact | SHA-256 |
| --- | --- |
| ratatan-live.txt | de65a3ecc9a2df04fe5926bc94e33b81bd7cc37b8f6882f47722694e62c8257b |
| ratatan-player.txt | dc7b99470f83976ecf561e2fe588acdd683480cd6de282fd173e6ec839a1ee78 |
| ratatan-UnityPlayer.dll | 1d546b1e762097fe15648497fcaef05f3d0785c5812c9e4d3f684711fd4dd909 |

Host launch-policy and iDeck lifecycle checks pass. Full Xcode Build 61 passes;
final linked debug dylib contains the exact test argument and fixed Steam
launch flags. Deep strict signature verification and in-place installation
succeed. Device test results are pending; Mac UI observation is locked.

## Build 61 result: worker reduction alone is insufficient

Actual child startup is tracked in the new 08:24 session. The native snapshot
confirms Job.Worker 0..1 and Background Job.Worker 0..1. The parameter reaches
the game and reduces worker creation, but later threads 0388/038c/0390 still
fail their 0x802000 call-return reservations. Do not call the worker cap a fix.

The same trace shows the existing generic reserve-pressure valve steering
512 MiB-minus-page guest allocations into FEX's [0x7c,0x80) host band first.
Only after that becomes full does it use its existing [0x74,0x78) fallback.
This unnecessarily shares the limited host-thread region while the alternate
Wine-checked region is usable.

## Build 62: change existing checked spill order

Next hypothesis: preserve the FEX host band by trying the *existing* guest
fallback window before the host-band window. No address range is added and
no reserve result is fabricated. Both attempts call the same checked
`allocate_virtual_memory` implementation. Existing dead-owner reclamation and
one retry remain. The ordinary runtime keeps the old order; the change requires
`MADEIRA_STEAM_UI_SESSION=1`. Set
`env.MADEIRA_STEAM_UI_GUEST_SPILL_FIRST=0` for an exact order opt-out.

The production helper's ASan/UBSan fixture validates ordinary/opt-out isolation,
first-window occupancy, fallback occupancy, honest failure, and restoring the
original address/size before a second attempt. All 37 native translation units,
full Xcode Build 62, pool-split and pool-low regression checks pass. Final
Mach-O marker and actual device effects must still be verified.

Build 62 installed in place; final linked debug dylib contains the new policy
marker. Steam saved login succeeds at 08:28:32. At 08:28:34 Steam's own
GameAction stops at `ShowInterstitials`, explicitly waiting for a user response;
this session has **not yet spawned Ratatan**. Therefore the pre-existing
Player.log copied during this interval is not accepted as Build 62 evidence.
The unknown prompt may not be bypassed; UI verification awaits the user because
Device Hub reports the Mac locked. The running session was resumed after each
bounded serial snapshot. No success claim is made for the spill-order patch.

A pre-existing host thread-create diagnostic test selected the new public
logging wrapper rather than the original implementation. Its extraction target
is corrected; the production thread implementation remains unchanged.

| Additional private artifact | SHA-256 |
| --- | --- |
| ratatan-stable61.txt | f85cc8d02ff4476f55ee183725d32bca2bdb41b0163ccb4543bc822c2c800525 |
| ratatan-stable62b.txt | 8ea34fefba32500e34b59d7f648480d4a3332a4511a5ced9486a91e77850fefe |
| ratatan-build62.log | 16ade040d2db66baab9e351ada361d709315c20130a374a4d48ceb7bce82ac1f |
| ratatan-gameprocess62.txt | 8a151b7561f3d8a4142e805d506a17d0d65a23c460fea2086646cbc1efdd0e12 |
