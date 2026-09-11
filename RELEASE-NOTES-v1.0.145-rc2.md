# Image Draw Bot v1.0.145-rc2 — Gartic Auto Tools

- Add conservative automatic Brush, Fill, Eraser and Clear selection for verified Gartic Phone layouts.
- Extend the same fail-closed tool-layout path and automatic brush-size presets to Gartic.io.
- Prefer manual anchored tool calibration when present, then fall back to visually verified browser-tool inference.
- Restore Brush automatically after Fill and Eraser-based canvas clearing.
- Keep multi-size Auto Brush bounded by BrowserBrushSize and CanvasGuard.
- Refuse guessed tool clicks when browser-layout confidence is low.
- Preserve the rc1 Total Draw Timer, automatic pixel brush width, Paint UI Automation sizing, profile isolation and ETA calibration.
