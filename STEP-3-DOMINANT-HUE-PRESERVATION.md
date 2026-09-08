# Step 3 — Dominant Hue Preservation

This patch adds a deterministic OKLab-based dominant-hue protection stage without changing stroke planning, fill strategy, time budgets, or renderer execution.

## What changed

- Large red, orange, yellow, green, cyan, blue, purple and magenta families are detected from visible colour coverage.
- Dominant hue families reserve reduced-palette slots before extra shades and small texture colours.
- Dynamic exact-colour reduction avoids collapsing two different protected hue families while cheaper same-family/detail merges still exist.
- Browser/game adaptive palette reduction uses the same dominant-family anchors.
- Diagnostics now report dominant hue families, coverage, selected anchors, preservation percentage and any lost dominant families.
- Tiny saturated accents below the coverage floor do not steal guaranteed slots from genuinely large objects.

## Intentionally unchanged

- Stroke planning and stroke ordering
- Fill / outline rendering
- Time budget engine
- Adaptive colour-count policy
- Mouse/tool execution
- Palette calibration

This is Step 3 only.
