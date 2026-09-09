import math
import unittest

from HybridCostModel import MODEL_VERSION, build_cost_model


def opts(**kw):
    out = dict(
        profile_key='microsoft-paint',
        profile_name='Microsoft Paint',
        speed='Balanced',
        precision='High',
        brush_px=1,
        delay=.006,
        paint_tool='Pencil',
        effective_paint_tool='Pencil',
        custom_color_workflow='calibrated-palette',
        use_region_fill_engine=False,
    )
    out.update(kw)
    return out


def calibration(*, samples=0, ratio=1.0, mape=None, runtime=None, seconds_per_path=None):
    return {
        'learned': bool(samples),
        'samples': samples,
        'ratio': ratio,
        'mape': mape,
        'operation_runtime': dict(runtime or {}),
        'seconds_per_completed_path': seconds_per_path,
    }


class HybridCostModelV2Tests(unittest.TestCase):
    def test_cold_start_keeps_conservative_v2_defaults(self):
        model = build_cost_model(opts(_hybrid_cost_calibration_override=calibration()))
        self.assertEqual(model.model_version, MODEL_VERSION)
        self.assertEqual(model.source, 'conservative-default')
        self.assertEqual(model.samples, 0)
        self.assertFalse(model.calibrated)
        self.assertEqual(model.calibration_confidence, 0.0)
        self.assertEqual(model.correction_ratio, 1.0)
        self.assertEqual(model.effective_correction_ratio, 1.0)
        self.assertEqual(model.uncertainty_multiplier, 1.0)
        self.assertGreater(model.path_fixed_seconds, 0.0)
        self.assertGreater(model.draw_seconds_per_px, 0.0)

    def test_more_clean_samples_raise_calibration_confidence(self):
        low = build_cost_model(opts(_hybrid_cost_calibration_override=calibration(samples=1, ratio=1.4, mape=.08)))
        high = build_cost_model(opts(_hybrid_cost_calibration_override=calibration(samples=20, ratio=1.4, mape=.08)))
        self.assertGreater(high.calibration_confidence, low.calibration_confidence)
        self.assertGreater(high.effective_correction_ratio, low.effective_correction_ratio)
        self.assertLessEqual(high.effective_correction_ratio, high.correction_ratio + 1e-9)
        self.assertEqual(high.source, 'calibrated-profile-v2')

    def test_high_historical_error_reduces_confidence(self):
        clean = build_cost_model(opts(_hybrid_cost_calibration_override=calibration(samples=12, ratio=1.2, mape=.05)))
        noisy = build_cost_model(opts(_hybrid_cost_calibration_override=calibration(samples=12, ratio=1.2, mape=1.2)))
        self.assertGreater(clean.calibration_confidence, noisy.calibration_confidence)
        self.assertLess(clean.uncertainty_multiplier, noisy.uncertainty_multiplier)

    def test_typed_point_measurement_remains_atomic_lower_bound(self):
        measured = 2.0
        model = build_cost_model(opts(_hybrid_cost_calibration_override=calibration(
            samples=3,
            ratio=1.0,
            mape=None,
            runtime={'dot': {'average_seconds': measured}},
        )))
        self.assertLess(model.calibration_confidence, 1.0)
        self.assertGreaterEqual(model.point_seconds, measured)
        self.assertGreaterEqual(model.path_seconds(((0, 0),)), measured)

    def test_single_noisy_operation_sample_does_not_replace_defaults(self):
        cold = build_cost_model(opts(_hybrid_cost_calibration_override=calibration()))
        measured = 3.0
        one = build_cost_model(opts(_hybrid_cost_calibration_override=calibration(
            samples=1,
            ratio=1.0,
            mape=.2,
            runtime={'color_change': {'average_seconds': measured, 'count': 1, 'total_seconds': measured}},
        )))
        self.assertNotAlmostEqual(one.color_change_seconds, measured, places=6)
        self.assertGreater(one.color_change_seconds, cold.color_change_seconds)
        self.assertLess(one.color_change_seconds, measured)

    def test_repeated_clean_operation_samples_move_toward_measurement(self):
        measured = .45
        low = build_cost_model(opts(_hybrid_cost_calibration_override=calibration(
            samples=1,
            ratio=1.0,
            mape=.05,
            runtime={'tool_change': {'average_seconds': measured, 'count': 1, 'total_seconds': measured}},
        )))
        high = build_cost_model(opts(_hybrid_cost_calibration_override=calibration(
            samples=30,
            ratio=1.0,
            mape=.05,
            runtime={'tool_change': {'average_seconds': measured, 'count': 30, 'total_seconds': measured * 30}},
        )))
        self.assertLess(abs(high.tool_change_seconds - measured), abs(low.tool_change_seconds - measured))

    def test_completed_path_floor_is_confidence_weighted(self):
        low = build_cost_model(opts(_hybrid_cost_calibration_override=calibration(
            samples=1, ratio=1.0, mape=.1, seconds_per_path=.4)))
        high = build_cost_model(opts(_hybrid_cost_calibration_override=calibration(
            samples=30, ratio=1.0, mape=.1, seconds_per_path=.4)))
        self.assertGreaterEqual(high.learned_path_floor_seconds, low.learned_path_floor_seconds)
        self.assertGreaterEqual(low.learned_path_floor_seconds, 0.0)

    def test_operation_breakdown_matches_shared_total(self):
        model = build_cost_model(opts(_hybrid_cost_calibration_override=calibration()))
        paths = [((0, 0), (10, 0)), ((20, 0), (20, 10))]
        total = model.operation_seconds(
            paths,
            color_changes=2,
            tool_changes=1,
            brush_changes=1,
            fill_actions=3,
            verification_actions=2,
        )
        breakdown = model.execution_breakdown(
            paths,
            color_changes=2,
            tool_changes=1,
            brush_changes=1,
            fill_actions=3,
            verification_actions=2,
        )
        self.assertAlmostEqual(total, breakdown['total_seconds'], places=9)
        self.assertEqual(breakdown['model_version'], MODEL_VERSION)
        self.assertGreaterEqual(breakdown['risk_adjusted_seconds'], breakdown['total_seconds'])

    def test_risk_adjustment_is_separate_from_base_geometry_cost(self):
        model = build_cost_model(opts(_hybrid_cost_calibration_override=calibration(samples=3, ratio=1.2, mape=.6)))
        path = ((0, 0), (100, 0))
        base = model.path_seconds(path)
        self.assertGreaterEqual(model.risk_adjusted_seconds(base), base)
        self.assertAlmostEqual(model.path_seconds(path), base, places=12)

    def test_risk_adjustment_rejects_invalid_seconds(self):
        model = build_cost_model(opts(_hybrid_cost_calibration_override=calibration()))
        for value in (-1.0, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                model.risk_adjusted_seconds(value)

    def test_invalid_calibration_values_are_safely_bounded(self):
        model = build_cost_model(opts(_hybrid_cost_calibration_override={
            'samples': 'bad',
            'ratio': float('inf'),
            'mape': -3,
            'operation_runtime': {'travel': {'average_seconds': float('nan')}},
        }))
        self.assertEqual(model.samples, 0)
        self.assertEqual(model.calibration_confidence, 0.0)
        self.assertTrue(math.isfinite(model.travel_seconds_per_px))
        self.assertTrue(math.isfinite(model.draw_seconds_per_px))
        self.assertGreater(model.travel_seconds_per_px, 0.0)

    def test_as_dict_exposes_version_confidence_ratio_and_uncertainty(self):
        model = build_cost_model(opts(_hybrid_cost_calibration_override=calibration(samples=8, ratio=1.3, mape=.12)))
        data = model.as_dict()
        for key in (
            'model_version', 'calibration_confidence', 'calibration_mape',
            'correction_ratio', 'effective_correction_ratio',
            'uncertainty_multiplier', 'calibrated', 'high_confidence',
        ):
            self.assertIn(key, data)
        self.assertEqual(data['model_version'], MODEL_VERSION)
        self.assertTrue(data['calibrated'])


if __name__ == '__main__':
    unittest.main()
