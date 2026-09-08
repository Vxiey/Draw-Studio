# Step 15 — Correction Review + User-safe Recovery UI

Step 15 adds a small recovery layer on top of Step 13 real-result scoring and
Step 14 post-draw correction. It does not change the renderer, palette logic,
stroke planner, or correction geometry.

## Goals

- Show clearly why post-draw correction ran, skipped, or stopped early.
- Keep real-result verification and correction metadata separate from preview
  estimates.
- Let the user choose a bounded correction-only retry without restarting the
  whole drawing.
- Let the user choose a full retry when a full re-render is safer.
- Never bypass Target Lock, Safety preflight, Dry run / Unlock, CanvasGuard, or
  the active input guards.
- Persist only compact numeric metadata. No screenshots, crops, thumbnails,
  hashes, raw pixels, or canvas image data are written to disk.

## New UI state

The Step 15 review card summarizes:

- real-result trust and confidence
- source-relative Visual Accuracy when available
- actual coverage when available
- correction paths planned/executed
- correction pixels selected as a count only
- why correction ran, skipped, or stopped early
- available user actions

Possible review states include:

- `no_result`
- `verification_unavailable`
- `manual_review_required`
- `correction_available`
- `correction_skipped`
- `corrected_partial`
- `corrected_pass`
- `within_gates`
- `verified_clean`

## User actions

### Review

Shows the complete correction-review text in a dialog. This is read-only.

### Correction only

Runs a new bounded correction pass using the existing plan and a fresh read-only
canvas snapshot. It does not clear the canvas, rebuild the full plan, or replay
the original drawing.

This button is enabled only when all of these are true:

- the previous result was trusted enough to correct
- the current mouse backend supports safe canvas snapshots
- the same setup safety chain is current
- full drawing is explicitly unlocked because native input will be sent
- the review state allows correction-only retry

### Full retry

Starts a normal full drawing retry with the current image/settings. It still uses
the complete normal safety chain and is blocked when the start guards are not
current.

## Privacy

Step 15 stores only compact numbers and status strings. It does not persist:

- screenshots
- canvas crops
- thumbnails
- hashes
- source pixels
- canvas pixels
- raw image buffers

## Build packaging

`CorrectionReviewRecovery.py` and this document are included by the PyInstaller
build script.
