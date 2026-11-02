# Steam child-window notice: observed failure and presentation fix

2026-11-01, isolated `experiment/steam64-cef64`, source cb3b835 plus local
changes. This is not a claim that the underlying address-space problem is fixed.

## Actual Kusch evidence

Build133 ran genuine saved-login AMD64 Steam/CEF in one native lifetime. Steam
tracked Hot Roads twice; guest744 exited0 at21:41:54 and guest1068 exited0
at21:46:19. The user reports that the game runs despite the native notice.
Interactive Steam navigation after each exit is not independently verified.

The stable7,120,224-byte native log, copied after intentionally ending that idle
Steam session, correlates both game starts with a request for Valve's
`bin/x86launcher.exe`, an i386 child. Both fail before guest initialization:

| Attempt | Free native VA observed | Result |
| --- | --- | --- |
| First game |1172MiB | guest-window-reserve / STATUS_NO_MEMORY |
| Second game |928MiB | guest-window-reserve / STATUS_NO_MEMORY |

This is below the4GiB window itself, as well as the existing additional8GiB
headroom rule. Merely lowering the headroom would not supply the missing4GiB.
The game executable is a separate AMD64 child, which needs no WoW64 window.
Thus the child failure is real, while the notice alone is not a game-failure
verdict. No Valve executable, authentication, licensing or allocation guard is
modified. The exact service role/required functionality of this helper remains
a separate investigation.

The native log also contains a later slot19 V8-table refusal. The parsed FEX
failure categories have no match in this captured log; this is not proof that
all runtime behavior is correct. The final separate lease-file copy failed when
the connection dropped. Earlier39/54-record snapshots remain valid observations,
not a complete end-of-session trace or permission to recycle reservations.

## Minimal presentation change, Build135

Previously, the observer converted any new matching child-window failure into
the same `startupFailure` state used for real launch refusal. A SwiftUI global
alert then took input away even if Steam/the game continued.

The observer now stores that observation as `runtimeNotice`, visible in iDeck
options under Runtime diagnostics, and retains a categorical diagnostic log.
It never opens a modal for this observation. Confirmed preflight refusal still
uses the separate startup-failure alert; normal session failure reporting and
all native allocation checks remain intact. The change does not assert that
the failed child is optional or that Steam/the game must be healthy.

Actual policy/observer host tests pass, including current-session/chunk/rotation
failure detection and preservation of the preflight refusal path. Full Xcode135
passes. Final debug-dylib marker and deep-strict signing pass; private FEX131
and helper126 overlays are byte-identical to the previous experiment. Kusch
installation receipt reports success. After reconnection actual installed135
was read back, genuine saved login succeeded, and the user confirms no popup and
two normal game/exit cycles. Steam logs independently record both exits0. The
third launch fails image placement and later CEF exhausts its table bank; see
[the Build135 milestone](CEF64_BUILD135_MILESTONE.md). Accounts/games/saves preserved;
temporary configs and original CEF attributes were restored/read-back verified
before upgrade.

## Next discriminator

Attribute image views and CEF table lifetimes during repeated game cycles,
using small diagnostic files without pausing the live session. Keep raw private
evidence outside Git and distinguish UI observations from exit/ACK records.

Investigate helper selection and real executable contracts before proposing a
64-bit replacement. Both official launcher files exist, but the found
`x64launcher.exe` strings inside the i386 image are `.rsrc` metadata with no code
reference established by this check. They do not prove an executable bridge,
argument equivalence or safe redirection. No replacement/interception is made.
The broader capacity/lifetime work must recover genuinely available disjoint
address space or reduce actual demands, without false grants or live-lease reuse.
