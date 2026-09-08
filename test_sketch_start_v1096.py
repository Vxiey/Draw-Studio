import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from PIL import Image,ImageDraw
from DrawBot import DrawBotApp,make_plan

class SketchStartTests(unittest.TestCase):
    def test_saved_subject_modes_cannot_block_sketch(self):
        im=Image.new('RGB',(80,80),'white');ImageDraw.Draw(im).ellipse((10,10,60,60),fill='red')
        for focus in ('Subject first','Subject only'):
            options=dict(outline=True,subject_focus=focus,draw_quality='Pixel Accurate',detail=8,
                         delay=.01,contrast=1,lines=True,brush_px=1,max_seconds=180,gpu_mode='CPU')
            plan=make_plan(im,(100,100),options)
            self.assertGreater(plan['count'],0)
            self.assertTrue(plan['options']['black_sketch'])
            self.assertEqual(plan['options']['subject_focus'],'Off')
            self.assertEqual(options['subject_focus'],focus)

    def test_subject_selection_keeps_sketch_and_does_not_change_quality(self):
        app=SimpleNamespace(outline=Mock(),subject_focus=Mock(),status=Mock(),
                            options_changed=Mock(),draw_quality=Mock(),brush_px=Mock())
        app.outline.get.return_value=True;app.subject_focus.get.return_value='Subject first'
        DrawBotApp.subject_focus_changed(app)
        app.subject_focus.set.assert_called_once_with('Off')
        app.outline.set.assert_not_called()
        app.draw_quality.set.assert_not_called()
        app.options_changed.assert_called_once()

    def test_subject_still_works_when_sketch_off(self):
        app=SimpleNamespace(outline=Mock(),subject_focus=Mock(),status=Mock(),
                            options_changed=Mock(),draw_quality=Mock(),brush_px=Mock())
        app.outline.get.return_value=False;app.subject_focus.get.return_value='Subject first'
        DrawBotApp.subject_focus_changed(app)
        app.draw_quality.set.assert_called_once_with('Pixel Accurate')
        app.subject_focus.set.assert_not_called()
