# Image Draw Bot v1.0.145-rc20 — Pixel Accurate Unified Execution Cost

- Move PixelStrokeEngine H/V orientation, deadline path splitting and bounded component scheduling to the shared stateful `ExecutionCostModel`.
- Reuse DrawBot's exact PixelMap-to-canvas scale overrides so Pixel Accurate optimizes real mouse execution time rather than source-space run count.
- Keep exact PixelMap coverage, connected-component safety, protected-detail phases, correction passes and Pixel Accuracy Score unchanged.
- Keep the 72-component bounded scheduler window; dynamic cursor travel is a first-path stateful delta so candidate ranking stays efficient.
- Recompute PixelStrokeEngine's scheduler diagnostic ETA from the final ordered base sequence instead of a separate manual accumulator.
- Preserve `adaptive_hybrid_cost=Off` as the deterministic legacy geometry fallback.
