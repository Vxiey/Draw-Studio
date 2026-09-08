# Step 5 — Adaptive Color Count

This patch extends Steps 1–4 by making `Exact color count = Auto` genuinely image-aware instead of resolving to one fixed count for the whole quality preset.

## What changed

- Added a bounded deterministic `AdaptiveColorCount` analyzer for Dynamic Exact color plans.
- Auto count now evaluates source color diversity, weighted color entropy, OKLab tone diversity, dominant hue families and local edge density.
- A compact greedy OKLab error curve estimates whether each additional color provides meaningful perceptual improvement.
- Simple flat artwork can use only the few colors it actually contains instead of paying for unused color slots.
- More complex gradients, photos and textured images are allowed to consume more of the profile/quality ceiling.
- Step 3 dominant hue families and light/dark structure establish a structural minimum so Auto cannot save colors by deleting a major color family.
- Step 4 still performs the final region-aware merge, so the adaptive count is an upper budget rather than a request to manufacture extra shades.
- Preview and final planning analyze the same untouched source image and therefore receive the same Auto recommendation.
- Profile Engine Auto now preserves `Exact color count = Auto` for adaptive-exact profiles. Existing profile values become hard ceilings instead of silently replacing Auto with a fixed number.
- Explicit numeric selections (`8`, `16`, `24`, `32`) remain unchanged and authoritative.
- Preview/debug metadata now reports recommended/ceiling colors, complexity score, dominant hue families, significant source buckets, estimated residual OKLab error and stop reason.
- Windows release packaging explicitly includes the new module.

## Performance

- Source analysis is downsampled to a maximum side of 176 px.
- Temporary color candidates are capped at 64.
- OKLab pair distances are calculated once in a small NumPy matrix and reused by the greedy value estimator.
- No per-pixel Python object graph or full-resolution repeated quantization is introduced.

## Intentionally unchanged

- Stroke generation and ordering
- Fill / outline strategy
- Mouse execution
- Palette calibration / exact swatch verification
- Canvas safety
- Time-budget/deadline decisions for Dynamic Exact color count

The metadata explicitly records `time_budget_applied = false`. A later step can combine this image-derived recommendation with the actual drawing deadline without replacing the image-complexity logic.
