# Draw Studio v1.0.58-beta

This beta focuses on canvas safety, deterministic rendering, release readiness and a clearer first-run experience.

## Highlights

- Runtime Safety UI with counters for drawn, clipped, skipped, edge-followed and blocked paths.
- Canvas Guard with SafePolygon, brush inset and FinalMouseGuard.
- Canvas polygon support and deterministic anchor detection.
- Safe canvas transform/rebase for small target-window movement.
- Deterministic edge verification before drawing.
- Safe Fill Mask for Better Fill and background Fill operations.
- Segment-by-segment stroke clipping against the safe polygon.
- Edge behaviors: Hard Clip, Adaptive Clip and Preserve Outline.
- Smart Preview Safety using the same effective safety/edge policy as execution.
- Safety Debug Overlay explaining why paths were drawn, clipped, skipped or edge-followed.
- Runtime Safety Reports saved locally as JSON + TXT.
- Profile Engine v2 with Auto / Manual settings policy.
- CPU/GPU/RAM resource scheduling support.
- Improved first-run guide and hover tooltips.
- GitHub Actions Windows build/publisher and PyInstaller/Inno Setup release pipeline.

## Privacy / diagnostics changes

- Removed the remote bug-report server/client upload path.
- Removed automatic crash-report upload.
- Removed telemetry/reporting configuration.
- Diagnostics are created locally and shared manually by the user.
- Runtime safety reports remain local.
- Source images are excluded from diagnostics packages.

## Renderer

Draw Studio uses deterministic image-processing and geometry algorithms. No AI/ML/OCR model is required by the renderer.

## Recommended installation

Use `DrawStudio-1.0.58-beta-Windows-x64-Setup.exe` from GitHub Releases when available. The portable ZIP is also supported.

## First-run order

1. Open Microsoft Paint or the supported target app.
2. Choose the matching profile.
3. Add the source image.
4. Calibrate tools/colors when required.
5. Select only the drawable canvas.
6. Run the small drawing test.
7. Lock setup.
8. Run Safety preflight.
9. Run Fast Dry run and inspect preview/safety/debug views.
10. Unlock full drawing and start.

`Esc` stops immediately and `F6` pauses/resumes.

## Beta note

This is a beta release. Test on a clean Windows 10/11 x64 machine and perform a dry run before allowing real mouse input.
