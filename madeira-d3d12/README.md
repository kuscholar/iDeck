# madeira-d3d12

Native D3D12 to Metal for Madeira, built on Apple's Metal Shader Converter.
Working name chosen to keep this distinct from Apple's D3DMetal, none of whose
implementation code is used here.

Execution design: `MADEIRA_NATIVE_D3D12_EXECUTION_DESIGN.md` (Codex, 2026-09-08).

## Status

| Milestone | State |
| --- | --- |
| M0 inventory and reversible integration plan | done, below |
| M1 converter and binding canary, macOS host | **passing, 26/26** |
| M1 native iOS on the vphone VM | **passing, 26/26** |
| M1 in-app iOS, under Madeira's own signing | **passing** |
| M1 physical iPhone (A15) | **passing, 27/27 on Apple A15 GPU** |
| M1 cross-target: iOS-hosted converter to macOS device | **passing** |
| M1 full remote render through rmetald with pixels in the guest | **passing**, closed by the offscreen triangle and the on-screen cube |
| M2 native D3D12 ABI and synchronization | **passing, 41/41 on vphone and on the A15** |
| M3a GPU buffer copy + readback | **passing, 54/54 local A15 and remote vphone** |
| M3 offscreen rendering | **passing, 77/77 on vphone and on the A15** -- triangle and depth-tested cube, pixels read back in the guest |
| M4 spinning cube and presentation | **passing on both devices (ml835)** -- tumbling cube on screen, runs until the window closes |
| Runtime DXIL conversion (fixture mode removed) | **passing, 90/90 on vphone and on the A15 (ml839)** |
| M5 textures, SRV/sampler descriptors, descriptor tables | **passing, 90/90 on both (ml839)** |
| M5 visible textured cube on screen | **passing on both (ml840)**, user-confirmed: bands stay local to each face |

Everything through M4 is built into the app and deployed to both devices. The
three PE artifacts live in `app/Madeira/arm64ec-windows/` and are reached from
the two launch buttons in `ContentView.swift`; nothing else outside this
directory and `build/madeira-d3d12/` changed, so the working D3D11 setup is
untouched. Nothing is committed or pushed.

**Fixture mode is gone.** The runtime no longer embeds any converted shader:
`MTLB` does not appear in `madeira_d3d12.dll` except inside an import name, and
the DLL shrank from 222,720 to 186,368 bytes when the four preconverted
libraries came out. Application DXIL is converted on the machine running the
guest, at pipeline creation, against the root signature the application actually
created.

The conversion request crosses the PE/unix boundary once per shader as winemetal
call 127, appended to the dispatch table rather than inserted, since the slot
number is the ABI. It is deliberately not remote-guarded: conversion is a byte
transform that dereferences no Metal handle, so it runs on the guest in both
backends. What follows the rendering backend is the TARGET, resolved once from
the device that will run the shaders (`MTLDevice_name` and `supportsFamily` are
both routed to the host in remote mode) instead of compiling for both platforms
and keeping whichever library loaded.

Root signatures are parsed from the real serialized container, a DXBC wrapper
around an RTS0 chunk. The layout was read from a working implementation rather
than recalled, and the serializer's output was checked against a blob produced
by Microsoft's own compiler: byte-identical apart from the digest, which is
deliberately left zero.

## What M1 proves

Run it with:

```sh
bash build/madeira-d3d12/build-canary.sh
./build/madeira-d3d12/out/msc_canary
```

The canary takes DXIL through the converter to a Metal pipeline and checks the
pixels that come back:

- The converter loads and its API matches the pinned package headers.
- An **explicitly constructed** root signature drives the argument-buffer
  layout. The canary builds `IRVersionedRootSignatureDescriptor` itself rather
  than leaning on the `RTS0` blob the shader compiler embedded, because a real
  runtime receives the root signature from the application.
- The emitted metallib loads on the device and builds a render pipeline.
- Two constant-buffer states produce two exactly predicted images. A wrong
  argument-buffer offset or bind point gives a wrong colour, not a plausible
  one.
- Recompiling identical inputs yields byte-identical output. That is neither
  necessary nor sufficient for cache safety: a compiler may emit equivalent
  binaries with differing metadata. What matters is identifying every relevant
  input and reusing only a valid artifact.
- **Argument-buffer layout with a real two-parameter root signature.** Four
  32-bit root constants at bytes 0..15 and a root CBV address at byte 16, with
  red and green sourced from the constants and blue from the CBV, so a mistake
  on either side changes the pixel. Verified, not assumed.
- **Cache-key differentiation.** Changing the minimum deployment target changes
  the output. Changing the root signature changes or rejects the compile.
- Invalid DXIL, a truncated blob and an unknown entry point all fail with
  bounded, named errors.

### Findings worth carrying into the runtime

**The converter does not validate entry-point names.** Measured: compiling with
`NoSuchEntryPoint` succeeds and links, and the only signal is that reflection
returns an **empty** entry-point function name. Left unchecked the failure
surfaces much later as a missing `MTLFunction`. The runtime has to impose this
bound itself; the canary does.

**The runtime companion header is single-TU.** Its `kIR*` bind points and helper
bodies are emitted only where `IR_PRIVATE_IMPLEMENTATION` is defined, and the
dylib exports none of them. Without that define they link as undefined symbols.
It also requires ARC in Objective-C mode, and it is written for C++, so the
canary is Objective-C++.

**Binding ABI, read from the package rather than assumed:** top-level argument
buffer at index 2, descriptor heap 0, sampler heap 1, vertex buffers from 6,
stage-in attributes from 11. With this root signature the single root CBV is a
64-bit GPU address at offset 0 of the argument buffer, and the buffer it points
at needs an explicit `useResource` because Metal cannot infer residency through
an argument buffer.

**Minimum GPU family did not change this shader's output.** Apple9 and Metal3
produced byte-identical libraries. That is a fact about a trivial shader, not a
reason to drop the family from the cache key: a shader using family-gated
features would diverge, and serving it an entry built for a different minimum
family would be wrong. The key is decided by what the compiler is *allowed* to
vary on, not by what it happened to vary on once.

**The binding offsets here are not a general layout specification.** Offset 0
for a lone root CBV, and 0/16 for constants-then-CBV, are what this package's
documented rule produces for these two signatures. Descriptor tables, multiple
spaces and larger constant blocks must each be derived from the documented ABI
and the package's own named constants and helpers.

**Measured on an M4 Max:** first conversion 1.0 ms, cached recompile 0.4 ms,
process footprint about 250 MB with the converter resident.

## iOS results

The same canary, built `arm64-apple-ios15.0` and run natively on the jailbroken
vphone VM over SSH, **passes all 26 checks**. Running it as a plain binary first
keeps three questions apart: whether the converter works on iOS, whether it
bundles and signs inside Madeira, and whether Madeira's startup path can drive
it. Those deserve separate failures.

```sh
bash build/madeira-d3d12/build-canary-ios.sh
# codesign -f -s - the binary, push it with the dylib and the .dxil fixtures,
# then run it from that directory on the device.
```

| | macOS M4 Max | iOS, vphone VM |
| --- | --- | --- |
| Result | 26/26 | 26/26 |
| Target | macOS 15.0 | iOS 17.0 |
| Device | Apple M4 Max | Apple Paravirtual device GPU |
| Argument buffers | tier 2 | tier 2 |
| First conversion | 0.9 ms | 2.2 ms |
| Cached recompile | 0.4 ms | 0.3 ms |

Two findings from the device run:

**The paravirtual GPU is not the obstacle it was assumed to be.** It reports
argument buffers tier 2, loads a converted library, builds a pipeline and
returns exactly the right pixels for both the single-CBV and the
constants-plus-CBV layouts. Remote Metal remains the intended backend for real
work, but the VM's own device is sufficient for converter and binding tests.

**Minimum GPU family changed the output on iOS where it had not on macOS.**
Apple9 versus Metal3 produced identical bytes on the Mac and *different* bytes on
the device, for the same shader. Keeping the family in the cache key on
principle rather than on the macOS observation turned out to be load-bearing one
platform later.

⚠️ **Not established by this run:** the binary is ad-hoc signed and run outside
Madeira, so it says nothing about bundling or about Madeira's signing
arrangement. It is one GPU on one virtual device; the physical A15 is untested.
An unsigned push is killed by AMFI, which is worth remembering when iterating.

## In-app result (gate 1)

The same canary, compiled into `libdxmt` and driven from Madeira's own startup
behind `Documents/madeira-d3d12.txt`:

```
[02:31:53.568] [INFO] madeira-d3d12: running the M1 canary in-app (dylib present: true)
[02:31:53.744] [OK]   madeira-d3d12: M1 canary PASSED in-app
```

27/27 with the full per-check transcript now written to
`Documents/madeira-d3d12-canary.log`, with the converter `dlopen`ed from the app bundle
under the app's own sandbox and signature. Every entry point is resolved through
`dlsym`, so a missing dylib or symbol is reported rather than aborting in dyld.
The bundled dylib is signed with the app's team by a build phase, because a loose
dylib copied as a resource is sealed by the bundle signature but never re-signed,
and dyld will not load code whose own signature does not match.

⚠️ The canary's 27 individual check lines go to stderr, which Madeira only
captures once the Wine log is wired up later in startup, so the log carries the
verdict but not the detail. Moving the call after that point would capture both.

🔑 **A gate that logs only on success is indistinguishable from one that never
ran.** The first attempt produced no output at all and cost a device run to
resolve; it turned out simply not to be the new build. The gate now reports its
decision either way, including the value it actually read.

## Physical hardware (A15)

The in-app canary on an iPhone 13 Pro, **27/27**:

```
ok  Metal device: Apple A15 GPU
    argument buffers tier 2
ok  state A read back as (255,0,0,255), expected (255,0,0,255)
ok  constants at 0 and CBV at 16 read back as (200,100,255,255), expected (200,100,255,255)
```

The A15 reports argument buffers tier 2, which converted libraries require, and
returns exactly the right pixels for both the single-CBV and the
constants-plus-CBV layouts. Conversion cost 16.8 ms first and 0.6 ms cached,
against 15.2 ms and 0.3 ms in-app on the VM, so the converter is not meaningfully
slower on real hardware. Process footprint grew 4.9 MB against 1.5 MB on the VM.

⚠️ This is the local Metal backend on hardware. It says nothing about the remote
path, which remains the open M1 gate.

## Cross-target result (gate 2, compiler-location half)

The design allows falling back to a macOS-hosted converter if the device cannot
produce libraries the remote Mac accepts. **It can, so the fallback is not
needed.**

On the device, targeting macOS 15.0, then loaded on the M4 Max:

```
ok  cross_vs.metallib loaded, functions: MainVS
ok  cross_ps.metallib loaded, functions: MainPS
ok  pipeline from the iOS-hosted, macOS-targeted libraries
```

And the output does not depend on which machine ran the compiler:

| | iOS-hosted | macOS-hosted |
| --- | --- | --- |
| vertex | `bf977bad7b2a9d58` | `bf977bad7b2a9d58` |
| fragment | `65a76c9b9c0066f8` | `65a76c9b9c0066f8` |

Byte-identical for the same target. That is **not** a proof of cross-platform
compiler equivalence: it is two trivial shaders on one converter build. The
policy is therefore the conservative one. **Namespace the shader cache by the
converter build and the compile platform**, or carry compile-location provenance
and require an explicit compatibility policy before sharing entries across
locations. Cache portability buys nothing for the cube milestone, so paying for
it with a correctness risk would be a bad trade. The GPU-family result is the
cautionary precedent: identical on macOS, different on iOS, same shader.

⚠️ This is the compiler-location half only. Rendering through rmetald with
pixels verified back in the guest is still untested.

## M2: native D3D12 ABI

A **separate** `madeira_d3d12.dll`, not a replacement for the bundled
`d3d12.dll`. The design says not to overwrite the shipped loader as the first
experiment, and keeping it separate means the working D3D11 path cannot regress
while this is unfinished.

```sh
bash build/madeira-d3d12/build-pe.sh     # -> out-pe/madeira_d3d12.dll + m2_abi.exe
```

| Artifact | Architecture | Verified |
| --- | --- | --- |
| `madeira_d3d12.dll` | `IMAGE_FILE_MACHINE_ARM64EC` (0xA641) | exports `MadeiraD3D12CreateDevice`, `MadeiraD3D12GetBuildMarker` |
| `m2_abi.exe` | x86-64, runs under FEX | 25 checks |

**Vtables are generated, not hand-written.** `src/pe/gen_vtables.py` parses the
real `d3d12.h` and emits a typed stub for all 158 slots across the six
interfaces, so an unimplemented method returns `E_NOTIMPL` and names itself
rather than jumping through a NULL slot. Implemented methods are assigned over
the stubs at construction, which makes the supported surface exactly the list of
assignments in `build_vtables()` instead of something implied by which slots
happen to be non-NULL. The build regenerates the header, so a toolchain update
cannot silently leave a vtable the wrong length.

Implemented: device create/QI/refcount plus queue, allocator, list and fence
creation; queue execute and signal; allocator reset; list close and reset;
fence completed-value, signal and event-on-completion.

What `m2_abi.exe` checks beyond the happy path: reference identity through
`QueryInterface`, a refused interface, refcount round-trips, a refused feature
level, the null-out-pointer support probe, double `Close`, allocator reset while
a list is still recording, waiting on an already-reached fence value, and five
record/close/execute/signal cycles followed by an ordered teardown to zero.

### Result: 41/41 on the vphone VM and on a physical iPhone 13 Pro

```
implementation: madeira-d3d12 M2 Sep 10 2026 18:10:14 [arm64ec]
...
32 checks, 0 failures
```

**The x86-64 guest reached ARM64EC code**, reported by the module's own build
marker rather than assumed from the loader having not complained. Every object
released to a zero refcount in order and the process exited 0.

Three contract corrections came out of review of the first passing run, which is
the value of having someone check a green result:

- **The test was executing an invalidated command list.** It reset the allocator
  after closing and then submitted that same list. Real D3D12 rejects that, and
  the implementation accepted it because it tracked only whether a list was
  closed, not which allocator storage it recorded against. Allocators now carry a
  generation that `Reset` bumps, lists record the generation they were built
  against, and `ExecuteCommandLists` refuses a mismatch.
- **A null event must block, not be refused.** `SetEventOnCompletion` with a null
  event returned `E_INVALIDARG`; the contract is to wait until the value is
  reached. It now waits on a condition variable over the fence's own lock, which
  releases the lock while sleeping so the signalling thread can get in. Holding
  it would have made the wait a deadlock.
- ⛔ **An earlier claim here was wrong.** The exceptions in the log are
  `0x40010006`, `DBG_PRINTEXCEPTION_C`, raised by this module's own
  `OutputDebugStringA`. The refusals return HRESULTs and throw nothing. The trace
  shows diagnostic prints crossing the boundary, not D3D12 failures unwinding.

🔑 **A timing assertion that a coarse clock can satisfy is not an assertion.**
The blocking-wait test first measured elapsed time: the A15 reported 157 ms
against a 150 ms delay, but the vphone reported 0 ms, which is equally consistent
with "the clock is coarse" and with "the signal landed first and the call never
blocked". The test now orders the threads with an event and asserts on the fence
value observed immediately before and after the call, which no clock resolution
can fake. Rerun:

| | before the call | after | elapsed |
| --- | --- | --- | --- |
| A15 | 1 | 42 | 160 ms |
| vphone | 1 | 42 | 0 ms |

Both provably blocked. The vphone's zero is now identified as what it always
was, a coarse `GetTickCount` on the VM, and it no longer decides the verdict.

One more behaviour worth noting. The refusals surface as real Windows
exceptions and unwind correctly through the EC/native boundary, visible in the
log as `[seh-xlate] EC/native TRANSLATED`, so `E_NOTIMPL` and `E_NOINTERFACE`
are travelling the actual SEH path rather than a shortcut. And the in-app canary
conversion took 15.2 ms against 2.2 ms standalone, which is first-touch cost on
the 30 MB converter rather than a slower device.

⚠️ **No Metal behind any of this.**
M2 is about the COM ABI, object lifetime and synchronisation being right on
their own, because mixing GPU work in would make a failure ambiguous. The buffer-copy and readback test is next and
gives the fence something real to synchronise, and that same path then carries
the converted-shader render that closes the outstanding M1 remote gate.

## M3a: real GPU copy and readback

The D3D12 layer drives Metal through the **existing winemetal bridge** that
`d3d11.dll` already uses, so it inherits the working local/remote split instead
of growing a second transport. `CreateCommittedResource` (buffers, all three
heaps), `Map`/`Unmap`, `CopyBufferRegion`, and an `ExecuteCommandLists` that
builds a real command buffer and encodes the copies through a blit encoder.

**The fence is backed by GPU completion, not submission.** Queue `Signal` waits
for the command buffers submitted before it to finish, then advances. Signalling
at submission would make the fence a counter, and a readback taken after the
waiter woke could legitimately contain nothing. This is the conservative
blocking form the design permits.

The test runs upload to default to readback with **every hop at a different
offset** (256, 512, 128) and a non-monotonic pattern, so a shifted or truncated
copy cannot look right. The readback buffer is pre-filled with a sentinel and
the regions outside the copy are checked, because writing too much is as wrong
as writing too little. Mapping the GPU-private buffer is refused.

54/54 on both backends, clean teardown, exit 0. The vphone run is genuinely
remote (`REMOTE MODE ... no local Metal objects`), and the DXMT readback
machinery carried it unchanged: `ml820 readback: 1 buffer(s) ... 0 failed`.

### ⛔ Ownership across the two backends is not symmetric

This cost three builds and only ever broke the A15. The rules, read from
winemetal's local implementations rather than assumed:

| call | local | remote |
| --- | --- | --- |
| `MTLCopyAllDevices` | +1, yours to release | interned |
| `NSArray objectAtIndex` | **unowned** | interned |
| `MTLCommandQueue commandBuffer` | **autoreleased, unowned** | interned with a reference |
| `MTLDevice newCommandQueue` | +1, yours to release | interned |

Releasing an unowned handle is harmless remotely, because every handle there
carries its own reference. Locally it deallocates a live Metal object out from
under the process, and the damage surfaces at **teardown**, far from the call.
🔑 Take an explicit `NSObject_retain` for anything held past the call that
returned it. A first theory that the fault was `newBufferWithBytesNoCopy`
page-alignment was **wrong** and fixing it changed nothing.

## Dependency

The converter is a locally supplied development dependency. `deps.sh` verifies
the pinned package hash before use and refuses to continue on a mismatch,
because the shader cache key includes the compiler package.

| Item | Value |
| --- | --- |
| Package | `research/GPTK/Metal Shader Converter 4.0 beta 2.pkg` |
| SHA-256 | `1acc33c87ea663933df89721a998d066106685473020bcbe007cee7a16155734` |
| Converter version | 4.0.1 |
| macOS dylib | universal, 60 MB, used for the fast native loop |
| iOS dylib | arm64, 30 MB, platform IOS, minos 13.0, sdk 26.4 |
| Shader compiler | DXC 1.9.2602.17, `toolchains/dxc-win/bin/x64/dxc.exe` under Homebrew Wine |

The iOS and macOS converters export the **same 116 symbols with zero
differences**, so the macOS loop is a fair proxy for API shape. The iOS build
links only against system libraries, has install name `@rpath/libmetalirconverter.dylib`
and is already signed. None of that is deployment proof: the in-app test still
has to show it loads under Madeira's actual signing arrangement.

### Licence position

⚠️ Two separate questions. Apple's grant is one; whether the converter can be
distributed inside Madeira's particular licence combination is another, and is
**not** settled here. Wine's LGPL and any GPL-covered component in the
combination need their own analysis before public distribution. Private
development builds and public redistribution are different activities.


Read from the installer agreement in the package, `Resources/English.lproj/License.rtf`
(Apple EA1844, 2023-05-31). Summarised, not legal advice.

The agreement splits its grant in two, and the split is the whole answer:

- **Section 2.A** covers the Apple Software **except** the dynamic libraries, and
  grants only install, internal use and test, for developing and testing software
  for Apple-branded products, with no distribution right. Note that the
  **headers are separately licensed**: `metal_irconverter/LICENSE.txt` and
  `metal_irconverter_runtime/LICENSE.txt` are the Apache License 2.0 in full, and
  each header carries an Apache-2.0 notice. Apache-2.0 permits redistribution
  subject to its notice requirements, so keeping the headers external here is
  dependency hygiene, not a licence obligation.
- **Section 2.B** covers the dynamic libraries specifically and grants a licence
  to "install, use, test, **and distribute** the Dynamic Libraries for the sole
  purpose of shader conversion".

So embedding `libmetalirconverter.dylib` in a development IPA for shader
conversion is the activity section 2.B names. Conditions that still bind: Apple
branded hardware only (2.C, 2.D), proprietary notices reproduced on each copy
(2.D), no service-bureau or time-sharing use (2.D), no reverse engineering
(2.E), and export control (9). The agreement's opening note also restricts use
to material you own or are authorised to use, which is about the shaders being
converted.

Keeping the dylib out of Git remains the practice here, as repository hygiene
rather than a licence requirement.

## Layout

```
madeira-d3d12/
  shaders/canary.hlsl            single root CBV fixture
  shaders/canary_layout.hlsl     root constants + root CBV, layout fixture
  shaders/*.dxil                 compiled fixtures, root signatures embedded
  tests/native/msc_canary.mm     the M1 canary
  include/ src/pe/ src/native/   empty, for M2 onward
build/madeira-d3d12/
  deps.sh                        dependency resolution and hash verification
  build-canary.sh                builds and links the canary
  out/                           build products, not committed
```

## Tracking note

`.gitignore` line 103 ignores `research/*` with explicit negations for the
subdirectories that are tracked, currently only `research/remote-metal/`. So
everything here is **untracked and invisible to `git status`** today. Adding
`!madeira-d3d12/` is what would put it under version control, and that
is deliberately left for the user to decide along with the commit boundary.
`build/madeira-d3d12/` is not ignored and does show as untracked.

## Rollback

Delete `madeira-d3d12/` and `build/madeira-d3d12/`. Nothing else
references them: no existing build script, source file or bundle resource was
changed to produce the current state.

## Next step

M1 in-app, as two separate gates:

1. **Physical iPhone.** iOS converter, iOS-targeted library, local Metal,
   verified pixels.
2. **vphone remote.** iOS converter, macOS-targeted library, through the
   existing remote protocol to rmetald, with pixels verified back in the guest.
   Remote Metal is the intended backend there, so AppleParavirtDevice is not the
   renderer under test.

Both need the converter embedded and loading under Madeira's real signing
arrangement, which is the part symbol parity does not establish.
