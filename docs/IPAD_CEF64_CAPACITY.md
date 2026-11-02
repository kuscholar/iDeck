# Physical iPad Air4: full64 capacity gate

2026-10-31, experimental checkout `experiment/steam64-cef64`.
Source HEAD cb3b835 plus local experimental code; the added HEAD commit changes
only the user's README text. Runtime base and private FEX/helper provenance stay
separate from this source label. No mainline merge or release is implied.

## Actual device and installation

User selected the connected physical iPad. Verified device: iPad Air4/A14,
product iPad13,1, iPadOS27.2. This is not the unavailable older iPad Pro or a
simulator. Normal GUI Xcode automatic signing, with this exact iPad selected,
generated compatible SteamUI main/helper profiles. Their exact device/team/
certificate/expiry/debug-permission checks pass; main profile includes Memory+,
and does not include Extended Virtual Addressing. No account re-login, private
entitlement or forged grant is used.

Full Build133 was first installed in `com.kuschqin.madeira.steamui`; full134
subsequently upgraded only that completed diagnostic app. Real installed version
readback, linked marker/hash checks and deep-strict signing pass. Existing
MacAllocator22 app/data are preserved. No iPhone credentials, login cache,
games or saves are transferred. Steam, Wine guest code and JIT were not launched
by these native capability probes.

## Observed failure and discriminator

The20region iPhone geometry requests about59.5GiB of simultaneous disjoint native
reservations. Actual133 on Air4 grants slot0 at7100000000+1GiB, then rejects
slot1 at717fff0000+40010000 with Mach `KERN_INVALID_ADDRESS` (1). The only own
successful mapping is released, cleanup0. No backing-edge test is reached.
This is not an observed physical-memory OOM or a Steam authentication failure.

Existing broad native inventory: the64..448GiB interval is a protected native
region with maximum protection0; no overwrite is attempted. In the high band,
a64KiB map at7000000000 succeeds;16GiB there and mappings at7400000000 and above
return invalid-address. This alone was insufficient to quantify the smaller band.

Build134 adds a double-gated, standalone bounds sampler. It performs32fixed
64KiB point samples at256MiB intervals and32prefix reservations of256MiB..8GiB,
with no overwrite, executable permission or memory access. Every successful
mapping is immediately released. Failures are reported separately by Mach code;
a collision is not treated as a kernel ceiling. A logging/cleanup/unexpected
address failure stops the routine. No normal runtime allocation is changed.

Actual134 sampling completes all64calls:48successes, all own cleanups0.

| Observation | Actual result |
| --- | --- |
| Continuous prefix from7000000000, size6GiB | success |
| Same prefix, size6.25GiB | KERN_INVALID_ADDRESS |
|64KiB at7180000000 (6GiB above base) | KERN_INVALID_ADDRESS |
| Higher tested points through71f0000000 | KERN_INVALID_ADDRESS |

These reserve-only results establish the measured high-band restriction under
the current Memory+-only signed launch. They are not full-range backing, total
system RAM, a guarantee about every other address, or Steam runtime validation.
The sampler footer0 means the measurement and cleanup completed; the full64
layout qualification still **fails**.

## Validation and remaining hypothesis

Production sampler host ASan/UBSan checks pass: constrained6GiB fixture,
collision distinction, exact ownership cleanup, unexpected returned address and
cleanup-failure stop. Original VM-backing observer and launcher checks pass;
the launcher check was rerun with normal Swift cache permission after a sandbox
cache-write denial. All37native units, full Xcode134, final Mach-O markers,
unchanged private FEX131/helper126 hashes, signing and actual install pass.

A bounded standard LLDB device-attach discriminator did not obtain an attached
target (`Process must be launched`). The pending sentinel was still present
before attempted attachment, and the exact fresh stopped task was ended in
cleanup. There is **no** debugger/JIT-enabled capacity result from that attempt.
Do not conclude that debugger attachment does or does not expand this limit.

Apple documents [Extended Virtual Addressing](https://developer.apple.com/documentation/bundleresources/entitlements/com.apple.developer.kernel.extended-virtual-addressing)
as a separate capability for a larger addressable space. The ordinary Xcode GUI capability request was subsequently executed. Xcode
refused Extended Virtual Addressing for the current Personal Team. The actual
activity-log SHA-256 is recorded in the evidence JSON. This is an entitlement
request refusal, not proof that the Apple ID is signed out. Memory+ is not EVA.

No granted EVA profile or JIT-enabled capacity pass was obtained for this iPad.
Keep the measured NO-GO for the unchanged layout/profile; do not add an ungranted
entitlement or restart Steam against that known-invalid reservation. No paid
account benefit or full64 iPad success is established. Subsequent iPhone135
results are separate and do not validate this iPad.

Redacted evidence and private artifact hashes:
[IPAD_CEF64_CAPACITY_EVIDENCE.json](IPAD_CEF64_CAPACITY_EVIDENCE.json).
