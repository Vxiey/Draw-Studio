# Step 1 — Source-Relative Accuracy

This patch changes accuracy reporting only. It does **not** change palette generation, palette matching, stroke planning, rendering strategy, or time budgeting.

## Implemented

- Preserves the untouched original source image for evaluation.
- Caches one normalized source buffer at the preview comparison size.
- Separates internal plan correctness from source similarity.
- Adds `Plan Execution Accuracy` while retaining legacy internal aliases for compatibility.
- Adds source-relative `Source Pixel Accuracy`, `Perceptual Color Accuracy` (OKLab), `Luminance Accuracy`, `Hue Accuracy`, `Edge Accuracy`, and combined `Visual Accuracy`.
- Keeps Coverage separate and only includes it when a real planner/simulator coverage value exists.
- Replaces the Accuracy error preview with a source-relative heat map combining perceptual color, luminance, and edge mismatch.
- Preserves separate runtime objects for original source, normalized source, quantized target (Pixel Accurate), and simulated final preview.
- Adds a divergence note when the internal plan executes perfectly but differs strongly from the original source.
- Adds deterministic tests for exact match, yellow→pink, luminance loss, missing coverage, and perfect-plan/wrong-source cases.

## Visual Accuracy weights

- Perceptual color: 40%
- Luminance: 20%
- Edge: 25%
- Coverage: 15%

If Coverage is unavailable for a legacy/non-Pixel-Accurate plan, it is not fabricated; the available components are reweighted instead.
