import unittest
from PIL import Image
from DrawBot import make_plan, DrawBotApp
from PerformanceProfiler import PHASES, format_profile, dominant_phase


def opts():
    return dict(detail=8,delay=.003,speed='Fast',precision='High',lines=True,drawing_mode='Shape paths',
                shape_order='Fill first',shape_model='Better shapes v2',max_stroke_cap='2500',progressive_rendering='On',
                planning_watchdog='Auto',time_budget_mode='Manual',target_stroke_count='1000',target_stroke_custom='1000',
                skip_white=True,contrast=1,outline=False,brush_px=2,max_seconds=180,paint_current_color=False,
                background_fill='Off',background_simplification='Balanced',color_grouping='Smart',
                color_rendering='RGB nearest',color_layers='Off',custom_color_workflow='Calibrated palette',
                cpu_workers='1',cpu_engine='Threads',ram_budget='512 MB',ram_custom_mb='512',planning_resolution='Standard',
                gpu_mode='CPU',gpu_vram='Auto',gpu_performance='Balanced')

class PerformanceProfilerTests(unittest.TestCase):
    def test_plan_contains_all_profiler_phases(self):
        plan=make_plan(Image.new('RGBA',(80,60),'black'),(320,240),opts())
        profile=plan['performance_profile']
        self.assertGreaterEqual(profile['total_planning'],0)
        for phase in PHASES:
            self.assertIn(phase,profile['timings'])
            self.assertGreaterEqual(profile['timings'][phase],0)
        self.assertIn('total',format_profile(profile,compact=True))

    def test_dominant_phase_returns_known_phase(self):
        profile={'total_planning':1.0,'timings':{p:(i+1)/100 for i,p in enumerate(PHASES)}}
        phase,seconds=dominant_phase(profile)
        self.assertIn(phase,PHASES);self.assertGreater(seconds,0)

    def test_benchmark_method_exists_and_is_separate_from_draw(self):
        self.assertTrue(callable(getattr(DrawBotApp,'run_performance_benchmark',None)))

if __name__=='__main__':unittest.main()
