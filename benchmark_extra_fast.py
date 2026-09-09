"""Synthetic source-raster benchmark; never sends mouse or network input.

This benchmark reports both planner-local Extra Fast cost and execution-sequence
telemetry. The latter includes pen-up travel and color-selection cost after the
existing bounded StrokeOptimizer ordering. It still does not claim measured
target-application wall-clock speed.
"""
from __future__ import annotations

import json
import os
import platform
from time import perf_counter

from PIL import Image, ImageDraw

from ContinuousPaths import build_execution_paths
from ExecutionTelemetry import execution_metrics
from ExtraFast2 import build_fast_paths, path_limits
from HybridCostModel import build_cost_model
from StrokeOptimizer import optimize_execution_groups
from Version import APP_VERSION


def raster(paths):
    im = Image.new('1', (320, 320))
    draw = ImageDraw.Draw(im)
    for path in paths:
        if len(path) == 1:
            draw.point(path[0], fill=1)
        else:
            draw.line(path, fill=1, width=1)
    return im.tobytes()


def _source_paths(group):
    return [[(a, b), (c, d)] if (a, b) != (c, d) else [(a, b)] for a, b, c, d in group]


def _optimize(groups, *, speed='Balanced'):
    optimized, _phase_hints, meta = optimize_execution_groups(
        groups,
        mode='Smart merge',
        drawing_mode='Smart paths (recommended)',
        speed=speed,
    )
    return optimized, meta


def run():
    cases = {
        'vertical_block': [[(x, 10, x, 290) for x in range(10, 290)]],
        'horizontal_block': [[(10, y, 290, y) for y in range(10, 290)]],
        'vertical_hole': [[
            (x, a, x, b)
            for x in range(10, 290)
            for a, b in ([(10, 100), (200, 290)] if 100 <= x <= 200 else [(10, 290)])
        ]],
        'separate_colors': [
            [(x, 10, x, 290) for x in range(10, 140)],
            [(x, 10, x, 290) for x in range(150, 290)],
        ],
        'thin_separated_lines': [[(x, 10, x, 290) for x in range(10, 290, 3)]],
        'mixed_axes': [[
            *[(x, 10, x, 140) for x in range(10, 140)],
            *[(160, y, 290, y) for y in range(160, 290)],
        ]],
    }

    options = {'speed': 'Balanced'}
    rows, points, _ = path_limits(options)
    model = build_cost_model(options)
    results = []

    for name, groups in cases.items():
        started = perf_counter()
        baseline = build_execution_paths(
            groups,
            enabled=True,
            max_rows_per_path=rows,
            max_points_per_path=points,
        )
        baseline_ms = (perf_counter() - started) * 1000.0

        started = perf_counter()
        candidate, extra_meta = build_fast_paths(groups, options)
        candidate_ms = (perf_counter() - started) * 1000.0

        source = [_source_paths(group) for group in groups]
        exact_raw = all(
            raster(source_group) == raster(base_group) == raster(candidate_group)
            for source_group, base_group, candidate_group in zip(source, baseline, candidate)
        )
        if not exact_raw:
            raise AssertionError(f'{name}: raw planner raster mismatch')

        baseline_metrics_raw = execution_metrics(baseline, model)
        candidate_metrics_raw = execution_metrics(candidate, model)

        ordered_baseline, baseline_optimizer = _optimize(baseline)
        ordered_candidate, candidate_optimizer = _optimize(candidate)
        exact_ordered = all(
            raster(source_group) == raster(base_group) == raster(candidate_group)
            for source_group, base_group, candidate_group in zip(source, ordered_baseline, ordered_candidate)
        )
        if not exact_ordered:
            raise AssertionError(f'{name}: ordered planner raster mismatch')

        baseline_metrics_ordered = execution_metrics(ordered_baseline, model)
        candidate_metrics_ordered = execution_metrics(ordered_candidate, model)

        results.append({
            'case': name,
            'exact_source_raster': True,
            'baseline_planning_ms': round(baseline_ms, 3),
            'candidate_planning_ms': round(candidate_ms, 3),
            'baseline_raw': baseline_metrics_raw,
            'candidate_raw': candidate_metrics_raw,
            'baseline_ordered': baseline_metrics_ordered,
            'candidate_ordered': candidate_metrics_ordered,
            'baseline_optimizer': baseline_optimizer,
            'candidate_optimizer': candidate_optimizer,
            'intrinsic_before_seconds': extra_meta['intrinsic_cost_before_seconds'],
            'intrinsic_after_seconds': extra_meta['intrinsic_cost_after_seconds'],
            'ordered_modeled_seconds_delta': round(
                candidate_metrics_ordered['modeled_total_seconds']
                - baseline_metrics_ordered['modeled_total_seconds'],
                6,
            ),
            'ordered_travel_px_delta': round(
                candidate_metrics_ordered['travel_px']
                - baseline_metrics_ordered['travel_px'],
                6,
            ),
        })

    return {
        'schema': 2,
        'benchmark': 'extra-fast-travel-telemetry',
        'version': APP_VERSION,
        'commit_sha': os.environ.get('GITHUB_SHA') or None,
        'platform': {
            'system': platform.system(),
            'release': platform.release(),
            'machine': platform.machine(),
            'python': platform.python_version(),
        },
        'cost_model': model.as_dict(),
        'ordering': {
            'optimizer': 'StrokeOptimizer Smart merge',
            'speed': 'Balanced',
            'semantic_scope': 'within color groups; no cross-color reorder in benchmark',
        },
        'scope': (
            'Synthetic source raster, width 1. Planning timings are single-run smoke metrics. '
            'Modeled execution includes path boundaries, draw distance, pen-up travel and '
            'color-selection cost; it is not measured target-application wall-clock speed.'
        ),
        'cases': results,
    }


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
