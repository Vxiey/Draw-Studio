import unittest
from pathlib import Path

from GarticPhoneFastRenderer import optimize_gartic_phone_groups, build_gartic_execution_paths
from ProfileEngine import resolve_profile_policy


BASE={
    'mode':'Shape paths','shape_order':'Fill first','shape_model':'Better shapes v2','max_stroke_cap':'2500',
    'progressive_rendering':'On','planning_watchdog':'On','time_budget_mode':'90 sec','target_stroke_count':'Auto','target_stroke_custom':'2500',
    'render_style':'Auto','draw_quality':'Balanced','quality':'Balanced','speed':'Fast','precision':'Normal',
    'planning_resolution':'Standard','resource_scheduler':'Auto','background_fill':'Off','fill_engine':'Auto','background_simplification':'Strong',
    'color_grouping':'Reduced palette','color_workflow':'Finish color first','stroke_optimizer':'Smart merge','adaptive_detail':'Balanced','visual_verification':'Off',
    'color_rendering':'RGB nearest','color_layers':'Off','custom_color_workflow':'Adaptive exact (recommended)','exact_color_limit':'8','tool_strategy':'Auto','edge_behavior':'Hard Clip',
}


class GarticPhoneTurboTests(unittest.TestCase):
    def test_vertical_orientation_wins_for_column_structure(self):
        palette=[(0,0,0),(255,255,255)]
        groups=[[(5,y,5,y) for y in range(8)],[]]
        out,meta=optimize_gartic_phone_groups(groups,palette,max_colors=2,min_run=1,gap_join=0)
        self.assertEqual(meta['orientations']['0'],'vertical')
        self.assertEqual(out[0],[(5,0,5,7)])
        self.assertEqual(meta['vertical_wins'],1)

    def test_horizontal_orientation_wins_for_row_structure(self):
        palette=[(0,0,0),(255,255,255)]
        groups=[[(0,4,12,4)],[]]
        out,meta=optimize_gartic_phone_groups(groups,palette,max_colors=2,min_run=1,gap_join=0)
        self.assertEqual(meta['orientations']['0'],'horizontal')
        self.assertEqual(out[0],[(0,4,12,4)])

    def test_reduces_palette_but_keeps_dark_structure(self):
        palette=[(0,0,0),(255,0,0),(0,255,0),(0,0,255),(255,255,0),(255,0,255),(0,255,255),(120,120,120),(255,255,255)]
        groups=[[(0,i,8,i)] for i in range(8)] + [[]]
        out,meta=optimize_gartic_phone_groups(groups,palette,max_colors=4,min_run=1)
        self.assertLessEqual(sum(bool(g) for g in out),4)
        self.assertTrue(out[0])
        self.assertGreater(meta['remapped_colors'],0)

    def test_vertical_paths_are_executed_in_original_coordinate_space(self):
        groups=[[(5,0,5,6)]]
        paths=build_gartic_execution_paths(groups,{'0':'vertical'})
        self.assertTrue(paths[0])
        points=[p for path in paths[0] for p in path]
        self.assertTrue(all(x==5 for x,_ in points))
        self.assertEqual({y for _,y in points},{0,6})

    def test_profile_auto_enables_gartic_turbo_policy(self):
        effective,meta=resolve_profile_policy('Gartic Phone',BASE,mode='Auto')
        self.assertTrue(meta['applied'])
        self.assertEqual(effective['mode'],'Smart paths (recommended)')
        self.assertEqual(effective['custom_color_workflow'],'Calibrated palette')
        self.assertEqual(effective['progressive_rendering'],'Off')
        self.assertEqual(effective['adaptive_detail'],'Strong simplify')
        self.assertEqual(effective['time_budget_mode'],'60 sec')
        self.assertEqual(effective['max_stroke_cap'],'1000')

    def test_manual_settings_do_not_force_turbo(self):
        effective,meta=resolve_profile_policy('Gartic Phone',BASE,mode='Manual settings')
        self.assertFalse(meta['applied'])
        self.assertEqual(effective,BASE)


    def test_gartic_palette_preset_is_available(self):
        from PaletteMaps import PRESETS
        preset=PRESETS['gartic-phone']
        self.assertEqual(len(preset.colors),72)
        self.assertEqual(len(preset.names),72)
        self.assertEqual(preset.names[:3],('R1C1','R1C2','R1C3'))

    def test_drawbot_contains_gartic_turbo_hook(self):
        text=Path(__file__).with_name('DrawBot.py').read_text(encoding='utf-8')
        self.assertIn('optimize_gartic_phone_groups',text)
        self.assertIn("gartic_phone_direct_paths",text)
        self.assertIn("Gartic Phone Engine v2 runs",text)


if __name__=='__main__':
    unittest.main()
