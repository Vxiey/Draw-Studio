# Step 10 — Preview Diagnostics, ΔE Heatmap and Benchmark Suite

Step 10 is a diagnostics-only layer built on Steps 1–9. It does not change color selection, stroke geometry, Fill safety, deadline scheduling, or native input.

## Preview chain

The preview workspace now exposes three distinct stages:

1. **Original** — untouched user source.
2. **Quantized target** — palette/quantized raster target before physical brush simulation.
3. **Simulated final** — the executable preview after brush width, fills and planned drawing geometry.

This makes it possible to see whether an error was introduced by palette/quantization or by execution geometry.

## Accuracy diagnostics

**ΔE heatmap** shows source-relative Euclidean OKLab color distance. Numeric metadata reports mean, median, p95, maximum and severe-error pixel percentage. The existing **Accuracy error** layer remains a combined perceptual color + luminance + edge map.

The diagnostics text keeps these independent:

- Visual Accuracy
- Source Pixel Accuracy
- Perceptual Color Accuracy
- Luminance / Hue / Edge Accuracy
- Coverage
- Plan Execution Accuracy
- OKLab ΔE mean and p95

Plan Execution Accuracy is never presented as source similarity.

## Calibration state

The preview diagnostics line reports the active profile's isolated state for palette, tools, exact color and timing. States remain **Unavailable / Estimated / Calibrated / Verified**.

## Real draw estimate

Diagnostics use the existing local DrawTimeEstimate model, including completed-draw calibration when available. It shows projected draw time, confidence, path count and the timing source. No network or telemetry is used.

## Benchmark suite

The new local benchmark suite runs four deterministic planning/preview cases against 75, 80, 150 and 300 second targets:

- flat illustration
- dominant hues
- texture
- small high-contrast detail

For every case it reports planning time, planned paths, projected draw time, whether the usable deadline was met, Visual Accuracy, Perceptual Color Accuracy and OKLab ΔE statistics.

The suite never arms or sends mouse/keyboard input, never captures the screen, and never uses network/telemetry.
