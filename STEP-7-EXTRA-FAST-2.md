# Step 7 — Extra Fast 2.0

This step upgrades the existing **Extra fast** preset without replacing the renderer or undoing Steps 1–6.

## What changed

- Extra Fast no longer forces the old `RGB nearest` + fixed calibrated-palette color path.
- Existing color settings remain active, including:
  - source-relative accuracy
  - OKLab matching
  - dominant hue preservation
  - region-aware color quantization
  - Adaptive Color Count
  - Time-aware Color Budget
- Large safe connected regions still prefer **closed outline + Fill** when that is faster and passes the existing safety/risk checks.
- Adaptive/Dynamic Exact plans can now use Fill with their **plan-local color indexes** instead of being forced to disable Fill.
- Regions that are unsafe or uneconomical to Fill fall back to **connected serpentine scanlines**.
- Extra Fast 2.0 uses longer lossless scanline paths under short deadlines to reduce mouse press/release boundaries.
- Scanline connectors remain restricted to overlapping adjacent pixels of the same planned color. No cross-gap shortcut is allowed.
- Fill tool-switch cost is modeled per color batch rather than pessimistically charging every region independently.
- Irregular fill regions are now previewed from their exact `row_spans` rather than their bounding rectangle, keeping source-relative preview accuracy truthful.
- White-background repair in Dynamic Exact Extra Fast plans is restricted to local fill bounds instead of painting the whole white background.

## Deadline path policy

Extra Fast 2.0 uses bounded path sizes:

- <= 80 s: up to 220 rows / 900 points per connected path
- <= 150 s: up to 180 rows / 760 points
- <= 300 s: up to 140 rows / 620 points
- otherwise: up to 110 rows / 480 points

These are path-boundary optimizations only. They do not merge colors or intentionally delete source pixels.

## Safety

- Existing Safe Fill Mask remains authoritative.
- Runtime CanvasGuard remains authoritative.
- Existing fill leak verification remains active.
- Hole-containing regions continue to fall back to strokes.
- Thin-neck/high-risk regions continue to fall back to strokes.
- Pixel Accurate mode keeps its existing exact-stroke protection.

## New diagnostics

`extra_fast_v2_meta` reports:

- fill region count
- connected scanline path count
- removed stroke boundaries
- scanline boundary reduction percentage
- selected deadline path policy
- whether the Step 1–6 color pipeline was preserved

## Verification

Added `test_step7_extra_fast2_v10131.py` covering:

- preservation of Step 1–6 color settings
- long connected scanlines for short deadlines
- no connector across a blank gap
- Dynamic Exact plan-local outline/fill
- no-Fill fallback to connected scanlines
- exact irregular fill preview spans

Targeted Step 1–7/fill/deadline/color regression set: **119 tests passed**.
`DrawBot.py --self-test`: **passed**.

A full `unittest discover` run was also started; the available execution window ended before the entire suite completed, with no failure reported before timeout.
