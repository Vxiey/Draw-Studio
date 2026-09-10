# Image Draw Bot — Step 16 Correction History + Before/After Metrics

Adds local per-profile correction history with compact before/after metrics. The UI can show recent correction results without storing image data.

## Included

- Profile-isolated correction history file
- Before/after Visual Accuracy and coverage metrics
- Correction state: corrected, partial, skipped, blocked
- Recent average Visual/Coverage delta
- History dialog in the Correction Review card
- Preview diagnostics summary line
- Defensive image-data field detector

## Privacy

No screenshots, crops, thumbnails, hashes, raw pixels or image bytes are saved. Only compact metrics and reason strings are persisted.

## Not changed

No changes to renderer geometry, palette generation, OKLab matching, post-draw correction targeting or time-budget strategy.
