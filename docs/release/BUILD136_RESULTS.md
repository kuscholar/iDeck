# Build136 merged-main regression: NO-GO for release

At the user's explicit request, main was merged with `experiment/steam64-cef64`
and pushed as `9ffacca5357985f5e4e92e1714188a5589f0fd9a`. This supersedes the
earlier instruction to keep that experiment unmerged; it does not establish
stability or authorize publishing private-only FEX material. Experimental layout
flags remain opt-in. The alpha4 release was not changed.

Full Xcode136,12 merged host regressions, linked nonmodal marker, final output-
handle guard disassembly and deep-strict signing pass. The documented MinGW
archive was restored from upstream and pinned-SHA256 checked. Kusch actually
installed/read back136 and genuine Steam saved login succeeded. No credentials
were entered. Interactive visuals were not independently validated.

First Hot Roads starts23:04:46 EST and exits0 at23:06:38; normal-close helper
ACK reports Steam focused. Second starts23:08:00 and exitsc0000135 at23:08:03.
No matching second-close UUID ACK arrives. A stale ACK is not a pass. No third
launch is attempted after that failure.

The original second-game failure is **JIT image-copy allocation**, not a missing
file: UnityPlayer section creation/query succeed AMD64, canonical image maps,
but a22.047MiB pool copy is refused. Bookkeeping shows81.844MiB total free but
only15.031MiB largest block. The outer loader status is secondary. This differs
from135's canonical image-spill mapping failure; neither proves a sole leak.

Actual startup geometry was smaller than requested:704MiB requested,560MiB
main span obtained, split extension refused, C304MiB and low-image margin262MiB.
The initial private test regex incorrectly read candidate hole566MiB as C size.
That gate is invalidated. The corrected bounded analyzer and host fixture check
read the actual fields and reject this run's geometry. Thus136 is not a valid
same-geometry comparison with135 or proof of a merge-induced regression.

The observed61-record lease snapshot has13successful adopts including6table
slots and no refusal through that snapshot; it is not complete-runtime coverage.
Historical CEF OOM lines are not attributed to this run.

The pending command was cleared, only the identified failed native test was
ended after game exit, and original attributes/global+CEF configs were restored
and read-back verified. Account/games/saves remain.136 stays installed; the
regression session is closed. No new release/tag/draft was created.

Next require actual geometry before another game run, then discriminate image
copy allocation/lifetime from canonical image placement and CEF table lifetime.
The exact private FEX131 source/relink distribution obligations also remain a
release gate; do not publish a binary whose corresponding material is absent.

Evidence: [BUILD136_EVIDENCE.json](BUILD136_EVIDENCE.json).
