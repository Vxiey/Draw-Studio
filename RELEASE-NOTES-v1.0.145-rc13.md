# Image Draw Bot v1.0.145-rc13 — Calibration & Recovery

- Add a profile-scoped Calibration Health score with separate palette, tool, exact-color, timing and layout confidence.
- Re-verify the live browser canvas even when Layout Fingerprint v2 already verified the cached palette.
- Perform canvas-only recalibration for small safe canvas drift while retaining the independently verified palette.
- Escalate DPI changes, large reflow and low canvas confidence to full read-only browser recalibration.
- Add bounded adaptive retries for transient visual palette-confidence failures; geometry/safety failures are never retried blindly.
- Export recalibration action, cache-refresh decision and retry telemetry into runtime calibration metadata.
