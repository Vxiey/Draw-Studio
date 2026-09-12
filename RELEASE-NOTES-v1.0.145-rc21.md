# Image Draw Bot v1.0.145-rc21 — Complete Cost Model Unification

- Remove the last live Region Fill dependency on `HybridCostModel`; the shared stateful `ExecutionCostModel` remains authoritative.
- Cost Fill seal strokes with the same source-to-canvas execution model used for scanlines, contours, Extra Fast, Pixel Accurate and ETA.
- Make Region Fill's emergency fallback purely deterministic and calibration-free so model failure cannot silently switch to a second learned policy.
- Move the reproducible engine benchmark to `ExecutionCostModel.sequence_cost`.
- Keep `HybridCostModel.py` as a compatibility module for historical tests/tools; it is no longer a live planner decision source.
- Preserve Fill safety gates and exact Pixel Accurate geometry.
