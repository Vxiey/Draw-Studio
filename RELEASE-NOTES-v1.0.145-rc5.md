# Image Draw Bot v1.0.145-rc5 — Smart Fill Engine

- Predict diagonal contour escape risk before choosing bucket Fill.
- Add conservative contour-seal strokes only when every added pixel is proven inside the connected source region.
- Keep all existing hard Fill safety blockers authoritative; seal logic never overrides a hard rejection.
- Charge seal strokes in Fill economics so Fill is selected only when it remains faster than connected runs/strokes.
- Execute seal strokes before the contour and runtime-verified Fill operation.
- Report sealed regions, seal-path count, escape risk and seal execution cost in planner metadata.
