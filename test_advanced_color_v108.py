import unittest
from pathlib import Path
from PIL import Image, ImageDraw

from LocalSanitization import safe_context
from AdvancedColor import (COLOR_LAYER_MODES, COLOR_RENDERING_MODES,
                           build_color_strokes, best_layer_for_rgb,
                           closest_palette_index, suggested_color_workflow,
                           validate_color_layers, validate_color_rendering,
                           validate_custom_color_workflow)
from DrawBot import make_plan


def opts(**changes):
    base=dict(detail=9,delay=.005,speed='Balanced',precision='High',lines=True,
              render_style='Standard / pixel',draw_quality='High likeness',human_mode='Subtle',
              gpu_mode='CPU',gpu_vram='Auto',gpu_performance='Balanced',background_fill='Off',
              background_simplification='Off',color_grouping='Smart',color_rendering='Perceptual match',
              color_layers='Off',custom_color_workflow='Calibrated palette',tool_strategy='Auto',
              portrait_focus=True,skip_white=True,contrast=1.0,outline=False,brush_px=1,max_seconds=600,
              paint_current_color=False,erase_mode=False,paint_tool='Use current tool',effective_paint_tool='Use current tool',
              tool_actions=[],fill_tool_available=False,fill_tool_actions=[],fill_restore_actions=[])
    base.update(changes);return base


class AdvancedColorV108Tests(unittest.TestCase):
    def test_modes_validate(self):
        for mode in COLOR_RENDERING_MODES:self.assertEqual(validate_color_rendering(mode),mode)
        for mode in COLOR_LAYER_MODES:self.assertEqual(validate_color_layers(mode),mode)
        for mode in ('Calibrated palette','Custom colors first','Custom colors only'):
            self.assertEqual(validate_custom_color_workflow(mode),mode)
        with self.assertRaises(ValueError):validate_color_rendering('AI color')
        with self.assertRaises(ValueError):validate_color_layers('Unsafe')
        with self.assertRaises(ValueError):validate_custom_color_workflow('Hidden')

    def test_perceptual_match_returns_palette_index(self):
        index=closest_palette_index((205,88,84),color_rendering='Perceptual match')
        self.assertIsInstance(index,int)
        self.assertGreaterEqual(index,0)

    def test_layered_mix_finds_secondary_for_missing_colour(self):
        primary,secondary,ratio,improvement=best_layer_for_rgb((128,85,60),color_rendering='Layered color mix',color_layers='Full color mix')
        self.assertIsInstance(primary,int)
        self.assertTrue(secondary is None or isinstance(secondary,int))
        self.assertGreaterEqual(ratio,0.0)
        self.assertGreaterEqual(improvement,0.0)

    def test_layered_build_adds_metadata_and_can_add_overlay_strokes(self):
        image=Image.new('RGBA',(32,24),(128,85,60,255))
        groups,meta=build_color_strokes(image,lines=False,skip_white=True,color_rendering='Layered color mix',color_layers='Full color mix')
        self.assertIsInstance(groups,list)
        self.assertEqual(meta['color_rendering'],'Layered color mix')
        self.assertEqual(meta['color_layers'],'Full color mix')
        self.assertIn('layered_pixels',meta)
        self.assertGreater(sum(len(g) for g in groups),0)

    def test_make_plan_records_advanced_color_metadata(self):
        image=Image.new('RGBA',(90,60),(128,85,60,255));draw=ImageDraw.Draw(image)
        draw.rectangle((20,10,70,50),fill=(38,201,201,255))
        plan=make_plan(image,(360,240),opts(color_rendering='Layered color mix',color_layers='Dual-color mix'))
        meta=plan['options']['advanced_color_meta']
        self.assertEqual(meta['color_rendering'],'Layered color mix')
        self.assertEqual(meta['color_layers'],'Dual-color mix')
        self.assertGreater(plan['count'],0)

    def test_safe_bug_report_context_includes_new_settings_only(self):
        cleaned=safe_context({'color_rendering':'Layered color mix','color_layers':'Dual-color mix','custom_color_workflow':'Custom colors first','palette_position':'1,2'})
        self.assertEqual(cleaned['color_rendering'],'Layered color mix')
        self.assertEqual(cleaned['color_layers'],'Dual-color mix')
        self.assertEqual(cleaned['custom_color_workflow'],'Custom colors first')
        self.assertNotIn('palette_position',cleaned)

    def test_release_build_collects_new_module_and_doc(self):
        source=(Path(__file__).resolve().parent/'build_exe.py').read_text(encoding='utf-8')
        self.assertIn("'--hidden-import', 'AdvancedColor'",source)
        self.assertNotIn('ADVANCED-COLOR-v1.0.8.md',source)

    def test_ui_exposes_advanced_color_controls(self):
        source=(Path(__file__).resolve().parent/'StudioUI.py').read_text(encoding='utf-8')
        for label in ('Color rendering','Color layers','Custom color workflow'):
            self.assertIn(label,source)

    def test_suggested_workflow_responds_to_large_custom_palette(self):
        self.assertIn('Custom colors first',suggested_color_workflow(32))
        self.assertIn('Calibrated palette',suggested_color_workflow(18))


if __name__=='__main__':unittest.main()
