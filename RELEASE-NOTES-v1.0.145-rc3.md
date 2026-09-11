# Image Draw Bot v1.0.145-rc3 — Fill, Brush and ETA Reliability

- Bound stateful Fill safety simulation to local ROIs while preserving global coverage state, reducing repeated full-canvas allocations.
- Make Extra Fast and RegionFill economics batch-aware so same-color Fill candidates are not penalized by duplicated tool-switch overhead.
- Improve adaptive brush planning with geometry-aware brush selection and collapse transient speed-only upshifts that would cost more UI switching than they save.
- Estimate draw time from the final execution sequence, including actual color, brush, Fill, verification and tool transitions instead of relying only on planner summary estimates.
- Keep existing browser CanvasGuard limits authoritative; full Gartic 5-brush CanvasGuard support remains follow-up work rather than being claimed complete in this RC.
- Include regression coverage for the Fill ROI allocation and batch/sequence cost-model fixes.
