# Draw Studio v1.0.124-beta — Step 26

## Detail Fidelity, Pixel-Accurate Planning & Named Color Intelligence

This release extends the Step 24–25 build with a consolidated Step 26 focused on preserving fine image detail and improving color parsing/diagnostics without changing the calibrated drawing palette.

### Detail fidelity / Pixel Accurate

- Full-resolution PixelMap planning
- CPU/GPU-routed pixel and edge analysis
- Improved edge, importance and micro-detail maps
- Better protection for isolated pixels and very small features
- Less destructive simplification
- Lossless-only simplification safeguards in Pixel Accurate mode
- Deterministic CPU fallback when GPU acceleration is unavailable

### Named Color Intelligence

- CSS4 and Tk/X11 named-color compatibility
- Flexible parsing for forms such as `DarkSlateBlue`, `dark slate blue` and normalized aliases
- `#RGB` and `#RGBA` support
- RGB, RGBA and ARGB parsing
- `gray` / `grey` normalization
- Canonical RGB deduplication for aliases/duplicate names
- Compatibility aliases including `agua -> aqua` and `crymson -> crimson`
- OKLab-based nearest human-readable color lookup
- Color-family metadata and improved diagnostics
- Static lookup data; no Matplotlib runtime dependency

Named colors are deliberately kept out of the calibrated game palette and drawing quantizer. The existing source RGB -> calibrated palette -> OKLab matching path remains authoritative.

### Verification

- Step 24–26 / Color / release regression selection: **79/79 passed**
- Advanced Color, Pixel Accurate and DrawBot integration selection: **104/104 passed**

### Package

`Draw-Studio-1.0.124-beta-Step26-Color-Engine-Named-Color-Intelligence.zip`

SHA-256:

`34dc39349b544e202166648df972ba2a07519262b425609fe5cd578566d98f49`

Note: the exact same ZIP bytes were briefly uploaded to the repository under the misleading filename `Draw-Studio-1.0.127-beta-e.zip`. This repository update restores the package's actual internal version/name without modifying its contents.
