# Image Draw Bot v1.0.144-rc9 — Refine picture colors and simplify Paint setup

- Remove the separate Smart custom palette / exact color button and its help block. Use the existing Custom color palette for picture or automatic Paint preparation.
- Refine the image palette using bounded OKLab source-color sampling, fill unused color slots, and preserve small color accents.
- Accept refinement steps only when sample squared color error improves without increasing the sample 95th-percentile error.
- Match image-palette colors by nearest OKLab distance, avoiding the standard-palette brightness bias in this workflow.
- Keep the same palette in preview and drawing. Keep the Paint + batch, 24-slot preparation limit, cancellation and 750 ms pauses.

The analysis uses at most 16,384 samples, eight refinement iterations and small distance chunks. Existing analysis caches are invalidated. After updating, rerun Custom color palette for picture and Build preview to use the refined palette. Photographic gradients remain approximations with a limited color count.

Regression coverage checks tone gradients, small saturated accents, deterministic output, cancellation, shared preview/runtime colors and Pixel Accurate planning. Actual Paint drawing still depends on the target installation and calibration.
