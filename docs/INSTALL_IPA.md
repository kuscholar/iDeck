# iDeck alpha IPA

Download `iDeck-0.1.3-alpha.1-build54.ipa` and `SHA256SUMS` from the
[alpha release](https://github.com/kuscholar/iDeck/releases/tag/v0.1.3-alpha.1).
The IPA is certificate-free ad-hoc signed. You must re-sign it with **your own**
Apple development account/profile for your device. No paid account is required
just to use the usual free-account development-signing route; its expiry and
limits still apply. The maintainer does not need your Apple password.

1. Verify the download's SHA-256 against `SHA256SUMS`.
2. Use your preferred IPA signer on a Mac/PC with your iPhone trusted/connected.
   [Sideloadly](https://sideloadly.io/) and
   [AltStore Classic](https://faq.altstore.io/altstore-classic/your-altstore)
   describe their own installation, account and refresh workflows.
3. **Keep the app extension** (`MadeiraJITHelper.appex`) and sign all nested code.
   The app and helper must have coherent bundle IDs and matching development
   profiles. JIT requires the app's debugging permission (`get-task-allow`);
   a distribution-only signature is not interchangeable with that requirement.
4. Complete the device's normal developer/trust prompts as needed. Open iDeck
   and follow its pairing/JIT setup. Signing alone does not enable JIT.
5. Supply a legitimate full Windows Steam/CEF client tree for the experimental
   runtime as described in [setup](GETTING_STARTED.md) and
   [Steam UI tests](../tests/steam-ui/README.md). The IPA does **not** contain
   Steam, a Steam login, games or Microsoft redistributables. The supported
   legacy-client acquisition/setup flow is still unfinished; this alpha is
   intended for technical testers who can prepare those prerequisites.
6. Sign in through Valve's own Steam UI and approve Steam Guard yourself.
   Never send account credentials, tokens or pairing files in bug reports.

The alpha targets iOS 26+ and JIT through Madeira's existing workflow. Physical
evidence is from an iPhone 15 Pro Max; iPad and general game support are not
validated. Some startup/login transitions and games can fail. See the upstream
[Madeira compatibility information](https://github.com/willfaust/Madeira#readme).

Build 54 passed local compilation, source-built dependency, relink, package and
signing checks. Phone installation was skipped at the owner's request. No
fresh different-account, Sideloadly/AltStore, JIT or gameplay test is claimed
for this package; the tools above are installation options rather than a
certified compatibility list.

## Modify and re-sign on macOS

The release's source and relink assets preserve component licenses. To modify
an LGPL static library, rebuild it for the matching iOS arm64 ABI, replace the
archive in the relink kit and run `python3 relink.py`. Replace the extracted
IPA's `Madeira.debug.dylib` with the output. Obtain your own main/helper development
profiles and use `tools/resign-app.py` from the source asset; see
[the audit](IPA_RELEASE_AUDIT.md). Recipients can modify and debug those changes.
Your own identity/profiles are required; the maintainer's key is not.
