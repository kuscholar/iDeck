# Contributing to iDeck

New iDeck-authored contributions use GPL-3.0-or-later with the Madeira Converter
Exception, version 1, for the contributor's own work only. Preserve component
licenses and all existing notices. Do not grant exceptions for third-party work.
Sign off commits with `git commit -s`. Report validation boundaries honestly.
Do not submit credentials, Valve/game binaries, signing assets or private logs.
FEX prohibits AI-generated contributions; do not make AI-generated FEX changes.
See [distribution requirements](docs/DISTRIBUTION.md).

## Inherited Madeira contribution policy (retained)

# Contributing

Contributions to Madeira are accepted under **GPL-3.0-or-later**. By submitting
a change you certify that you wrote it or otherwise have the right to submit it
under that licence, per the
[Developer Certificate of Origin](https://developercertificate.org/), and you
sign off your commits:

    git commit -s

Each submodule fork carries its own `LICENSE-MADEIRA.md` and `CONTRIBUTING.md`.
Do not remove or alter upstream copyright or licence notices in any of them.

Changes intended for an upstream project should be sent to that project against
its own tree, under its own licence. Note that FEX-Emu's contribution policy
prohibits AI-generated code; see the note in `README.md`.

## Additional permission for Apple's Metal Shader Converter

Madeira links with Apple's proprietary Metal Shader Converter library and
Apple system frameworks. Contributions to this repository are accepted under
GPL-3.0-or-later **with the Madeira Converter Exception, version 1** (the
additional permission in `LICENSE-EXCEPTION.md`, prepared 2026-09-16 and
adopted on 2026-09-24, before any public push), so that the combination
can be conveyed. By submitting a contribution you
agree that your contribution carries that additional permission too.
