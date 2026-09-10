# Image Draw Bot v1.0.132-rc1 — engine integration

This release candidate builds on the supplied v1.0.131-beta source. It reuses
Hybrid Renderer 3.0, Pixel Stroke Engine, Extra Fast, the deadline scheduler,
profile calibration, snapshot verification and correction systems.

## Changes

- Vectorized horizontal and vertical run extraction using row/column-sized
  temporary buffers. Pixels, holes, transparency and palette assignments remain exact.
- Removed duplicate component-segment validation while retaining full coverage
  and spill validation. Cancellation is checked during coverage verification.
- Cached immutable component costs inside each scheduling job and bounded the
  number of queued component jobs. No persistent cross-profile geometry cache.
- Compare H/V candidates after path ordering; accept an ordering only when its
  estimated cost does not increase. Include scaled canvas distances, travel and
  actual color selections in the component sequence estimate.
- Preserve collinear reversals in continuous paths. A turning point that covers
  otherwise missed pixels must not be removed by simplification.
- Split exact axis-aligned pixel paths into shorter operations for active deadlines.
  Target durations are estimates, not guarantees about target-app latency.
- Skip operations that cannot fit the remaining estimated budget. Runtime timing
  excludes pauses; the wall-clock deadline still continues while paused.
- Display a labeled heuristic timing range and distinguish structure sent from
  visually verified canvas coverage. Bound the first timing outlier.
- Correct legacy Auto Fill Off handling when no separate region-fill setting exists.
  An explicitly enabled region-fill setting remains independent of background fill.
- Validate source-relative improvement before correction. Reject brush footprints
  that could worsen neighbouring pixels; bound palette-distance temporaries.
- Recovery fingerprints now include ordered geometry, tool/profile/DPI context and
  fill/clear preludes. Older incompatible checkpoints will not skip completed work.
- In-memory normalized-preview reuse requires the same source object and size.
- Release/disarm input before diagnostics; diagnostic write failures cannot hold
  the mouse button down. Release-settle cancellation still performs mouse-up.
- Benchmark tracing is cleaned up on error. Add `benchmark_engine.py` for isolated,
  repeated reference/candidate comparisons without mouse input.
- Normal Start.bat launches with installed acceleration. Optional GPU installation
  requires the existing installers or explicit `Start.bat --gpu` / `--update`.

## Starting the source package

1. Extract the entire ZIP into a new folder on Windows 10/11.
2. Install Python 3.10 or newer if needed, then run Start.bat. First base dependency
   installation needs internet access. Optional GPU installation is separate.
3. Select the intended profile. Calibrate tools/colors and mark the actual canvas.
4. Load the image, choose the existing mode and create a manual preview.
5. Run the cursor-only test and a small drawing before a full drawing.
6. Use the visible Pause/Resume and Stop controls; keep the target canvas unchanged.

Start with Balanced timing. Extra Fast prioritizes broad coverage; Pixel Accurate
preserves the mapped pixel geometry and may take longer. Neither guarantees the
original image's exact colors when the target palette or brush cannot reproduce them.

## Validation and publication

See docs/ENGINE-VALIDATION-v1.0.132-rc1.md for measured results and the exact limits.
The package contains Python source and the existing Windows build scripts. No new
Windows EXE was built in this Linux environment. GitHub has not been updated.

Build locally on Windows using Build-Release.bat. Complete real Paint/browser,
DPI/zoom, stop/pause and optional GPU checks before publishing. The source release
gate and mocked-input tests do not replace those checks.
