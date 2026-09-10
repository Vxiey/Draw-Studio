# Image Draw Bot 1.0.133-rc1 — 100 maintenance improvements

This source candidate builds on the delivered 1.0.132-rc1 engine integration.
The [numbered Swedish change list](docs/100-UPPDATERINGAR-v1.0.133-rc1.md)
records 100 concrete behavior changes across 17 production modules.

- Unlimited accuracy no longer receives an automatic stroke cap; fixed timers
  ignore unrelated stale manual values and honor a zero reserve.
- Verified color caches validate individual entries, serialize concurrent updates,
  preserve recently verified colors and use durable atomic writes.
- Preview maps bound sampled dots/segments, reduce full-image copies, composite
  transparency consistently and respond to cancellation during safety/fill work.
- Resume state rejects corrupt counters/keys/flags and fingerprints alpha pixels.
- Profile import validates JSON before use and refuses changes during active work
  or when the current settings cannot be saved.
- Runtime scheduling validates costs, isolates timing samples and reports why
  operations were skipped. ETA uses recorded dot timings and distance cost floors.
- Workspace readiness requires a target; common errors provide specific recovery steps.

## Use

Extract the complete source ZIP to a new Windows folder and run `Start.bat`.
Keep your existing installation for rollback. Base dependency installation may
need internet; optional GPU installation is separate. Select the intended target,
check calibration and canvas, then run the usual small test before full drawing.

## Compatibility and validation

See [validation](docs/VALIDATION-v1.0.133-rc1.md) and the change list's compatibility
section. Older resume fingerprints intentionally become incompatible. Malformed
cache/profile data is rejected; unusual manually chosen profile keys may use new
filenames. Built-in and generated custom profile keys retain their filenames.

No EXE was built here. Windows desktop input, Paint/browser interaction, DPI,
GPU execution and installer behavior must be checked on Windows before release.
The packaged validation report was recorded before this GitHub upload. Advanced features listed as deferred in the earlier
engine-integration candidate remain deferred.
