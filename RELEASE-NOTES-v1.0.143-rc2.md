# Draw Studio 1.0.143-rc2

## Microsoft Paint — compact visible canvas fix

- Fixes the false `Paint canvas visible area is too small. Enlarge Paint or select the drawing area manually.` failure.
- Auto calibration no longer requires the visible canvas to span 35% of the entire Paint window.
- The minimum safe drawable area is now DPI-scaled, so a valid compact canvas can be calibrated inside a large/maximized Paint window.
- Paint resize handles and thin edge chrome are excluded from the blank-canvas measurement instead of splitting one large canvas into smaller fragments.
- The drawable interior must still be blank and verified, and visible borders must still be distinguishable from Paint workspace.
- Clipped client edges retain larger safety insets.
- Genuinely tiny, covered or ambiguous regions still fall back to manual drawing-area selection.

## Regression coverage

- Compact visible canvas accepted.
- Edge resize handle does not split a blank canvas.
- Truly tiny visible area remains rejected.
- Existing full and clipped canvas behavior remains covered.
- Full Windows/Linux CI and DrawBot Windows self-test are required before publication.
