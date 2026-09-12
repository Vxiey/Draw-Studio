# Image Draw Bot v1.0.145-rc12 — ETA Calibration 2.0

- Persist profile-isolated per-operation timing EMAs across completed real draws.
- Compare the current final execution sequence against measured stroke, colour, tool, Fill and verification costs.
- Allow measured operation evidence to correct ETA both lower and higher instead of acting only as an upward floor.
- Weight operation calibration by model coverage, sample depth and historical prediction error.
- Blend only the residual completed-draw ratio after typed operation calibration to avoid double-counting the same runtime evidence.
- Export operation-calibration coverage, ratio and confidence in draw-time diagnostics.
