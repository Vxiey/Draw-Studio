# Validation — Draw Studio 1.0.133-rc1

Base: delivered 1.0.132-rc1. Environment: Python 3.12 on Linux, synthetic images,
isolated temporary files and fake clocks/input. No desktop input was sent.

## Automated checks

- Full `python3 -m unittest discover`: see the exact final count and result in
  `validation-v1.0.133-rc1.json`.
- 51 new regression tests in `test_hundred_improvements.py`, including concurrent
  cache updates, interrupted file writes, corrupt checkpoints, bounded previews,
  alpha-sensitive resume, profile JSON errors, timing samples and UI readiness.
- `python3 DrawBot.py --self-test`: exit code 0.
- `python3 ReleaseCandidateHardening.py --source-gate`: PASS, 5,000 lifecycle and
  profile-isolation cycles; version, installer metadata and workflow checked locally.
- Release archive: standard source-tree validator and ZIP CRC/integrity check.
- All 100 numbered changes reference changed production code in 17 modules.
  Tests, version updates and documents are not counted toward the 100.

The suite emits existing Pillow getdata deprecation warnings in older tests.
These warnings do not indicate test failures. No comparative speed benchmark was
run for this maintenance batch, so no percentage performance gain is claimed.

## Required Windows validation before publication

This is source code, not a built Windows EXE. GUI startup, actual Paint/browser
mouse delivery, DPI/zoom behavior, stop/pause during physical drawing, GPU execution,
and installer round-trip remain unverified here. Automated simulated-input tests
and source metadata checks do not establish those results.

These local validation results were recorded before the GitHub upload. The
workflow points at the new release notes and can build Windows artifacts.
A successful CI build does not establish physical Paint/browser or GPU validation.

## Compatibility

The RGBA plan hash invalidates older resume fingerprints. Bad cache entries are
ignored; unusual manually created profile keys may use new collision-resistant
filenames. Existing built-in and generated custom profile keys are unchanged.
Stricter profile import rejects duplicate JSON keys, non-finite numbers and a
zero-area canvas. Keep the earlier installation for rollback and extract this
candidate into its own folder.

The advanced features deferred in the previous candidate remain deferred:
progressive-pass crash resume, general dirty-tile replanning and physical
brush-shape calibration. This batch is maintenance of the existing systems.
