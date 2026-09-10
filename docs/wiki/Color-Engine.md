# Color Engine

Image Draw Bot maps source-image colors to colors the selected target can actually draw.

The color system includes:

- OKLab-based perceptual color matching
- calibrated target palettes
- color grouping and reduction
- Named Color Intelligence
- CSS4 and Tk/X11 compatible color names
- RGB, RGBA, ARGB and HEX parsing
- human-readable color diagnostics

Named colors are diagnostic/input helpers. They do **not** automatically add extra colors to a calibrated target palette.

## Why can a photo look posterized?

**Quantized target** shows the colors selected by the current plan. A limited target palette can replace many skin tones and shadows with the same pink, gray or white. This can happen before any strokes are drawn.

Check the target profile: **Other drawing app** with **palette Unavailable / exact Unavailable** is not a calibrated Microsoft Paint preview. Choose Microsoft Paint and calibrate its RGB controls. For image-specific colors, use **Adaptive exact (recommended)** or **Exact custom + palette fallback**, with Faithful or Exact fidelity, then rebuild the preview. More colors can preserve more gradients but increase drawing time.

**Custom color palette for picture** analyzes image colors and, from rc7, saves up to 24 of them into Paint Custom colors using + with a pause between additions. From rc8, the completed picture palette is shared by Pixel Accurate, normal color-run planning, the preview and runtime selectors for that same loaded image. Earlier releases could keep showing an old preview or bypass this palette in Pixel Accurate. Run the picture-palette button again after updating, then rebuild the preview. A photograph is still reduced to a limited number of representative colors. Calibration alone does not undo quantization.

The diagnostic **luminance +15%** measures brightness drift in the mapped colors; it is not a brightness adjustment setting. A pair such as **LightGray→White** describes a detected color substitution. Compare the rebuilt Quantized target and Simulated final before a full drawing. Neither is a guarantee of the actual Paint result.
