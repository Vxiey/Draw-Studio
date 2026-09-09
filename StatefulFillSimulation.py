"""Stateful discrete Fill simulation for Draw Studio v1.0.132-beta.

The existing FillOptimizer remains the topology detector and RegionFillEngine
remains the first safety/cost gate. This module adds a second, state-at-operation
check: it rasterizes the planned contour with the configured brush footprint,
flood-fills from the planned seed, and rejects any region that can escape its
intended row-span mask or loses too much interior to a narrow passage.

This is a deterministic discrete brush model. Runtime CanvasGuard and the
existing post-Fill guard-pixel verification remain authoritative against Paint/
browser anti-aliasing and application-specific behaviour.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, asdict
from typing import Any, Iterable

import numpy as np


@dataclass(frozen=True)
class FillSimulationResult:
    safe: bool
    reason: str
    intended_pixels: int
    flood_pixels: int
    contour_pixels: int
    spill_pixels: int
    missing_pixels: int
    missing_percent: float
    seed_pixel: tuple[int, int] | None
    brush_px: int
    guards_checked: int = 0

    def as_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["missing_percent"] = round(float(out["missing_percent"]), 4)
        return out


def _mask_from_spans(region: dict[str, Any], size: tuple[int, int]) -> np.ndarray:
    w, h = map(int, size)
    mask = np.zeros((h, w), dtype=np.bool_)
    for raw in region.get("row_spans") or ():
        try:
            y, x0, x1 = map(int, raw)
        except (TypeError, ValueError):
            continue
        if y < 0 or y >= h:
            continue
        if x1 < x0:
            x0, x1 = x1, x0
        x0 = max(0, x0); x1 = min(w-1, x1)
        if x0 <= x1:
            mask[y, x0:x1+1] = True
    return mask


def _line_points(a, b):
    x0, y0 = map(lambda v: int(round(float(v))), a)
    x1, y1 = map(lambda v: int(round(float(v))), b)
    dx = abs(x1-x0); sx = 1 if x0 < x1 else -1
    dy = -abs(y1-y0); sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        yield x0, y0
        if x0 == x1 and y0 == y1:
            break
        e2 = 2*err
        if e2 >= dy:
            err += dy; x0 += sx
        if e2 <= dx:
            err += dx; y0 += sy


def _paint_square(mask: np.ndarray, x: int, y: int, brush_px: int) -> None:
    h, w = mask.shape
    b = max(1, int(brush_px))
    lo = (b-1)//2
    hi = b//2
    x0=max(0,x-lo);x1=min(w-1,x+hi)
    y0=max(0,y-lo);y1=min(h-1,y+hi)
    if x0<=x1 and y0<=y1:
        mask[y0:y1+1,x0:x1+1]=True


def _contour_wall(region: dict[str, Any], size: tuple[int, int], brush_px: int) -> np.ndarray:
    w, h = map(int, size)
    wall = np.zeros((h, w), dtype=np.bool_)
    contour = tuple(region.get("contour") or ())
    if len(contour) < 4:
        return wall
    for a, b in zip(contour, contour[1:]):
        for x, y in _line_points(a, b):
            if 0 <= x < w and 0 <= y < h:
                _paint_square(wall, x, y, brush_px)
    return wall


def _flood(blank: np.ndarray, seed: tuple[int, int], intended: np.ndarray,
           *, cancelled=lambda: False) -> tuple[np.ndarray, int, bool]:
    h, w = blank.shape
    sx, sy = map(int, seed)
    visited = np.zeros_like(blank)
    if not (0 <= sx < w and 0 <= sy < h) or not bool(blank[sy, sx]):
        return visited, 0, False
    q=deque([(sx,sy)]);visited[sy,sx]=True;spill=0;steps=0
    while q:
        x,y=q.popleft();steps+=1
        if steps % 2048 == 0 and cancelled():
            raise InterruptedError()
        if not bool(intended[y,x]):
            spill += 1
            return visited, spill, True
        for nx,ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
            if 0<=nx<w and 0<=ny<h and blank[ny,nx] and not visited[ny,nx]:
                visited[ny,nx]=True;q.append((nx,ny))
    return visited, spill, False


def simulate_fill_region(region: dict[str, Any], size: tuple[int, int], *,
                         brush_px: int = 1, painted_state: np.ndarray | None = None,
                         max_missing_percent: float = 8.0,
                         cancelled=lambda: False) -> tuple[FillSimulationResult, np.ndarray]:
    """Simulate one contour+Fill operation against the current discrete canvas."""
    w,h=map(int,size)
    intended=_mask_from_spans(region,(w,h))
    intended_n=int(np.count_nonzero(intended))
    state=(np.asarray(painted_state,dtype=np.bool_).copy()
           if painted_state is not None else np.zeros((h,w),dtype=np.bool_))
    if state.shape != intended.shape:
        raise ValueError("painted_state shape does not match Fill canvas")
    if intended_n <= 0:
        return FillSimulationResult(False,"missing exact row-span mask",0,0,0,0,0,100.0,None,max(1,int(brush_px))),state
    contour=tuple(region.get("contour") or ())
    if len(contour) < 5 or contour[0] != contour[-1]:
        return FillSimulationResult(False,"planned contour is not a closed loop",intended_n,0,0,0,intended_n,100.0,
                                    tuple(region.get("seed_pixel") or ()) or None,max(1,int(brush_px))),state
    if np.any(state & intended):
        return FillSimulationResult(False,"Fill region overlaps already-painted state",intended_n,0,0,0,intended_n,100.0,
                                    tuple(region.get("seed_pixel") or ()) or None,max(1,int(brush_px))),state

    wall=_contour_wall(region,(w,h),brush_px)
    wall_n=int(np.count_nonzero(wall))
    outside_wall=wall & ~intended
    if np.any(outside_wall):
        near=np.zeros_like(intended)
        near[1:,:] |= intended[:-1,:]; near[:-1,:] |= intended[1:,:]
        near[:,1:] |= intended[:,:-1]; near[:,:-1] |= intended[:,1:]
        far=outside_wall & ~near
        if np.any(far):
            spill=int(np.count_nonzero(far))
            return FillSimulationResult(False,"contour brush footprint paints beyond the safe one-pixel boundary halo",
                                        intended_n,0,wall_n,spill,intended_n,100.0,
                                        tuple(region.get("seed_pixel") or ()) or None,max(1,int(brush_px))),state

    seed=region.get("seed_pixel")
    try:
        seed=(int(seed[0]),int(seed[1]))
    except Exception:
        return FillSimulationResult(False,"missing/invalid Fill seed",intended_n,0,wall_n,0,intended_n,100.0,None,max(1,int(brush_px))),state
    blank=~(state|wall)
    flood,spill,escaped=_flood(blank,seed,intended,cancelled=cancelled)
    flood_n=int(np.count_nonzero(flood))
    if escaped or spill:
        return FillSimulationResult(False,"stateful flood escaped the intended component",intended_n,flood_n,wall_n,
                                    max(1,spill),intended_n,100.0,seed,max(1,int(brush_px))),state

    covered=(flood|wall)&intended
    missing=int(np.count_nonzero(intended & ~covered))
    missing_pct=missing/max(1,intended_n)*100.0
    guards=0
    for raw in region.get("guard_pixels") or ():
        try:gx,gy=map(int,raw)
        except Exception:continue
        if 0<=gx<w and 0<=gy<h:
            guards+=1
            if flood[gy,gx]:
                return FillSimulationResult(False,"outside guard pixel became flood-connected",intended_n,flood_n,wall_n,
                                            1,missing,missing_pct,seed,max(1,int(brush_px)),guards),state
    if missing_pct > float(max_missing_percent):
        return FillSimulationResult(False,"narrow passage/brush footprint removes too much intended interior",
                                    intended_n,flood_n,wall_n,0,missing,missing_pct,seed,max(1,int(brush_px)),guards),state

    new_state=state.copy()
    new_state |= wall
    new_state |= flood
    return FillSimulationResult(True,"closed contour remains bounded in current canvas state",intended_n,flood_n,wall_n,
                                0,missing,missing_pct,seed,max(1,int(brush_px)),guards),new_state


def filter_stateful_fill_regions(regions: Iterable[dict[str, Any]], size: tuple[int, int], *,
                                 brush_px: int = 1, cancelled=lambda: False) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows=list(regions or ())
    accepted=[];rejected=[];state=np.zeros((int(size[1]),int(size[0])),dtype=np.bool_)
    for serial,raw in enumerate(rows):
        if cancelled():raise InterruptedError()
        region=dict(raw)
        result,next_state=simulate_fill_region(region,size,brush_px=brush_px,painted_state=state,cancelled=cancelled)
        region["stateful_fill_simulation"]=result.as_dict()
        if result.safe:
            region["fill_sequence_index"]=serial
            accepted.append(region);state=next_state
        else:
            rejected.append({"region_id":region.get("region_fill_id",serial),"reason":result.reason,
                             "spill_pixels":result.spill_pixels,"missing_percent":result.missing_percent})
    return accepted,{
        "enabled":True,"model":"stateful discrete contour + flood simulation",
        "runtime_guard_authoritative":True,"input_regions":len(rows),
        "accepted_regions":len(accepted),"rejected_regions":len(rejected),
        "painted_state_pixels":int(np.count_nonzero(state)),"rejections":rejected[:24],
    }
