# Draw Studio v1.0.128-beta — Step 29: Hybrid Renderer 3.0

Step 29 adds specialised deterministic drawing modes while keeping Draw Studio's existing input, calibration and CanvasGuard architecture unchanged.

## New Hybrid Renderer 3.0

A new **Hybrid Renderer 3.0** rendering style adds:

- **Auto Hybrid**
- **Pixel Art**
- **Icon / Logo**
- **Line Art**
- **Portrait**
- **Shaded Object**
- **Deadline Silhouette**

Hybrid Renderer 3.0 is an orchestration layer. It reuses the existing tested Pixel Accurate, Quick Sketch Fill + Contour, Shape Paths, PortraitPlanner, adaptive-detail and deadline engines rather than creating another native-input engine.

## Auto Hybrid

Auto Hybrid performs bounded local Pillow/NumPy analysis using source dimensions, transparency, white fraction, chroma, luminance variation, edge density, gradients and coarse color occupancy.

Analysis is capped to a 160 px thumbnail and never uploads the source image.

**No AI, ML, OCR, face recognition or semantic object recognition is used.** Because of that, Auto Hybrid deliberately does not automatically claim an image is a portrait. Portrait remains an explicit mode.

## Mode behaviour

### Pixel Art

- full-resolution Pixel Accurate / PixelMap planning
- lossless raster runs
- micro-detail protection
- destructive simplification disabled

### Icon / Logo

- safe closed-region Fill where verified
- visible outer contours
- structural runs
- detail correction
- scanline fallback when Fill is unavailable or unsafe

### Line Art

- contour-first Better Shapes v2
- structural line preservation
- no background Fill
- conservative/lossless detail handling

### Portrait

- existing PortraitPlanner for single-colour drawing
- Maximum likeness/detail policy
- high-detail perceptual colour path for colour targets
- Detail Zoom support

### Shaded Object

- base regions first
- shadow/highlight shape passes
- contours
- detail pass
- progressive rendering

### Deadline Silhouette

- recognition-first silhouette
- safe Fill + contour pipeline
- critical marks after the main silhouette
- reduced palette and bounded stroke budget for short deadlines

## Safety and profile isolation

Hybrid Renderer 3.0 cannot authorize or control native input. It does not change target handles, target locks, canvas coordinates, palette/tool coordinates, Small Test, Safety Preflight, Fast Dry Run, Start authorization or CanvasGuard state.

A defensive invariant compares protected safety/input state before and after Hybrid policy resolution and aborts planning if a future change attempts to modify it.

`hybrid_mode` is stored per profile and is supported by Step 27 `.drawprofile` export/import. Calibration and timing state remain isolated per target.

## Preview diagnostics

Preview diagnostics now expose:

- requested Hybrid mode
- resolved Hybrid mode
- selected underlying renderer
- ordered passes
- source-analysis metrics
- active deadline used by routing
- `semantic_ai_used: false`
- `ocr_used: false`
- native-input/safety status

## Build integration

`HybridRenderer3` is included as a PyInstaller hidden import and the Step 29 technical guide is bundled with packaged Windows builds.

Native Windows version metadata is also synchronized to **1.0.128**.

## Verification

Windows Step 29 regression selection: **64/64 passed**.

The selection includes:

- Hybrid Renderer 3.0 routing and safety invariants
- real Pixel Accurate plan integration
- Quick Sketch Fill + Contour regression tests
- PortraitPlanner integration
- profile isolation and safe profile switching
- Step 28 target capabilities
- Step 27 profile export/import portability
- Python compilation checks for the integrated modules

## Roadmap

Step 29 is complete. The next ordinary roadmap step remains **Step 30 — Release Candidate Hardening**.
