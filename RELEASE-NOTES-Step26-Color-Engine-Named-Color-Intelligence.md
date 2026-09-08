# Draw Studio v1.0.124-beta — Step 26 Color Engine: Named Color Intelligence

This patch extends the existing Step 26 build with a named-colour intelligence layer while preserving the calibrated rendering pipeline.

## Added

- Static CSS4 + Tk/X11 compatible colour vocabulary.
- Tolerant colour-name normalization and alias resolution.
- CSS short hex plus explicit RGB/RGBA/ARGB text parsing.
- OKLab nearest human-readable colour names.
- Numeric OKLab colour-family classification.
- Representative named source-to-render mapping diagnostics.
- Compatibility handling for `gray`/`grey`, `agua`/`aqua` and `crymson`/`crimson`.

## Safety / compatibility

- Named colours are never inserted into the target/game palette.
- Existing `AARRGGBB` parsing remains unchanged.
- No Matplotlib runtime dependency was added.
- Existing Paint/game palette calibration remains authoritative.

## Validation

- Named Color + core Color Engine regression suite: 35/35.
- Step 24–26 + Color Engine + release regression selection: 79/79.
- Additional Advanced Color / Pixel Accurate / DrawBot integration selection: 104/104.
