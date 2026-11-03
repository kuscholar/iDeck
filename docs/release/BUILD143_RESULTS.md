# Build143 / v0.1.3-alpha.5 — experimental checkpoint

**Known issue: Steam can freeze after returning from the third game exit.**
The user requested this checkpoint release with that limitation. This is not a
stable release or an evidence-backed claim that repeated gameplay is solved.

The user confirms Steam menu is visible and home/library navigation is more
fluid. Official logs track three Hot Roads launches and three exit-code0 ends.
The latest user observation confirms that Steam then freezes after the third
return; this supersedes earlier incomplete stability impressions.

Build143 separates sampling suppression from the broader LEAN switch: periodic
thread-suspending samplers and the compositor stack walker stop, while existing
VM warming/replay, errors and bounded real-stall evidence remain. Hidden log-list
parsing pauses during Steam. The menu helper uses the owned existing window,
avoiding the demonstrated synchronous secondary-Steam child startup wait. These
changes do not solve every child/bootstrap or repeated-game memory problem.

Full Xcode/native37, production-policy host checks, linked final markers,
deep-strict signing, actual installation/readback and fresh saved Steam login
pass. The user tested the signed development build. The public IPA is repackaged
with ad-hoc signatures, no maintainer profile/certificate, and must be re-signed
by each tester. It was audited but not installed again after that repackaging.
No clean-machine or independent-device runtime pass is claimed.

GPU automatic selection was separately exercised and not promoted: missing
GPU-disable arguments are not proof of a CEF hardware backend. The public
compatibility defaults retain software policy and interpreted JavaScript.

## Setup and upgrade boundaries

Install using your own coherent main/helper profiles as in INSTALL_IPA.md.
Keep the same app bundle identity when upgrading, and back up important data.
Do not delete the working app or copy someone else's Steam auth/prefix. Users
must obtain their own legitimate Steam files and authenticate through Valve.

The actual Steam64 test used an already configured separate wine-steam64 prefix
and source-CEF resources. The IPA contains the selection code/runtime, not those
Valve files or that device configuration. A fresh Steam64 installation is not
validated or advertised as one-click working. Existing ordinary setup remains;
see the architecture/experiment docs for the preconfigured research path.

## Corresponding source and relinking

The source companion includes this release's application snapshot, all unchanged
component-source archives from alpha4, and FEX-local131 with the exact ten-file
source overlay plus pins/options/rebuild recipe. Its DLL hash matches the tested
and shipped component. Previously local changes are supplied as corresponding
source for this user-requested iDeck release, not submitted upstream to FEX.
Only the FEX DLL and helper PE differ from alpha4's PE resources; unchanged
resources retain their prior source/notice provenance. The changed native archive
is built from this release's top-level Wine-derived source and pinned headers.

The relink companion contains all103 exact main debug-dylib inputs and a portable
command, executed successfully. Preserve GPL/LGPL/MPL and component notices,
including the Madeira exception only where granted. No Valve/game payloads,
authentication data, raw logs, private profiles or signing keys are distributed.
See BUILD143_EVIDENCE.json and the companion SOURCE_MANIFEST.json for boundaries.

The exact native recipe is build143-native.sh; set WINE_CONFIG_BUILD to the
matching configured Wine host-header directory if it is outside the checkout.
Its source/flags match the tested recipe; path handling alone is made portable.
Portable relinking reproduces all __TEXT section hashes of the tested debug
dylib. This does not prove a full independent-machine rebuild or device pass.
