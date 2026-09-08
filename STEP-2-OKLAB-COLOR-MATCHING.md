# Step 2 — OKLab Color Matching

This patch changes colour matching only. It does **not** add dominant-hue palette extraction, adaptive colour counts, new fill/outline rendering, or time-budget changes.

## Implemented

- Uses OKLab as the canonical perceptual geometry for palette candidate selection.
- Keeps legacy `RGB nearest` behavior unchanged.
- Adds OKLab lightness/chroma/hue preservation for Balanced and Faithful modes.
- Adds a bounded per-colour hue-family penalty to prevent catastrophic saturated swaps such as yellow → pink when a related swatch is available.
- Uses OKLab geometry in dynamic exact-color cluster reduction.
- Uses the same OKLab candidate scoring in ExactColorEngine.
- Updates Pixel Accurate CPU palette mapping to OKLab and passes the active Color Fidelity policy through the Pixel Accurate path.
- Updates the CUDA palette kernel to use sRGB → OKLab and mirror the CPU fidelity penalties.
- Adds `delta_e_oklab` to colour fidelity diagnostics while retaining CIEDE2000 diagnostics for compatibility.
- Keeps palette generation, palette size, stroke planning, renderer strategy and time budgeting unchanged.

## Scope boundary

This is not yet dominant-hue preservation across the whole image. That remains a later colour-engine step. Step 2 only fixes the geometry used when comparing an existing source/cluster colour against existing candidate colours.
