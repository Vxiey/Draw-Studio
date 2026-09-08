"""Read-only browser layout state comparison for automatic recalibration.

The module contains no mouse or keyboard input.  It compares client-relative
canvas/palette geometry so a harmless window translation is not confused with
browser zoom/reflow, while DPI/client-size/layout changes are detected.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence


@dataclass(frozen=True)
class BrowserLayoutState:
    client_size: tuple[int, int]
    dpi: int | None
    canvas_rel: tuple[int, int, int, int] | None
    palette_rel: tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class BrowserLayoutDelta:
    changed: bool
    reasons: tuple[str, ...]
    max_palette_shift: int
    max_canvas_shift: int

    @property
    def reason(self) -> str:
        return ', '.join(self.reasons) if self.reasons else 'layout unchanged'


def _client(rect: Sequence[int]) -> tuple[int, int, int, int]:
    if not isinstance(rect, (tuple, list)) or len(rect) != 4:
        raise ValueError('Browser client rectangle is unavailable.')
    l, t, r, b = map(int, rect)
    if r <= l or b <= t:
        raise ValueError('Browser client rectangle is invalid.')
    return l, t, r, b


def make_layout_state(client_rect: Sequence[int], dpi: int | None,
                      canvas_box: Sequence[int] | None,
                      palette_positions: Iterable[Sequence[int]] = ()) -> BrowserLayoutState:
    l, t, r, b = _client(client_rect)
    canvas_rel = None
    if canvas_box is not None:
        if not isinstance(canvas_box, (tuple, list)) or len(canvas_box) != 4:
            raise ValueError('Browser canvas box is invalid.')
        cl, ct, cr, cb = map(int, canvas_box)
        canvas_rel = (cl-l, ct-t, cr-l, cb-t)
    palette_rel = tuple((int(p[0])-l, int(p[1])-t) for p in palette_positions)
    return BrowserLayoutState(
        client_size=(r-l, b-t),
        dpi=(int(dpi) if dpi is not None else None),
        canvas_rel=canvas_rel,
        palette_rel=palette_rel,
    )


def compare_layout_states(old: BrowserLayoutState | None, new: BrowserLayoutState,
                          *, tolerance_px: int = 4) -> BrowserLayoutDelta:
    if old is None:
        return BrowserLayoutDelta(True, ('initial browser calibration',), 0, 0)
    tolerance = max(0, int(tolerance_px))
    reasons: list[str] = []
    if old.client_size != new.client_size:
        reasons.append(f'client resize {old.client_size[0]}×{old.client_size[1]}→{new.client_size[0]}×{new.client_size[1]}')
    if old.dpi is not None and new.dpi is not None and old.dpi != new.dpi:
        reasons.append(f'DPI {old.dpi}→{new.dpi}')

    canvas_shift = 0
    if old.canvas_rel is None or new.canvas_rel is None:
        if old.canvas_rel != new.canvas_rel:
            reasons.append('canvas detection changed')
    else:
        canvas_shift = max(abs(a-b) for a, b in zip(old.canvas_rel, new.canvas_rel))
        if canvas_shift > tolerance:
            reasons.append(f'canvas reflow/zoom {canvas_shift}px')

    palette_shift = 0
    if len(old.palette_rel) != len(new.palette_rel):
        reasons.append(f'palette count {len(old.palette_rel)}→{len(new.palette_rel)}')
    elif old.palette_rel:
        palette_shift = max(
            max(abs(ox-nx), abs(oy-ny))
            for (ox, oy), (nx, ny) in zip(old.palette_rel, new.palette_rel)
        )
        if palette_shift > tolerance:
            reasons.append(f'palette reflow/zoom {palette_shift}px')

    return BrowserLayoutDelta(bool(reasons), tuple(reasons), palette_shift, canvas_shift)
