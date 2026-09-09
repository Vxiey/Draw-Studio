import unittest

from benchmark_extra_fast import run


class ExtraFastTravelTelemetryBenchmarkTests(unittest.TestCase):
    def test_benchmark_reports_complete_ordered_telemetry_without_claiming_wall_clock(self):
        report = run()
        self.assertEqual(report['schema'], 2)
        self.assertEqual(report['benchmark'], 'extra-fast-travel-telemetry')
        self.assertIn('not measured target-application wall-clock speed', report['scope'])
        self.assertEqual(len(report['cases']), 6)
        for row in report['cases']:
            self.assertTrue(row['exact_source_raster'])
            for key in ('baseline_raw', 'candidate_raw', 'baseline_ordered', 'candidate_ordered'):
                metrics = row[key]
                self.assertIn('travel_px', metrics)
                self.assertIn('draw_px', metrics)
                self.assertIn('path_boundaries', metrics)
                self.assertIn('modeled_total_seconds', metrics)
                self.assertGreaterEqual(metrics['travel_px'], 0.0)
                self.assertGreaterEqual(metrics['draw_px'], 0.0)
                self.assertGreaterEqual(metrics['modeled_total_seconds'], 0.0)
            self.assertIn('optimizer_pen_up_before', row['baseline_optimizer'])
            self.assertIn('optimizer_pen_up_after', row['baseline_optimizer'])
            self.assertIn('ordered_travel_px_delta', row)
            self.assertIn('ordered_modeled_seconds_delta', row)


if __name__ == '__main__':
    unittest.main()
