# Draw Studio 1.0.140-rc1

This release integrates the drawing-engine correctness and performance work completed in v1.0.134 through v1.0.140 and restores the Windows release/update chain so installed builds can discover and install newer versions.

## Drawing engine

- Canonical raster-identity regression oracle and generated property coverage.
- Ordered execution/travel telemetry and travel-aware Extra Fast candidate selection.
- Geometry-safe bounded 2-opt with strict pen-up travel non-regression.
- Portrait outline/tone semantic barriers that survive target-path caps.
- Hybrid Cost Model v2 with confidence-weighted calibration, MAPE-aware uncertainty and compatible atomic point timing.

## Windows self-update

- Update Center accepts only the exact versioned Windows installer from this repository.
- Downloaded installers are size-checked, SHA-256 verified and PE-header checked before launch.
- Installed Draw Studio builds update the existing installation in place using the fixed application AppId.
- In-app updates use a very-silent installer handoff, controlled application shutdown, and automatic relaunch after installation.
- Portable/source runs never overwrite themselves in place; they use the normal installer flow.
- A `Version.py` change merged to `main` automatically triggers the verified Windows release workflow.

## Release validation

The release workflow runs source hygiene, release hardening, full Windows regressions, `DrawBot.py --self-test`, package validation, and a silent install/self-test/uninstall round trip before publishing assets.

This RC remains unsigned unless code signing is explicitly enabled.
