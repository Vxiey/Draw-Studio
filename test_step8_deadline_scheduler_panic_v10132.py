import unittest

from DeadlineScheduler import DeadlineScheduler, NORMAL, CATCH_UP, PANIC


class Step8DeadlineSchedulerTests(unittest.TestCase):
    def test_slow_measured_runtime_reprojects_remaining_work(self):
        now = [0.0]
        seq = [
            {'estimated_cost_seconds': 1.0, 'deadline_phase': 'major_coverage', 'importance': .95, 'structural_score': .9, 'operation_type':'long_stroke'},
            {'estimated_cost_seconds': 1.0, 'deadline_phase': 'structure', 'importance': .9, 'structural_score': .8, 'operation_type':'long_stroke'},
            {'estimated_cost_seconds': 1.0, 'deadline_phase': 'important_details', 'importance': .85, 'structural_score': .1, 'operation_type':'long_stroke'},
        ]
        sched = DeadlineScheduler(seq, start_time=0.0, budget_seconds=5.0, clock=lambda: now[0])
        first = sched.before(seq[0])
        self.assertTrue(first.execute)
        now[0] = 2.0  # first 1s-estimated path really took 2s
        sched.after(seq[0])
        telem = sched.telemetry()
        self.assertGreater(telem['runtime_cost_multiplier'], 1.5)
        self.assertGreater(telem['predicted_remaining_seconds'], 2.5)
        decision = sched.before(seq[1])
        self.assertIn(decision.mode, (CATCH_UP, PANIC))

    def test_fast_runtime_can_recover_from_catchup(self):
        now = [0.0]
        seq = [
            {'estimated_cost_seconds': 4.5, 'deadline_phase': 'major_coverage', 'importance': .95, 'structural_score': .9},
            {'estimated_cost_seconds': 4.5, 'deadline_phase': 'structure', 'importance': .9, 'structural_score': .9},
        ]
        sched = DeadlineScheduler(seq, start_time=0.0, budget_seconds=10.0, clock=lambda: now[0])
        self.assertEqual(sched.before(seq[0]).mode, CATCH_UP)
        now[0] = 1.0
        sched.after(seq[0])
        # Remaining 4.5 estimated seconds are now projected with the fast live rate.
        d2 = sched.before(seq[1])
        self.assertEqual(d2.mode, NORMAL)
        self.assertEqual(sched.telemetry()['recovered_from_catchup'], 1)

    def test_panic_is_structure_first_and_drops_cleanup(self):
        now = [2.0]
        structure = {'estimated_cost_seconds': 2.0, 'deadline_phase': 'structure', 'importance': .9, 'structural_score': .9}
        cleanup = {'estimated_cost_seconds': 4.0, 'deadline_phase': 'correction', 'importance': .2, 'structural_score': 0, 'optional': True}
        sched = DeadlineScheduler([structure, cleanup], start_time=0.0, budget_seconds=5.0, clock=lambda: now[0])
        d1 = sched.before(structure)
        self.assertTrue(d1.execute)
        self.assertEqual(d1.mode, PANIC)
        now[0] = 3.0
        sched.after(structure)
        d2 = sched.before(cleanup)
        self.assertFalse(d2.execute)
        self.assertTrue(d2.panic)
        self.assertIn('dropped', d2.reason)

    def test_panic_can_keep_exceptionally_important_small_detail_after_structure(self):
        now = [0.0]
        structure = {'estimated_cost_seconds': .4, 'deadline_phase': 'structure', 'importance': .95, 'structural_score': .95}
        detail = {'estimated_cost_seconds': .2, 'deadline_phase': 'important_details', 'importance': .96, 'structural_score': .05}
        cleanup = {'estimated_cost_seconds': 3.0, 'deadline_phase': 'correction', 'importance': .1, 'structural_score': 0, 'optional': True}
        sched = DeadlineScheduler([structure, detail, cleanup], start_time=0.0, budget_seconds=2.5, clock=lambda: now[0])
        # Force panic because total planned work does not fit.
        d1 = sched.before(structure)
        self.assertEqual(d1.mode, PANIC)
        now[0] = .25
        sched.after(structure)
        self.assertGreaterEqual(sched.structural_coverage(), .99)
        d2 = sched.before(detail)
        self.assertTrue(d2.execute)

    def test_hard_render_guard_drops_remaining_work(self):
        now = [9.85]
        entry = {'estimated_cost_seconds': .1, 'deadline_phase': 'major_coverage', 'importance': 1.0, 'structural_score': 1.0}
        sched = DeadlineScheduler([entry], start_time=0.0, budget_seconds=10.0, clock=lambda: now[0])
        d = sched.before(entry)
        self.assertFalse(d.execute)
        self.assertEqual(d.mode, PANIC)
        self.assertIn('hard render budget', d.reason)

    def test_telemetry_exposes_live_strategy_and_phase_counts(self):
        now = [0.0]
        entry = {'estimated_cost_seconds': .5, 'deadline_phase': 'major_coverage', 'importance': .9, 'structural_score': .9, 'operation_type':'outline'}
        sched = DeadlineScheduler([entry], start_time=0.0, budget_seconds=5.0, clock=lambda: now[0])
        self.assertTrue(sched.before(entry).execute)
        now[0] = .6
        sched.after(entry)
        t = sched.telemetry()
        self.assertIn('runtime_cost_multiplier', t)
        self.assertIn('runtime_samples', t)
        self.assertIn('strategy', t)
        self.assertEqual(t['phase_executed'].get('major_coverage'), 1)
        meta = sched.meta()
        self.assertIn('live measured execution EMA', meta['runtime_prediction_source'])

    def test_unlimited_mode_never_enters_panic(self):
        now = [100.0]
        entry = {'estimated_cost_seconds': 999.0, 'deadline_phase':'correction', 'importance':.1, 'optional':True}
        sched = DeadlineScheduler([entry], start_time=0.0, budget_seconds=None, clock=lambda: now[0])
        d = sched.before(entry)
        self.assertTrue(d.execute)
        self.assertEqual(d.mode, NORMAL)


if __name__ == '__main__':
    unittest.main()
