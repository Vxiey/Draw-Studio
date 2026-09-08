import unittest
from pathlib import Path

from ProfileEngine import (PROFILE_ENGINE_MODES, policy_for, policy_summary,
                           resolve_profile_policy, validate_profile_engine)
from Version import APP_VERSION, FILE_VERSION


BASE={
    'mode':'Smart paths (recommended)','shape_order':'Fill first','shape_model':'Auto','max_stroke_cap':'Auto',
    'progressive_rendering':'Auto','planning_watchdog':'Auto','time_budget_mode':'Manual','target_stroke_count':'Auto','target_stroke_custom':'2500',
    'render_style':'Auto','draw_quality':'High likeness','quality':'Balanced','speed':'Balanced','precision':'High',
    'planning_resolution':'High','resource_scheduler':'Auto','background_fill':'Conservative','fill_engine':'Auto','background_simplification':'Balanced',
    'color_grouping':'Smart','color_workflow':'Finish color first','stroke_optimizer':'Auto','adaptive_detail':'Auto','visual_verification':'Auto',
    'color_rendering':'Perceptual match','color_layers':'Off','custom_color_workflow':'Adaptive exact (recommended)','exact_color_limit':'Auto','tool_strategy':'Auto','edge_behavior':'Auto',
}

class ProfileEngineV1045Tests(unittest.TestCase):
    def test_modes_validate(self):
        for value in PROFILE_ENGINE_MODES:
            self.assertEqual(validate_profile_engine(value),value)
        with self.assertRaises(ValueError):validate_profile_engine('Force')

    def test_paint_policy_quality_fill_exact_and_verification(self):
        effective,meta=resolve_profile_policy('Microsoft Paint',BASE,mode='Auto')
        self.assertEqual(effective['mode'],'Shape paths')
        self.assertEqual(effective['fill_engine'],'Closed regions v2')
        self.assertEqual(effective['background_fill'],'Balanced')
        self.assertEqual(effective['custom_color_workflow'],'Adaptive exact (recommended)')
        self.assertEqual(effective['exact_color_limit'],'Auto')
        self.assertEqual(effective['exact_color_limit_profile_ceiling'],32)
        self.assertEqual(effective['visual_verification'],'Strict')
        self.assertTrue(meta['applied'])

    def test_skribbl_fast_reduces_colors_strokes_and_time(self):
        effective,_=resolve_profile_policy('Skribbl.io Fast',BASE,mode='Auto')
        self.assertEqual(effective['exact_color_limit'],'Auto')
        self.assertEqual(effective['color_grouping'],'Reduced palette')
        self.assertEqual(effective['adaptive_detail'],'Strong simplify')
        self.assertEqual(effective['stroke_optimizer'],'Smart merge')
        self.assertEqual(effective['mode'],'Smart paths (recommended)')
        self.assertEqual(effective['custom_color_workflow'],'Calibrated palette')
        self.assertEqual(effective['time_budget_mode'],'Skribbl 60')
        self.assertEqual(effective['max_stroke_cap'],'1000')

    def test_skribbl_quality_keeps_more_detail(self):
        effective,_=resolve_profile_policy('Skribbl.io',BASE,mode='Auto')
        self.assertEqual(effective['exact_color_limit'],'Auto')
        self.assertEqual(effective['exact_color_limit_profile_ceiling'],18)
        self.assertEqual(effective['color_grouping'],'Smart')
        self.assertEqual(effective['adaptive_detail'],'Preserve detail')
        self.assertEqual(effective['quality'],'High detail')
        self.assertEqual(effective['time_budget_mode'],'Skribbl Default')

    def test_gartic_is_timer_aware(self):
        effective,_=resolve_profile_policy('Gartic.io',BASE,mode='Auto')
        self.assertEqual(effective['time_budget_mode'],'60 sec')
        self.assertEqual(effective['target_stroke_count'],'Auto')
        self.assertEqual(effective['progressive_rendering'],'On')
        self.assertEqual(effective['mode'],'Shape paths')

    def test_all_policy_values_match_renderer_enums(self):
        from ContinuousPaths import DRAWING_MODES
        from ShapePaths import SHAPE_MODEL_MODES, SHAPE_ORDERS, STROKE_CAPS
        from ProgressiveRenderer import PROGRESSIVE_RENDERING_MODES
        from PlanningWatchdog import PLANNING_WATCHDOG_MODES
        from TimeBudget import TIME_BUDGET_MODES, TARGET_STROKE_COUNTS
        from FillOptimizer import FILL_ENGINES
        from ColorGrouping import COLOR_GROUPING_MODES
        from StrokeOptimizer import STROKE_OPTIMIZER_MODES
        from AdaptiveDetail import ADAPTIVE_DETAIL_MODES
        from VisualVerification import VISUAL_VERIFICATION_MODES
        from AdvancedColor import COLOR_RENDERING_MODES, COLOR_LAYER_MODES, CUSTOM_COLOR_WORKFLOWS
        from DynamicColors import EXACT_COLOR_LIMITS
        from EdgeBehavior import EDGE_BEHAVIOR_MODES
        names=('Microsoft Paint','Skribbl.io Fast','Skribbl.io','Gartic.io','Gartic Phone','Sketchful.io','Drawize','Other drawing app')
        for name in names:
            o=policy_for(name)['overrides']
            self.assertIn(o['mode'],DRAWING_MODES);self.assertIn(o.get('shape_order','Fill first'),SHAPE_ORDERS)
            if 'shape_model' in o:self.assertIn(o['shape_model'],SHAPE_MODEL_MODES)
            if 'max_stroke_cap' in o:self.assertIn(o['max_stroke_cap'],STROKE_CAPS)
            self.assertIn(o['progressive_rendering'],PROGRESSIVE_RENDERING_MODES)
            self.assertIn(o['planning_watchdog'],PLANNING_WATCHDOG_MODES)
            self.assertIn(o['time_budget_mode'],TIME_BUDGET_MODES);self.assertIn(o['target_stroke_count'],TARGET_STROKE_COUNTS)
            if 'fill_engine' in o:self.assertIn(o['fill_engine'],FILL_ENGINES)
            self.assertIn(o['color_grouping'],COLOR_GROUPING_MODES);self.assertIn(o['stroke_optimizer'],STROKE_OPTIMIZER_MODES)
            self.assertIn(o['adaptive_detail'],ADAPTIVE_DETAIL_MODES);self.assertIn(o['visual_verification'],VISUAL_VERIFICATION_MODES)
            self.assertIn(o['color_rendering'],COLOR_RENDERING_MODES);self.assertIn(o['color_layers'],COLOR_LAYER_MODES)
            self.assertIn(o['custom_color_workflow'],CUSTOM_COLOR_WORKFLOWS);self.assertIn(o['exact_color_limit'],EXACT_COLOR_LIMITS)
            self.assertIn(o['edge_behavior'],EDGE_BEHAVIOR_MODES)

    def test_manual_settings_are_preserved(self):
        requested=dict(BASE);requested.update({'mode':'Dots','exact_color_limit':'32','time_budget_mode':'10 min'})
        effective,meta=resolve_profile_policy('Skribbl.io Fast',requested,mode='Manual settings')
        self.assertEqual(effective,requested)
        self.assertFalse(meta['applied']);self.assertEqual(meta['changed_count'],0)

    def test_policy_cannot_contain_native_safety_state(self):
        forbidden={'armed','mouse','target_lock','target_window','preflight','dry_run','start_authorization','corners','palette_positions','tool_actions'}
        for name in ('Microsoft Paint','Skribbl.io Fast','Skribbl.io','Gartic.io','Gartic Phone','Sketchful.io','Drawize','Other drawing app'):
            keys=set(policy_for(name)['overrides'])
            self.assertTrue(keys.isdisjoint(forbidden),f'{name}: {keys & forbidden}')

    def test_unknown_custom_profile_uses_generic_policy(self):
        generic=policy_for('Other drawing app')
        custom=policy_for('My custom profile')
        self.assertEqual(custom['overrides'],generic['overrides'])

    def test_ui_and_options_hooks_exist(self):
        ui=Path(__file__).with_name('StudioUI.py').read_text(encoding='utf-8')
        bot=Path(__file__).with_name('DrawBot.py').read_text(encoding='utf-8')
        self.assertIn("'Profile policy'",ui)
        self.assertIn("'Edge behavior'",ui)
        self.assertIn('resolve_profile_policy',bot)
        self.assertIn("'profile_policy_meta':profile_policy_meta",bot)

    def test_release_version(self):
        self.assertEqual(APP_VERSION,'1.0.124-beta')
        self.assertEqual(FILE_VERSION,'1.0.124')
        self.assertIn('Profile Engine v2',policy_summary('Microsoft Paint'))

if __name__=='__main__':unittest.main()
