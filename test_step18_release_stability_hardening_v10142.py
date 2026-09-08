import time
import unittest
from pathlib import Path

from ReleaseStabilityHardening import (
    EventCoalescer,
    PreviewAttemptGuard,
    ProgressThrottle,
    apply_preview_memory_limits,
    classify_preview_timeout,
    estimate_preview_working_set_mb,
    merge_stability_meta,
)


class Step18ReleaseStabilityHardeningTests(unittest.TestCase):
    def test_preview_memory_guard_reduces_only_when_estimate_exceeds_budget(self):
        low = apply_preview_memory_limits(900_000, 1300, memory_budget_mb=220)
        self.assertTrue(low.reduced)
        self.assertLess(low.resolved_pixels, low.requested_pixels)
        self.assertGreaterEqual(low.resolved_pixels, 120_000)
        high = apply_preview_memory_limits(240_000, 680, memory_budget_mb=2048)
        self.assertFalse(high.reduced)
        self.assertEqual(high.resolved_pixels, 240_000)
        self.assertGreater(estimate_preview_working_set_mb(900_000), estimate_preview_working_set_mb(240_000))

    def test_preview_attempt_guard_times_out_and_exposes_metadata(self):
        now = [100.0]
        guard = PreviewAttemptGuard(timeout_seconds=1.0, clock=lambda: now[0], label='preview')
        self.assertFalse(guard.cancelled())
        now[0] = 101.01
        self.assertTrue(guard.cancelled())
        self.assertTrue(guard.meta()['timed_out'])
        self.assertGreaterEqual(guard.meta()['checks'], 2)

    def test_preview_attempt_guard_user_cancel_distinct_from_timeout(self):
        guard = PreviewAttemptGuard(timeout_seconds=10.0, external_cancelled=lambda: True, label='preview')
        self.assertTrue(guard.cancelled())
        meta = guard.meta()
        self.assertTrue(meta['cancelled_by_user'])
        self.assertFalse(meta['timed_out'])

    def test_event_coalescer_bounds_noisy_status_progress_events(self):
        q = EventCoalescer(max_events=5)
        for i in range(50):
            q.push('status', f'status {i}')
            q.push('progress', (i, 50))
        q.push('done', 'preview')
        events = q.drain()
        kinds = [e[0] for e in events]
        self.assertLessEqual(len(events), 5)
        self.assertEqual(kinds.count('status'), 1)
        self.assertEqual(kinds.count('progress'), 1)
        self.assertIn(('done', 'preview'), events)
        self.assertGreater(q.stats()['coalesced'], 0)

    def test_progress_throttle_prevents_event_storm_but_allows_completion(self):
        now = [0.0]
        throttle = ProgressThrottle(min_interval_seconds=0.5, min_delta_percent=5.0, clock=lambda: now[0])
        self.assertTrue(throttle.should_emit(0, 100))
        self.assertFalse(throttle.should_emit(1, 100))
        now[0] = 0.6
        self.assertFalse(throttle.should_emit(2, 100))
        self.assertTrue(throttle.should_emit(100, 100))

    def test_timeout_classifier_and_meta_are_safe(self):
        near = classify_preview_timeout(8.8, timeout_seconds=10.0)
        self.assertEqual(near['state'], 'near-timeout')
        primary = classify_preview_timeout(10.1, timeout_seconds=10.0)
        self.assertEqual(primary['recommended_action'], 'retry fast fallback')
        fallback = classify_preview_timeout(6.2, timeout_seconds=6.0, fallback_used=True)
        self.assertEqual(fallback['state'], 'fallback-timeout')
        opts = {}
        meta = merge_stability_meta(opts, preview_timeout=fallback)
        self.assertFalse(meta['mouse_input'])
        self.assertFalse(meta['stores_image_data'])
        self.assertIn('release_stability_meta', opts)


    def test_preview_diagnostics_show_release_stability_status(self):
        from PreviewDiagnostics import build_preview_diagnostics, format_preview_diagnostics
        opts = {'release_stability_meta': {
            'preview_memory_limits': {'reduced': True},
            'preview_attempt': {'timeout_seconds': 14.0},
            'preview_timeout': {'state': 'primary-timeout'},
        }}
        text = format_preview_diagnostics(build_preview_diagnostics(opts))
        self.assertIn('Release stability:', text)
        self.assertIn('preview memory reduced', text)
        self.assertIn('watchdog 14s', text)

    def test_release_build_collects_step18_module_and_doc(self):
        source = Path('build_exe.py').read_text(encoding='utf-8')
        self.assertIn("'--hidden-import', 'ReleaseStabilityHardening'", source)
        self.assertIn('STEP-18-RELEASE-STABILITY-HARDENING.md', source)
        self.assertTrue(Path('STEP-18-RELEASE-STABILITY-HARDENING.md').is_file())


if __name__ == '__main__':
    unittest.main()
