# Step 25 — Quick Sketch Fill + Contour Renderer

Step 25 adds a recognition-first renderer for short drawing rounds. It prefers a completed, readable sketch over a partially finished high-detail raster.

## Pipeline

1. Keep a bounded hue-safe color palette using the existing Step 2–6 color system.
2. Preserve long/structural runs while pruning only bounded micro texture.
3. Detect large closed regions from the already-quantized execution groups.
4. Pass every candidate through Region Fill Engine and Safe Fill Mask.
5. Convert accepted regions to the existing runtime OUTLINE_FILL path.
6. Leave unsafe/rejected regions as connected scanline/serpentine fallback work.
7. Add a simplified dark visible contour after the safe Fill pass.
8. Hand remaining detail budget to Adaptive Detail Zoom and Deadline/Panic scheduling.

## UI

Rendering style now includes `Quick Sketch Fill + Contour`.

Quick Sketch style:
- Simple
- Balanced
- Detailed

Fill preference:
- Safe Fill First
- Balanced
- Scanline Preferred

## Auto Tuner

For short 75/80-second-class budgets, Auto Tuner may select Quick Sketch when Fill is calibrated and the source has bounded shape/color complexity. Texture-heavy sources keep the existing deadline hybrid renderer.

## Safety

Quick Sketch does not bypass any Fill safety. Region Fill Engine, Safe Fill Mask, CanvasGuard, Target Lock and runtime verification remain authoritative. Fill-unavailable or unsafe regions stay normal connected scanline work.

It never changes Paint zoom, browser page zoom, canvas geometry or calibration coordinates.
