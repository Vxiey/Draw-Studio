# Image Draw Bot v1.0.145-rc23 — Region Brush ROI Packing

- Move Adaptive Region Hybrid multi-brush raster work from full-canvas temporary masks to each connected component's exact bbox ROI.
- Translate every generated ROI-local path back to absolute planner coordinates before execution-cost evaluation and return.
- Preserve exact brush-footprint erosion, even-brush geometry, residual repair and full-component fallback behavior.
- Add ROI workspace diagnostics so large sparse canvases expose the temporary-mask reduction.
- Keep the verified Gartic brush ladder and real execution-cost selection unchanged.
- Reduce CPU/RAM pressure without changing selected source pixels or allowing brush spill.
