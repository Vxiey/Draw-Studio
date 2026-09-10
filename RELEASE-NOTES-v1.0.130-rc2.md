# Image Draw Bot v1.0.130-rc2 — Release Candidate Hardening II

This second release candidate is a release-engineering and stability pass on top of the verified v1.0.129-rc1 renderer/input feature set. No new drawing engine is introduced.

## RC2 hardening

- Clean release branch: removes leftover one-shot integration and patch scripts/workflows.
- Permanent source-tree hygiene gate blocks `*_once.py` and one-shot workflow files from future release builds.
- Release publishing uses version-only release-note naming.
- Manifest validation now verifies app version, file version, channel, Windows x64 architecture, SHA-256 and exact artifact byte size.
- PE/Inno/Version.py consistency gates remain mandatory.
- Update Center remains pinned to the official `Vxiey/Image-Draw-Bot` repository and RC channel policy.
- Hybrid Renderer 3.0, Pixel Accurate, CanvasGuard and profile isolation behavior remain feature-frozen for release validation.

## Required release gates

A v1.0.130-rc2 Windows build is accepted only after the complete regression suite, DrawBot self-test, source hygiene checks, 5,000-cycle lifecycle soak, profile-isolation soak, packaged ZIP/manifest/checksum validation and silent installer → installed EXE self-test → silent uninstall all pass.

## Artifacts

- `ImageDrawBot-1.0.130-rc2-Windows-x64.zip`
- `ImageDrawBot-1.0.130-rc2-Windows-x64-Setup.exe`
- `ImageDrawBot-1.0.130-rc2-SHA256.txt`
- `ImageDrawBot-1.0.130-rc2-manifest.json`

The Windows binaries remain unsigned until an Authenticode certificate is configured.
