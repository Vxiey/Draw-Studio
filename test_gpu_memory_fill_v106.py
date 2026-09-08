import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

import GpuAcceleration as ga
from AppTools import save_calibration, load_calibration, build_tool_action
from CalibrationAnchors import make_anchor
from FillOptimizer import detect_background
from DrawBot import make_plan


class GpuMemoryAndFillV106Tests(unittest.TestCase):
    def test_workspace_planner_uses_full_frame_when_budget_allows(self):
        info=ga.AccelerationInfo('Auto','CUDA',True,'GPU',total_vram_mb=8192,free_vram_mb=7000,vram_budget_mb=4096)
        plan=ga.plan_vram_allocation(info,800,600,arrays=8)
        self.assertEqual(plan['mode'],'full')
        self.assertEqual(plan['tile_rows'],600)
        self.assertGreater(plan['workspace_mb'],0)

    def test_workspace_planner_tiles_when_budget_is_small(self):
        info=ga.AccelerationInfo('Auto','CUDA',True,'GPU',total_vram_mb=1024,free_vram_mb=900,vram_budget_mb=128)
        plan=ga.plan_vram_allocation(info,5000,4000,arrays=12)
        self.assertEqual(plan['mode'],'tiled')
        self.assertLess(plan['tile_rows'],4000)
        self.assertGreaterEqual(plan['tile_rows'],16)

    def test_tile_ranges_cover_image_once_in_core_rows(self):
        ranges=list(ga._tile_ranges(101,24,4))
        covered=[]
        for start,end,read0,read1,core0,core1 in ranges:
            self.assertLessEqual(read0,start)
            self.assertGreaterEqual(read1,end)
            self.assertEqual(end-start,core1-core0)
            covered.extend(range(start,end))
        self.assertEqual(covered,list(range(101)))

    def test_advanced_scaler_cpu_fallback_keeps_exact_target_size(self):
        image=Image.new('L',(333,211),128)
        out,info=ga.resize_gray_advanced(image,(137,89),'CPU','Auto','Balanced')
        self.assertEqual(out.size,(137,89))
        self.assertFalse(info.accelerated)
        self.assertIn('Lanczos',info.scaler)

    def test_green_background_is_detected_for_fill(self):
        image=Image.new('RGB',(120,80),(17,176,60))
        draw=ImageDraw.Draw(image);draw.rectangle((30,20,90,65),fill=(255,120,41))
        result=detect_background(image,'Auto')
        self.assertTrue(result.enabled)
        self.assertGreater(result.border_confidence,.95)
        self.assertGreater(result.image_coverage,.50)
        self.assertIsNotNone(result.color_index)

    def test_mixed_border_is_not_auto_filled(self):
        image=Image.new('RGB',(80,80),'white');draw=ImageDraw.Draw(image)
        draw.rectangle((0,0,39,79),fill=(17,176,60));draw.rectangle((40,0,79,79),fill=(255,120,41))
        result=detect_background(image,'Auto')
        self.assertFalse(result.enabled)

    def test_make_plan_removes_base_background_strokes_when_fill_available(self):
        image=Image.new('RGBA',(120,80),(17,176,60,255));draw=ImageDraw.Draw(image)
        draw.rectangle((35,20,85,60),fill=(255,120,41,255))
        options=dict(detail=8,delay=.005,speed='Balanced',precision='High',lines=True,
                     render_style='Standard / pixel',draw_quality='High likeness',human_mode='Subtle',gpu_mode='CPU',
                     gpu_vram='Auto',gpu_performance='Balanced',background_fill='Auto',portrait_focus=True,
                     skip_white=True,contrast=1.0,outline=False,brush_px=1,max_seconds=180,
                     paint_current_color=False,erase_mode=False,paint_tool='Use current tool',tool_actions=[],
                     fill_tool_available=True,fill_tool_actions=[('fill',(10,10))],fill_restore_actions=[('brush',(20,20))])
        plan=make_plan(image,(600,400),options)
        fill=plan['options'].get('background_fill_plan')
        self.assertTrue(fill and fill['enabled'])
        self.assertEqual(plan['groups'][fill['color_index']],[])
        self.assertGreater(plan['count'],0)

    def test_generic_tool_calibration_is_profile_anchored_and_translates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'tools.json'
            anchor=make_anchor((100,100,900,700))
            save_calibration('skribbl',{'Brush':(140,150),'Fill':(170,150)},anchor=anchor,path=path)
            loaded=load_calibration('skribbl',path)
            self.assertIn('Fill',loaded['tools'])
            kind,point=build_tool_action('skribbl','Fill',(120,130,920,730),path)
            self.assertEqual(kind,'fill')
            self.assertEqual(point,(190,180))

    def test_paint_fill_can_be_calibrated_as_direct_tool(self):
        from PaintTools import save_tool_calibration, load_tool_calibration, build_tool_actions
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'paint-tools.json'
            anchor=make_anchor((100,100,900,700))
            save_tool_calibration({'Pencil':(140,150),'Fill':(190,150)},(700,150),path,anchor=anchor)
            data=load_tool_calibration(path)
            self.assertIn('Fill',data['tools'])
            actions=build_tool_actions('Fill',path,current_client_rect=(120,130,920,730))
            self.assertEqual(actions,[('tool',(210,180))])

    def test_white_background_does_not_waste_a_fill_operation(self):
        image=Image.new('RGB',(100,70),'white')
        result=detect_background(image,'Auto')
        self.assertFalse(result.enabled)
        self.assertIn('white',result.reason.lower())

    def test_release_build_collects_new_tool_modules(self):
        source=(Path(__file__).resolve().parent/'build_exe.py').read_text(encoding='utf-8')
        self.assertIn("'--hidden-import', 'FillOptimizer'",source)
        self.assertIn("'--hidden-import', 'AppTools'",source)
        self.assertIn("'--hidden-import', 'AppToolCalibration'",source)

    def test_bug_report_allows_background_fill_setting_only(self):
        from LocalSanitization import safe_context
        cleaned=safe_context({'background_fill':'Auto','unsafe_fill_coordinate':'10,20'})
        self.assertEqual(cleaned.get('background_fill'),'Auto')
        self.assertNotIn('unsafe_fill_coordinate',cleaned)


if __name__=='__main__':
    unittest.main()
