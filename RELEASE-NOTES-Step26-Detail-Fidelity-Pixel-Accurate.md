# Image Draw Bot v1.0.124-beta — Step 26 Detail Fidelity & Pixel-Accurate Planning

## Added

- Makes the Pixel Accurate fidelity contract explicit before any lossy planner policy can run.
- Keeps a full-resolution target `PixelMap`; every drawable target pixel survives analysis.
- Reuses Step 23 workload routing for palette matching and edge analysis on measured CUDA/OpenCL/CPU backends with deterministic NumPy fallback.
- Strengthens the visual importance map with a dedicated micro-detail score for thin/isolated palette transitions.
- Protects pupils, tiny marks, one-pixel contours, narrow features and small high-value color boundaries from later scheduling loss.
- Reports palette, edge, importance and micro-detail analysis backends in PixelMap diagnostics.
- Enforces lossless-only simplification in Pixel Accurate mode: adaptive simplification Off, background simplification Off, Accurate color grouping and component-safe/travel-only optimization.
- Preserves the existing component scheduler, adaptive brush engine, progressive deadline execution and correction passes.

## Compatibility / safety

Step 26 does not change target coordinates, browser/Paint zoom, calibration, CanvasGuard, Region Fill safety rules or mouse ownership. Equal-color runs/components may still be merged when the merge is geometrically lossless.
