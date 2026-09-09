# Draw Studio 1.0.143-rc1

## Microsoft Paint — clipped canvas calibration

- Fixes the `Paint canvas is clipped or too small` failure when modern Paint shows a valid blank canvas that extends beyond the client viewport.
- Auto calibration now treats a large, blank, visually verified visible canvas rectangle as a safe drawing viewport even when the document is clipped at the left, right or bottom window edge.
- Clipped edges receive a larger safety inset before coordinates are saved.
- Visible canvas borders are still verified against the non-white Paint workspace, preventing covered or ambiguous regions from being accepted.
- Truly small drawing regions still fail with a manual-selection fallback instead of unsafe guessing.
- Existing Paint palette, Pencil, Fill, Eraser and custom RGB calibration remain unchanged.

## Regression coverage

- Fully visible canvas behavior remains locked.
- Left/right/bottom clipped canvas viewport detection is covered.
- Covered canvas rejection remains covered.
- Full Windows/Linux CI and DrawBot Windows self-test are required before publication.
