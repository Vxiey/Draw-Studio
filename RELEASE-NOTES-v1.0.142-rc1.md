# Image Draw Bot 1.0.142-rc1

## Microsoft Paint — picture custom palette

- Adds **Custom color palette for picture** directly to the Paint color-calibration area.
- Requires a loaded image and analyzes it with Image Draw Bot's production DynamicColors/OKLab color planner.
- Prepares only a bounded set of useful exact RGB colors; normal Paint palette colors are reused when they are already sufficient.
- Reserves a small bounded detail-color budget for high-edge pixels so eyes, thin contours and small isolated color fields can survive palette reduction.
- Automatically opens Paint **Edit colors**, enters Red/Green/Blue values, confirms each custom color, and saves the picture palette for the current image/calibration.
- If numeric RGB controls are not calibrated yet, the feature calibrates them first without requiring full automatic canvas detection.
- Exact RGB calibration is now saved before canvas detection, so a clipped/zoomed Paint canvas can fall back to manual drawing-area selection without losing custom-color support.
- Prepared picture colors only seed the numeric selection method. The normal first rendered-stroke verification remains mandatory before a color is trusted.
- Native mouse input is bounded, cancellation-aware, and always disarmed in a `finally` cleanup path.

## Regression coverage

- Image fingerprint and image/calibration cache isolation.
- Bounded production palette generation and cache reuse.
- Exact R/G/B typing order.
- Cancellation, dialog escape and input disarm.
- Paint-only UI scope and no-image guard.
- Full Windows/Linux CI and DrawBot Windows self-test remain mandatory before release.
