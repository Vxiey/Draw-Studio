import unittest
from pathlib import Path
from PIL import Image, ImageDraw

from FillOptimizer import (detect_fill_regions, remove_filled_region_strokes,
                           simplify_background, validate_background_fill)
from ColorGrouping import group_palette_strokes
from SmartTools import choose_paint_tool
from DrawBot import make_plan


def opts(**changes):
    base=dict(detail=9,delay=.005,speed='Balanced',precision='High',lines=True,
              render_style='Standard / pixel',draw_quality='High likeness',human_mode='Subtle',
              gpu_mode='CPU',gpu_vram='Auto',gpu_performance='Balanced',background_fill='Balanced',
              background_simplification='Balanced',color_grouping='Smart',tool_strategy='Auto',
              portrait_focus=True,skip_white=True,contrast=1.0,outline=False,brush_px=1,max_seconds=600,
              paint_current_color=False,erase_mode=False,paint_tool='Use current tool',effective_paint_tool='Use current tool',
              tool_actions=[],fill_tool_available=True,fill_tool_actions=[('fill',(10,10))],fill_restore_actions=[('brush',(20,20))])
    base.update(changes);return base


class AutoFillSmartToolsV107Tests(unittest.TestCase):
    def test_fill_modes_validate_and_legacy_auto_remains_readable(self):
        for mode in ('Auto','Off','Conservative','Balanced','Aggressive'):
            self.assertEqual(validate_background_fill(mode),mode)
        with self.assertRaises(ValueError):validate_background_fill('Unsafe')

    def test_large_interior_rectangle_is_safe_fill_candidate(self):
        image=Image.new('RGB',(90,70),'white');draw=ImageDraw.Draw(image)
        draw.rectangle((20,15,70,55),fill=(255,120,41))
        regions=detect_fill_regions(image,'Balanced')
        self.assertTrue(regions)
        region=regions[0]
        self.assertEqual(region.bbox,(20,15,70,55))
        self.assertEqual(region.rgb,(255,120,41))
        self.assertGreaterEqual(region.bbox_density,.99)
        self.assertGreater(region.estimated_saved_strokes,10)

    def test_border_touching_component_is_not_interior_fill(self):
        image=Image.new('RGB',(80,60),'white');draw=ImageDraw.Draw(image)
        draw.rectangle((0,10,50,50),fill=(255,120,41))
        self.assertEqual(detect_fill_regions(image,'Balanced'),[])

    def test_irregular_component_is_rejected_in_balanced_mode(self):
        image=Image.new('RGB',(80,60),'white');draw=ImageDraw.Draw(image)
        draw.rectangle((15,10,60,18),fill=(255,120,41));draw.rectangle((15,18,24,50),fill=(255,120,41))
        self.assertEqual(detect_fill_regions(image,'Balanced',engine='Safe rectangles'),[])

    def test_remove_filled_rectangle_splits_horizontal_runs(self):
        from FillOptimizer import FillRegionPlan
        groups=[[(0,5,20,5)]]
        region=FillRegionPlan(0,(0,0,0),(5,2,15,8),(10,5),70,1.0,8)
        result=remove_filled_region_strokes(groups,[region])
        self.assertEqual(result[0],[(0,5,4,5),(16,5,20,5)])

    def test_background_simplification_is_border_connected(self):
        image=Image.new('RGB',(70,50),(20,170,62));draw=ImageDraw.Draw(image)
        # small JPEG-like background variations
        for x in range(0,70,5):draw.point((x,0),fill=(25,174,66))
        draw.rectangle((20,12,50,40),fill=(255,120,41))
        out,meta=simplify_background(image,'Balanced')
        self.assertTrue(meta.enabled)
        self.assertGreater(meta.coverage,.4)
        self.assertEqual(out.getpixel((35,25)),(255,120,41))

    def test_smart_grouping_does_not_change_exact_colors(self):
        groups=[[(0,0,20,0)],[(0,1,2,1)],[]]
        palette=((0,0,0),(255,0,0),(0,255,0))
        result,order,meta=group_palette_strokes(groups,palette,'Smart')
        self.assertEqual(result,groups)
        self.assertEqual(order,[0,1])
        self.assertEqual(meta['merged_colors'],0)

    def test_reduced_palette_can_merge_rare_near_color(self):
        groups=[[(0,0,100,0)],[(0,1,2,1)]]
        palette=((100,100,100),(112,108,105))
        result,order,meta=group_palette_strokes(groups,palette,'Reduced palette')
        self.assertEqual(meta['merged_colors'],1)
        self.assertFalse(result[1])
        self.assertEqual(order,[0])

    def test_smart_tool_prefers_pencil_for_portrait(self):
        calibration={'opacity_100':[1,1],'tools':{'Pencil':[2,2]},'brush_menu':[3,3],'brush_preset':[4,4]}
        self.assertEqual(choose_paint_tool('Auto (recommended)','Auto',calibration,portrait=True,brush_px=1),'Pencil')
        self.assertEqual(choose_paint_tool('Auto (recommended)','Speed first',calibration,portrait=True,brush_px=1),'Brush')

    def test_explicit_tool_is_never_overridden(self):
        self.assertEqual(choose_paint_tool('Pencil','Speed first',{},portrait=False,brush_px=5),'Pencil')

    def test_make_plan_uses_region_fill_and_reduces_strokes(self):
        image=Image.new('RGBA',(180,120),'white');draw=ImageDraw.Draw(image)
        draw.rectangle((40,25,140,95),fill=(255,120,41,255))
        with_fill=make_plan(image,(720,480),opts())
        without=make_plan(image,(720,480),opts(background_fill='Off',background_simplification='Off'))
        self.assertTrue(with_fill['options'].get('fill_regions'))
        self.assertLess(with_fill['count'],without['count'])

    def test_plan_records_background_and_color_metadata(self):
        image=Image.new('RGBA',(120,80),(17,176,60,255));draw=ImageDraw.Draw(image)
        draw.rectangle((35,20,85,60),fill=(255,120,41,255))
        plan=make_plan(image,(600,400),opts())
        self.assertIn('background_simplification_meta',plan['options'])
        self.assertIn('color_grouping_meta',plan['options'])
        self.assertEqual(plan['options']['color_grouping_meta']['mode'],'Smart')

    def test_release_build_collects_new_modules_and_doc(self):
        source=(Path(__file__).resolve().parent/'build_exe.py').read_text(encoding='utf-8')
        self.assertIn("'--hidden-import', 'ColorGrouping'",source)
        self.assertIn("'--hidden-import', 'SmartTools'",source)
        self.assertNotIn('AUTO-FILL-SMART-TOOLS-v1.0.7.md',source)

    def test_ui_exposes_v107_controls(self):
        source=(Path(__file__).resolve().parent/'StudioUI.py').read_text(encoding='utf-8')
        for label in ('Auto Fill','Background simplification','Color grouping','Tool strategy'):
            self.assertIn(label,source)

    def test_bug_report_accepts_only_safe_new_settings(self):
        from LocalSanitization import safe_context
        cleaned=safe_context({'background_simplification':'Balanced','color_grouping':'Smart','tool_strategy':'Auto','fill_seed':'10,20'})
        self.assertEqual(cleaned['background_simplification'],'Balanced')
        self.assertEqual(cleaned['color_grouping'],'Smart')
        self.assertEqual(cleaned['tool_strategy'],'Auto')
        self.assertNotIn('fill_seed',cleaned)

    def test_fill_guard_detects_outside_change(self):
        from ScreenGuard import GuardedMouse
        class Mouse:
            def __init__(self):self.pos=(5,5)
            def get_position(self):return self.pos
            def move(self,x,y):self.pos=(x,y)
            def press(self):pass
            def release(self):pass
        class Monitor:
            def __init__(self):self.changed=False
            def verify(self,target,point):pass
            def color(self,point):return (220,20,20) if self.changed else (255,255,255)
        monitor=Monitor();guard=GuardedMouse(Mouse(),monitor,1)
        points=[(5,5),(6,6)];before=guard.snapshot_colors(points)
        monitor.changed=True
        with self.assertRaises(InterruptedError):guard.verify_unchanged(points,before)


if __name__=='__main__':unittest.main()
