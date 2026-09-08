# Step 4 — Region-aware Color Quantization

This patch extends the Step 3 dominant-hue work without changing the drawing executor, fill strategy, time-budget engine, mouse safety, calibration, or canvas safety systems.

## What changed

- Dynamic Exact quantization now uses local region context in addition to global OKLab distance.
- Nearby same-hue colours that repeatedly touch inside the same spatial area are treated as likely texture/shading and are preferred merge candidates.
- Highlight, midtone, and shadow roles are classified from OKLab lightness so a highlight is not casually collapsed into its shadow just because the palette cap is tight.
- Small protected details receive a strong merge penalty. The Dynamic Exact path reuses the existing AdaptiveDetail protected mask instead of introducing a competing feature detector.
- Region analysis records coarse spatial occupancy and quantizer-label adjacency with compact NumPy arrays; no per-pixel Python objects are created.
- Step 3 dominant hue families remain protected through forced merges by tracking the original protected families represented by each cluster.
- Gartic/Skribbl adaptive palettes can retain a small bounded set of local high-contrast detail anchors after dominant hue and luminance requirements are satisfied.
- Region-aware diagnostics are exposed for preview/debug pipelines, including texture merges, tone-conflict merges, protected-detail merges, forced merges, protected-detail buckets, and retained detail anchors.

## Compatibility fix

The Step 3 palette anchor ordering could discard the global brightest/darkest anchor when that colour belonged to a dominant hue family and the palette cap was tight. Step 4 substitutes that dominant-family representative with the required extreme colour when appropriate, preserving both the dominant family and luminance anchor.

## Intentionally unchanged

- Stroke generation/planning strategy
- Fill/outline rendering strategy
- Drawing speed and time-budget logic
- Palette calibration and exact-swatch verification
- Mouse execution and safety guards
- Canvas calibration/selection
- Existing profile isolation

The purpose of this step is only to make palette reduction region-aware: remove low-value texture variation first while retaining dominant hues, highlights/shadows, and important local details.
