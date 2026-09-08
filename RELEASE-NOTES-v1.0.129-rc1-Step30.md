# Draw Studio v1.0.129-rc1 — Step 30: Release Candidate Hardening

This release candidate freezes the numbered feature roadmap and focuses on release reliability, installer/update correctness, package cleanliness and regression prevention.

## Step 30 changes

- Adds `ReleaseCandidateHardening.py` as a hard pre-release gate.
- Adds 5,000-cycle start/stop/disarm lifecycle soak testing.
- Adds repeated profile-storage isolation soak testing.
- Fixes Update Center to use the active `Vxiey/Draw-Studio` repository.
- RC update-channel selection no longer treats beta-stage releases as RC-channel updates.
- Synchronizes `Version.py`, PE version metadata and the Inno Setup fallback version.
- Hardens `build_release.py` with source gating, stale-artifact cleanup, manifest creation and post-build validation.
- Windows CI validates ZIP, installer, SHA-256 and manifest before publishing artifacts.
- Windows CI performs a silent installer → installed EXE self-test → silent uninstall round trip.
- Git tag/version mismatch remains a hard release failure.
- GitHub Release publishing uses the current Step 30 release notes instead of the old v1.0.58 notes.
- Adds a permanent RC gate workflow for source consistency, full regression discovery and self-test.
- Historical tests that were intended to track the current build are frozen to the RC1 version so full discovery can be used as a real release gate.
- Step 30 source/package validation rejects temporary patch workflows/scripts and runtime/debug leakage.

## Feature freeze

No new drawing engine features are added in this RC. Hybrid Renderer 3.0 from Step 29 remains the current rendering architecture. During RC hardening, accepted changes should be limited to release blockers, crash/freeze fixes, security fixes, installer/update corrections, regressions and documentation/test fixes.

## Safety

Step 30 does not weaken or bypass CanvasGuard, target locks, calibration, visual preflight, Fast Dry Run, small-test requirements or native-input authorization. The new release gate itself performs no native mouse input.

## Version

- App version: `1.0.129-rc1`
- Windows file version: `1.0.129`
- Channel: `rc`

The verified source ZIP SHA-256 is published separately in `SOURCE-PACKAGE-SHA256.txt` after packaging.
