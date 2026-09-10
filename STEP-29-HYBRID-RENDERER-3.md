# Step 29 — New Draw Modes / Hybrid Renderer 3.0

Step 29 adds a deterministic orchestration layer for different image structures without adding a second mouse/input engine.

## New rendering style

Select **Hybrid Renderer 3.0** and then choose a Hybrid mode:

- **Auto Hybrid** — bounded source statistics choose an appropriate specialised mode.
- **Pixel Art** — routes into the existing full-resolution Pixel Accurate / PixelMap pipeline.
- **Icon / Logo** — prioritises safe closed-region Fill, outer contours, structural runs and detail correction.
- **Line Art** — contour-first Shape Paths with preserved structural lines and micro-lines.
- **Portrait** — uses the existing PortraitPlanner for single-colour targets; full-colour targets use a high-detail perceptual path instead of pretending face recognition exists.
- **Shaded Object** — progressive base regions, shading/highlights, contours and detail passes.
- **Deadline Silhouette** — recognition-first silhouette/fill/contour planning with a bounded path budget.

## Auto Hybrid analysis

Auto Hybrid uses only local Pillow/NumPy image statistics:

- source dimensions
- transparency fraction
- white-background fraction
- chroma fraction
- luminance variance
- edge density and mean gradient
- coarse quantized color occupancy
- dominant-color coverage
- flatness / line-art / pixel-art scores derived from those measurements

Analysis is capped to a 160 px thumbnail. No image is uploaded.

**No AI, machine learning, OCR, face recognition or semantic object recognition is used.** Auto Hybrid therefore never automatically claims that an image is a portrait. Portrait is an explicit user-selected mode.

## Existing engines reused

Hybrid Renderer 3.0 deliberately routes into existing tested engines instead of duplicating geometry/input code:

- `PixelAccuratePlanner`
- `QuickSketchFillContour`
- `ShapePaths`
- `PortraitPlanner`
- `AdaptiveDetail`
- `DetailZoomPass`
- `ProgressiveRenderer`
- `TimeBudget` / deadline scheduling
- existing color engine and OKLab palette matching

This means future fixes in those engines continue to benefit Step 29 modes.

## Safety contract

`HybridRenderer3.py` is planning policy only. It never writes:

- target handles/windows
- canvas coordinates/polygons
- palette positions
- tool click coordinates
- target-lock state
- small-test state
- safety-preflight state
- dry-run state
- Start/input authorisation
- CanvasGuard enablement

A defensive invariant compares protected safety/input fields before and after Hybrid policy resolution and aborts planning if a future change attempts to modify them.

## Profile isolation

`hybrid_mode` is saved per profile and included in Step 27 `.drawprofile` export/import. It does not share calibration or timing state between targets.

## Preview diagnostics

Preview diagnostics expose:

- requested Hybrid mode
- resolved Hybrid mode
- base renderer selected
- ordered rendering passes
- source-analysis metrics
- deadline used for routing
- explicit `semantic_ai_used: false`
- explicit `ocr_used: false`
- safety contract text

## Version

Step 29 is released as **Image Draw Bot v1.0.128-beta**.

Step 30 remains **Release Candidate Hardening**.
