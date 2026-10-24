# Steam CEF compatibility matrix

Revision scope: experimental branch based on ee9fd2f, audited in
BIG_PICTURE_ARCHITECTURE.md. Updated 2026-10-23. Historical evidence refers to
published notes at deezhizyu/madeira 97e2ce2, not a new device run.

| Area | Historical report | Current source/local evidence | Current-device status / next discriminator |
|---|---|---|---|
| Real Steam login | Interactive login/QR refresh reported | Existing services + desktop + steam.exe route; new isolated opt-in launch policy compiles | Build 11 blank desktop; first chrome_elf assertion precedes later exhaustion; no login UI |
| CEF child model | Single-process CEF needed for VA capacity | Initial webhelper allowed, --single-process injected; --type children refused | Build 11 CEF initializes, then chrome_elf refcount assertion; no BrowserReady |
| dwrite/text | Missing unixlib, then text rendered | dwrite object compiled and explicitly archived by native build script | Current Steam text not observed |
| JIT provisioning | Early detach avoided a historical stall | Existing StikJIT/pool setup; no new entitlement requested | Build 11 accepted 880 MiB A/B + 352 MiB C; Build 13 automatic paired JIT diagnostics passed |
| libcef+0x41258FB | kr=10 on mapped RW data; cause open | Later owner/backing probes present; no new retry/protection workaround | Not reproduced; collect Mach return code and mapping/backing lifetime first |
| Skia tile displacement | 254px tile-related displacement; FEX hypothesis unproved | Existing surface/compositor path; new observer reports only host present, never correctness | Need paired SRC/SURF checksums and isolated raster PE/control; not yet implemented |
| CM networking | TCP connected; some TLS; WebSocket/auth failed | Existing native network stack and true Valve auth remain | CEF load failed before UI; CM/TLS/WS/auth behavior not yet evaluated |
| Auth/licensing | Genuine client sign-in, not bypass | New route does not use Dock token transfer or fabricated game identity | Human login/Steam Guard and license validation pending |
| Isolation | All guest children share one Mach task | New mode requires .steamui bundle suffix and flag=1; symlinked client files rejected | Separate Steam UI Lab installed; working app retained |
| Lifecycle | Fatal helper can kill app; guest process != Mach process | Per-child categorical events added behind session flag; no retries/forced termination | Actual Build 12/13 x64 child/shared-map/exit tests PASS; basic chrome_elf import/heap/thread and Build 15 FLS lifetime/isolation tests PASS |
| Rendering/UI | Login had corrupt tiles | Real UI still goes through existing GDI/DXMT/Metal; no UI replacement | Steam error dialog/desktop captured; no real CEF content |
| Big Picture | No reliable end-to-end evidence in handoff | Deliberately absent from first login-only command | Gate until interactive login and CEF stability established |
| Bluetooth/navigation | No applicable current test | Existing GameController/XInput input path unchanged | Backbone game success is not Bluetooth/Steam UI validation |
| Game and return | Ordinary games can run in baseline | One-session-per-app and shared task remain | Launch-from-Big-Picture and return not tested |

No row marked source/local evidence is a device success claim. The experiment
has not fixed the three historical fault families. Source-level instrumentation
and a successful link only make the next test possible.


Build 16 actual CEF ownership trace: the failing CRT PTD has one observed set
and its first callback faults at chrome_elf+0xd7e3e; no earlier FLS delivery for
that pointer. Synthetic FLS still PASS with observer loaded. This narrows the
investigation to pre-callback allocation/free/corruption or translation, without
proving any of them. See STEAM_UI_FLS_TRACE_EVIDENCE.json; interactive CEF remains
unverified. Callback/refcount behavior was not changed.


Builds 18/19: pre-callback PA metadata has slot_size=8192/refcount=0 for a PTD
whose inspected CRT allocation requests 128 bytes. Native logs also prove a real
and soft pool overlap. The feature-flagged strict overlap experiment rejects
12 such candidates and exposes STATUS_NO_MEMORY, with a later fatal at
libcef+0x6923404 rather than chrome_elf+0xd7e3e. This is an allocation/layout
gate, not CEF success or proof of the sole original cause. Existing brp-contain
text misclassifies generic fatal byte patterns; use module/RVA/context.
See STEAM_UI_ALLOCATOR_EVIDENCE.json and Build 19 reproduction instructions.


2026-10-23 offline interval audit: four full reported pools plus current FEX/cage
claims require at least 88 GiB+64 KiB inside a 64 GiB high-band policy, before
other allocations. This is a current-layout bound, not an iPhone-wide NO-GO.
Numeric inventory and isolated reserve-only PE are locally validated/compiled;
no new device or Windows execution. One CoreDevice 4016 availability failure
left lock state unknown; installed candidate remains Build 19. See
STEAM_UI_ADDRESS_SPACE.md and STEAM_UI_RESERVATION_PROBE_EVIDENCE.json.


Builds 20/21 actual Kusch tests: reserve-only PE returns two distinct MEM_RESERVE
intervals then NULL/error487/exit70. The new pre-Wine native probe completes all
62 fixed no-overwrite PROT_NONE requests: only four high-band aligned bases
succeed (both sizes), 27 lower bases fail kr3 with existing native map context;
all created mappings and query ports released. This confirms a current-layout
capacity gate, not interactive CEF or a device-wide impossibility result.
See STEAM_UI_NATIVE_VM_EVIDENCE.json. Installed candidate is Build 21; previous
4016 and pending Build 20 gates are obsolete.


Build23 actual Kusch i386 result: genuine chrome_elf import, verifier and four
heap/thread rounds PASS, exit0. Full libcef/Steam is NOT covered. Native
jit26_detach breakpoint followed guest completion; clean teardown is unproven.
Build24's explicit Steam32Lab full-client launch is a separate pending test.
Evidence: STEAM_UI_X86_EVIDENCE.json.


Build25 full x86 client: initial gdi32 get_gdi_client_ptr access violation;
existing MADEIRA_GDI_SHARED_SECTION=1 then publishes the table into the WoW child
and reaches a visible genuine Steam updater (download complete, installing).
This is pre-CEF progress; BrowserReady/login and Big Picture remain unverified.
The official updater is allowed to change binaries; re-pin them before later
compatibility conclusions. See STEAM_UI_X86_EVIDENCE.json.


Build26: exact genuine Crashpad child admitted only under two experimental
flags. Actual native admission marker + GDI child views, Valve BrowserReady and
visible real Steam login (account/password/QR) confirmed on Kusch. Login
interaction/authentication, library, Big Picture and game/controller remain
unverified. Private artifact hashes: STEAM_UI_X86_EVIDENCE.json. Preserve live
session for user sign-in; never publish QR/auth data or claim full PoC success.
