"""Detail-aware preview resampling for Image Draw Bot v1.0.113-beta.

The final drawing plan remains untouched.  This module only improves bounded UI
previews by preserving high-contrast micro-features that would otherwise be
averaged away during downscaling (eyes, pupils, nostrils, lip lines, hairline
edges, tiny shadow boundaries, etc.).  It is deterministic and uses only source
pixels; no AI/ML/face recognition is involved.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import MutableMapping, Sequence

import numpy as np
from PIL import Image, ImageFilter, ImageOps

PREVIEW_DETAIL_MODES = ("Fast", "Balanced", "Detailed", "Micro detail")


@dataclass(frozen=True)
class PreviewDetailProfile:
    oversample: int
    threshold: float
    recovery_strength: float
    dark_bias: float
    sharpen_percent: int


_PROFILES = {
    "Fast": PreviewDetailProfile(1, 255.0, 0.0, 0.0, 0),
    "Balanced": PreviewDetailProfile(2, 34.0, 0.28, 0.06, 35),
    "Detailed": PreviewDetailProfile(2, 22.0, 0.46, 0.10, 65),
    "Micro detail": PreviewDetailProfile(3, 14.0, 0.62, 0.14, 90),
}

# Keep the temporary oversampled raster bounded even for very large source files.
_MAX_OVERSAMPLED_PIXELS = 2_400_000


def validate_preview_detail_mode(mode: str) -> str:
    if mode not in PREVIEW_DETAIL_MODES:
        raise ValueError("Preview detail must be Fast, Balanced, Detailed or Micro detail.")
    return mode


def _bounded_factor(size: Sequence[int], requested: int) -> int:
    w, h = max(1, int(size[0])), max(1, int(size[1]))
    factor = max(1, int(requested))
    while factor > 1 and w * h * factor * factor > _MAX_OVERSAMPLED_PIXELS:
        factor -= 1
    return factor


def _rgba_visible_array(image: Image.Image, size: tuple[int, int], factor: int) -> tuple[Image.Image, np.ndarray]:
    source = ImageOps.exif_transpose(image).convert("RGBA")
    hi_size = (max(1, size[0] * factor), max(1, size[1] * factor))
    hi = source.resize(hi_size, Image.Resampling.LANCZOS)
    return hi, np.asarray(hi, dtype=np.uint8)


def _cell_extreme(rgb: np.ndarray, base_rgb: np.ndarray, factor: int, dark_bias: float):
    """Return a representative micro-feature pixel and contrast for each cell."""
    h = base_rgb.shape[0]
    w = base_rgb.shape[1]
    # Visible luminance; alpha is handled separately and white is the visual canvas.
    luma = rgb[..., 0] * 0.299 + rgb[..., 1] * 0.587 + rgb[..., 2] * 0.114
    cells_rgb = rgb.reshape(h, factor, w, factor, 3).transpose(0, 2, 1, 3, 4).reshape(h, w, factor * factor, 3)
    cells_luma = luma.reshape(h, factor, w, factor).transpose(0, 2, 1, 3).reshape(h, w, factor * factor)
    base_luma = base_rgb[..., 0] * 0.299 + base_rgb[..., 1] * 0.587 + base_rgb[..., 2] * 0.114
    delta = np.abs(cells_luma - base_luma[..., None])
    # A slight dark bias helps thin pupils/eye contours survive without turning
    # every bright highlight into a dark mark.  Bright extremes still win when
    # their actual deviation is stronger.
    dark = np.clip(base_luma[..., None] - cells_luma, 0.0, 255.0)
    score = delta + dark * float(dark_bias)
    choice = np.argmax(score, axis=2)
    rows = np.arange(h)[:, None]
    cols = np.arange(w)[None, :]
    chosen = cells_rgb[rows, cols, choice]
    contrast = cells_luma.max(axis=2) - cells_luma.min(axis=2)
    return chosen, contrast


def detail_aware_resize(image: Image.Image, size: Sequence[int], mode: str = "Detailed", *,
                        cancelled=lambda: False,
                        metadata: MutableMapping | None = None) -> Image.Image:
    """Resize RGBA while recovering high-contrast micro-features.

    Flat regions remain normal Lanczos output.  Only cells with enough local
    luminance range blend toward a representative source subpixel, which keeps
    small dark/bright structures visible at preview scale.
    """
    validate_preview_detail_mode(mode)
    w, h = max(1, int(size[0])), max(1, int(size[1]))
    profile = _PROFILES[mode]
    factor = _bounded_factor((w, h), profile.oversample)
    if cancelled():
        raise InterruptedError()

    source = ImageOps.exif_transpose(image).convert("RGBA")
    if factor <= 1 or profile.recovery_strength <= 0.0:
        out = source.resize((w, h), Image.Resampling.LANCZOS)
        if metadata is not None:
            metadata.update({
                "preview_detail_mode": mode,
                "preview_detail_oversample": 1,
                "preview_detail_recovered_cells": 0,
                "preview_detail_recovered_percent": 0.0,
                "preview_detail_threshold": int(profile.threshold),
            })
        return out

    hi, arr = _rgba_visible_array(source, (w, h), factor)
    if cancelled():
        raise InterruptedError()
    # Flatten transparency against white for feature selection, but preserve alpha
    # from the normal resample in the returned preview image.
    alpha = arr[..., 3:4].astype(np.float32) / 255.0
    visible = arr[..., :3].astype(np.float32) * alpha + 255.0 * (1.0 - alpha)
    base = hi.resize((w, h), Image.Resampling.LANCZOS)
    base_arr = np.asarray(base, dtype=np.uint8).astype(np.float32)
    base_alpha = base_arr[..., 3:4] / 255.0
    base_visible = base_arr[..., :3] * base_alpha + 255.0 * (1.0 - base_alpha)

    chosen, contrast = _cell_extreme(visible, base_visible, factor, profile.dark_bias)
    active = contrast >= float(profile.threshold)
    strength = np.clip((contrast - profile.threshold) / max(1.0, 90.0 - profile.threshold), 0.0, 1.0)
    strength = (0.20 + 0.80 * strength) * float(profile.recovery_strength)
    strength *= active.astype(np.float32)
    mixed = base_visible * (1.0 - strength[..., None]) + chosen * strength[..., None]
    mixed = np.rint(mixed).clip(0, 255).astype(np.uint8)

    out_arr = np.asarray(base, dtype=np.uint8).copy()
    # Convert recovered *visible* RGB back to straight-alpha RGB.  Keeping visible
    # RGB directly while also retaining alpha would composite transparency twice
    # later in the planner and could create pale halos around PNG edges.
    a = out_arr[..., 3:4].astype(np.float32) / 255.0
    denom = np.maximum(a, 1.0 / 255.0)
    straight = (mixed.astype(np.float32) - 255.0 * (1.0 - a)) / denom
    straight = np.where(a > 0.0, straight, out_arr[..., :3].astype(np.float32))
    out_arr[..., :3] = np.rint(straight).clip(0, 255).astype(np.uint8)
    out = Image.fromarray(out_arr, mode="RGBA")
    if profile.sharpen_percent > 0:
        alpha_channel = out.getchannel("A")
        out = out.filter(ImageFilter.UnsharpMask(radius=0.55, percent=profile.sharpen_percent, threshold=2))
        out.putalpha(alpha_channel)
    if metadata is not None:
        recovered = int(np.count_nonzero(active))
        total = max(1, w * h)
        metadata.update({
            "preview_detail_mode": mode,
            "preview_detail_oversample": factor,
            "preview_detail_recovered_cells": recovered,
            "preview_detail_recovered_percent": round(recovered * 100.0 / total, 3),
            "preview_detail_threshold": int(profile.threshold),
            "preview_detail_max_local_contrast": round(float(np.max(contrast)) if contrast.size else 0.0, 2),
        })
    return out


def detail_aware_resize_gray(image: Image.Image, size: Sequence[int], mode: str = "Detailed", *,
                             cancelled=lambda: False,
                             metadata: MutableMapping | None = None) -> Image.Image:
    """Grayscale equivalent used by the shaded portrait preview path."""
    rgba = ImageOps.exif_transpose(image).convert("L").convert("RGBA")
    enhanced = detail_aware_resize(rgba, size, mode, cancelled=cancelled, metadata=metadata)
    return enhanced.convert("L")
