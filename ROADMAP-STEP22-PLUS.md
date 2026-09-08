# Roadmap — Step 27+

Step 22 is now implemented. Steps 23–27 are now implemented as well.

## Completed — Step 22 — Universal Hardware Auto Benchmark

- NVIDIA / AMD / Intel adapter detection
- CUDA / OpenCL / CPU microbenchmarking where available
- per-workload backend preference
- CPU/RAM/VRAM-safe adaptive hardware profile
- automatic re-benchmark when the hardware/runtime signature changes
- full CPU fallback

## Completed — Step 23

- real OKLab / DeltaE routing
- real palette matching routing
- real edge and pixel-workload routing
- quantization distance routing
- CUDA + OpenCL + NumPy per-workload selection
- per-workload runtime failure quarantine and CPU fallback

## Completed — Step 24

Adaptive Detail Zoom Pass:

- Auto / Off / 2x / 4x internal source zoom
- high-frequency ROI detection
- source-backed micro-detail recovery
- OKLab palette-safe color selection
- deadline-aware optional detail paths
- no Paint/browser page zoom or calibration movement

## Completed — Step 25

Quick Sketch Fill + Contour Renderer:

- recognition-first contour + safe Fill pipeline
- real OUTLINE_FILL use for large verified closed regions
- connected scanline fallback for unsafe/unavailable Fill
- Simple / Balanced / Detailed sketch styles
- Safe Fill First / Balanced / Scanline Preferred policies
- short-deadline Auto Tuner selection for bounded shape sources
- Adaptive Detail Zoom handoff for critical micro-details

## Completed — Step 26

Detail Fidelity & Pixel-Accurate Planning:

- explicit full-resolution PixelMap fidelity contract
- measured CUDA/OpenCL/CPU palette and edge analysis routing
- strengthened importance analysis with micro-detail scoring
- protection for tiny/thin high-value palette features
- lossless-only run/component merging in Pixel Accurate mode
- destructive simplification, reduced palettes and smart merge kept disabled for Pixel Accurate plans

## Completed — Step 27 — Export / Import Profiles

Export/import one profile at a time as `.drawprofile`/JSON with schema migration, pre-import validation, renderer/resource settings, canvas/calibration metadata, Replace/Import-as-copy conflict handling, strict profile isolation and reset-to-defaults. Machine-specific hardware/timing state and all native-input authorization remain excluded.

## Completed — Step 27.5 — One-click Setup + Automatic Canvas/Palette Verification

A unified read-only setup action now reuses the existing Paint/Browser detectors, discovers or reuses the target, writes only verified calibration state, then performs a second independent live canvas/palette verification pass. Failure blocks setup safely and falls back to manual calibration. It never unlocks or starts drawing.

## Completed — Step 28 — More Drawing Targets

Adds a central target-capability registry and dedicated **Kleki** + **Magma** profiles. Verified automatic targets stay explicitly separated from manual browser targets, so Drawize/Gartic.io/Kleki/Magma never inherit unverified auto-detection. Every profile keeps a unique storage key for settings, calibration, layout fingerprints and timing data; manual targets use explicit tool/palette/canvas calibration with no hard-coded coordinates.

## Completed — Step 29 — New Draw Modes / Hybrid Renderer 3.0

Adds a deterministic Hybrid Renderer 3.0 orchestration layer with Auto Hybrid plus specialised Pixel Art, Icon / Logo, Line Art, Portrait, Shaded Object and Deadline Silhouette modes. It routes into the existing Pixel Accurate, Quick Sketch Fill + Contour, Shape Paths, PortraitPlanner, adaptive detail and deadline engines instead of duplicating native input. Auto Hybrid uses bounded Pillow/NumPy structure statistics only; it does not use AI, ML, OCR or face recognition. CanvasGuard, calibration, target locks, preflight and dry-run remain authoritative.

## Step 30 — Release Candidate Hardening

Run longer real-world stability passes, validate installer/update flows and freeze the release branch.
