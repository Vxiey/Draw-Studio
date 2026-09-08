import tempfile
import threading
import unittest
from pathlib import Path

from PIL import Image

from DrawBot import execute_plan, make_plan
from ScreenGuard import GuardedMouse
from PaintTools import build_tool_actions, load_tool_calibration, save_tool_calibration
from test_drawbot import Mouse, NoWait, options

ANCHOR={'version':1,'client_rect':[10,20,1010,720]}
CURRENT=(30,40,1030,740)  # translated +20,+20, same layout size


class PaintToolTests(unittest.TestCase):
    def test_tool_calibration_roundtrip_and_brush_dropdown_sequence(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'paint-tools.json'
            save_tool_calibration({'Pencil':(110,20),'Eraser':(120,20)},(50,400),path,
                                  anchor=ANCHOR,brush_menu=(100,20),brush_preset=(170,70))
            data=load_tool_calibration(path)
            self.assertEqual(data['tools']['Eraser'],[120,20])
            self.assertEqual(build_tool_actions('Brush',path,current_client_rect=CURRENT),[
                ('brush-menu',(120,40)),('brush-preset',(190,90)),('opacity',(70,420))])
            self.assertEqual(build_tool_actions('Eraser',path,current_client_rect=CURRENT),[('tool',(140,40))])

    def test_auto_prefers_pencil_without_touching_brush_opacity(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'paint-tools.json'
            save_tool_calibration({'Pencil':(110,20)},(50,400),path,anchor=ANCHOR,
                                  brush_menu=(100,20),brush_preset=(170,70))
            self.assertEqual(build_tool_actions('Auto (recommended)',path,current_client_rect=CURRENT),[
                ('tool',(130,40))])

    def test_auto_accepts_pencil_without_opacity_calibration(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'paint-tools.json'
            save_tool_calibration({'Pencil':(110,20)},None,path,anchor=ANCHOR)
            self.assertEqual(build_tool_actions('Auto (recommended)',path,current_client_rect=CURRENT),[('tool',(130,40))])

    def test_auto_requires_solid_calibration_when_pencil_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'paint-tools.json'
            save_tool_calibration({},None,path,anchor=ANCHOR,brush_menu=(100,20),brush_preset=(170,70))
            with self.assertRaisesRegex(ValueError,'Auto .* needs'):
                build_tool_actions('Auto (recommended)',path,current_client_rect=CURRENT)

    def test_uncalibrated_automatic_tool_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError,'Calibrate Paint tools'):
                build_tool_actions('Brush',Path(tmp)/'missing.json',current_client_rect=CURRENT)

    def test_resize_rejected_before_tool_clicks(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'paint-tools.json'
            save_tool_calibration({'Pencil':(110,20)},(50,400),path,anchor=ANCHOR)
            with self.assertRaisesRegex(ValueError,'layout changed size'):
                build_tool_actions('Pencil',path,current_client_rect=(30,40,1230,840))

    def test_brush_requires_concrete_preset_and_opacity(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'paint-tools.json'
            save_tool_calibration({},None,path,anchor=ANCHOR,brush_menu=(100,20))
            with self.assertRaisesRegex(ValueError,'Brush preset'):
                build_tool_actions('Brush',path,current_client_rect=CURRENT)
            save_tool_calibration({},None,path,anchor=ANCHOR,brush_menu=(100,20),brush_preset=(170,70))
            with self.assertRaisesRegex(ValueError,'100% opacity'):
                build_tool_actions('Brush',path,current_client_rect=CURRENT)

    def test_pencil_tool_is_selected_before_color_without_opacity_click(self):
        opts=dict(options(),tool_actions=[('tool',(900,20))],paint_tool='Pencil')
        plan=make_plan(Image.new('RGBA',(4,1),'black'),(40,10),opts)
        mouse=Mouse();mouse.verify_ink=lambda p,rgb:None
        execute_plan(plan,(100,100,40,10),[(800,30)]*18,mouse,NoWait(),threading.Event(),lambda *a:None)
        click_positions=[];current=None
        for action in mouse.actions:
            if action[0]=='move':current=action[1:]
            elif action[0]=='click':click_positions.append(current)
        self.assertEqual(click_positions[:2],[(900,20),(800,30)])

    def test_brush_menu_and_preset_are_selected_before_opacity_and_color(self):
        opts=dict(options(),tool_actions=[('brush-menu',(900,20)),('brush-preset',(850,80)),('opacity',(40,500))],paint_tool='Brush')
        plan=make_plan(Image.new('RGBA',(4,1),'black'),(40,10),opts)
        mouse=Mouse();mouse.verify_ink=lambda p,rgb:None
        execute_plan(plan,(100,100,40,10),[(800,30)]*18,mouse,NoWait(),threading.Event(),lambda *a:None)
        click_positions=[];current=None
        for action in mouse.actions:
            if action[0]=='move':current=action[1:]
            elif action[0]=='click':click_positions.append(current)
        self.assertEqual(click_positions[:4],[(900,20),(850,80),(40,500),(800,30)])

    def test_color_mismatch_stops_after_first_stroke_without_retry(self):
        opts=dict(options(),tool_actions=[('tool',(900,20))],paint_tool='Pencil')
        plan=make_plan(Image.new('RGBA',(12,1),'black'),(120,10),opts)
        mouse=Mouse();checks=[]
        def fail(point,rgb):
            checks.append((point,rgb));raise InterruptedError('wrong color; no automatic retry')
        mouse.verify_ink=fail
        with self.assertRaisesRegex(InterruptedError,'no automatic retry'):
            execute_plan(plan,(100,100,120,10),[(800,30)]*18,mouse,NoWait(),threading.Event(),lambda *a:None)
        self.assertEqual(len(checks),1)
        self.assertEqual(sum(a[0]=='press' for a in mouse.actions),1)
        click_positions=[];current=None
        for action in mouse.actions:
            if action[0]=='move':current=action[1:]
            elif action[0]=='click':click_positions.append(current)
        self.assertEqual(click_positions.count((800,30)),1)

    def test_segment_verifier_finds_offset_ink_away_from_midpoint(self):
        class SegmentMonitor:
            def verify(self,target,point):pass
            def colors_near(self,point,radius=2):
                # Only the 20% probe sees the dark rendered stroke. A midpoint-only
                # verifier would have falsely stopped.
                return [(8,8,8)] if point[0] < 40 else [(245,245,245)]
        guard=GuardedMouse(Mouse(),SegmentMonitor(),1)
        guard.verify_ink_segment((10,10),(110,10),(0,0,0),3)

    def test_first_stroke_patch_accepts_antialiased_edge_but_rejects_low_opacity(self):
        class PatchMonitor:
            def verify(self,target,point):pass
            def colors_near(self,point,radius=2):return [(245,245,245),(0,0,0),(120,120,120)]
        mouse=Mouse();guard=GuardedMouse(mouse,PatchMonitor(),1);guard.verify_ink((10,10),(0,0,0))
        class OpacityMonitor(PatchMonitor):
            def colors_near(self,point,radius=2):return [(51,51,51)]*25
        guard=GuardedMouse(mouse,OpacityMonitor(),1)
        with self.assertRaisesRegex(InterruptedError,'100%'):guard.verify_ink((10,10),(0,0,0))

    def test_eraser_plan_uses_single_mask_group_without_palette_click(self):
        opts=dict(options(),paint_current_color=True,erase_mode=True,paint_tool='Eraser',tool_actions=[('tool',(900,20))])
        plan=make_plan(Image.new('RGBA',(6,1),'black'),(60,10),opts)
        self.assertEqual(len(plan['groups']),1);self.assertTrue(plan['groups'][0])
        mouse=Mouse();execute_plan(plan,(100,100,60,10),[],mouse,NoWait(),threading.Event(),lambda *a:None)
        click_positions=[];current=None
        for action in mouse.actions:
            if action[0]=='move':current=action[1:]
            elif action[0]=='click':click_positions.append(current)
        self.assertIn((900,20),click_positions);self.assertNotIn((800,30),click_positions)


if __name__=='__main__':unittest.main()
