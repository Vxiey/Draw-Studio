# Image Draw Bot v1.0.145-rc22 — Learned Cursor Travel Integrity

- Keep real cursor-distance cost additive even when a profile has learned dot/stroke operation runtimes.
- Treat learned operation runtime as the nominal path body/baseline instead of replacing stateful travel.
- Add runtime aliases so `short_stroke` and `long_stroke` can safely reuse generic `stroke/path/drag` measurements.
- Preserve the existing bounded distance curve, operation switch calibration and cold-start behavior.
- Bump `ExecutionCostModel` to v4 and keep cost breakdown fields summing to the exact modeled total.
- Prevent calibrated routing from becoming distance-blind after several completed draws.
