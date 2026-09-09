import unittest

from ContinuousPaths import build_execution_paths
from RasterIdentity import (
    canonical_pixels_from_runs,
    compare_grouped_runs_to_paths,
    compare_runs_to_paths,
    rasterize_segment,
)


def _paths_for_runs(runs):
    return [[(a, b), (c, d)] if (a, b) != (c, d) else [(a, b)] for a, b, c, d in runs]


class RasterIdentityTests(unittest.TestCase):
    def test_integer_rasterization_is_endpoint_inclusive_and_reversible(self):
        cases = [
            (0, 0, 5, 0),
            (2, -3, 2, 4),
            (0, 0, 5, 5),
            (5, 1, 0, 4),
        ]
        for segment in cases:
            pixels = rasterize_segment(segment)
            self.assertEqual(pixels[0], (segment[0], segment[1]))
            self.assertEqual(pixels[-1], (segment[2], segment[3]))
            reverse = (segment[2], segment[3], segment[0], segment[1])
            self.assertEqual(set(pixels), set(rasterize_segment(reverse)))

    def test_exact_axis_paths_report_zero_difference(self):
        source = [(0, 0, 5, 0), (2, 0, 2, 4), (-2, -1, -2, -1)]
        report = compare_runs_to_paths(source, _paths_for_runs(source))
        self.assertTrue(report.safe, report.as_dict())
        self.assertEqual(report.raster_difference_pixels, 0)
        self.assertEqual(report.missing_pixels, frozenset())
        self.assertEqual(report.extra_pixels, frozenset())

    def test_missing_pixels_are_reported(self):
        source = [(0, 0, 5, 0)]
        report = compare_runs_to_paths(source, [[(0, 0), (3, 0)]])
        self.assertFalse(report.safe)
        self.assertEqual(report.missing_pixels, frozenset({(4, 0), (5, 0)}))
        self.assertEqual(report.raster_difference_pixels, 2)

    def test_axis_connector_outside_source_is_reported_with_origin(self):
        source = [(0, 0, 2, 0), (0, 2, 2, 2)]
        report = compare_runs_to_paths(source, [[(0, 0), (2, 0), (2, 2), (0, 2)]])
        self.assertFalse(report.safe)
        self.assertIn((2, 1), report.extra_pixels)
        self.assertIsNotNone(report.first_error)
        self.assertEqual(report.first_error.path_index, 0)
        self.assertEqual(report.first_error.segment_index, 1)
        self.assertEqual(report.first_error.reason, 'segment_leaves_source_raster')

    def test_new_diagonal_is_rejected_even_when_every_pixel_is_source(self):
        source = [(0, 0, 2, 0), (0, 1, 2, 1)]
        candidate = [[(0, 0), (2, 0), (1, 1), (0, 1), (2, 1)]]
        report = compare_runs_to_paths(source, candidate)
        self.assertTrue(report.exact_raster, report.as_dict())
        self.assertFalse(report.safe)
        self.assertTrue(any(i.reason == 'new_diagonal_segment' for i in report.unsafe_segments))

    def test_passthrough_source_diagonal_is_allowed(self):
        source = [(0, 0, 6, 4)]
        for path in ([[(0, 0), (6, 4)]], [[(6, 4), (0, 0)]]):
            report = compare_runs_to_paths(source, path)
            self.assertTrue(report.safe, report.as_dict())

    def test_continuous_planner_hollow_rectangle_is_lossless(self):
        source = [(2, 2, 20, 2), (2, 20, 20, 20), (2, 3, 2, 19), (20, 3, 20, 19)]
        paths = build_execution_paths([source], enabled=True)[0]
        report = compare_runs_to_paths(source, paths)
        self.assertTrue(report.safe, report.as_dict())

    def test_touching_corners_do_not_gain_cross_gap_connector(self):
        source = [(0, 0, 0, 0), (1, 1, 1, 1)]
        paths = build_execution_paths([source], enabled=True)[0]
        report = compare_runs_to_paths(source, paths)
        self.assertTrue(report.safe, report.as_dict())
        self.assertEqual(len(paths), 2)

    def test_grouped_colors_are_verified_independently(self):
        groups = [
            [(0, y, 4, y) for y in range(3)],
            [(10, y, 12, y) for y in range(3)],
        ]
        execution = build_execution_paths(groups, enabled=True)
        reports = compare_grouped_runs_to_paths(groups, execution)
        self.assertEqual(len(reports), 2)
        self.assertTrue(all(report.safe for report in reports))
        self.assertNotEqual(canonical_pixels_from_runs(groups[0]), canonical_pixels_from_runs(groups[1]))

    def test_group_count_mismatch_is_rejected(self):
        with self.assertRaises(ValueError):
            compare_grouped_runs_to_paths([[(0, 0, 1, 0)]], [])


if __name__ == '__main__':
    unittest.main()
