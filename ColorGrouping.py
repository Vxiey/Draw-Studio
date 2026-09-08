"""Color-phase scheduling for palette drawings (v1.0.7)."""
from __future__ import annotations

COLOR_GROUPING_MODES = ("Accurate", "Smart", "Reduced palette")

from ColorFidelity import palette_match_cost, validate_color_fidelity


def validate_color_grouping(mode: str) -> str:
    if mode not in COLOR_GROUPING_MODES:
        raise ValueError("Color grouping must be Accurate, Smart or Reduced palette.")
    return mode


def _stroke_weight(stroke):
    x1,y1,x2,y2 = stroke
    return max(1, abs(int(x2)-int(x1)) + abs(int(y2)-int(y1)) + 1)


def _distance2(a,b):
    return sum((int(a[i])-int(b[i]))**2 for i in range(3))


def group_palette_strokes(groups, palette_rgb, mode="Smart", color_fidelity="Balanced"):
    """Return (groups, color_order, metadata).

    Smart never changes a requested RGB: it simply draws high-coverage colors
    first and small detail colors later. Reduced palette may merge only rare,
    perceptually close calibrated colors to reduce color switches.
    """
    validate_color_grouping(mode)
    validate_color_fidelity(color_fidelity)
    work = [list(group) for group in groups]
    weights = [sum(_stroke_weight(s) for s in group) for group in work]
    merged = 0
    if mode == "Reduced palette":
        total = max(1, sum(weights)); active = [i for i,w in enumerate(weights) if w]
        # Merge a rare color only into a significantly more-used close color.
        for index in sorted(active, key=lambda i: weights[i]):
            if not work[index] or weights[index] > total * .10: continue
            candidates = [j for j in active if j != index and work[j] and weights[j] >= weights[index]
                          and _distance2(palette_rgb[index], palette_rgb[j]) <= 38*38]
            if not candidates: continue
            target = min(candidates, key=lambda j: (palette_match_cost(palette_rgb[index], palette_rgb[j], color_rendering="Perceptual match", fidelity=color_fidelity), -weights[j]))
            work[target].extend(work[index]); work[index] = []
            weights[target] += weights[index]; weights[index] = 0; merged += 1
    active = [i for i,w in enumerate(weights) if w]
    if mode == "Accurate":
        order = active
    else:
        # Base/larger color masses first, fine detail colors last.  This also
        # makes later detail strokes naturally correct tiny fill/overpaint edges.
        order = sorted(active, key=lambda i: (-weights[i], i))
    return work, order, {
        "mode": mode,
        "active_colors": len(active),
        "merged_colors": merged,
        "stroke_weight": sum(weights),
        "color_fidelity": color_fidelity,
    }
