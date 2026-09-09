# Windows code signing

The published 1.0.133-rc2 is unsigned. This preparatory change does not sign it
retroactively and does not certify Smart App Control compatibility.

## Ready build path

On a Windows signing machine, provision a publicly trusted RSA code-signing
certificate/private key through the provider's supported hardware or cloud KSP.
The certificate must be accessible in CurrentUser/My. Do not commit keys or
certificate passwords. Install Windows SDK SignTool and set:

- DRAWSTUDIO_SIGNTOOL: absolute path to signtool.exe
- DRAWSTUDIO_SIGNING_THUMBPRINT: certificate's 40-character thumbprint

Run `python build_release.py --installer --signed`.

The build checks RSA, private-key availability and code-signing EKU, signs the
application and unsigned native EXE/DLL/PYD dependencies, preserves valid upstream
signatures and verifies the distribution. Inno Setup signs Setup and its
uninstaller. SHA-256 and RFC3161 timestamps are used. ZIP files, checksums and the
manifest are produced after signing. Signing failure aborts the signed build;
it does not silently produce an unsigned fallback. The manifest reports actual
signing mode. Ordinary unsigned development builds remain available.

Current GitHub-hosted runners do not have a signing identity provisioned by
this change. Configure the chosen provider's supported signing access before
enabling signed builds in CI; no identity, certificate purchase, or service
account has been created. Publish the signed result as a NEW version; do not
replace the existing rc2 files or their updater digests.

## Remaining validation

A trusted signature supplies a verified publisher identity. SmartScreen may
still warn about a new signed file. Smart App Control and managed App Control
policies are separate checks: test a signed installation, startup, native
extensions, Paint preparation and the updater on a clean Windows 11 machine
with Smart App Control enabled. Paint preparation currently invokes PowerShell
and .NET UI Automation; this path needs explicit testing under script policies.
Do not describe passing unit tests as passing Smart App Control.

A real Defender detection needs the exact detection name and file hash, then
review/remediation or Microsoft's false-positive submission process. Signing
alone is not antivirus clearance. Do not disable Windows protections or use a
self-signed certificate as a public trust substitute.

## Provider selection

Microsoft currently supports individuals in the USA/Canada for Artifact Signing
Public Trust; a Swedish individual needs another eligible provider or an eligible
verified organization. The user's verified legal identity must determine the
publisher name. No pricing or subscription is selected in this change.

Sources:
- [Microsoft signing for Smart App Control](https://learn.microsoft.com/en-us/windows/apps/develop/smart-app-control/code-signing-for-smart-app-control)
- [Microsoft signing options and eligibility](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/code-signing-options)
- [Artifact Signing FAQ and SmartScreen reputation](https://learn.microsoft.com/en-us/azure/artifact-signing/faq)
- [Inno Setup signing](https://jrsoftware.org/ishelp/topic_setup_signtool.htm)
