# Image Draw Bot v1.0.144-rc12 — Paint palette transaction stability

- Harden Microsoft Paint picture-palette preparation with explicit OPEN → WRITE → VERIFY → COMMIT → VERIFY transaction states.
- Retry transient Paint RGB-entry failures up to three bounded attempts with adaptive backoff instead of continuing with stale UI state.
- Re-read calibrated Edit colors controls during recovery and after every committed custom color before moving to the next RGB value.
- Never click + / Add to custom colors until the live R/G/B fields have been verified for the requested color.
- On cancellation or final failure, safely escape the Paint modal and always release native input ownership.
- Preserve the existing picture-palette planner, perceptual refinement, cache, CanvasGuard, render-resume and anchor-safety behavior.
- Keep possible Fill leaks as a hard stop; regions rejected before Fill continue to use the existing safe stroke/scanline fallback.
- Add focused regression coverage for retry bounds, transient recovery, exception preservation and no premature Add-to-custom-colors click.

The release remains protected by source-package checks, portable raster/planner regressions, the complete Windows regression suite, ImageDrawBot self-test, packaged-release validation and silent installer install/uninstall verification before publication.
