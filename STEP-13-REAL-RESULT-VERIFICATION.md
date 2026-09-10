# Step 13 — Real Result Verification + Safe Canvas Snapshot Scoring

This step adds a safe post-draw verification pass for completed real drawings.

The verifier compares the final canvas snapshot against the original source and,
when available, against the simulated final/quantized target. It is read-only and
in-memory only. Image Draw Bot does not save screenshots, crops, source pixels,
image hashes, thumbnails, OCR output, telemetry, account data, or network data.

Saved feedback contains only compact values such as Visual Accuracy, actual
coverage, actual-vs-simulated score, confidence, trust level, and reason flags.

Trust levels:

- `high`: clean geometry, nonblank canvas, strong source/simulation agreement.
- `medium`: usable for Auto Tuner learning, but with minor notes.
- `low`: scored for diagnostics only; not trusted for quality learning.
- `none`: unavailable or rejected.

This step does not change the renderer, color engine, palette extraction,
stroke planning, timing model, or mouse delivery strategy.
