# Build145 / v0.1.3-alpha.6 — Steam64 setup, one step at a time

**Experimental prerelease. Known issue: Steam can freeze after returning from
the third game exit. This release improves setup, not that runtime limitation.**

## What changed

Steam64 now has a launcher acquisition/repair path:18 immutable official Valve
HTTPS packages,6229 stock file hashes, bounded streaming ZIP validation and
transactional rollback. The matched source-built open compatibility components
are installed only after stock files pass verification. Activation is one atomic
config switch with a durable receipt; the old environment remains intact and
accounts/games/saves are not transferred. Cancel/retry retains verified cache.

The visible flow is now Install Steam → Connect LocalDevVPN → Pair this device
→ Enable JIT, then Launch Steam. Runtime preparation happens inside installation;
signing and native address checks remain automatic mandatory gates. Pair in
iDeck directly shows the existing on-device instructions/PIN; the iOS host is
still called Madeira. Completed tasks are checked/skipped and the view advances
after a complete scan. Recovery/import/account/auto-start choices are Advanced
options. New product installs default built-in JIT; existing method choices stay.

## Evidence boundaries

The user reports that Build144 installation can complete, then requests this
setup simplification. Build145's host flow/gating and existing readiness/JIT
integration checks pass. Full Xcode145 and final linked/resource pins pass.
The separate Fresh Test145 was development-signed, installed/read back and
opened on Kusch; Documents was empty before launch and original iDeck143 stayed
at its prior URL/version. Pairing may survive reinstall in its own Keychain,
so empty Documents is not claimed to mean an empty pairing Keychain.

The revised complete145 UI flow, Steam login and repeated gameplay have not
received a new user acceptance result. The public IPA is repackaged with ad-hoc
signatures and no maintainer profile; it was not installed again in that form.
Recipients must sign using their own coherent main/helper development profiles
and activate JIT. Build143's existing third-return failure remains prominent.

## Capacity and version limits

Steam64 does not increase virtual address space. The profile needs a specific
large disjoint layout and a successful native reservation check on app startup;
a map boundary alone is insufficient. 32-bit games/auxiliaries still have limits.
The matched snapshot is Steam manifest1769025840 (January22,2026), CEF126,
with bootstrap updates held to keep matched components. It is not the latest
Steam/Chromium. A future snapshot needs compatibility and security reassessment.
No Valve Steam/client/libcef binary is bundled or patched. Source-built
Chromium ELF and standalone Crashpad support are bundled under their own licenses.

## Source and relink materials

Download both source companions, the relink and license/audit packages, the IPA
and inventory JSON, and SHA256SUMS. The main source companion retains alpha.5's
unchanged component/source provenance and exact FEX131 overlay plus this release's
application snapshot. No new FEX source changes are made. The separate Steam64
support-source companion includes pinned focused Chromium/CEF source, actual
adapted Crashpad-mingw94 source with dependencies, matching build recipes,
config_guard.c and notices. Chromium is a focused snapshot, not a claimed copy
of the entire browser checkout; the supplied exact recipe fetches additional
public pinned inputs. Full independent-machine/offline rebuilding is not claimed.

The 105-input application relink command was executed; every one of 30 __TEXT
section hashes matches the built main debug dylib. Source/notices are supplied
for the actual shipped helpers; no Valve binary, game, auth cache, private log,
profile, pairing file or key is included. Preserve all component licenses and
only apply the Madeira exception where its licensors granted it.

The application shell can be rebuilt from the tag after staging the documented
runtime resources. Use docs/STEAM64_SETUP.md and tools/stage-steam64-compatibility.py
with the exact support components from the IPA/rebuilt artifacts, existing
FEX-local131 source overlay and its pinned runtime. Build with scheme Madeira,
CURRENT_PROJECT_VERSION=145 and your own team/bundle identifiers. This public IPA
retains com.kuschqin.madeira.steamui for continuity with alpha.5; keep an existing
installation's coherent IDs when upgrading. See INSTALL_IPA.md for resigning.
