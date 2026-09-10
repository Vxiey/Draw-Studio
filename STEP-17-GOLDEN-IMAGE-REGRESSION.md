# Step 17 — Golden Image Regression Suite

Image Draw Bot now ships a small local golden-image regression suite for the color, accuracy, timing and correction pipeline added in Steps 1-16.

## What it checks

The suite uses deterministic synthetic PNG fixtures:

- `yellow-banana-hue-guard.png` — catches yellow drifting to pink/orange.
- `red-bananas-texture.png` — catches texture quantization and red/green tone-anchor regressions.
- `dominant-hue-four-color.png` — catches loss of red/yellow/green/blue under tight color ceilings.
- `small-detail-preservation.png` — catches over-aggressive simplification and unsafe correction regressions.

## Metrics used

Each case checks the source-relative metrics from Step 1:

- Visual Accuracy
- Source Pixel Accuracy
- Perceptual Color Accuracy
- Hue Accuracy
- Luminance Accuracy
- Edge Accuracy
- Coverage
- OKLab ΔE distribution
- estimated draw time against usable budget

## Privacy and safety

The fixture images are generated from code and are included only as local regression assets. The suite never uses user images, mouse input, screen capture, network, telemetry, screenshots, crops, hashes or persisted pixels.

## UI

The Tools page includes **Golden tests**, which runs the suite locally through the normal planning pipeline without arming native input.
