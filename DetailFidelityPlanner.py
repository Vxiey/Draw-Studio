"""Step 26 — Detail Fidelity & Pixel-Accurate Planning policy.

This module is intentionally small: the heavy raster work remains in the proven
PixelAccuratePlanner / PixelStrokeEngine / PixelAccuracyEngine stack. Step 26
makes the fidelity contract explicit so future profile/timer policies cannot
silently re-enable destructive simplification for Pixel Accurate plans.
"""
from __future__ import annotations

from typing import Mapping

STEP26_NAME = "Detail Fidelity & Pixel-Accurate Planning"
STEP26_ENGINE = "Step 26 Detail Fidelity"


def apply_detail_fidelity_policy(options: Mapping | None) -> tuple[dict, dict]:
    """Return a copy of *options* with the Step 26 fidelity contract applied.

    Pixel Accurate is lossless at target raster resolution. Adjacent equal-color
    pixels may later be merged into runs/components, but no source pixel may be
    removed by adaptive detail, background simplification, reduced palettes or
    smart geometric merging.
    """
    out = dict(options or {})
    quality = str(out.get("draw_quality") or "")
    active = quality == "Pixel Accurate" and not bool(out.get("outline"))
    changes: dict[str, dict[str, object]] = {}
    if active:
        required = {
            "adaptive_detail": "Off",
            "background_simplification": "Off",
            "color_grouping": "Accurate",
            "stroke_optimizer": "Travel only",
            "target_stroke_count_resolved": None,
        }
        for key, value in required.items():
            old = out.get(key)
            if old != value:
                changes[key] = {"from": old, "to": value}
                out[key] = value
        out["planning_resolution_effective"] = "Pixel Accurate / full target"
        out.pop("real_speed_budget_meta", None)

    meta = {
        "step": 26,
        "name": STEP26_NAME,
        "engine": STEP26_ENGINE,
        "active": active,
        "full_resolution_pixelmap": active,
        "destructive_simplification": False if active else None,
        "lossless_run_merging_only": active,
        "tiny_feature_protection": active,
        "changed_settings": changes,
    }
    return out, meta
