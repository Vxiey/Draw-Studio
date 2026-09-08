# Step 26 — Detail Fidelity & Pixel-Accurate Planning

Step 26 formalizes the high-fidelity raster path used by **Pixel Accurate** mode.

- Analyze the fitted target at full target-pixel resolution.
- Route palette matching and edge analysis through the measured Step 23 CUDA/OpenCL/CPU backend.
- Build edge, importance and micro-detail maps before stroke scheduling.
- Protect tiny/thin high-value features such as pupils, narrow contours and isolated color marks.
- Allow only lossless same-color run/component merging.
- Keep adaptive detail and background simplification Off, color grouping Accurate, and destructive stroke merging disabled.
- Preserve CPU fallback, CanvasGuard, calibration, Region Fill safety, progressive deadline scheduling and correction passes.

The target application is never zoomed or transformed by this feature.
