import unittest

from ExecutionTelemetry import draw_distance_px, execution_metrics, flatten_groups, pen_up_distance_px
from HybridCostModel import HybridCostModel


def model(**kw):
    values = dict(
        profile_key='test',
        source='unit',
        samples=0,
        travel_seconds_per_px=0.1,
        draw_seconds_per_px=0.2,
        path_fixed_seconds=1.0,
        point_seconds=0.5,
        color_change_seconds=2.0,
        tool_change_seconds=3.0,
        brush_change_seconds=4.0,
        fill_action_seconds=5.0,
        verification_seconds=6.0,
        learned_path_floor_seconds=0.0,
        scale_x=1.0,
        scale_y=1.0,
    )
    values.update(kw)
    return HybridCostModel(**values)


class ExecutionTelemetryTests(unittest.TestCase):
    def test_draw_and_pen_up_distance_are_separate(self):
        paths = [((0, 0), (3, 0)), ((6, 0), (6, 4))]
        self.assertEqual(draw_distance_px(paths), 7.0)
        self.assertEqual(pen_up_distance_px(paths), 3.0)

    def test_initial_cursor_is_counted_when_supplied(self):
        paths = [((3, 4), (6, 4))]
        self.assertEqual(pen_up_distance_px(paths), 0.0)
        self.assertEqual(pen_up_distance_px(paths, cursor=(0, 0)), 5.0)

    def test_execution_metrics_include_cross_group_travel_and_color_cost(self):
        groups = [
            [((0, 0), (3, 0))],
            [((6, 0), (6, 4))],
        ]
        out = execution_metrics(groups, model())
        self.assertEqual(out['path_count'], 2)
        self.assertEqual(out['path_boundaries'], 2)
        self.assertEqual(out['draw_px'], 7.0)
        self.assertEqual(out['travel_px'], 3.0)
        self.assertEqual(out['color_change_count'], 2)
        self.assertEqual(out['modeled_color_seconds'], 4.0)
        self.assertAlmostEqual(out['modeled_path_seconds'], 3.7, places=6)
        self.assertAlmostEqual(out['modeled_total_seconds'], 7.7, places=6)
        self.assertAlmostEqual(out['modeled_risk_adjusted_seconds'], 7.7, places=6)
        self.assertEqual(out['cost_model_version'], 2)
        self.assertEqual(out['cost_model_confidence'], 0.0)
        self.assertEqual(out['cost_model_uncertainty_multiplier'], 1.0)

    def test_v2_uncertainty_is_reported_without_changing_base_total(self):
        groups = [[((0, 0), (10, 0)), ((30, 0), (40, 0))]]
        m = model(
            samples=3,
            calibration_confidence=.25,
            uncertainty_multiplier=1.3,
        )
        out = execution_metrics(groups, m)
        self.assertEqual(out['cost_model_version'], 2)
        self.assertEqual(out['cost_model_confidence'], .25)
        self.assertEqual(out['cost_model_uncertainty_multiplier'], 1.3)
        self.assertGreater(out['modeled_risk_adjusted_seconds'], out['modeled_total_seconds'])
        self.assertAlmostEqual(
            out['modeled_risk_adjusted_seconds'],
            out['modeled_total_seconds'] * 1.3,
            places=6,
        )

    def test_legacy_model_without_v2_fields_remains_supported(self):
        class LegacyModel:
            scale_x = 1.0
            scale_y = 1.0
            color_change_seconds = 2.0
            def path_seconds(self, path, *, cursor=None):
                return 1.0

        out = execution_metrics([[((0, 0), (1, 0))]], LegacyModel())
        self.assertEqual(out['cost_model_version'], 1)
        self.assertEqual(out['cost_model_confidence'], 0.0)
        self.assertEqual(out['cost_model_uncertainty_multiplier'], 1.0)
        self.assertEqual(out['modeled_risk_adjusted_seconds'], out['modeled_total_seconds'])

    def test_color_order_changes_travel_without_changing_draw_distance(self):
        groups = [
            [((100, 0), (110, 0))],
            [((0, 0), (10, 0))],
            [((20, 0), (30, 0))],
        ]
        a = execution_metrics(groups, model(), color_order=[0, 1, 2])
        b = execution_metrics(groups, model(), color_order=[1, 2, 0])
        self.assertEqual(a['draw_px'], b['draw_px'])
        self.assertNotEqual(a['travel_px'], b['travel_px'])

    def test_flatten_groups_preserves_requested_color_order_then_missing_groups(self):
        groups = [
            [((0, 0),)],
            [((1, 0),)],
            [((2, 0),)],
        ]
        out = flatten_groups(groups, [2, 0])
        self.assertEqual(out, [((2, 0),), ((0, 0),), ((1, 0),)])


if __name__ == '__main__':
    unittest.main()
