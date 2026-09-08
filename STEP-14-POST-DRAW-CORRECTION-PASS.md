# Step 14 — Post-draw Correction Pass

Step 14 adds one bounded correction pass after a real drawing finishes and Step 13 has produced a trusted final-canvas score.

## What it does

- Uses the in-memory final canvas snapshot from Step 13.
- Compares the actual result against the original source at the planning resolution.
- Finds only high-confidence missed pixels or source-relative colour errors.
- Converts those pixels into same-palette, CanvasGuard-protected correction paths.
- Runs at most one correction pass.
- Stops early when the remaining deadline reserve is too small.

## What it will not do

- It does not save screenshots, crops, hashes, thumbnails or pixels.
- It does not repaint outside the expected source/plan foreground.
- It does not run on blank or low-trust snapshots.
- It does not run when unexpected ink outside the plan is too high.
- It does not change palette extraction, the main renderer or the deadline scheduler.

## Safety model

The correction pass uses the normal Draw Studio execution layer. Existing CanvasGuard, color selection, profile isolation, stroke delivery and safety report systems remain active. Correction data stored after a draw is compact metadata only: path counts, pixel counts, trust state and before/after accuracy numbers.
