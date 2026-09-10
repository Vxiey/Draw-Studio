# Image Draw Bot Step 14 — Post-draw Correction Pass

- Adds one bounded post-draw correction pass after a trusted Step 13 real-result snapshot.
- Corrects missed coverage and high source-relative colour errors using the existing profile palette.
- Uses OKLab source comparison at planning resolution.
- Limits correction by max pixels, max paths and remaining deadline headroom.
- Skips unsafe cases: low-trust snapshot, blank canvas, unexpected ink, dry-run/test/resume and current-colour mode.
- Saves no screenshots, crops, hashes, thumbnails or pixels.
- Adds preview diagnostics for correction status and post-correction score.
