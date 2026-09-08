# Step 16 — Correction History + Before/After Metrics

Step 16 adds local, profile-isolated correction history for Draw Studio.

## What it records

After a real completed draw or correction-only retry, Draw Studio can store a compact history entry with:

- before-correction Visual Accuracy and source-relative metrics
- after-correction Visual Accuracy when a trusted post-correction score exists
- coverage before/after
- correction paths planned/executed
- selected correction pixel count
- reason correction ran, skipped or stopped
- deadline/context labels such as profile, renderer, strategy, brush width and workflow

## What it does not record

No image data is persisted.

Draw Studio does not save:

- screenshots
- crops
- thumbnails
- raw pixels
- image bytes
- canvas/source bitmaps
- hashes of image data

Only compact numeric metrics and short reason strings are written.

## Profile isolation

Each profile gets its own history file:

- `correction-history-microsoft-paint.json`
- `correction-history-gartic-phone.json`
- `correction-history-skribbl.json`

Paint history cannot affect Gartic or Skribbl history.

## UI

The Correction Review card now includes a History / before-after action. It shows recent compact results for the current profile, including before → after Visual Accuracy and path counts.

## Boundaries

This step does not change renderer geometry, palette matching, correction targeting, time budgets or safety gates.
