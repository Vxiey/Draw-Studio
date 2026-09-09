"""Canonical raster identity oracle for Draw Studio planning tests.

This module is deliberately independent from Pillow and the production planners.
It turns source segments and generated execution paths into exact integer pixel
sets so lossless path optimizations can prove that they neither add nor omit
planned pixels.

The oracle is test/validation infrastructure only; importing it has no runtime
effect on drawing behavior.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

Point = tuple[int, int]
Segment = tuple[int, int, int, int]
Path = Sequence[Point]


def _point(value: Sequence[int]) -> Point:
    if len(value) != 2:
        raise ValueError(f"Expected point pair, got {value!r}")
    return int(value[0]), int(value[1])


def _segment(value: Sequence[int]) -> Segment:
    if len(value) != 4:
        raise ValueError(f"Expected segment quadruple, got {value!r}")
    return tuple(map(int, value))  # type: ignore[return-value]


def rasterize_segment(segment: Sequence[int]) -> tuple[Point, ...]:
    """Rasterize a segment with integer Bresenham semantics, including endpoints."""
    x0, y0, x1, y1 = _segment(segment)
    points: list[Point] = []
    dx = abs(x1 - x0)
    sx = 1 if x0 < x1 else -1
    dy = -abs(y1 - y0)
    sy = 1 if y0 < y1 else -1
    error = dx + dy

    while True:
        points.append((x0, y0))
        if x0 == x1 and y0 == y1:
            break
        e2 = error * 2
        if e2 >= dy:
            error += dy
            x0 += sx
        if e2 <= dx:
            error += dx
            y0 += sy
    return tuple(points)


def canonical_pixels_from_runs(strokes: Iterable[Sequence[int]]) -> frozenset[Point]:
    pixels: set[Point] = set()
    for stroke in strokes:
        pixels.update(rasterize_segment(stroke))
    return frozenset(pixels)


def canonical_pixels_from_paths(paths: Iterable[Path]) -> frozenset[Point]:
    pixels: set[Point] = set()
    for raw_path in paths:
        path = tuple(_point(p) for p in raw_path)
        if not path:
            continue
        if len(path) == 1:
            pixels.add(path[0])
            continue
        for a, b in zip(path, path[1:]):
            pixels.update(rasterize_segment((a[0], a[1], b[0], b[1])))
    return frozenset(pixels)


def _normalized_endpoints(segment: Segment) -> tuple[Point, Point]:
    a = (segment[0], segment[1])
    b = (segment[2], segment[3])
    return (a, b) if a <= b else (b, a)


@dataclass(frozen=True)
class RasterIssue:
    path_index: int
    segment_index: int
    start: Point
    end: Point
    reason: str
    pixels: tuple[Point, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "path_index": self.path_index,
            "segment_index": self.segment_index,
            "start": self.start,
            "end": self.end,
            "reason": self.reason,
            "pixels": list(self.pixels),
        }


@dataclass(frozen=True)
class RasterIdentityReport:
    source_pixels: int
    rendered_pixels: int
    missing_pixels: frozenset[Point]
    extra_pixels: frozenset[Point]
    unsafe_segments: tuple[RasterIssue, ...]

    @property
    def raster_difference_pixels(self) -> int:
        return len(self.missing_pixels | self.extra_pixels)

    @property
    def exact_raster(self) -> bool:
        return self.raster_difference_pixels == 0

    @property
    def safe(self) -> bool:
        return self.exact_raster and not self.unsafe_segments

    @property
    def first_error(self) -> RasterIssue | None:
        return self.unsafe_segments[0] if self.unsafe_segments else None

    def as_dict(self) -> dict[str, object]:
        return {
            "source_pixels": self.source_pixels,
            "rendered_pixels": self.rendered_pixels,
            "missing_pixels": sorted(self.missing_pixels),
            "extra_pixels": sorted(self.extra_pixels),
            "raster_difference_pixels": self.raster_difference_pixels,
            "exact_raster": self.exact_raster,
            "safe": self.safe,
            "unsafe_segments": [issue.as_dict() for issue in self.unsafe_segments],
            "first_error": None if self.first_error is None else self.first_error.as_dict(),
        }


def compare_runs_to_paths(
    strokes: Iterable[Sequence[int]],
    paths: Iterable[Path],
    *,
    require_axis_aligned_connectors: bool = True,
) -> RasterIdentityReport:
    """Compare source raster runs with generated execution paths.

    Axis-aligned generated segments are allowed only when all their pixels already
    belong to the source raster. A diagonal segment is accepted only when that
    exact segment (or its reverse) existed in the source, so planners cannot
    invent diagonal connectors while preserving passthrough source diagonals.
    """
    source_segments = tuple(_segment(stroke) for stroke in strokes)
    path_list = tuple(tuple(_point(p) for p in path) for path in paths)

    source_pixels = canonical_pixels_from_runs(source_segments)
    rendered_pixels: set[Point] = set()
    issues: list[RasterIssue] = []

    source_diagonals = {
        _normalized_endpoints(segment)
        for segment in source_segments
        if segment[0] != segment[2] and segment[1] != segment[3]
    }

    for path_index, path in enumerate(path_list):
        if not path:
            continue
        if len(path) == 1:
            rendered_pixels.add(path[0])
            if path[0] not in source_pixels:
                issues.append(
                    RasterIssue(
                        path_index,
                        0,
                        path[0],
                        path[0],
                        "point_outside_source_raster",
                        (path[0],),
                    )
                )
            continue

        for segment_index, (start, end) in enumerate(zip(path, path[1:])):
            segment = (start[0], start[1], end[0], end[1])
            segment_pixels = rasterize_segment(segment)
            rendered_pixels.update(segment_pixels)

            outside = tuple(sorted(set(segment_pixels) - source_pixels))
            if outside:
                issues.append(
                    RasterIssue(
                        path_index,
                        segment_index,
                        start,
                        end,
                        "segment_leaves_source_raster",
                        outside,
                    )
                )

            diagonal = start[0] != end[0] and start[1] != end[1]
            if require_axis_aligned_connectors and diagonal:
                if _normalized_endpoints(segment) not in source_diagonals:
                    issues.append(
                        RasterIssue(
                            path_index,
                            segment_index,
                            start,
                            end,
                            "new_diagonal_segment",
                            segment_pixels,
                        )
                    )

    rendered = frozenset(rendered_pixels)
    missing = frozenset(source_pixels - rendered)
    extra = frozenset(rendered - source_pixels)
    return RasterIdentityReport(
        source_pixels=len(source_pixels),
        rendered_pixels=len(rendered),
        missing_pixels=missing,
        extra_pixels=extra,
        unsafe_segments=tuple(issues),
    )


def compare_grouped_runs_to_paths(
    groups: Sequence[Sequence[Sequence[int]]],
    execution_groups: Sequence[Sequence[Path]],
    *,
    require_axis_aligned_connectors: bool = True,
) -> tuple[RasterIdentityReport, ...]:
    if len(groups) != len(execution_groups):
        raise ValueError(
            f"Group count mismatch: {len(groups)} source groups vs "
            f"{len(execution_groups)} execution groups"
        )
    return tuple(
        compare_runs_to_paths(
            source,
            paths,
            require_axis_aligned_connectors=require_axis_aligned_connectors,
        )
        for source, paths in zip(groups, execution_groups)
    )
