# Additional permission for the Apple Metal Shader Converter (GPL-3.0 section 7)

Prepared 2026-09-16 for review. NOT IN EFFECT until the copyright
holder completes the adoption line below. Distribution begins with the first
push to a public remote, not with a release tag, so the line must be
completed BEFORE any public push (the repository's `.githooks/pre-push`
refuses a remote push while this file is a draft; enable it with
`git config core.hooksPath .githooks`). Every copy of this text in the
forks and the runtime follows this adoption. See "Scope and authority" for
what it can and cannot cover.

Adopted on: 2026-09-24
By: Will Faust

Madeira is licensed under the GNU General Public License, version 3 or (at
your option) any later version (see `COPYING`). The following additional
permission applies to the parts of Madeira whose copyright is held by the
Madeira authors (see "Scope and authority"):

### Madeira Converter Exception, version 1 (of 2026-09-16; in effect from the adoption date above)

Additional permission under GNU GPL version 3 section 7.

If you modify this Program, or any covered work, by linking or combining it
with the Apple Metal Shader Converter dynamic library
(libmetalirconverter.dylib, in any version) or with Apple's Metal,
Foundation, CoreGraphics, QuartzCore, UIKit, AppKit and related system
frameworks, or with modified versions of those libraries, the licensors of
this Program grant you additional permission to convey the resulting work.
Corresponding Source for a non-source form of such a combination shall
include the source code for the parts of the Program used in the
combination, but need not include the source code of those Apple libraries.
This permission does not extend to those libraries, which remain subject to
Apple's own licence terms. You may remove this additional permission from
copies you convey, as GPL-3.0 section 7 allows.

## Scope and authority

An additional permission can be attached only by the copyright holder of
the code it covers. It therefore covers, and only covers:

- the Madeira application and tooling in this repository (all commits are
  by the Madeira author; contributions are accepted under `CONTRIBUTING.md`,
  which from this date includes this permission);
- the native Direct3D 12 runtime in `research/madeira-d3d12` (same author;
  its own `LICENSE` file carries the same text);
- the Madeira-authored modifications in the FEX and DXMT forks and in the
  rpmalloc fork under FEX/External (commits by Will Faust), whose
  `LICENSE-MADEIRA.md` files reproduce this permission in full. Upstream
  FEX and DXMT code is MIT and upstream rpmalloc is 0BSD; Ryan Houdek's
  rpmalloc commits are 0BSD; none needs an exception.

It does NOT cover, and nothing here changes:

- upstream Wine code. The Wine fork was relicensed from LGPL-2.1-or-later
  to GPL-3.0-or-later under LGPL section 3, which is irreversible for that
  copy and makes the Wine authors' code GPL-only in that tree; no exception
  can be attached to it by anyone but them. The path being prepared is an
  LGPL branch built from the upstream wine-11.4 baseline with the
  Madeira-authored patches reapplied under LGPL-2.1-or-later, documented in
  `docs/wine-lgpl-provenance.md`;
- the Apple libraries themselves. The converter library is tracked in this
  repository (whether that co-location, or the built app, forms a combined
  work with the GPL code is a question for the legal review, not settled by
  this file) and it is distributed only under Apple's agreement
  (`app/Madeira/d3d12/METAL-SHADER-CONVERTER-AGREEMENT.txt`, section 2.B:
  distribution "for the sole purpose of shader conversion").

This file is a licensing statement by the copyright holder, not legal
advice; the assembled application must be reviewed before public release
(see `docs/LICENSING.md`).
