# Release notes — Step 21 Build / Publisher / GitHub Release Clean-up

Step 21 focuses on release hygiene and repository structure.

## Added

- `ReleasePackage.py` for deterministic source release validation, source ZIP creation, SHA-256 checksums and compact release manifests.
- `GITHUB-RELEASE-TEMPLATE.md` for tag releases.
- `docs/PUBLISHING.md` with local and GitHub release instructions.
- `docs/RELEASE-STRUCTURE.md` describing which files belong in source, portable ZIP and installer releases.
- `ROADMAP-STEP22-PLUS.md` for future feature work after the beta/release-candidate cleanup.
- Step 21 regression tests for clean source archives, workflow configuration, docs and release naming.

## Changed

- README now starts as a real project landing page instead of an old single-version changelog entry.
- GitHub workflow is clearer and includes a source-tree validation step before Windows build packaging.
- Build metadata includes release-manifest output and stronger tag/version checks.
- PyInstaller resource list includes Step 21 documentation.

## Safety / privacy

- Runtime logs, safety reports, diagnostics, crash dumps and generated release archives are blocked from source release packages.
- No screenshots, crops, thumbnails, hashes, image bytes or telemetry are added.

## Not changed

- Renderer, color engine, stroke planning, calibration, correction and auto-tuner behavior are unchanged in this step.
