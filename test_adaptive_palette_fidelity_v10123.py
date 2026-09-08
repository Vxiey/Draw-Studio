import unittest

from AdaptivePaletteFidelity import adaptive_palette_cap, select_adaptive_palette
from RealSpeedBudget import recommend_budget, reduce_palette_groups
from GarticPhoneFastRenderer import optimize_gartic_phone_groups


class AdaptivePaletteFidelity123Tests(unittest.TestCase):
    def _complex_palette(self):
        # Five luminance levels across several hue families, representative of
        # a rich game palette rather than the previous red/orange-heavy 6-colour case.
        return [
            (10,10,10),(45,35,30),(80,70,60),(125,115,105),(185,175,165),(240,235,225),
            (95,25,18),(145,45,25),(205,75,25),(245,125,25),(255,190,55),
            (65,55,25),(115,95,35),(175,145,45),(225,195,85),
            (25,55,80),(40,90,125),(75,135,165),(130,185,205),
            (55,25,75),(95,45,115),(145,80,155),(195,130,195),
            (40,80,45),(70,125,70),(120,175,110),(175,220,165),
            (85,55,40),(130,85,55),(180,125,80),(225,175,125),
        ]

    def _groups(self, palette):
        groups=[]
        for i,_ in enumerate(palette):
            # Spread colours around the canvas and vary mass so spatial + tone
            # anchors have meaningful work to do.
            y=i%15; x=(i*17)%90; length=6+(i%7)*3
            groups.append([(x,y,x+length,y)])
        return groups

    def test_faithful_60_second_cap_is_not_old_six_color_limit(self):
        self.assertGreaterEqual(adaptive_palette_cap(60,'Faithful',profile_key='gartic-phone'),22)
        self.assertLessEqual(adaptive_palette_cap(60,'Fast',profile_key='gartic-phone'),6)

    def test_real_speed_policy_receives_faithful_palette_capacity(self, tmp_path=None):
        # No persisted sample needed: fallback throughput still must not force
        # Faithful back to 6 colours.
        rec=recommend_budget('gartic-phone',60,color_fidelity='Faithful')
        self.assertGreaterEqual(rec.max_colors,22)

    def test_adaptive_selector_preserves_tone_ladder_and_uses_more_than_six(self):
        palette=self._complex_palette();groups=self._groups(palette)
        keep,mapping,meta=select_adaptive_palette(groups,palette,28,fidelity='Faithful')
        self.assertGreater(len(keep),6)
        self.assertGreaterEqual(meta['tone_bins_after'],4)
        self.assertFalse(meta['midtone_loss'])
        self.assertGreater(meta['palette_coverage_percent'],0)
        self.assertEqual(set(mapping),set(range(len(palette))))

    def test_reducer_reports_anti_posterization_diagnostics(self):
        palette=self._complex_palette();groups=self._groups(palette)
        out,meta=reduce_palette_groups(groups,palette,28,color_fidelity='Faithful')
        self.assertTrue(meta['anti_posterization'])
        self.assertIn(meta['posterization_risk'],('LOW','MEDIUM','HIGH'))
        self.assertIn('palette_coverage_percent',meta)
        self.assertIn('p95_reduction_delta_e2000',meta)
        self.assertGreater(sum(bool(g) for g in out),6)

    def test_gartic_optimizer_exposes_palette_quality(self):
        palette=self._complex_palette();groups=self._groups(palette)
        out,meta=optimize_gartic_phone_groups(groups,palette,max_colors=28,min_run=1,color_fidelity='Faithful')
        self.assertTrue(meta['anti_posterization'])
        self.assertGreater(meta['active_colors_after'],6)
        self.assertIn('palette_coverage_percent',meta)
        self.assertIn('posterization_risk',meta)
        self.assertFalse(meta['midtone_loss'])
        self.assertEqual(sum(bool(g) for g in out),meta['active_colors_after'])


if __name__=='__main__':
    unittest.main()
